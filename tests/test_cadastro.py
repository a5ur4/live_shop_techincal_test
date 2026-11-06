import pytest

from tests.helpers import assert_erro, criar_cliente


async def test_cria_loja(client):
    resp = await client.post("/lojas", json={"nome": "  Loja da Ana  "})

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["id"] == 1
    assert corpo["nome"] == "Loja da Ana"
    assert corpo["criado_em"]


@pytest.mark.parametrize(
    "corpo",
    [{}, {"nome": ""}, {"nome": "   "}, {"nome": None}, {"nome": 123}, {"nome": "x" * 121}],
)
async def test_loja_exige_nome_valido(client, corpo):
    resp = await client.post("/lojas", json=corpo)

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "nome"


async def test_cria_cliente_normalizando_email(client):
    resp = await client.post("/clientes", json={"nome": "João", "email": "Joao@Example.COM"})

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["nome"] == "João"
    assert corpo["email"] == "joao@example.com"


@pytest.mark.parametrize(
    ("corpo", "campo"),
    [
        ({"email": "a@example.com"}, "nome"),
        ({"nome": "Ana"}, "email"),
        ({"nome": "Ana", "email": "nao-e-email"}, "email"),
        ({"nome": "", "email": "a@example.com"}, "nome"),
    ],
)
async def test_cliente_exige_campos_validos(client, corpo, campo):
    resp = await client.post("/clientes", json=corpo)

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert campo in [d["campo"] for d in erro["detalhes"]]


async def test_email_duplicado_retorna_409(client):
    await criar_cliente(client, email="ana@example.com")

    resp = await client.post("/clientes", json={"nome": "Outra Ana", "email": "ANA@example.com"})

    assert_erro(resp, 409, "email_ja_cadastrado")


async def test_campo_desconhecido_e_rejeitado(client):
    # Evita que um erro de digitação ("nomee") passe despercebido.
    resp = await client.post("/lojas", json={"nome": "Loja", "nomee": "x"})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "nomee"
