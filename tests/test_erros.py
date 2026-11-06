"""O formato de erro precisa ser o mesmo em toda a API, inclusive fora das rotas."""

from tests.helpers import assert_erro


async def test_rota_inexistente_usa_formato_padrao(client):
    resp = await client.get("/nao-existe")

    assert_erro(resp, 404, "rota_nao_encontrada")


async def test_metodo_nao_permitido_usa_formato_padrao(client):
    resp = await client.delete("/lojas")

    assert_erro(resp, 405, "metodo_nao_permitido")


async def test_json_malformado_usa_formato_padrao(client):
    resp = await client.post(
        "/lojas", content=b"{nome: sem aspas", headers={"content-type": "application/json"}
    )

    assert_erro(resp, 422, "entrada_invalida")


async def test_corpo_que_nao_e_objeto_usa_formato_padrao(client):
    resp = await client.post("/lojas", json=["nome"])

    assert_erro(resp, 422, "entrada_invalida")
