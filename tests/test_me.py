"""Rotas /me: mesma regra das rotas com {id}, mas a conta vem do token."""

import pytest

from tests.helpers import assert_erro, auth, criar_cliente, criar_loja, publicar, seguir


@pytest.mark.parametrize(("tipo", "criar"), [("cliente", criar_cliente), ("loja", criar_loja)])
async def test_perfil_da_conta_logada(client, tipo, criar):
    conta = await criar(client, nome="Ana", email="ana@example.com")

    resp = await client.get("/me", headers=auth(conta))

    assert resp.status_code == 200
    assert resp.json() == {
        "tipo": tipo,
        "id": conta["id"],
        "nome": "Ana",
        "email": "ana@example.com",
        "criado_em": conta["criado_em"],
    }


async def test_perfil_sem_token_retorna_401(client):
    assert_erro(await client.get("/me"), 401, "nao_autenticado")


async def test_cliente_segue_le_feed_e_lista_seguidas_pelo_me(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client, "Loja da Ana")
    await publicar(client, loja, "novidade")

    seguiu = await client.post(f"/me/seguindo/{loja['id']}", headers=auth(cliente))
    feed = await client.get("/me/feed", headers=auth(cliente))
    seguidas = await client.get("/me/seguindo", headers=auth(cliente))

    assert seguiu.status_code == 201
    assert seguiu.json()["cliente_id"] == cliente["id"]
    assert [i["texto"] for i in feed.json()["itens"]] == ["novidade"]
    assert [i["loja"]["nome"] for i in seguidas.json()["itens"]] == ["Loja da Ana"]


async def test_feed_pelo_me_e_igual_ao_feed_pelo_id(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente, loja["id"])
    for i in range(3):
        await publicar(client, loja, f"N{i}")

    pelo_me = await client.get("/me/feed", params={"limite": 2}, headers=auth(cliente))
    pelo_id = await client.get(
        f"/clientes/{cliente['id']}/feed", params={"limite": 2}, headers=auth(cliente)
    )

    assert pelo_me.json() == pelo_id.json()


async def test_deixar_de_seguir_pelo_me(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente, loja["id"])

    primeira = await client.delete(f"/me/seguindo/{loja['id']}", headers=auth(cliente))
    segunda = await client.delete(f"/me/seguindo/{loja['id']}", headers=auth(cliente))

    assert primeira.status_code == 204
    assert_erro(segunda, 404, "nao_segue_loja")


async def test_seguir_pelo_me_mantem_regras_de_404_e_409(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente, loja["id"])

    assert_erro(
        await client.post(f"/me/seguindo/{loja['id']}", headers=auth(cliente)), 409, "ja_segue_loja"
    )
    assert_erro(
        await client.post("/me/seguindo/999", headers=auth(cliente)), 404, "loja_nao_encontrada"
    )


async def test_lojista_publica_e_lista_as_proprias_novidades_pelo_me(client):
    loja = await criar_loja(client)
    outra = await criar_loja(client)
    await publicar(client, outra, "da outra")

    resp = await client.post("/me/novidades", json={"texto": "minha"}, headers=auth(loja))
    minhas = await client.get("/me/novidades", headers=auth(loja))

    assert resp.status_code == 201
    assert resp.json()["loja_id"] == loja["id"]
    assert [n["texto"] for n in minhas.json()["itens"]] == ["minha"]


@pytest.mark.parametrize(
    ("metodo", "rota", "conta_errada"),
    [
        ("get", "/me/feed", "loja"),
        ("get", "/me/seguindo", "loja"),
        ("post", "/me/seguindo/1", "loja"),
        ("delete", "/me/seguindo/1", "loja"),
        ("get", "/me/novidades", "cliente"),
        ("post", "/me/novidades", "cliente"),
    ],
)
async def test_rotas_me_exigem_o_tipo_certo_de_conta(client, metodo, rota, conta_errada):
    conta = await (criar_loja if conta_errada == "loja" else criar_cliente)(client)
    kwargs = {"json": {"texto": "x"}} if metodo == "post" and "novidades" in rota else {}

    resp = await client.request(metodo, rota, headers=auth(conta), **kwargs)

    assert_erro(resp, 403, "acesso_negado")
