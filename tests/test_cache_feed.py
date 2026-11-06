"""Cache da primeira página do feed (Redis): HIT/MISS/BYPASS, invalidação e TTL."""

from app.core.redis import ResilientRedis, get_redis
from app.main import app
from tests.helpers import auth, criar_cliente, criar_loja, publicar, seguir


async def _feed(client, cliente, **params):
    resp = await client.get(f"/clientes/{cliente['id']}/feed", params=params, headers=auth(cliente))
    assert resp.status_code == 200, resp.text
    return resp


async def _cenario(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente, loja["id"])
    await publicar(client, loja, "primeira")
    return cliente, loja


async def test_primeira_leitura_e_miss_e_a_segunda_e_hit_com_o_mesmo_conteudo(client):
    cliente, _ = await _cenario(client)

    miss = await _feed(client, cliente)
    hit = await _feed(client, cliente)

    assert miss.headers["x-cache"] == "MISS"
    assert hit.headers["x-cache"] == "HIT"
    assert hit.json() == miss.json()


async def test_cache_e_por_limite(client):
    cliente, _ = await _cenario(client)
    await _feed(client, cliente, limite=20)

    resp = await _feed(client, cliente, limite=5)

    assert resp.headers["x-cache"] == "MISS"


async def test_paginas_com_cursor_nao_usam_cache(client):
    cliente, loja = await _cenario(client)
    await publicar(client, loja, "segunda")
    primeira = await _feed(client, cliente, limite=1)

    resp = await _feed(client, cliente, limite=1, cursor=primeira.json()["proximo_cursor"])

    assert resp.headers["x-cache"] == "BYPASS"
    assert [i["texto"] for i in resp.json()["itens"]] == ["primeira"]


async def test_seguir_e_deixar_de_seguir_invalidam_o_cache_na_hora(client):
    cliente, loja = await _cenario(client)
    outra = await criar_loja(client)
    await publicar(client, outra, "da outra")
    await _feed(client, cliente)

    await seguir(client, cliente, outra["id"])
    depois_de_seguir = await _feed(client, cliente)
    await client.delete(f"/me/seguindo/{outra['id']}", headers=auth(cliente))
    depois_de_deixar = await _feed(client, cliente)

    assert depois_de_seguir.headers["x-cache"] == "MISS"
    assert {i["texto"] for i in depois_de_seguir.json()["itens"]} == {"primeira", "da outra"}
    assert depois_de_deixar.headers["x-cache"] == "MISS"
    assert [i["texto"] for i in depois_de_deixar.json()["itens"]] == ["primeira"]


async def test_publicacao_nova_aparece_quando_o_cache_expira(client, redis):
    cliente, loja = await _cenario(client)
    await _feed(client, cliente)
    await publicar(client, loja, "nova")

    em_cache = await _feed(client, cliente)
    await redis.cliente.delete(f"feed:{cliente['id']}")  # simula o fim do TTL
    expirado = await _feed(client, cliente)

    assert [i["texto"] for i in em_cache.json()["itens"]] == ["primeira"]
    assert [i["texto"] for i in expirado.json()["itens"]] == ["nova", "primeira"]


async def test_cache_tem_ttl_curto_que_nao_e_renovado(client, redis):
    cliente, _ = await _cenario(client)
    await _feed(client, cliente, limite=20)
    ttl_inicial = await redis.cliente.ttl(f"feed:{cliente['id']}")

    await _feed(client, cliente, limite=10)  # grava outro campo no mesmo hash

    assert 0 < ttl_inicial <= 30
    assert await redis.cliente.ttl(f"feed:{cliente['id']}") <= ttl_inicial


async def test_cache_de_um_cliente_nao_vaza_para_outro(client):
    ana, loja = await _cenario(client)
    bia = await criar_cliente(client)
    await _feed(client, ana)

    resp = await _feed(client, bia)

    assert resp.headers["x-cache"] == "MISS"
    assert resp.json()["itens"] == []


async def test_me_feed_usa_o_mesmo_cache(client):
    cliente, _ = await _cenario(client)
    await _feed(client, cliente)

    resp = await client.get("/me/feed", headers=auth(cliente))

    assert resp.headers["x-cache"] == "HIT"


async def test_sem_redis_o_feed_sai_do_banco(client):
    cliente, _ = await _cenario(client)
    app.dependency_overrides[get_redis] = lambda: ResilientRedis(None)

    resp = await _feed(client, cliente)

    assert resp.headers["x-cache"] == "MISS"
    assert [i["texto"] for i in resp.json()["itens"]] == ["primeira"]
