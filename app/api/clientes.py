from fastapi import APIRouter, status

from app.api.deps import SessionDep
from app.core.errors import respostas_erro
from app.schemas import ClienteCriar, ClienteOut, SeguindoOut
from app.services import clientes as service

router = APIRouter(prefix="/clientes", tags=["Clientes"])


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
