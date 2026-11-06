"""Rate limit do login: conta falhas por e-mail e por IP numa janela fixa.

- Bloqueio por e-mail protege uma conta específica contra força bruta.
- Bloqueio por IP (limite maior) protege contra quem testa muitos e-mails.
- Login certo zera o contador do e-mail; o do IP só expira com a janela.
- Contadores ficam no Redis (compartilhados entre instâncias). Se o Redis falhar, cai
  para contadores em memória do processo: o limite continua valendo (por instância) e o
  login continua disponível. Nunca "libera geral". Ver docs/adr/0008.
"""

import time

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.errors import MuitasTentativasError
from app.core.redis import ResilientRedis

settings = get_settings()

_FALHOU = object()


class _ContadorLocal:
    """Fallback em memória: {chave: (falhas, expira_em_monotonic)}, com teto de tamanho."""

    MAX_CHAVES = 100_000

    def __init__(self) -> None:
        self._dados: dict[str, tuple[int, float]] = {}

    def _vivo(self, chave: str) -> tuple[int, float] | None:
        item = self._dados.get(chave)
        if item and item[1] <= time.monotonic():
            del self._dados[chave]
            return None
        return item

    def falhas_e_ttl(self, chave: str) -> tuple[int, int]:
        item = self._vivo(chave)
        return (item[0], int(item[1] - time.monotonic()) + 1) if item else (0, 0)

    def incrementar(self, chave: str, janela: int) -> None:
        if len(self._dados) >= self.MAX_CHAVES:
            agora = time.monotonic()
            self._dados = {k: v for k, v in self._dados.items() if v[1] > agora}
        item = self._vivo(chave)
        falhas, expira = item if item else (0, time.monotonic() + janela)
        self._dados[chave] = (falhas + 1, expira)

    def limpar(self, chave: str) -> None:
        self._dados.pop(chave, None)


_local = _ContadorLocal()


def _chaves(tipo: str, email: str, ip: str) -> list[tuple[str, int]]:
    return [
        (f"login:falhas:{tipo}:email:{email}", settings.login_max_falhas_email),
        (f"login:falhas:ip:{ip}", settings.login_max_falhas_ip),
    ]


async def _falhas_e_ttl(redis: ResilientRedis, chave: str) -> tuple[int, int]:
    async def _ler(r: Redis) -> tuple[int, int]:
        async with r.pipeline(transaction=False) as pipe:
            falhas, ttl = await pipe.get(chave).ttl(chave).execute()
        return int(falhas or 0), ttl

    resultado = await redis.executar(_ler, _FALHOU, "rate limit")
    return _local.falhas_e_ttl(chave) if resultado is _FALHOU else resultado


async def verificar(redis: ResilientRedis, tipo: str, email: str, ip: str) -> None:
    """Levanta 429 se o e-mail ou o IP já esgotaram as tentativas da janela."""
    for chave, limite in _chaves(tipo, email, ip):
        falhas, ttl = await _falhas_e_ttl(redis, chave)
        if falhas >= limite:
            raise MuitasTentativasError(retry_after=max(ttl, 1))


async def registrar_falha(redis: ResilientRedis, tipo: str, email: str, ip: str) -> None:
    janela = settings.login_janela_minutos * 60
    chaves = [chave for chave, _ in _chaves(tipo, email, ip)]

    async def _incrementar(r: Redis) -> None:
        async with r.pipeline(transaction=True) as pipe:
            for chave in chaves:
                # NX: a janela começa na primeira falha e não é estendida pelas seguintes.
                pipe.incr(chave).expire(chave, janela, nx=True)
            await pipe.execute()

    if await redis.executar(_incrementar, _FALHOU, "rate limit") is _FALHOU:
        for chave in chaves:
            _local.incrementar(chave, janela)


async def limpar(redis: ResilientRedis, tipo: str, email: str) -> None:
    chave = f"login:falhas:{tipo}:email:{email}"
    _local.limpar(chave)
    await redis.executar(lambda r: r.delete(chave), None, "rate limit")
