"""Perfil da conta logada (cliente ou lojista): consultar, editar e excluir. Ver docs/adr/0009."""

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflitoError
from app.core.redis import ResilientRedis
from app.core.security import TipoConta
from app.models import Cliente, Loja, RefreshToken
from app.schemas import ContaEditar
from app.services import auth, cache_feed
from app.services.clientes import obter_cliente
from app.services.lojas import obter_loja


async def obter_conta(session: AsyncSession, tipo: TipoConta, conta_id: int) -> Cliente | Loja:
    if tipo == "cliente":
        return await obter_cliente(session, conta_id)
    return await obter_loja(session, conta_id)


async def editar_conta(
    session: AsyncSession, tipo: TipoConta, conta_id: int, dados: ContaEditar
) -> Cliente | Loja:
    conta = await obter_conta(session, tipo, conta_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(conta, campo, valor)
    try:
        await session.commit()
    except IntegrityError as exc:
        # O único UNIQUE que a edição pode violar é o do e-mail; o banco decide, sem corrida.
        await session.rollback()
        raise ConflitoError(
            f"Já existe um cadastro com o e-mail {dados.email}.", codigo="email_ja_cadastrado"
        ) from exc
    return conta


async def excluir_conta(
    session: AsyncSession, redis: ResilientRedis, tipo: TipoConta, conta_id: int, senha: str
) -> None:
    """Exclusão definitiva, confirmada pela senha.

    O banco apaga em cascata o que depende da conta (seguidores; numa loja, também as
    novidades). Refresh tokens não têm FK (apontam para duas tabelas) e são apagados aqui,
    na mesma transação. Ids vêm de IDENTITY e nunca são reaproveitados, então um access
    token ainda válido da conta excluída não passa a valer para outra conta.
    """
    conta = await obter_conta(session, tipo, conta_id)
    auth.conferir_senha(conta, senha, "senha")

    await session.execute(
        delete(RefreshToken).where(RefreshToken.tipo == tipo, RefreshToken.conta_id == conta_id)
    )
    await session.delete(conta)
    await session.commit()
    if tipo == "cliente":
        await cache_feed.invalidar(redis, conta_id)
