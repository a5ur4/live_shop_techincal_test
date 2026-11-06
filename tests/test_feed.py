import pytest
from sqlalchemy import text

from tests.helpers import assert_erro, criar_cliente, criar_loja, publicar, seguir


async def _textos(client, cliente_id: int, **params) -> list[str]:
    resp = await client.get(f"/clientes/{cliente_id}/feed", params=params)
    assert resp.status_code == 200, resp.text
    return [item["texto"] for item in resp.json()["itens"]]


async def test_feed_traz_so_novidades_de_lojas_seguidas(client):
    cliente = await criar_cliente(client)
    seguida = await criar_loja(client, "Seguida")
    outra_seguida = await criar_loja(client, "Outra seguida")
    nao_seguida = await criar_loja(client, "Não seguida")
    await seguir(client, cliente["id"], seguida["id"])
    await seguir(client, cliente["id"], outra_seguida["id"])

    await publicar(client, seguida["id"], "A1")
    await publicar(client, nao_seguida["id"], "N1")
    await publicar(client, outra_seguida["id"], "B1")

    assert sorted(await _textos(client, cliente["id"])) == ["A1", "B1"]


async def test_feed_nao_mistura_clientes(client):
    ana = await criar_cliente(client, email="ana@example.com")
    bia = await criar_cliente(client, email="bia@example.com")
    loja_ana = await criar_loja(client)
    loja_bia = await criar_loja(client)
    await seguir(client, ana["id"], loja_ana["id"])
    await seguir(client, bia["id"], loja_bia["id"])
    await publicar(client, loja_ana["id"], "da Ana")
    await publicar(client, loja_bia["id"], "da Bia")

    assert await _textos(client, ana["id"]) == ["da Ana"]
    assert await _textos(client, bia["id"]) == ["da Bia"]


async def test_feed_vem_da_mais_recente_para_a_mais_antiga(client):
    cliente = await criar_cliente(client)
    loja_a = await criar_loja(client)
    loja_b = await criar_loja(client)
    await seguir(client, cliente["id"], loja_a["id"])
    await seguir(client, cliente["id"], loja_b["id"])

    # Intercala as lojas para garantir que a ordem é global, não por loja.
    for i, loja in enumerate([loja_a, loja_b, loja_a, loja_b, loja_a]):
        await publicar(client, loja["id"], f"N{i}")

    assert await _textos(client, cliente["id"]) == ["N4", "N3", "N2", "N1", "N0"]


async def test_feed_desempata_pelo_id_quando_horario_e_igual(client, engine):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente["id"], loja["id"])
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO novidades (loja_id, texto, criado_em) VALUES "
                "(:loja, 'primeira', '2026-01-01T12:00:00Z'),"
                "(:loja, 'segunda', '2026-01-01T12:00:00Z'),"
                "(:loja, 'mais antiga', '2025-12-31T12:00:00Z')"
            ),
            {"loja": loja["id"]},
        )

    assert await _textos(client, cliente["id"]) == ["segunda", "primeira", "mais antiga"]


async def test_feed_inclui_dados_da_loja_e_preco(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client, "Loja da Ana")
    await seguir(client, cliente["id"], loja["id"])
    novidade = await publicar(client, loja["id"], "Tênis novo", preco="299.90")

    resp = await client.get(f"/clientes/{cliente['id']}/feed")

    assert resp.json()["itens"] == [
        {
            "id": novidade["id"],
            "loja": {"id": loja["id"], "nome": "Loja da Ana"},
            "texto": "Tênis novo",
            "preco": "299.90",
            "criado_em": novidade["criado_em"],
        }
    ]


async def test_feed_vazio_quando_nao_segue_ninguem(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await publicar(client, loja["id"], "ninguém vê")

    assert await _textos(client, cliente["id"]) == []


async def test_feed_inclui_novidades_publicadas_antes_de_seguir(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await publicar(client, loja["id"], "antiga")
    await seguir(client, cliente["id"], loja["id"])

    assert await _textos(client, cliente["id"]) == ["antiga"]


async def _cenario_com_novidades(client, quantidade: int) -> int:
    cliente = await criar_cliente(client)
    loja_a = await criar_loja(client)
    loja_b = await criar_loja(client)
    await seguir(client, cliente["id"], loja_a["id"])
    await seguir(client, cliente["id"], loja_b["id"])
    for i in range(quantidade):
        await publicar(client, (loja_a if i % 2 else loja_b)["id"], f"N{i}")
    return cliente["id"]


async def test_feed_limite_padrao_e_20(client):
    cliente_id = await _cenario_com_novidades(client, 25)

    textos = await _textos(client, cliente_id)

    assert textos == [f"N{i}" for i in range(24, 4, -1)]


async def test_feed_respeita_limite_informado(client):
    cliente_id = await _cenario_com_novidades(client, 10)

    assert await _textos(client, cliente_id, limite=3) == ["N9", "N8", "N7"]


async def test_feed_aceita_limite_maximo_50(client):
    cliente_id = await _cenario_com_novidades(client, 55)

    assert len(await _textos(client, cliente_id, limite=50)) == 50


@pytest.mark.parametrize("limite", [0, -1, 51, "abc"])
async def test_feed_limite_invalido_retorna_422(client, limite):
    cliente = await criar_cliente(client)

    resp = await client.get(f"/clientes/{cliente['id']}/feed", params={"limite": limite})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "limite"


async def test_feed_de_cliente_inexistente_retorna_404(client):
    resp = await client.get("/clientes/999/feed")

    assert_erro(resp, 404, "cliente_nao_encontrado")


async def _pagina(client, cliente_id: int, **params) -> dict:
    resp = await client.get(f"/clientes/{cliente_id}/feed", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_feed_sem_proxima_pagina_tem_cursor_nulo(client):
    cliente_id = await _cenario_com_novidades(client, 3)

    pagina = await _pagina(client, cliente_id, limite=3)

    assert len(pagina["itens"]) == 3
    assert pagina["proximo_cursor"] is None


async def test_feed_pagina_por_cursor_sem_repetir_nem_pular(client):
    cliente_id = await _cenario_com_novidades(client, 25)

    vistos, cursor, paginas = [], None, 0
    while True:
        params = {"limite": 10} | ({"cursor": cursor} if cursor else {})
        pagina = await _pagina(client, cliente_id, **params)
        vistos += [item["texto"] for item in pagina["itens"]]
        paginas += 1
        cursor = pagina["proximo_cursor"]
        if cursor is None:
            break

    assert paginas == 3
    assert vistos == [f"N{i}" for i in range(24, -1, -1)]


async def test_feed_cursor_e_estavel_com_publicacao_entre_paginas(client):
    cliente_id = await _cenario_com_novidades(client, 4)
    primeira = await _pagina(client, cliente_id, limite=2)

    # Algo novo chega enquanto o cliente rola: não deve aparecer nem deslocar a página 2.
    loja_id = primeira["itens"][0]["loja"]["id"]
    await publicar(client, loja_id, "nova")
    segunda = await _pagina(client, cliente_id, limite=2, cursor=primeira["proximo_cursor"])

    assert [i["texto"] for i in primeira["itens"]] == ["N3", "N2"]
    assert [i["texto"] for i in segunda["itens"]] == ["N1", "N0"]


async def test_feed_cursor_desempata_pelo_id(client, engine):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente["id"], loja["id"])
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO novidades (loja_id, texto, criado_em) "
                "SELECT :loja, 'mesmo horario ' || g, '2026-01-01T12:00:00Z' "
                "FROM generate_series(1, 5) g"
            ),
            {"loja": loja["id"]},
        )

    primeira = await _pagina(client, cliente["id"], limite=3)
    segunda = await _pagina(client, cliente["id"], limite=3, cursor=primeira["proximo_cursor"])

    ids = [i["id"] for i in primeira["itens"] + segunda["itens"]]
    assert ids == [5, 4, 3, 2, 1]
    assert segunda["proximo_cursor"] is None


@pytest.mark.parametrize(
    "cursor",
    [
        "lixo",
        "!!!",
        "eyJjIjoiMjAyNi0wMS0wMSJ9",  # {"c":"2026-01-01"} sem id e sem fuso
        "eyJjIjoib250ZW0iLCJpZCI6MX0",  # {"c":"ontem","id":1}
    ],
)
async def test_feed_cursor_invalido_retorna_422(client, cursor):
    cliente = await criar_cliente(client)

    resp = await client.get(f"/clientes/{cliente['id']}/feed", params={"cursor": cursor})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"] == [{"campo": "cursor", "mensagem": "Cursor inválido."}]
