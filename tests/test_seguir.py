from tests.helpers import assert_erro, auth, criar_cliente, criar_loja, publicar, seguir


def _rota(cliente: dict, loja_id: int) -> str:
    return f"/clientes/{cliente['id']}/seguindo/{loja_id}"


async def test_cliente_segue_loja(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)

    resp = await client.post(_rota(cliente, loja["id"]), headers=auth(cliente))

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["cliente_id"] == cliente["id"]
    assert corpo["loja_id"] == loja["id"]
    assert corpo["criado_em"]


async def test_seguir_exige_token(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)

    resp = await client.post(_rota(cliente, loja["id"]))

    assert_erro(resp, 401, "nao_autenticado")


async def test_seguir_em_nome_de_outro_cliente_retorna_403(client):
    # Também cobre "cliente inexistente": o token nunca é de um id que não existe.
    ana = await criar_cliente(client)
    loja = await criar_loja(client)

    resp = await client.post(f"/clientes/999/seguindo/{loja['id']}", headers=auth(ana))

    assert_erro(resp, 403, "acesso_negado")


async def test_seguir_loja_inexistente_retorna_404(client):
    cliente = await criar_cliente(client)

    resp = await client.post(_rota(cliente, 999), headers=auth(cliente))

    assert_erro(resp, 404, "loja_nao_encontrada")


async def test_seguir_a_mesma_loja_duas_vezes_retorna_409(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente, loja["id"])

    resp = await client.post(_rota(cliente, loja["id"]), headers=auth(cliente))

    assert_erro(resp, 409, "ja_segue_loja")


async def test_seguir_com_id_nao_numerico_retorna_422(client):
    resp = await client.post("/clientes/abc/seguindo/1")

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "cliente_id"


async def test_deixar_de_seguir_remove_lojas_do_feed(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente, loja["id"])
    await publicar(client, loja, "some do feed")

    resp = await client.delete(_rota(cliente, loja["id"]), headers=auth(cliente))

    assert resp.status_code == 204
    assert resp.content == b""
    feed = await client.get(f"/clientes/{cliente['id']}/feed", headers=auth(cliente))
    assert feed.json()["itens"] == []


async def test_pode_seguir_de_novo_depois_de_deixar(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente, loja["id"])
    await client.delete(_rota(cliente, loja["id"]), headers=auth(cliente))

    resp = await client.post(_rota(cliente, loja["id"]), headers=auth(cliente))

    assert resp.status_code == 201


async def test_deixar_de_seguir_loja_que_nao_segue_retorna_404(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)

    resp = await client.delete(_rota(cliente, loja["id"]), headers=auth(cliente))

    assert_erro(resp, 404, "nao_segue_loja")


async def test_deixar_de_seguir_loja_inexistente_retorna_404(client):
    cliente = await criar_cliente(client)

    resp = await client.delete(_rota(cliente, 999), headers=auth(cliente))

    assert_erro(resp, 404, "loja_nao_encontrada")


async def test_deixar_de_seguir_exige_token_do_proprio_cliente(client):
    ana = await criar_cliente(client)
    bia = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, bia, loja["id"])

    sem_token = await client.delete(_rota(bia, loja["id"]))
    token_da_ana = await client.delete(_rota(bia, loja["id"]), headers=auth(ana))

    assert_erro(sem_token, 401, "nao_autenticado")
    assert_erro(token_da_ana, 403, "acesso_negado")
