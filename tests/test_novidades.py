import pytest

from tests.helpers import assert_erro, auth, criar_loja


async def test_publica_novidade_sem_preco(client):
    loja = await criar_loja(client)

    resp = await client.post(
        f"/lojas/{loja['id']}/novidades", json={"texto": "Live hoje às 20h"}, headers=auth(loja)
    )

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
        f"/lojas/{loja['id']}/novidades",
        json={"texto": "Promo", "preco": enviado},
        headers=auth(loja),
    )

    assert resp.status_code == 201
    assert resp.json()["preco"] == esperado


@pytest.mark.parametrize("texto", ["x", "x" * 500])
async def test_texto_nos_limites_e_aceito(client, texto):
    loja = await criar_loja(client)

    resp = await client.post(
        f"/lojas/{loja['id']}/novidades", json={"texto": texto}, headers=auth(loja)
    )

    assert resp.status_code == 201


@pytest.mark.parametrize("texto", ["", "   ", "x" * 501, None])
async def test_texto_invalido_retorna_422(client, texto):
    loja = await criar_loja(client)

    resp = await client.post(
        f"/lojas/{loja['id']}/novidades", json={"texto": texto}, headers=auth(loja)
    )

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "texto"


async def test_texto_obrigatorio(client):
    loja = await criar_loja(client)

    resp = await client.post(
        f"/lojas/{loja['id']}/novidades", json={"preco": "10"}, headers=auth(loja)
    )

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0] == {"campo": "texto", "mensagem": "Campo obrigatório."}


@pytest.mark.parametrize("preco", [0, "0", -1, "-0.01", "abc", "10.123"])
async def test_preco_invalido_retorna_422(client, preco):
    loja = await criar_loja(client)

    resp = await client.post(
        f"/lojas/{loja['id']}/novidades",
        json={"texto": "Promo", "preco": preco},
        headers=auth(loja),
    )

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "preco"


async def test_publicar_exige_token_de_lojista(client):
    loja = await criar_loja(client)

    resp = await client.post(f"/lojas/{loja['id']}/novidades", json={"texto": "Oi"})

    assert_erro(resp, 401, "nao_autenticado")


async def test_publicar_em_outra_loja_retorna_403(client):
    # Também cobre "loja inexistente": o token nunca é de um id que não existe.
    minha = await criar_loja(client)
    outra = await criar_loja(client)

    for loja_id in (outra["id"], 999):
        resp = await client.post(
            f"/lojas/{loja_id}/novidades", json={"texto": "Oi"}, headers=auth(minha)
        )
        assert_erro(resp, 403, "acesso_negado")
