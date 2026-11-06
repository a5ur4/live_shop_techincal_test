"""Login, refresh token (com rotação) e logout. Ver docs/adr/0007."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import EntradaInvalidaError, ErroDetalhe, NaoAutenticadoError
from app.core.redis import ResilientRedis
from app.core.security import TipoConta, criar_token, gerar_hash_senha, verificar_senha
from app.models import Cliente, Loja, RefreshToken
from app.schemas import TokenOut
from app.services import rate_limit

settings = get_settings()

_MODELOS = {"cliente": Cliente, "loja": Loja}


def _hash(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode()).hexdigest()


def _refresh_invalido() -> NaoAutenticadoError:
    return NaoAutenticadoError(
        "Refresh token inválido, expirado ou revogado.", codigo="refresh_invalido"
    )


async def _emitir(
    session: AsyncSession, tipo: TipoConta, conta_id: int, familia: uuid.UUID | None = None
) -> TokenOut:
    """Gera access token (JWT) + refresh token (opaco) e grava o hash do refresh."""
    acesso = criar_token(tipo, conta_id)
    refresh = secrets.token_urlsafe(32)
    validade = timedelta(days=settings.refresh_expira_dias)
    session.add(
        RefreshToken(
            tipo=tipo,
            conta_id=conta_id,
            token_hash=_hash(refresh),
            familia=familia or uuid.uuid4(),
            expira_em=datetime.now(UTC) + validade,
        )
    )
    await session.commit()
    return TokenOut(
        access_token=acesso.access_token,
        expires_in=acesso.expires_in,
        refresh_token=refresh,
        refresh_expires_in=int(validade.total_seconds()),
    )


async def autenticar(
    session: AsyncSession,
    redis: ResilientRedis,
    tipo: TipoConta,
    email: str,
    senha: str,
    ip: str,
) -> TokenOut:
    email = email.strip().lower()
    await rate_limit.verificar(redis, tipo, email, ip)

    modelo = _MODELOS[tipo]
    conta = await session.scalar(select(modelo).where(modelo.email == email))
    # Mesma resposta (e mesmo custo de verificação) para e-mail inexistente e senha errada.
    if not verificar_senha(senha, conta.senha_hash if conta else None):
        await rate_limit.registrar_falha(redis, tipo, email, ip)
        raise NaoAutenticadoError("E-mail ou senha incorretos.", codigo="credenciais_invalidas")

    await rate_limit.limpar(redis, tipo, email)
    return await _emitir(session, tipo, conta.id)


async def renovar(session: AsyncSession, refresh_token: str) -> TokenOut:
    """Troca um refresh válido por um novo par de tokens (rotação).

    O UPDATE ... WHERE revogado_em IS NULL é atômico: se dois pedidos usarem o mesmo
    token ao mesmo tempo, só um consegue; o outro é tratado como reuso.
    """
    token_hash = _hash(refresh_token)
    agora = datetime.now(UTC)
    usado = (
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revogado_em.is_(None),
                RefreshToken.expira_em > agora,
            )
            .values(revogado_em=agora)
            .returning(RefreshToken.tipo, RefreshToken.conta_id, RefreshToken.familia)
        )
    ).first()
    if usado is not None:
        return await _emitir(session, usado.tipo, usado.conta_id, usado.familia)

    existente = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if existente is not None and existente.revogado_em is not None:
        # Reuso de token já trocado: sinal de vazamento. Derruba a sessão inteira.
        await _revogar_familia(session, existente.familia)
    raise _refresh_invalido()


async def _revogar_familia(session: AsyncSession, familia: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.familia == familia, RefreshToken.revogado_em.is_(None))
        .values(revogado_em=datetime.now(UTC))
    )
    await session.commit()


async def logout(session: AsyncSession, refresh_token: str) -> None:
    """Revoga a sessão (família) do refresh informado. Idempotente: token desconhecido é ok."""
    familia = await session.scalar(
        select(RefreshToken.familia).where(RefreshToken.token_hash == _hash(refresh_token))
    )
    if familia is not None:
        await _revogar_familia(session, familia)


async def revogar_todos(session: AsyncSession, tipo: TipoConta, conta_id: int) -> None:
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.tipo == tipo,
            RefreshToken.conta_id == conta_id,
            RefreshToken.revogado_em.is_(None),
        )
        .values(revogado_em=datetime.now(UTC))
    )


async def trocar_senha(
    session: AsyncSession, tipo: TipoConta, conta_id: int, senha_atual: str, nova_senha: str
) -> None:
    """Exige a senha atual (um access token roubado não basta) e encerra as outras sessões."""
    conta = await session.get(_MODELOS[tipo], conta_id)
    if conta is None or not verificar_senha(senha_atual, conta.senha_hash):
        raise EntradaInvalidaError(
            "Dados de entrada inválidos.",
            detalhes=[ErroDetalhe(campo="senha_atual", mensagem="Senha atual incorreta.")],
        )
    conta.senha_hash = gerar_hash_senha(nova_senha)
    # Refresh tokens existentes deixam de valer; access tokens expiram sozinhos (curtos).
    await revogar_todos(session, tipo, conta_id)
    await session.commit()
