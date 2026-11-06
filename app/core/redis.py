"""Cliente Redis usado como cache do feed e contador do rate limit (ver docs/adr/0008).

O Redis é **acessório**: se estiver fora do ar, a API continua funcionando (o cache é
ignorado e o rate limit deixa passar), só registra um aviso. Por isso os timeouts são
curtos e todo acesso passa por `ResilientRedis`, que nunca propaga erro de conexão.
"""

import logging
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def criar_cliente_redis(url: str) -> Redis:
    return Redis.from_url(
        url,
        decode_responses=True,
        socket_timeout=settings.redis_timeout_s,
        socket_connect_timeout=settings.redis_timeout_s,
    )


class ResilientRedis:
    """Envolve o Redis: em falha, loga e devolve `padrao` em vez de levantar exceção."""

    def __init__(self, cliente: Redis | None) -> None:
        self.cliente = cliente

    async def executar[T](
        self, operacao: Callable[[Redis], Awaitable[T]], padrao: T, descricao: str
    ) -> T:
        if self.cliente is None:
            return padrao
        try:
            return await operacao(self.cliente)
        except (RedisError, OSError, TimeoutError) as exc:
            logger.warning("Redis indisponível (%s): %s", descricao, exc)
            return padrao

    async def ping(self) -> bool:
        return await self.executar(lambda r: r.ping(), False, "ping")

    async def aclose(self) -> None:
        if self.cliente is not None:
            await self.cliente.aclose()


_redis = ResilientRedis(criar_cliente_redis(settings.redis_url) if settings.redis_url else None)


def get_redis() -> ResilientRedis:
    """Dependência FastAPI. Os testes trocam por um cliente ligado ao Redis de teste."""
    return _redis
