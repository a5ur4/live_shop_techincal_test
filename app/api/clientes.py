from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import ClienteId, LojaId, SessionDep
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
        "cliente_nao_encontrado", "loja_nao_encontrada", "ja_segue_loja", "entrada_invalida"
    ),
    summary="Cliente passa a seguir uma loja",
)
async def seguir_loja(cliente_id: ClienteId, loja_id: LojaId, session: SessionDep):
    return await service.seguir_loja(session, cliente_id, loja_id)


@router.delete(
    "/{cliente_id}/seguindo/{loja_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro(
        "cliente_nao_encontrado", "loja_nao_encontrada", "nao_segue_loja", "entrada_invalida"
    ),
    summary="Cliente deixa de seguir uma loja",
)
async def deixar_de_seguir(cliente_id: ClienteId, loja_id: LojaId, session: SessionDep) -> None:
    await service.deixar_de_seguir(session, cliente_id, loja_id)


@router.get(
    "/{cliente_id}/feed",
    response_model=FeedOut,
    responses=respostas_erro("cliente_nao_encontrado", "entrada_invalida"),
    summary="Feed com as novidades das lojas seguidas",
    description=(
        "Novidades das lojas que o cliente segue, da mais recente para a mais antiga. "
        "Para a próxima página, repita a chamada com `cursor=<proximo_cursor>`."
    ),
)
async def feed(
    cliente_id: ClienteId,
    session: SessionDep,
    limite: Annotated[
        int, Query(ge=1, le=LIMITE_MAXIMO, description="Quantidade de itens (1 a 50).")
    ] = LIMITE_PADRAO,
    cursor: Annotated[
        str | None,
        Query(max_length=200, description="`proximo_cursor` da página anterior."),
    ] = None,
):
    return await feed_service.montar_feed(session, cliente_id, limite, cursor)
