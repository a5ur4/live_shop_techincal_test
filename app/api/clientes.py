from fastapi import APIRouter, status

from app.api.deps import SessionDep
from app.core.errors import respostas_erro
from app.schemas import ClienteCriar, ClienteOut
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
