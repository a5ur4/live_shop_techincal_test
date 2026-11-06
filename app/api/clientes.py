from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import SessionDep
from app.core.errors import respostas_erro
from app.schemas import ClienteCriar, ClienteOut, FeedOut, SeguindoOut
from app.services import clientes as service
from app.services import feed as feed_service

router = APIRouter(prefix="/clientes", tags=["Clientes"])

LIMITE_PADRAO = 20
LIMITE_MAXIMO = 50


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ClienteOut,
    responses=respostas_erro(409, 422),
    summary="Cria um cliente",
)
async def criar_cliente(dados: ClienteCriar, session: SessionDep):
    return await service.criar_cliente(session, dados)


@router.post(
    "/{cliente_id}/seguindo/{loja_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=SeguindoOut,
    responses=respostas_erro(404, 409, 422),
    summary="Cliente passa a seguir uma loja",
)
async def seguir_loja(cliente_id: int, loja_id: int, session: SessionDep):
    return await service.seguir_loja(session, cliente_id, loja_id)


@router.get(
    "/{cliente_id}/feed",
    response_model=FeedOut,
    responses=respostas_erro(404, 422),
    summary="Feed com as novidades das lojas seguidas",
    description="Da mais recente para a mais antiga.",
)
async def feed(
    cliente_id: int,
    session: SessionDep,
    limite: Annotated[
        int, Query(ge=1, le=LIMITE_MAXIMO, description="Quantidade de itens (1 a 50).")
    ] = LIMITE_PADRAO,
):
    return await feed_service.montar_feed(session, cliente_id, limite)
