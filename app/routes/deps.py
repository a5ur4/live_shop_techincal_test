from typing import Annotated

from fastapi import Depends, Path, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AcessoNegadoError, NaoAutenticadoError
from app.core.redis import ResilientRedis, get_redis
from app.core.security import Identidade, TipoConta, ler_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[ResilientRedis, Depends(get_redis)]

ClienteId = Annotated[int, Path(description="Id do cliente.", examples=[1])]
LojaId = Annotated[int, Path(description="Id da loja.", examples=[1])]

# Paginação comum a todas as listas (ver docs/adr/0006).
LIMITE_PADRAO = 20
LIMITE_MAXIMO = 50
Limite = Annotated[int, Query(ge=1, le=LIMITE_MAXIMO, description="Quantidade de itens (1 a 50).")]
Cursor = Annotated[
    str | None, Query(max_length=200, description="`proximo_cursor` da página anterior.")
]

# auto_error=False: sem token, quem responde é NaoAutenticadoError, no formato padrão.
_oauth2_cliente = OAuth2PasswordBearer(
    tokenUrl="/auth/clientes/token",
    scheme_name="Cliente",
    description="Login de cliente: e-mail e senha do cadastro em POST /clientes.",
    auto_error=False,
)
_oauth2_loja = OAuth2PasswordBearer(
    tokenUrl="/auth/lojas/token",
    scheme_name="Lojista",
    description="Login de lojista: e-mail e senha do cadastro em POST /lojas.",
    auto_error=False,
)


def _identidade(token: str | None, tipo: TipoConta) -> Identidade:
    if not token:
        raise NaoAutenticadoError("Token de acesso ausente.")
    identidade = ler_token(token)
    if identidade is None:
        raise NaoAutenticadoError("Token inválido ou expirado.")
    if identidade.tipo != tipo:
        raise AcessoNegadoError(f"Este endpoint exige login de {tipo}.")
    return identidade


async def _exigir_cliente_dono(
    cliente_id: ClienteId, token: Annotated[str | None, Depends(_oauth2_cliente)]
) -> int:
    """Os ids continuam na rota (enunciado); o token precisa ser do mesmo cliente."""
    if _identidade(token, "cliente").id != cliente_id:
        raise AcessoNegadoError("Este token não dá acesso a este cliente.")
    return cliente_id


async def _exigir_loja_dona(
    loja_id: LojaId, token: Annotated[str | None, Depends(_oauth2_loja)]
) -> int:
    if _identidade(token, "loja").id != loja_id:
        raise AcessoNegadoError("Este token não dá acesso a esta loja.")
    return loja_id


# Use no lugar de ClienteId/LojaId nas rotas protegidas: valida token e dono numa linha.
ClienteAutenticado = Annotated[int, Depends(_exigir_cliente_dono)]
LojaAutenticada = Annotated[int, Depends(_exigir_loja_dona)]


# --- Rotas /me: a conta vem do token, não da URL ---------------------------------


async def _cliente_atual(token: Annotated[str | None, Depends(_oauth2_cliente)]) -> int:
    return _identidade(token, "cliente").id


async def _loja_atual(token: Annotated[str | None, Depends(_oauth2_loja)]) -> int:
    return _identidade(token, "loja").id


async def _conta_atual(
    token_cliente: Annotated[str | None, Depends(_oauth2_cliente)],
    token_loja: Annotated[str | None, Depends(_oauth2_loja)],
) -> Identidade:
    # Os dois esquemas leem o mesmo header; declarar ambos faz o OpenAPI aceitar
    # qualquer um deles (requisitos alternativos) nesta rota.
    token = token_cliente or token_loja
    if not token:
        raise NaoAutenticadoError("Token de acesso ausente.")
    identidade = ler_token(token)
    if identidade is None:
        raise NaoAutenticadoError("Token inválido ou expirado.")
    return identidade


ClienteAtual = Annotated[int, Depends(_cliente_atual)]
LojaAtual = Annotated[int, Depends(_loja_atual)]
ContaAtual = Annotated[Identidade, Depends(_conta_atual)]
