from tests.helpers import assert_erro, criar_cliente, criar_loja, seguir


async def test_cliente_segue_loja(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)

    resp = await client.post(f"/clientes/{cliente['id']}/seguindo/{loja['id']}")

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["cliente_id"] == cliente["id"]
    assert corpo["loja_id"] == loja["id"]
    assert corpo["criado_em"]


async def test_seguir_com_cliente_inexistente_retorna_404(client):
    loja = await criar_loja(client)

    resp = await client.post(f"/clientes/999/seguindo/{loja['id']}")

    assert_erro(resp, 404, "cliente_nao_encontrado")


async def test_seguir_loja_inexistente_retorna_404(client):
    cliente = await criar_cliente(client)

    resp = await client.post(f"/clientes/{cliente['id']}/seguindo/999")

    assert_erro(resp, 404, "loja_nao_encontrada")


async def test_seguir_a_mesma_loja_duas_vezes_retorna_409(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    await seguir(client, cliente["id"], loja["id"])

    resp = await client.post(f"/clientes/{cliente['id']}/seguindo/{loja['id']}")

    assert_erro(resp, 409, "ja_segue_loja")


async def test_seguir_com_id_nao_numerico_retorna_422(client):
    resp = await client.post("/clientes/abc/seguindo/1")

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "cliente_id"
