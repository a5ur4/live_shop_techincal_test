"""Login (OAuth2 password flow), validação do JWT e regra "o token é do dono do {id}"."""

from datetime import timedelta

import jwt
import pytest

from app.core.security import criar_token
from tests.helpers import SENHA, assert_erro, auth, criar_cliente, criar_loja, login


@pytest.mark.parametrize(("tipo", "criar"), [("clientes", criar_cliente), ("lojas", criar_loja)])
async def test_login_devolve_access_token_bearer(client, tipo, criar):
    conta = await criar(client, email="ana@example.com")

    resp = await login(client, tipo, "ANA@example.com")  # e-mail não diferencia maiúsculas

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["expires_in"] == 30 * 60
    assert jwt.decode(corpo["access_token"], options={"verify_signature": False})["sub"] == str(
        conta["id"]
    )


@pytest.mark.parametrize(
    ("email", "senha"),
    [("ana@example.com", "senha-errada"), ("ninguem@example.com", SENHA)],
    ids=["senha_errada", "email_inexistente"],
)
async def test_login_invalido_retorna_401_sem_revelar_o_motivo(client, email, senha):
    await criar_cliente(client, email="ana@example.com")

    resp = await login(client, "clientes", email, senha)

    erro = assert_erro(resp, 401, "credenciais_invalidas")
    assert erro["mensagem"] == "E-mail ou senha incorretos."


async def test_credencial_de_cliente_nao_loga_como_lojista(client):
    await criar_cliente(client, email="ana@example.com")

    resp = await login(client, "lojas", "ana@example.com")

    assert_erro(resp, 401, "credenciais_invalidas")


async def test_login_sem_campos_retorna_422(client):
    resp = await client.post("/auth/clientes/token", data={})

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert {d["campo"] for d in erro["detalhes"]} == {"username", "password"}


async def test_rota_protegida_sem_token_retorna_401_com_www_authenticate(client):
    cliente = await criar_cliente(client)

    resp = await client.get(f"/clientes/{cliente['id']}/feed")

    assert_erro(resp, 401, "nao_autenticado")
    assert resp.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "token",
    [
        "nao-e-um-jwt",
        jwt.encode(
            {"sub": "1", "tipo": "cliente", "exp": 9999999999},
            "outra-chave-com-pelo-menos-32-bytes!!",
        ),
        criar_token("cliente", 1, expira_em=timedelta(seconds=-1)).access_token,
    ],
    ids=["malformado", "assinatura_invalida", "expirado"],
)
async def test_token_invalido_retorna_401(client, token):
    cliente = await criar_cliente(client)
    assert cliente["id"] == 1

    resp = await client.get("/clientes/1/feed", headers={"Authorization": f"Bearer {token}"})

    assert_erro(resp, 401, "nao_autenticado")


async def test_token_de_lojista_nao_acessa_rota_de_cliente(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)
    assert cliente["id"] == loja["id"]  # mesmo id numérico, tipos diferentes

    resp = await client.get(f"/clientes/{cliente['id']}/feed", headers=auth(loja))

    assert_erro(resp, 403, "acesso_negado")


async def test_token_de_cliente_nao_publica_novidade(client):
    cliente = await criar_cliente(client)
    loja = await criar_loja(client)

    resp = await client.post(
        f"/lojas/{loja['id']}/novidades", json={"texto": "Oi"}, headers=auth(cliente)
    )

    assert_erro(resp, 403, "acesso_negado")


async def test_cadastro_e_health_sao_publicos(client):
    assert (await client.get("/health")).status_code == 200
    assert (
        await client.post("/lojas", json={"nome": "L", "email": "l@x.com", "senha": SENHA})
    ).status_code == 201
