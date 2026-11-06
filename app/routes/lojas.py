from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.errors import respostas_erro
from app.routes.deps import LIMITE_PADRAO, Cursor, Limite, LojaAutenticada, LojaId, SessionDep
from app.schemas import (
    LojaCriar,
    LojaDetalhe,
    LojaOut,
    LojaPublica,
    NovidadeCriar,
    NovidadeOut,
    Pagina,
)
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


@router.get(
    "",
    response_model=Pagina[LojaPublica],
    responses=respostas_erro("entrada_invalida"),
    summary="Lista as lojas",
    description="Em ordem de cadastro, paginado por cursor. `q` filtra por parte do nome.",
)
async def listar_lojas(
    session: SessionDep,
    limite: Limite = LIMITE_PADRAO,
    cursor: Cursor = None,
    q: Annotated[
        str | None, Query(min_length=1, max_length=120, description="Parte do nome da loja.")
    ] = None,
):
    return await service.listar_lojas(session, limite, cursor, q)


@router.get(
    "/{loja_id}",
    response_model=LojaDetalhe,
    responses=respostas_erro("loja_nao_encontrada", "entrada_invalida"),
    summary="Detalhes públicos de uma loja",
)
async def detalhar_loja(loja_id: LojaId, session: SessionDep):
    return await service.detalhar_loja(session, loja_id)


@router.get(
    "/{loja_id}/novidades",
    response_model=Pagina[NovidadeOut],
    responses=respostas_erro("loja_nao_encontrada", "entrada_invalida"),
    summary="Novidades publicadas por uma loja",
    description="Da mais recente para a mais antiga, paginado por cursor. Público.",
)
async def listar_novidades(
    loja_id: LojaId,
    session: SessionDep,
    limite: Limite = LIMITE_PADRAO,
    cursor: Cursor = None,
):
    return await service.listar_novidades(session, loja_id, limite, cursor)
