from sqlalchemy.exc import OperationalError

from app.core.db import get_session
from app.core.redis import get_redis
from app.main import app
from tests.helpers import assert_erro


async def test_health_ok(client):
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "banco": "ok", "cache": "ok"}


async def test_health_sem_redis_continua_200_e_informa_cache_indisponivel(client):
    from app.core.redis import ResilientRedis

    app.dependency_overrides[get_redis] = lambda: ResilientRedis(None)

    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["cache"] == "indisponivel"


async def test_health_com_banco_fora_retorna_503(client):
    class SessaoQuebrada:
        async def execute(self, *_):
            raise OperationalError("SELECT 1", {}, ConnectionRefusedError())

    async def _sessao_quebrada():
        yield SessaoQuebrada()

    app.dependency_overrides[get_session] = _sessao_quebrada

    resp = await client.get("/health")

    assert_erro(resp, 503, "banco_indisponivel")
