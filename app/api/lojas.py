from fastapi import APIRouter, status

from app.api.deps import SessionDep
from app.core.errors import respostas_erro
from app.schemas import LojaCriar, LojaOut, NovidadeCriar, NovidadeOut
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


@router.post(
    "/{loja_id}/novidades",
    status_code=status.HTTP_201_CREATED,
    response_model=NovidadeOut,
    responses=respostas_erro(404, 422),
    summary="Loja publica uma novidade",
)
async def publicar_novidade(loja_id: int, dados: NovidadeCriar, session: SessionDep):
    return await service.publicar_novidade(session, loja_id, dados)
