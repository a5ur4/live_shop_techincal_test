"""Editar e remover novidades: só a loja dona, pela rota com id ou por /me."""

import pytest

from tests.helpers import assert_erro, auth, criar_cliente, criar_loja, publicar, seguir


def _rota(loja: dict, novidade: dict, via_me: bool) -> str:
    if via_me:
        return f"/me/novidades/{novidade['id']}"
    return f"/lojas/{loja['id']}/novidades/{novidade['id']}"


@pytest.mark.parametrize("via_me", [False, True])
async def test_edita_texto_e_preco(client, via_me):
    loja = await criar_loja(client)
    novidade = await publicar(client, loja, "Original", preco="10.00")

    resp = await client.patch(
        _rota(loja, novidade, via_me), json={"texto": "Editada", "preco": 25}, headers=auth(loja)
    )

    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["id"] == novidade["id"]
    assert corpo["texto"] == "Editada"
    assert corpo["preco"] == "25.00"
    assert corpo["criado_em"] == novidade["criado_em"]
    assert novidade["editado_em"] is None
    assert corpo["editado_em"] is not None


async def test_edicao_parcial_mantem_campos_nao_enviados(client):
    loja = await criar_loja(client)
    novidade = await publicar(client, loja, "Original", preco="10.00")

    resp = await client.patch(
        _rota(loja, novidade, False), json={"texto": "Só o texto"}, headers=auth(loja)
    )

    assert resp.json()["texto"] == "Só o texto"
    assert resp.json()["preco"] == "10.00"


async def test_preco_null_remove_o_preco(client):
    loja = await criar_loja(client)
    novidade = await publicar(client, loja, "Original", preco="10.00")

    resp = await client.patch(
        _rota(loja, novidade, False), json={"preco": None}, headers=auth(loja)
    )

    assert resp.json()["preco"] is None
    assert resp.json()["texto"] == "Original"


@pytest.mark.parametrize(
    ("corpo", "campo"),
    [
        ({}, None),
        ({"texto": None}, "texto"),
        ({"texto": "   "}, "texto"),
        ({"preco": 0}, "preco"),
        ({"loja_id": 2}, "loja_id"),
    ],
)
async def test_edicao_invalida_retorna_422(client, corpo, campo):
    loja = await criar_loja(client)
    novidade = await publicar(client, loja, "Original")

    resp = await client.patch(_rota(loja, novidade, False), json=corpo, headers=auth(loja))

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == campo


@pytest.mark.parametrize("via_me", [False, True])
async def test_remove_novidade(client, via_me):
    loja = await criar_loja(client)
    fica = await publicar(client, loja, "Fica")
    sai = await publicar(client, loja, "Sai")

    resp = await client.delete(_rota(loja, sai, via_me), headers=auth(loja))
    de_novo = await client.delete(_rota(loja, sai, via_me), headers=auth(loja))
    lista = await client.get(f"/lojas/{loja['id']}/novidades")

    assert resp.status_code == 204
    assert_erro(de_novo, 404, "novidade_nao_encontrada")
    assert [n["id"] for n in lista.json()["itens"]] == [fica["id"]]


@pytest.mark.parametrize("metodo", ["patch", "delete"])
async def test_novidade_de_outra_loja_retorna_404(client, metodo):
    dona = await criar_loja(client)
    outra = await criar_loja(client)
    novidade = await publicar(client, dona, "da dona")
    kwargs = {"json": {"texto": "invasão"}} if metodo == "patch" else {}

    # Pela rota da própria loja com o id de novidade alheia: não revela que ela existe.
    pela_rota = await getattr(client, metodo)(
        f"/lojas/{outra['id']}/novidades/{novidade['id']}", headers=auth(outra), **kwargs
    )
    pelo_me = await getattr(client, metodo)(
        f"/me/novidades/{novidade['id']}", headers=auth(outra), **kwargs
    )

    assert_erro(pela_rota, 404, "novidade_nao_encontrada")
    assert_erro(pelo_me, 404, "novidade_nao_encontrada")
    assert (await client.get(f"/lojas/{dona['id']}/novidades")).json()["itens"][0]["texto"] == (
        "da dona"
    )


@pytest.mark.parametrize("metodo", ["patch", "delete"])
async def test_rota_de_outra_loja_retorna_403(client, metodo):
    dona = await criar_loja(client)
    outra = await criar_loja(client)
    novidade = await publicar(client, dona, "da dona")
    kwargs = {"json": {"texto": "invasão"}} if metodo == "patch" else {}

    resp = await getattr(client, metodo)(
        f"/lojas/{dona['id']}/novidades/{novidade['id']}", headers=auth(outra), **kwargs
    )

    assert_erro(resp, 403, "acesso_negado")


async def test_cliente_nao_edita_novidade(client):
    loja = await criar_loja(client)
    cliente = await criar_cliente(client)
    novidade = await publicar(client, loja, "x")

    resp = await client.delete(f"/me/novidades/{novidade['id']}", headers=auth(cliente))

    assert_erro(resp, 403, "acesso_negado")


async def test_feed_mostra_texto_editado_e_esconde_removida(client):
    loja = await criar_loja(client, "Loja")
    cliente = await criar_cliente(client)
    await seguir(client, cliente, loja["id"])
    editada = await publicar(client, loja, "Antes")
    removida = await publicar(client, loja, "Some")

    await client.patch(_rota(loja, editada, True), json={"texto": "Depois"}, headers=auth(loja))
    await client.delete(_rota(loja, removida, True), headers=auth(loja))
    # Primeira leitura do feed: cache vazio, vem do banco (o atraso do cache é do ADR 0008).
    feed = await client.get("/me/feed", headers=auth(cliente))

    itens = feed.json()["itens"]
    assert [i["texto"] for i in itens] == ["Depois"]
    assert itens[0]["editado_em"] is not None
