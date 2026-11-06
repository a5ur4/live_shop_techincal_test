"""Endpoints de leitura: lojas (públicos) e lojas seguidas (do próprio cliente)."""

import pytest
from sqlalchemy import text

from tests.helpers import assert_erro, auth, criar_cliente, criar_loja, publicar, seguir


async def _todas_as_paginas(client, rota: str, headers=None, **params) -> tuple[list, int]:
    itens, cursor, paginas = [], None, 0
    while True:
        query = params | ({"cursor": cursor} if cursor else {})
        resp = await client.get(rota, params=query, headers=headers)
        assert resp.status_code == 200, resp.text
        itens += resp.json()["itens"]
        paginas += 1
        cursor = resp.json()["proximo_cursor"]
        if cursor is None:
            return itens, paginas


# --- GET /lojas ----------------------------------------------------------------


async def test_lista_lojas_em_ordem_de_cadastro_sem_dados_de_login(client):
    for nome in ["A", "B", "C"]:
        await criar_loja(client, nome)

    resp = await client.get("/lojas")

    assert resp.status_code == 200
    corpo = resp.json()
    assert [loja["nome"] for loja in corpo["itens"]] == ["A", "B", "C"]
    assert set(corpo["itens"][0]) == {"id", "nome", "criado_em"}
    assert corpo["proximo_cursor"] is None


async def test_lista_lojas_pagina_por_cursor(client):
    for i in range(7):
        await criar_loja(client, f"L{i}")

    itens, paginas = await _todas_as_paginas(client, "/lojas", limite=3)

    assert [loja["nome"] for loja in itens] == [f"L{i}" for i in range(7)]
    assert paginas == 3


@pytest.mark.parametrize(
    ("busca", "esperado"),
    [("moda", ["Moda da Ana", "Super Moda"]), ("%", ["100% Natural"]), ("_", ["Loja_X"])],
)
async def test_lista_lojas_filtra_por_nome_sem_interpretar_curingas(client, busca, esperado):
    for nome in ["Moda da Ana", "Tech", "Super Moda", "100% Natural", "Loja_X"]:
        await criar_loja(client, nome)

    resp = await client.get("/lojas", params={"q": busca})

    assert [loja["nome"] for loja in resp.json()["itens"]] == esperado


# --- GET /lojas/{id} -----------------------------------------------------------


async def test_detalha_loja_com_total_de_seguidores(client):
    loja = await criar_loja(client, "Loja da Ana")
    for _ in range(3):
        await seguir(client, await criar_cliente(client), loja["id"])

    resp = await client.get(f"/lojas/{loja['id']}")

    assert resp.status_code == 200
    assert resp.json() == {
        "id": loja["id"],
        "nome": "Loja da Ana",
        "criado_em": loja["criado_em"],
        "total_seguidores": 3,
    }


async def test_detalhar_loja_inexistente_retorna_404(client):
    assert_erro(await client.get("/lojas/999"), 404, "loja_nao_encontrada")


# --- GET /lojas/{id}/novidades ---------------------------------------------------


async def test_lista_novidades_da_loja_mais_recente_primeiro_e_so_dela(client):
    loja = await criar_loja(client)
    outra = await criar_loja(client)
    for i in range(5):
        await publicar(client, loja, f"N{i}")
    await publicar(client, outra, "de outra loja")

    itens, paginas = await _todas_as_paginas(client, f"/lojas/{loja['id']}/novidades", limite=2)

    assert [n["texto"] for n in itens] == ["N4", "N3", "N2", "N1", "N0"]
    assert paginas == 3


async def test_novidades_com_mesmo_horario_nao_se_perdem_na_paginacao(client, engine):
    loja = await criar_loja(client)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO novidades (loja_id, texto, criado_em) "
                "SELECT :loja, 'n' || g, '2026-01-01T12:00:00Z' FROM generate_series(1, 5) g"
            ),
            {"loja": loja["id"]},
        )

    itens, _ = await _todas_as_paginas(client, f"/lojas/{loja['id']}/novidades", limite=2)

    assert [n["id"] for n in itens] == [5, 4, 3, 2, 1]


async def test_novidades_de_loja_inexistente_retorna_404(client):
    assert_erro(await client.get("/lojas/999/novidades"), 404, "loja_nao_encontrada")


def _cursor(dados: dict) -> str:
    import base64
    import json

    return base64.urlsafe_b64encode(json.dumps(dados).encode()).decode().rstrip("=")


@pytest.mark.parametrize("rota", ["/lojas", "/lojas/1/novidades"])
@pytest.mark.parametrize(
    "cursor",
    [
        "lixo",
        _cursor({"id": 2**64}),  # estouraria o BIGINT no Postgres
        _cursor({"id": 0}),
        _cursor({"id": -1}),
        _cursor({"c": "2026-01-01T00:00:00+00:00", "id": 2**70}),
        _cursor([1, 2]),
    ],
    ids=["lixo", "id_gigante", "id_zero", "id_negativo", "posicao_id_gigante", "nao_objeto"],
)
async def test_cursor_invalido_nas_listas_de_lojas_retorna_422(client, rota, cursor):
    await criar_loja(client)

    resp = await client.get(rota, params={"cursor": cursor})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "cursor"


# --- GET /clientes/{id}/seguindo -------------------------------------------------


async def test_lista_lojas_seguidas_mais_recentes_primeiro(client):
    cliente = await criar_cliente(client)
    lojas = [await criar_loja(client, f"L{i}") for i in range(5)]
    for loja in lojas:
        await seguir(client, cliente, loja["id"])
    await criar_loja(client, "não seguida")

    itens, paginas = await _todas_as_paginas(
        client, f"/clientes/{cliente['id']}/seguindo", headers=auth(cliente), limite=2
    )

    assert [i["loja"]["nome"] for i in itens] == ["L4", "L3", "L2", "L1", "L0"]
    assert set(itens[0]) == {"loja", "seguindo_desde"}
    assert paginas == 3


async def test_lojas_seguidas_exige_token_do_proprio_cliente(client):
    ana = await criar_cliente(client)
    bia = await criar_cliente(client)

    sem_token = await client.get(f"/clientes/{bia['id']}/seguindo")
    outro = await client.get(f"/clientes/{bia['id']}/seguindo", headers=auth(ana))

    assert_erro(sem_token, 401, "nao_autenticado")
    assert_erro(outro, 403, "acesso_negado")
