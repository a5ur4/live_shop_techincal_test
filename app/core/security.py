"""Hash de senha (argon2) e emissão/validação de JWT. Ver docs/adr/0007."""

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TipoConta = Literal["cliente", "loja"]

settings = get_settings()

if settings.jwt_secret:
    _segredo = settings.jwt_secret
else:
    logger.warning("JWT_SECRET não definido: usando chave aleatória (apenas desenvolvimento).")
    _segredo = secrets.token_urlsafe(32)

# Argon2id com os parâmetros recomendados pelo pwdlib. Os testes trocam por um hasher
# mais barato (tests/conftest.py) para não gastar segundos por cadastro.
hasher = PasswordHash.recommended()

# Hash de uma senha qualquer: usado no login de e-mail inexistente para que a resposta
# leve o mesmo tempo que uma senha errada (não revela quais e-mails existem).
_HASH_FICTICIO = hasher.hash(secrets.token_urlsafe(16))


def gerar_hash_senha(senha: str) -> str:
    return hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    if senha_hash is None:
        hasher.verify(senha, _HASH_FICTICIO)
        return False
    try:
        return hasher.verify(senha, senha_hash)
    except Exception:  # hash corrompido ou de algoritmo desconhecido
        return False


@dataclass(frozen=True)
class Token:
    access_token: str
    expires_in: int


@dataclass(frozen=True)
class Identidade:
    tipo: TipoConta
    id: int


def criar_token(tipo: TipoConta, conta_id: int, expira_em: timedelta | None = None) -> Token:
    validade = expira_em or timedelta(minutes=settings.jwt_expira_minutos)
    agora = datetime.now(UTC)
    payload = {"sub": str(conta_id), "tipo": tipo, "iat": agora, "exp": agora + validade}
    token = jwt.encode(payload, _segredo, algorithm=settings.jwt_algoritmo)
    return Token(access_token=token, expires_in=int(validade.total_seconds()))


def ler_token(token: str) -> Identidade | None:
    """Devolve a identidade do token, ou None se for inválido, expirado ou malformado."""
    try:
        payload = jwt.decode(
            token,
            _segredo,
            algorithms=[settings.jwt_algoritmo],
            options={"require": ["sub", "tipo", "exp"]},
        )
        tipo, conta_id = payload["tipo"], int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
    if tipo not in ("cliente", "loja"):
        return None
    return Identidade(tipo=tipo, id=conta_id)
