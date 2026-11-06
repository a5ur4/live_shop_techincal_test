from typing import Literal

from sqlalchemy import select, true, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.paginacao import codificar_posicao, decodificar_posicao
from app.core.redis import ResilientRedis
from app.models import Loja, Novidade, Seguidor
from app.schemas import FeedItem, FeedOut, LojaResumo
from app.services import cache_feed
from app.services.clientes import obter_cliente

settings = get_settings()

StatusCache = Literal["HIT", "MISS", "BYPASS"]


async def montar_feed(
    session: AsyncSession, cliente_id: int, limite: int, cursor: str | None = None
) -> FeedOut:
    """Feed montado na leitura (fan-out on read). Ver docs/adr/0002.

    Para cada loja seguida, um LATERAL busca só as `limite` novidades mais
    recentes daquela loja usando o índice (loja_id, criado_em DESC, id DESC).
    Depois junta tudo e corta em `limite`. O custo depende de
    "lojas seguidas × limite", não do total de novidades publicadas.

    Com `cursor`, continua estritamente depois do último item da página anterior
    (paginação por keyset), usando o mesmo índice.
    """
    depois_de = decodificar_posicao(cursor) if cursor else None
    await obter_cliente(session, cliente_id)

    # Busca um item a mais para saber se existe próxima página.
    busca = limite + 1
    ultimas_da_loja = (
        select(
            Novidade.id,
            Novidade.loja_id,
            Novidade.texto,
            Novidade.preco,
            Novidade.criado_em,
            Novidade.editado_em,
        )
        .where(Novidade.loja_id == Seguidor.loja_id)
        .order_by(Novidade.criado_em.desc(), Novidade.id.desc())
        .limit(busca)
    )
    if depois_de:
        ultimas_da_loja = ultimas_da_loja.where(
            tuple_(Novidade.criado_em, Novidade.id) < tuple_(*depois_de)
        )
    ultimas_da_loja = ultimas_da_loja.lateral("ultimas_da_loja")

    n = ultimas_da_loja.c
    stmt = (
        select(
            n.id, n.texto, n.preco, n.criado_em, n.editado_em, Loja.id.label("loja_id"), Loja.nome
        )
        .select_from(Seguidor)
        .join(ultimas_da_loja, true())
        .join(Loja, Loja.id == Seguidor.loja_id)
        .where(Seguidor.cliente_id == cliente_id)
        .order_by(n.criado_em.desc(), n.id.desc())
        .limit(busca)
    )
    linhas = (await session.execute(stmt)).all()

    tem_mais = len(linhas) > limite
    linhas = linhas[:limite]
    itens = [
        FeedItem(
            id=row.id,
            loja=LojaResumo(id=row.loja_id, nome=row.nome),
            texto=row.texto,
            preco=row.preco,
            criado_em=row.criado_em,
            editado_em=row.editado_em,
        )
        for row in linhas
    ]
    proximo = codificar_posicao(linhas[-1].criado_em, linhas[-1].id) if tem_mais else None
    return FeedOut(itens=itens, proximo_cursor=proximo)


async def ler_feed(
    session: AsyncSession,
    redis: ResilientRedis,
    cliente_id: int,
    limite: int,
    cursor: str | None = None,
) -> tuple[FeedOut, StatusCache]:
    """Feed com cache da primeira página. Devolve também HIT/MISS/BYPASS (header X-Cache)."""
    if cursor or settings.feed_cache_ttl_s <= 0:
        return await montar_feed(session, cliente_id, limite, cursor), "BYPASS"

    if (em_cache := await cache_feed.obter(redis, cliente_id, limite)) is not None:
        return em_cache, "HIT"

    feed = await montar_feed(session, cliente_id, limite)
    await cache_feed.salvar(redis, cliente_id, limite, feed)
    return feed, "MISS"
