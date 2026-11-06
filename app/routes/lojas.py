from fastapi import APIRouter, status

from app.core.errors import respostas_erro
from app.routes.deps import LojaAutenticada, SessionDep
from app.schemas import LojaCriar, LojaOut, NovidadeCriar, NovidadeOut
from app.services import lojas as service

router = APIRouter(prefix="/lojas", tags=["Lojas"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=LojaOut,
    responses=respostas_erro("email_ja_cadastrado", "entrada_invalida"),
    summary="Cria uma loja (cadastro do lojista)",
)
async def criar_loja(dados: LojaCriar, session: SessionDep):
    return await service.criar_loja(session, dados)


@router.post(
    "/{loja_id}/novidades",
    status_code=status.HTTP_201_CREATED,
    response_model=NovidadeOut,
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Loja publica uma novidade",
    description="Exige token de lojista da própria loja.",
)
async def publicar_novidade(loja_id: LojaAutenticada, dados: NovidadeCriar, session: SessionDep):
    return await service.publicar_novidade(session, loja_id, dados)
