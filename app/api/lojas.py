from fastapi import APIRouter, status

from app.api.deps import SessionDep
from app.core.errors import respostas_erro
from app.schemas import LojaCriar, LojaOut
from app.services import lojas as service

router = APIRouter(prefix="/lojas", tags=["Lojas"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=LojaOut,
    responses=respostas_erro(422),
    summary="Cria uma loja",
)
async def criar_loja(dados: LojaCriar, session: SessionDep):
    return await service.criar_loja(session, dados)
