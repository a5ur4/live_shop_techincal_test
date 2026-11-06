"""Rotas da conta logada: o id vem do token, não da URL (ver docs/adr/0007).

Equivalem às rotas com `{id}` (que continuam existindo, como pede o enunciado), mas o
cliente do app não precisa conhecer nem enviar o próprio id.
"""

from fastapi import APIRouter, status

from app.core.errors import respostas_erro
from app.routes.deps import (
    LIMITE_PADRAO,
    ClienteAtual,
    ContaAtual,
    Cursor,
    Limite,
    LojaAtual,
    LojaId,
    SessionDep,
)
from app.schemas import (
    ContaOut,
    FeedOut,
    LojaSeguida,
    NovidadeCriar,
    NovidadeOut,
    Pagina,
    SeguindoOut,
)
from app.services import clientes as clientes_service
from app.services import feed as feed_service
from app.services import lojas as lojas_service

router = APIRouter(prefix="/me", tags=["Minha conta"])

_SO_CLIENTE = "Exige token de **cliente**; token de lojista recebe 403."
_SO_LOJA = "Exige token de **lojista**; token de cliente recebe 403."


@router.get(
    "",
    response_model=ContaOut,
    responses=respostas_erro("nao_autenticado"),
    summary="Perfil da conta logada (cliente ou lojista)",
)
async def perfil(conta: ContaAtual, session: SessionDep):
    if conta.tipo == "cliente":
        registro = await clientes_service.obter_cliente(session, conta.id)
    else:
        registro = await lojas_service.obter_loja(session, conta.id)
    return ContaOut(
        tipo=conta.tipo,
        id=registro.id,
        nome=registro.nome,
        email=registro.email,
        criado_em=registro.criado_em,
    )


@router.get(
    "/feed",
    response_model=FeedOut,
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Meu feed",
    description=_SO_CLIENTE,
)
async def meu_feed(
    cliente_id: ClienteAtual,
    session: SessionDep,
    limite: Limite = LIMITE_PADRAO,
    cursor: Cursor = None,
):
    return await feed_service.montar_feed(session, cliente_id, limite, cursor)


@router.get(
    "/seguindo",
    response_model=Pagina[LojaSeguida],
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Lojas que eu sigo",
    description=_SO_CLIENTE,
)
async def minhas_lojas_seguidas(
    cliente_id: ClienteAtual,
    session: SessionDep,
    limite: Limite = LIMITE_PADRAO,
    cursor: Cursor = None,
):
    return await clientes_service.listar_seguindo(session, cliente_id, limite, cursor)


@router.post(
    "/seguindo/{loja_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=SeguindoOut,
    responses=respostas_erro(
        "nao_autenticado",
        "acesso_negado",
        "loja_nao_encontrada",
        "ja_segue_loja",
        "entrada_invalida",
    ),
    summary="Passo a seguir uma loja",
    description=_SO_CLIENTE,
)
async def seguir(cliente_id: ClienteAtual, loja_id: LojaId, session: SessionDep):
    return await clientes_service.seguir_loja(session, cliente_id, loja_id)


@router.delete(
    "/seguindo/{loja_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro(
        "nao_autenticado",
        "acesso_negado",
        "loja_nao_encontrada",
        "nao_segue_loja",
        "entrada_invalida",
    ),
    summary="Deixo de seguir uma loja",
    description=_SO_CLIENTE,
)
async def deixar_de_seguir(cliente_id: ClienteAtual, loja_id: LojaId, session: SessionDep) -> None:
    await clientes_service.deixar_de_seguir(session, cliente_id, loja_id)


@router.post(
    "/novidades",
    status_code=status.HTTP_201_CREATED,
    response_model=NovidadeOut,
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Publico uma novidade na minha loja",
    description=_SO_LOJA,
)
async def publicar(loja_id: LojaAtual, dados: NovidadeCriar, session: SessionDep):
    return await lojas_service.publicar_novidade(session, loja_id, dados)


@router.get(
    "/novidades",
    response_model=Pagina[NovidadeOut],
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Novidades da minha loja",
    description=_SO_LOJA,
)
async def minhas_novidades(
    loja_id: LojaAtual,
    session: SessionDep,
    limite: Limite = LIMITE_PADRAO,
    cursor: Cursor = None,
):
    return await lojas_service.listar_novidades(session, loja_id, limite, cursor)
