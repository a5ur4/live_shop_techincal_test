import pytest

from tests.helpers import SENHA, assert_erro, criar_cliente, criar_loja

LOJA_VALIDA = {"nome": "Loja da Ana", "email": "ana@lojadaana.com", "senha": SENHA}
CLIENTE_VALIDO = {"nome": "João", "email": "joao@example.com", "senha": SENHA}


async def test_cria_loja(client):
    resp = await client.post("/lojas", json=LOJA_VALIDA | {"nome": "  Loja da Ana  "})

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["id"] == 1
    assert corpo["nome"] == "Loja da Ana"
    assert corpo["email"] == "ana@lojadaana.com"
    assert corpo["criado_em"]


@pytest.mark.parametrize("dados", [LOJA_VALIDA, CLIENTE_VALIDO])
async def test_resposta_do_cadastro_nao_expoe_senha(client, dados):
    rota = "/lojas" if dados is LOJA_VALIDA else "/clientes"

    resp = await client.post(rota, json=dados)

    assert resp.status_code == 201
    assert not {"senha", "senha_hash"} & set(resp.json())


@pytest.mark.parametrize(
    "nome",
    [None, "", "   ", 123, "x" * 121],
    ids=["ausente", "vazio", "espacos", "numero", "longo"],
)
async def test_loja_exige_nome_valido(client, nome):
    corpo = {k: v for k, v in LOJA_VALIDA.items() if k != "nome"}
    if nome is not None:
        corpo["nome"] = nome

    resp = await client.post("/lojas", json=corpo)

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert [d["campo"] for d in erro["detalhes"]] == ["nome"]


@pytest.mark.parametrize("rota", ["/lojas", "/clientes"])
@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("email", None),
        ("email", "nao-e-email"),
        ("senha", None),
        ("senha", "curta"),
        ("senha", "x" * 129),
    ],
)
async def test_cadastro_exige_email_e_senha_validos(client, rota, campo, valor):
    corpo = dict(LOJA_VALIDA if rota == "/lojas" else CLIENTE_VALIDO)
    if valor is None:
        del corpo[campo]
    else:
        corpo[campo] = valor

    resp = await client.post(rota, json=corpo)

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert [d["campo"] for d in erro["detalhes"]] == [campo]


async def test_cria_cliente_normalizando_email(client):
    resp = await client.post("/clientes", json=CLIENTE_VALIDO | {"email": "Joao@Example.COM"})

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["nome"] == "João"
    assert corpo["email"] == "joao@example.com"


async def test_cliente_exige_nome(client):
    resp = await client.post("/clientes", json=CLIENTE_VALIDO | {"nome": ""})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert [d["campo"] for d in erro["detalhes"]] == ["nome"]


async def test_email_de_cliente_duplicado_retorna_409(client):
    await criar_cliente(client, email="ana@example.com")

    resp = await client.post("/clientes", json=CLIENTE_VALIDO | {"email": "ANA@example.com"})

    assert_erro(resp, 409, "email_ja_cadastrado")


async def test_email_de_loja_duplicado_retorna_409(client):
    await criar_loja(client, email="contato@loja.com")

    resp = await client.post("/lojas", json=LOJA_VALIDA | {"email": "Contato@Loja.com"})

    assert_erro(resp, 409, "email_ja_cadastrado")


async def test_mesmo_email_pode_ser_cliente_e_loja(client):
    # Contas independentes, com logins separados (ver ADR 0007).
    await criar_cliente(client, email="ana@example.com")

    resp = await client.post("/lojas", json=LOJA_VALIDA | {"email": "ana@example.com"})

    assert resp.status_code == 201


async def test_campo_desconhecido_e_rejeitado(client):
    # Evita que um erro de digitação ("nomee") passe despercebido.
    resp = await client.post("/lojas", json=LOJA_VALIDA | {"nomee": "x"})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "nomee"
