"""Infra de testes: Postgres real, banco de teste criado e migrado automaticamente.

- O banco `TEST_DATABASE_URL` é criado se não existir e recebe as migrations
  (downgrade base + upgrade head, o que também testa as migrations).
- Cada teste começa com as tabelas vazias (TRUNCATE) e ids reiniciados.
- A sessão da app é trocada por uma ligada ao banco de teste via dependency_overrides.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import security
from app.core.config import get_settings
from app.core.db import get_session
from app.core.redis import ResilientRedis, criar_cliente_redis, get_redis
from app.main import app

TEST_DATABASE_URL = get_settings().test_database_url
TEST_REDIS_URL = get_settings().test_redis_url


async def _criar_banco_se_nao_existir() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin.connect() as conn:
        existe = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": url.database}
        )
        if not existe:
            await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    await admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def banco_de_teste() -> None:
    asyncio.run(_criar_banco_se_nao_existir())
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    cfg.attributes["configure_logger"] = False
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def hash_de_senha_rapido(monkeypatch) -> None:
    # Argon2 com custo mínimo: o algoritmo é o mesmo, mas cada hash leva ~1ms em vez de ~50ms.
    rapido = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=1024, parallelism=1),))
    monkeypatch.setattr(security, "hasher", rapido)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    # NullPool: cada teste roda no seu event loop; conexões não são reaproveitadas entre loops.
    eng = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE novidades, seguidores, clientes, lojas, refresh_tokens "
                "RESTART IDENTITY CASCADE"
            )
        )
    yield eng
    await eng.dispose()


@pytest.fixture
async def redis() -> AsyncIterator[ResilientRedis]:
    # Um cliente por teste (cada teste tem seu event loop) num banco Redis só de teste,
    # esvaziado antes de começar.
    cliente = criar_cliente_redis(TEST_REDIS_URL)
    await cliente.flushdb()
    yield ResilientRedis(cliente)
    await cliente.aclose()


@pytest.fixture
async def client(engine: AsyncEngine, redis: ResilientRedis) -> AsyncIterator[AsyncClient]:
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _session_de_teste():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = _session_de_teste
    app.dependency_overrides[get_redis] = lambda: redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
