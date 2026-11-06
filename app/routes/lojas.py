from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.errors import respostas_erro
from app.routes.deps import (
    LIMITE_PADRAO,
    Cursor,
    Limite,
    LojaAutenticada,
    LojaId,
    NovidadeId,
    RedisDep,
    SessionDep,
)
from app.schemas import (
    ContaEditar,
    ExcluirContaIn,
    LojaCriar,
    LojaDetalhe,
    LojaOut,
    LojaPublica,
    NovidadeCriar,
    NovidadeEditar,
    NovidadeOut,
    Pagina,
)
from app.services import contas as contas_service
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


@router.patch(
    "/{loja_id}",
    response_model=LojaOut,
    responses=respostas_erro(
        "nao_autenticado",
        "acesso_negado",
        "loja_nao_encontrada",
        "email_ja_cadastrado",
        "entrada_invalida",
    ),
    summary="Edita o cadastro da loja (nome e/ou e-mail)",
    description="Exige token de lojista da própria loja. Só os campos enviados mudam.",
)
async def editar_loja(loja_id: LojaAutenticada, dados: ContaEditar, session: SessionDep):
    return await contas_service.editar_conta(session, "loja", loja_id, dados)


@router.delete(
    "/{loja_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro(
        "nao_autenticado", "acesso_negado", "loja_nao_encontrada", "entrada_invalida"
    ),
    summary="Exclui a loja",
    description=(
        "Definitivo. Exige token de lojista da própria loja e a senha atual no corpo. "
        "Apaga também as novidades e os seguidores da loja."
    ),
)
async def excluir_loja(
    loja_id: LojaAutenticada, dados: ExcluirContaIn, session: SessionDep, redis: RedisDep
) -> None:
    await contas_service.excluir_conta(session, redis, "loja", loja_id, dados.senha)


@router.patch(
    "/{loja_id}/novidades/{novidade_id}",
    response_model=NovidadeOut,
    responses=respostas_erro(
        "nao_autenticado", "acesso_negado", "novidade_nao_encontrada", "entrada_invalida"
    ),
    summary="Loja edita uma novidade",
    description=(
        "Exige token de lojista da própria loja. Só os campos enviados mudam; "
        "`preco: null` remove o preço. `criado_em` não muda; `editado_em` é preenchido."
    ),
)
async def editar_novidade(
    loja_id: LojaAutenticada, novidade_id: NovidadeId, dados: NovidadeEditar, session: SessionDep
):
    return await service.editar_novidade(session, loja_id, novidade_id, dados)


@router.delete(
    "/{loja_id}/novidades/{novidade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro(
        "nao_autenticado", "acesso_negado", "novidade_nao_encontrada", "entrada_invalida"
    ),
    summary="Loja remove uma novidade",
    description="Exige token de lojista da própria loja.",
)
async def remover_novidade(
    loja_id: LojaAutenticada, novidade_id: NovidadeId, session: SessionDep
) -> None:
    await service.remover_novidade(session, loja_id, novidade_id)
