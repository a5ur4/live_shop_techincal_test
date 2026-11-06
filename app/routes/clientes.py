from fastapi import APIRouter, Response, status

from app.core.errors import respostas_erro
from app.routes.deps import (
    LIMITE_PADRAO,
    ClienteAutenticado,
    Cursor,
    Limite,
    LojaId,
    RedisDep,
    SessionDep,
)
from app.schemas import (
    ClienteCriar,
    ClienteOut,
    ContaEditar,
    ExcluirContaIn,
    FeedOut,
    LojaSeguida,
    Pagina,
    SeguindoOut,
)
from app.services import clientes as service
from app.services import contas as contas_service
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
async def seguir_loja(
    cliente_id: ClienteAutenticado, loja_id: LojaId, session: SessionDep, redis: RedisDep
):
    return await service.seguir_loja(session, redis, cliente_id, loja_id)


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
    cliente_id: ClienteAutenticado, loja_id: LojaId, session: SessionDep, redis: RedisDep
) -> None:
    await service.deixar_de_seguir(session, redis, cliente_id, loja_id)


@router.get(
    "/{cliente_id}/feed",
    response_model=FeedOut,
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Feed com as novidades das lojas seguidas",
    description=(
        "Novidades das lojas que o cliente segue, da mais recente para a mais antiga. "
        "Para a próxima página, repita a chamada com `cursor=<proximo_cursor>`.\n\n"
        "Header `X-Cache`: `HIT` (primeira página vinda do cache), `MISS` (calculada e "
        "guardada) ou `BYPASS` (páginas com cursor). Novidades novas aparecem em até 30s; "
        "seguir ou deixar de seguir atualiza na hora."
    ),
)
async def feed(
    cliente_id: ClienteAutenticado,
    session: SessionDep,
    redis: RedisDep,
    response: Response,
    limite: Limite = LIMITE_PADRAO,
    cursor: Cursor = None,
):
    feed, status_cache = await feed_service.ler_feed(session, redis, cliente_id, limite, cursor)
    response.headers["X-Cache"] = status_cache
    return feed


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


@router.patch(
    "/{cliente_id}",
    response_model=ClienteOut,
    responses=respostas_erro(
        "nao_autenticado",
        "acesso_negado",
        "cliente_nao_encontrado",
        "email_ja_cadastrado",
        "entrada_invalida",
    ),
    summary="Edita o cadastro do cliente (nome e/ou e-mail)",
    description="Exige token do próprio cliente. Só os campos enviados mudam.",
)
async def editar_cliente(cliente_id: ClienteAutenticado, dados: ContaEditar, session: SessionDep):
    return await contas_service.editar_conta(session, "cliente", cliente_id, dados)


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro(
        "nao_autenticado", "acesso_negado", "cliente_nao_encontrado", "entrada_invalida"
    ),
    summary="Exclui a conta do cliente",
    description=(
        "Definitivo. Exige token do próprio cliente e a senha atual no corpo. "
        "Apaga também as lojas seguidas."
    ),
)
async def excluir_cliente(
    cliente_id: ClienteAutenticado, dados: ExcluirContaIn, session: SessionDep, redis: RedisDep
) -> None:
    await contas_service.excluir_conta(session, redis, "cliente", cliente_id, dados.senha)
