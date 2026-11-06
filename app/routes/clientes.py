from fastapi import APIRouter, status

from app.core.errors import respostas_erro
from app.routes.deps import LIMITE_PADRAO, ClienteAutenticado, Cursor, Limite, LojaId, SessionDep
from app.schemas import ClienteCriar, ClienteOut, FeedOut, LojaSeguida, Pagina, SeguindoOut
from app.services import clientes as service
from app.services import feed as feed_service

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ClienteOut,
    responses=respostas_erro("email_ja_cadastrado", "entrada_invalida"),
    summary="Cria um cliente",
)
async def criar_cliente(dados: ClienteCriar, session: SessionDep):
    return await service.criar_cliente(session, dados)


@router.post(
    "/{cliente_id}/seguindo/{loja_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=SeguindoOut,
    responses=respostas_erro(
        "nao_autenticado",
        "acesso_negado",
        "loja_nao_encontrada",
        "ja_segue_loja",
        "entrada_invalida",
    ),
    summary="Cliente passa a seguir uma loja",
)
async def seguir_loja(cliente_id: ClienteAutenticado, loja_id: LojaId, session: SessionDep):
    return await service.seguir_loja(session, cliente_id, loja_id)


@router.delete(
    "/{cliente_id}/seguindo/{loja_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro(
        "nao_autenticado",
        "acesso_negado",
        "loja_nao_encontrada",
        "nao_segue_loja",
        "entrada_invalida",
    ),
    summary="Cliente deixa de seguir uma loja",
)
async def deixar_de_seguir(
    cliente_id: ClienteAutenticado, loja_id: LojaId, session: SessionDep
) -> None:
    await service.deixar_de_seguir(session, cliente_id, loja_id)


@router.get(
    "/{cliente_id}/feed",
    response_model=FeedOut,
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Feed com as novidades das lojas seguidas",
    description=(
        "Novidades das lojas que o cliente segue, da mais recente para a mais antiga. "
        "Para a próxima página, repita a chamada com `cursor=<proximo_cursor>`."
    ),
)
async def feed(
    cliente_id: ClienteAutenticado,
    session: SessionDep,
    limite: Limite = LIMITE_PADRAO,
    cursor: Cursor = None,
):
    return await feed_service.montar_feed(session, cliente_id, limite, cursor)


@router.get(
    "/{cliente_id}/seguindo",
    response_model=Pagina[LojaSeguida],
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Lojas que o cliente segue",
    description="Das seguidas mais recentemente para as mais antigas, paginado por cursor.",
)
async def listar_seguindo(
    cliente_id: ClienteAutenticado,
    session: SessionDep,
    limite: Limite = LIMITE_PADRAO,
    cursor: Cursor = None,
):
    return await service.listar_seguindo(session, cliente_id, limite, cursor)
