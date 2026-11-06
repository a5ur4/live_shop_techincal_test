import pytest

from tests.helpers import assert_erro, criar_loja


async def test_publica_novidade_sem_preco(client):
    loja = await criar_loja(client)

    resp = await client.post(f"/lojas/{loja['id']}/novidades", json={"texto": "Live hoje às 20h"})

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["loja_id"] == loja["id"]
    assert corpo["texto"] == "Live hoje às 20h"
    assert corpo["preco"] is None
    assert corpo["criado_em"]


@pytest.mark.parametrize(
    ("enviado", "esperado"), [("199.90", "199.90"), (10, "10.00"), (0.01, "0.01")]
)
async def test_publica_novidade_com_preco(client, enviado, esperado):
    loja = await criar_loja(client)

    resp = await client.post(
        f"/lojas/{loja['id']}/novidades", json={"texto": "Promo", "preco": enviado}
    )

    assert resp.status_code == 201
    assert resp.json()["preco"] == esperado


@pytest.mark.parametrize("texto", ["x", "x" * 500])
async def test_texto_nos_limites_e_aceito(client, texto):
    loja = await criar_loja(client)

    resp = await client.post(f"/lojas/{loja['id']}/novidades", json={"texto": texto})

    assert resp.status_code == 201


@pytest.mark.parametrize("texto", ["", "   ", "x" * 501, None])
async def test_texto_invalido_retorna_422(client, texto):
    loja = await criar_loja(client)

    resp = await client.post(f"/lojas/{loja['id']}/novidades", json={"texto": texto})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "texto"


async def test_texto_obrigatorio(client):
    loja = await criar_loja(client)

    resp = await client.post(f"/lojas/{loja['id']}/novidades", json={"preco": "10"})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0] == {"campo": "texto", "mensagem": "Campo obrigatório."}


@pytest.mark.parametrize("preco", [0, "0", -1, "-0.01", "abc", "10.123"])
async def test_preco_invalido_retorna_422(client, preco):
    loja = await criar_loja(client)

    resp = await client.post(
        f"/lojas/{loja['id']}/novidades", json={"texto": "Promo", "preco": preco}
    )

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "preco"


async def test_publicar_em_loja_inexistente_retorna_404(client):
    resp = await client.post("/lojas/999/novidades", json={"texto": "Oi"})

    assert_erro(resp, 404, "loja_nao_encontrada")
