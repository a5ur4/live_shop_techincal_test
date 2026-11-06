"""Rotas da conta logada: o id vem do token, não da URL (ver docs/adr/0007).

Equivalem às rotas com `{id}` (que continuam existindo, como pede o enunciado), mas o
cliente do app não precisa conhecer nem enviar o próprio id.
"""

from fastapi import APIRouter, Response, status

from app.core.errors import respostas_erro
from app.core.security import TipoConta
from app.models import Cliente, Loja
from app.routes.deps import (
    LIMITE_PADRAO,
    ClienteAtual,
    ContaAtual,
    Cursor,
    Limite,
    LojaAtual,
    LojaId,
    NovidadeId,
    RedisDep,
    SessionDep,
)
from app.schemas import (
    ContaEditar,
    ContaOut,
    ExcluirContaIn,
    FeedOut,
    LojaSeguida,
    NovidadeCriar,
    NovidadeEditar,
    NovidadeOut,
    Pagina,
    SeguindoOut,
    TrocaSenhaIn,
)
from app.services import auth as auth_service
from app.services import clientes as clientes_service
from app.services import contas as contas_service
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
    return _conta_out(conta.tipo, await contas_service.obter_conta(session, conta.tipo, conta.id))


@router.patch(
    "",
    response_model=ContaOut,
    responses=respostas_erro(
        "nao_autenticado",
        "cliente_nao_encontrado",
        "loja_nao_encontrada",
        "email_ja_cadastrado",
        "entrada_invalida",
    ),
    summary="Edito meu perfil (nome e/ou e-mail)",
    description="Só os campos enviados mudam. Trocar o e-mail troca o login.",
)
async def editar_perfil(conta: ContaAtual, dados: ContaEditar, session: SessionDep):
    registro = await contas_service.editar_conta(session, conta.tipo, conta.id, dados)
    return _conta_out(conta.tipo, registro)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro(
        "nao_autenticado", "cliente_nao_encontrado", "loja_nao_encontrada", "entrada_invalida"
    ),
    summary="Excluo minha conta",
    description=(
        "Definitivo. Exige a senha atual no corpo. Apaga as lojas seguidas (cliente) ou as "
        "novidades e os seguidores (lojista) e encerra todas as sessões."
    ),
)
async def excluir_conta(
    conta: ContaAtual, dados: ExcluirContaIn, session: SessionDep, redis: RedisDep
) -> None:
    await contas_service.excluir_conta(session, redis, conta.tipo, conta.id, dados.senha)


def _conta_out(tipo: TipoConta, registro: Cliente | Loja) -> ContaOut:
    return ContaOut(
        tipo=tipo,
        id=registro.id,
        nome=registro.nome,
        email=registro.email,
        criado_em=registro.criado_em,
    )


@router.put(
    "/senha",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro("nao_autenticado", "entrada_invalida"),
    summary="Troca a minha senha",
    description=(
        "Exige a senha atual. Encerra todas as sessões (refresh tokens) da conta; "
        "access tokens já emitidos valem até expirar."
    ),
)
async def trocar_senha(conta: ContaAtual, dados: TrocaSenhaIn, session: SessionDep) -> None:
    await auth_service.trocar_senha(
        session, conta.tipo, conta.id, dados.senha_atual, dados.nova_senha
    )


@router.get(
    "/feed",
    response_model=FeedOut,
    responses=respostas_erro("nao_autenticado", "acesso_negado", "entrada_invalida"),
    summary="Meu feed",
    description=_SO_CLIENTE + " Mesmo cache e header `X-Cache` de `GET /clientes/{id}/feed`.",
)
async def meu_feed(
    cliente_id: ClienteAtual,
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
async def seguir(cliente_id: ClienteAtual, loja_id: LojaId, session: SessionDep, redis: RedisDep):
    return await clientes_service.seguir_loja(session, redis, cliente_id, loja_id)


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
async def deixar_de_seguir(
    cliente_id: ClienteAtual, loja_id: LojaId, session: SessionDep, redis: RedisDep
) -> None:
    await clientes_service.deixar_de_seguir(session, redis, cliente_id, loja_id)


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


@router.patch(
    "/novidades/{novidade_id}",
    response_model=NovidadeOut,
    responses=respostas_erro(
        "nao_autenticado", "acesso_negado", "novidade_nao_encontrada", "entrada_invalida"
    ),
    summary="Edito uma novidade da minha loja",
    description=_SO_LOJA + " Só os campos enviados mudam; `preco: null` remove o preço.",
)
async def editar_novidade(
    loja_id: LojaAtual, novidade_id: NovidadeId, dados: NovidadeEditar, session: SessionDep
):
    return await lojas_service.editar_novidade(session, loja_id, novidade_id, dados)


@router.delete(
    "/novidades/{novidade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro(
        "nao_autenticado", "acesso_negado", "novidade_nao_encontrada", "entrada_invalida"
    ),
    summary="Removo uma novidade da minha loja",
    description=_SO_LOJA,
)
async def remover_novidade(
    loja_id: LojaAtual, novidade_id: NovidadeId, session: SessionDep
) -> None:
    await lojas_service.remover_novidade(session, loja_id, novidade_id)
