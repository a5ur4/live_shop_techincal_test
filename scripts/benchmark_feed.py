"""Benchmark do feed com uma loja de 100 mil seguidores (ver docs/adr/0008).

Uso: `make benchmark` (precisa de Postgres e Redis no ar: `make db`).

Monta um banco separado (`feed_bench`, nunca o de desenvolvimento) com:
- 1 loja "grande" seguida por todos os 100 mil clientes + 2.000 lojas pequenas;
- cada cliente segue a grande e mais 5 pequenas; o cliente 1 segue ~500 lojas (pior caso);
- 50 novidades por loja (~100 mil), espalhadas nos últimos 30 dias.

E mede, chamando a app real em processo (httpx + ASGI, sem rede nem uvicorn), a latência
de publicar na loja grande, do feed com e sem cache e do detalhe da loja grande.
"""

import asyncio
import statistics
import time

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.db import get_session
from app.core.redis import ResilientRedis, criar_cliente_redis, get_redis
from app.core.security import criar_token
from app.main import app

settings = get_settings()
URL_BENCH = make_url(settings.database_url).set(database="feed_bench")
REDIS_BENCH = "redis://127.0.0.1:6379/14"

CLIENTES = 100_000
LOJAS_PEQUENAS = 2_000
NOVIDADES_POR_LOJA = 50
LOJAS_DO_PIOR_CASO = 500

POPULAR = [
    "TRUNCATE novidades, seguidores, clientes, lojas, refresh_tokens RESTART IDENTITY CASCADE",
    # loja 1 = grande; 2..2001 = pequenas. Senha '!' = login impossível (não é usado aqui).
    f"""INSERT INTO lojas (nome, email, senha_hash)
        SELECT 'Loja ' || g, 'loja' || g || '@bench.invalid', '!'
        FROM generate_series(1, {LOJAS_PEQUENAS + 1}) g""",
    f"""INSERT INTO clientes (nome, email, senha_hash)
        SELECT 'Cliente ' || g, 'cliente' || g || '@bench.invalid', '!'
        FROM generate_series(1, {CLIENTES}) g""",
    "INSERT INTO seguidores (cliente_id, loja_id) SELECT id, 1 FROM clientes",
    # +5 lojas pequenas distintas por cliente (deslocamentos múltiplos de 397 não colidem).
    f"""INSERT INTO seguidores (cliente_id, loja_id)
        SELECT c.id, 2 + ((c.id + k * 397) % {LOJAS_PEQUENAS})
        FROM clientes c CROSS JOIN generate_series(1, 5) k
        ON CONFLICT DO NOTHING""",
    f"""INSERT INTO seguidores (cliente_id, loja_id)
        SELECT 1, 2 + g FROM generate_series(0, {LOJAS_DO_PIOR_CASO - 1}) g
        ON CONFLICT DO NOTHING""",
    f"""INSERT INTO novidades (loja_id, texto, preco, criado_em)
        SELECT l, 'Novidade ' || n || ' da loja ' || l,
               CASE WHEN n % 3 = 0 THEN NULL ELSE (n * 10)::numeric END,
               now() - (random() * interval '30 days')
        FROM generate_series(1, {LOJAS_PEQUENAS + 1}) l,
             generate_series(1, {NOVIDADES_POR_LOJA}) n""",
    "ANALYZE",
]


async def preparar_banco() -> None:
    admin = create_async_engine(
        URL_BENCH.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin.connect() as conn:
        if not await conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = 'feed_bench'")):
            await conn.execute(text('CREATE DATABASE "feed_bench"'))
    await admin.dispose()

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", URL_BENCH.render_as_string(hide_password=False))
    cfg.attributes["configure_logger"] = False
    await asyncio.to_thread(command.upgrade, cfg, "head")

    engine = create_async_engine(URL_BENCH, poolclass=NullPool)
    inicio = time.perf_counter()
    async with engine.begin() as conn:
        await conn.execute(text("SET statement_timeout = 0"))
        for sql in POPULAR:
            await conn.execute(text(sql))
    async with engine.connect() as conn:
        totais = (
            await conn.execute(
                text(
                    "SELECT (SELECT count(*) FROM seguidores),"
                    " (SELECT count(*) FROM seguidores WHERE loja_id = 1),"
                    " (SELECT count(*) FROM seguidores WHERE cliente_id = 1),"
                    " (SELECT count(*) FROM novidades)"
                )
            )
        ).one()
    await engine.dispose()
    print(
        f"Banco feed_bench populado em {time.perf_counter() - inicio:.1f}s: "
        f"{totais[0]:,} relações de seguir, {totais[1]:,} seguidores da loja grande, "
        f"cliente 1 segue {totais[2]} lojas, {totais[3]:,} novidades.\n"
    )


def _resumo(nome: str, tempos: list[float]) -> str:
    ms = sorted(t * 1000 for t in tempos)
    p = statistics.quantiles(ms, n=100)
    return f"| {nome} | {len(ms)} | {statistics.median(ms):.1f} | {p[94]:.1f} | {p[98]:.1f} |"


async def medir(client: AsyncClient, metodo: str, rota: str, n: int, **kwargs) -> list[float]:
    tempos = []
    for _ in range(n):
        inicio = time.perf_counter()
        resp = await client.request(metodo, rota, **kwargs)
        tempos.append(time.perf_counter() - inicio)
        assert resp.status_code < 300, resp.text
    return tempos


async def explicar_feed_pior_caso() -> str:
    engine = create_async_engine(URL_BENCH, poolclass=NullPool)
    sql = """
        EXPLAIN (ANALYZE, BUFFERS)
        SELECT u.id FROM seguidores s
        JOIN LATERAL (
            SELECT n.id, n.criado_em FROM novidades n WHERE n.loja_id = s.loja_id
            ORDER BY n.criado_em DESC, n.id DESC LIMIT 21
        ) u ON true
        WHERE s.cliente_id = 1
        ORDER BY u.criado_em DESC, u.id DESC LIMIT 21"""
    async with engine.connect() as conn:
        plano = [linha[0] for linha in await conn.execute(text(sql))]
    await engine.dispose()
    return next(linha for linha in plano if "Execution Time" in linha).strip()


async def main() -> None:
    await preparar_banco()

    engine = create_async_engine(URL_BENCH, pool_size=5)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    redis_bench = criar_cliente_redis(REDIS_BENCH)
    await redis_bench.flushdb()

    async def _sessao():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = _sessao
    sem_cache = ResilientRedis(None)
    com_cache = ResilientRedis(redis_bench)

    def h(tipo: str, conta_id: int) -> dict[str, str]:
        return {"Authorization": f"Bearer {criar_token(tipo, conta_id).access_token}"}

    linhas = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://bench") as client:
        await medir(client, "GET", "/health", 20)  # aquecimento (pool, caches do Postgres)

        app.dependency_overrides[get_redis] = lambda: sem_cache
        linhas.append(
            _resumo(
                "Publicar na loja de 100 mil seguidores",
                await medir(
                    client,
                    "POST",
                    "/lojas/1/novidades",
                    200,
                    json={"texto": "Promoção relâmpago"},
                    headers=h("loja", 1),
                ),
            )
        )
        linhas.append(
            _resumo(
                "Feed, cliente típico (6 lojas), sem cache",
                await medir(client, "GET", "/clientes/2/feed", 300, headers=h("cliente", 2)),
            )
        )
        linhas.append(
            _resumo(
                "Feed, pior caso (~500 lojas seguidas), sem cache",
                await medir(client, "GET", "/clientes/1/feed", 200, headers=h("cliente", 1)),
            )
        )
        pagina = await client.get("/clientes/1/feed", headers=h("cliente", 1))
        linhas.append(
            _resumo(
                "Feed, pior caso, 2ª página (cursor)",
                await medir(
                    client,
                    "GET",
                    "/clientes/1/feed",
                    200,
                    headers=h("cliente", 1),
                    params={"cursor": pagina.json()["proximo_cursor"]},
                ),
            )
        )

        app.dependency_overrides[get_redis] = lambda: com_cache
        await client.get("/clientes/1/feed", headers=h("cliente", 1))  # popula o cache
        linhas.append(
            _resumo(
                "Feed, pior caso, com cache (HIT)",
                await medir(client, "GET", "/clientes/1/feed", 300, headers=h("cliente", 1)),
            )
        )
        linhas.append(
            _resumo(
                "Detalhe da loja grande (COUNT de 100 mil)",
                await medir(client, "GET", "/lojas/1", 200),
            )
        )

    app.dependency_overrides.clear()
    await redis_bench.flushdb()
    await redis_bench.aclose()
    await engine.dispose()

    print("| Cenário | Requisições | p50 (ms) | p95 (ms) | p99 (ms) |")
    print("| --- | --- | --- | --- | --- |")
    print("\n".join(linhas))
    print(f"\nEXPLAIN ANALYZE do feed no pior caso: {await explicar_feed_pior_caso()}")


if __name__ == "__main__":
    asyncio.run(main())
