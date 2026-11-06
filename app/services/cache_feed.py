"""Cache da primeira página do feed no Redis (ver docs/adr/0008).

- Só a primeira página (sem cursor), que é o que o app abre várias vezes por dia.
- Um hash por cliente (`feed:{id}`), um campo por `limite`; TTL curto (FEED_CACHE_TTL_S).
- Seguir/deixar de seguir apaga o cache do cliente na hora.
- Publicação nova NÃO invalida caches (uma loja de 100 mil seguidores exigiria 100 mil
  DELs): aparece no feed em até TTL segundos. É o trade-off aceito.
- Redis fora do ar = sem cache: o feed sai do banco normalmente.
"""

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.redis import ResilientRedis
from app.schemas import FeedOut

settings = get_settings()


def _chave(cliente_id: int) -> str:
    return f"feed:{cliente_id}"


async def obter(redis: ResilientRedis, cliente_id: int, limite: int) -> FeedOut | None:
    bruto = await redis.executar(
        lambda r: r.hget(_chave(cliente_id), str(limite)), None, "cache do feed"
    )
    return FeedOut.model_validate_json(bruto) if bruto else None


async def salvar(redis: ResilientRedis, cliente_id: int, limite: int, feed: FeedOut) -> None:
    chave = _chave(cliente_id)

    async def _gravar(r: Redis) -> None:
        async with r.pipeline(transaction=True) as pipe:
            pipe.hset(chave, str(limite), feed.model_dump_json())
            # NX: o TTL conta a partir do primeiro campo gravado; gravar outro `limite`
            # não estende a vida dos que já estavam lá.
            pipe.expire(chave, settings.feed_cache_ttl_s, nx=True)
            await pipe.execute()

    await redis.executar(_gravar, None, "cache do feed")


async def invalidar(redis: ResilientRedis, cliente_id: int) -> None:
    await redis.executar(lambda r: r.delete(_chave(cliente_id)), None, "cache do feed")
