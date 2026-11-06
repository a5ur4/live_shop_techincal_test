"""Refresh token (rotação e reuso), logout, rate limit do login e troca de senha."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.redis import ResilientRedis, get_redis
from app.main import app
from tests.helpers import SENHA, assert_erro, auth, criar_cliente, criar_loja, login


async def _tokens(client, tipo="clientes", email="ana@example.com", senha=SENHA) -> dict:
    resp = await login(client, tipo, email, senha)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _refresh(client, refresh_token: str):
    return await client.post("/auth/refresh", json={"refresh_token": refresh_token})


# --- Refresh token -------------------------------------------------------------------


async def test_login_devolve_refresh_token(client):
    await criar_cliente(client, email="ana@example.com")

    tokens = await _tokens(client)

    assert tokens["refresh_token"]
    assert tokens["refresh_expires_in"] == 30 * 24 * 3600


@pytest.mark.parametrize(("tipo", "criar"), [("clientes", criar_cliente), ("lojas", criar_loja)])
async def test_refresh_gera_novo_par_que_funciona(client, tipo, criar):
    conta = await criar(client, email="ana@example.com")
    tokens = await _tokens(client, tipo)

    resp = await _refresh(client, tokens["refresh_token"])

    assert resp.status_code == 200
    novos = resp.json()
    assert novos["refresh_token"] != tokens["refresh_token"]
    perfil = await client.get("/me", headers={"Authorization": f"Bearer {novos['access_token']}"})
    assert perfil.json()["id"] == conta["id"]


async def test_refresh_ja_usado_e_rejeitado_e_derruba_a_sessao(client):
    await criar_cliente(client, email="ana@example.com")
    original = await _tokens(client)
    rotacionado = (await _refresh(client, original["refresh_token"])).json()

    # Alguém reapresenta o token antigo (vazado): rejeita e revoga a família toda...
    reuso = await _refresh(client, original["refresh_token"])
    # ...inclusive o token legítimo mais novo.
    depois = await _refresh(client, rotacionado["refresh_token"])

    assert_erro(reuso, 401, "refresh_invalido")
    assert_erro(depois, 401, "refresh_invalido")


async def test_reuso_nao_afeta_outras_sessoes_da_mesma_conta(client):
    await criar_cliente(client, email="ana@example.com")
    celular = await _tokens(client)
    notebook = await _tokens(client)
    await _refresh(client, celular["refresh_token"])

    await _refresh(client, celular["refresh_token"])  # reuso no celular

    assert (await _refresh(client, notebook["refresh_token"])).status_code == 200


async def test_refresh_expirado_ou_desconhecido_retorna_401(client, engine):
    await criar_cliente(client, email="ana@example.com")
    tokens = await _tokens(client)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE refresh_tokens SET expira_em = :passado"),
            {"passado": datetime.now(UTC) - timedelta(seconds=1)},
        )

    assert_erro(await _refresh(client, tokens["refresh_token"]), 401, "refresh_invalido")
    assert_erro(await _refresh(client, "nao-existe"), 401, "refresh_invalido")


async def test_banco_guarda_so_o_hash_do_refresh(client, engine):
    await criar_cliente(client, email="ana@example.com")
    tokens = await _tokens(client)

    async with engine.connect() as conn:
        hashes = (await conn.execute(text("SELECT token_hash FROM refresh_tokens"))).scalars()
        guardados = list(hashes)

    assert tokens["refresh_token"] not in guardados
    assert all(len(h) == 64 for h in guardados)


# --- Logout --------------------------------------------------------------------------


async def test_logout_revoga_o_refresh(client):
    await criar_cliente(client, email="ana@example.com")
    tokens = await _tokens(client)

    resp = await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    assert resp.status_code == 204
    assert_erro(await _refresh(client, tokens["refresh_token"]), 401, "refresh_invalido")


async def test_logout_e_idempotente(client):
    for _ in range(2):
        resp = await client.post("/auth/logout", json={"refresh_token": "qualquer"})
        assert resp.status_code == 204


# --- Rate limit do login -------------------------------------------------------------


async def test_cinco_falhas_bloqueiam_o_email_com_retry_after(client):
    await criar_cliente(client, email="ana@example.com")
    for _ in range(5):
        assert_erro(
            await login(client, "clientes", "ana@example.com", "errada"),
            401,
            "credenciais_invalidas",
        )

    # Bloqueado mesmo com a senha certa: senão o atacante saberia quando acertou.
    resp = await login(client, "clientes", "ana@example.com", SENHA)

    assert_erro(resp, 429, "muitas_tentativas")
    assert 0 < int(resp.headers["retry-after"]) <= 15 * 60


async def test_bloqueio_e_por_email_e_por_tipo_de_conta(client):
    await criar_cliente(client, email="ana@example.com")
    await criar_cliente(client, email="bia@example.com")
    await criar_loja(client, email="ana@example.com")
    for _ in range(5):
        await login(client, "clientes", "ana@example.com", "errada")

    assert (await login(client, "clientes", "bia@example.com")).status_code == 200
    assert (await login(client, "lojas", "ana@example.com")).status_code == 200


async def test_login_certo_zera_as_falhas_do_email(client):
    await criar_cliente(client, email="ana@example.com")
    for _ in range(4):
        await login(client, "clientes", "ana@example.com", "errada")
    assert (await login(client, "clientes", "ana@example.com")).status_code == 200

    for _ in range(4):
        await login(client, "clientes", "ana@example.com", "errada")

    assert (await login(client, "clientes", "ana@example.com")).status_code == 200


async def test_vinte_falhas_do_mesmo_ip_bloqueiam_qualquer_email(client):
    await criar_cliente(client, email="vitima@example.com")
    for i in range(20):
        await login(client, "clientes", f"tentativa{i}@example.com", "errada")

    assert_erro(await login(client, "clientes", "vitima@example.com"), 429, "muitas_tentativas")


@pytest.fixture
def sem_redis(monkeypatch):
    from app.services import rate_limit

    monkeypatch.setattr(rate_limit, "_local", rate_limit._ContadorLocal())
    app.dependency_overrides[get_redis] = lambda: ResilientRedis(None)


async def test_sem_redis_o_login_continua_funcionando(client, sem_redis):
    await criar_cliente(client, email="ana@example.com")

    assert (await login(client, "clientes", "ana@example.com")).status_code == 200


async def test_sem_redis_o_rate_limit_continua_valendo_em_memoria(client, sem_redis):
    # Derrubar o Redis não pode virar passe livre para força bruta.
    await criar_cliente(client, email="ana@example.com")
    for _ in range(5):
        await login(client, "clientes", "ana@example.com", "errada")

    resp = await login(client, "clientes", "ana@example.com")

    assert_erro(resp, 429, "muitas_tentativas")
    assert int(resp.headers["retry-after"]) > 0


# --- Troca de senha ------------------------------------------------------------------


async def test_troca_de_senha_vale_no_proximo_login_e_encerra_sessoes(client):
    cliente = await criar_cliente(client, email="ana@example.com")
    sessao = await _tokens(client)

    resp = await client.put(
        "/me/senha",
        json={"senha_atual": SENHA, "nova_senha": "nova-senha-123"},
        headers=auth(cliente),
    )

    assert resp.status_code == 204
    assert_erro(await login(client, "clientes", "ana@example.com"), 401, "credenciais_invalidas")
    assert (await login(client, "clientes", "ana@example.com", "nova-senha-123")).status_code == 200
    assert_erro(await _refresh(client, sessao["refresh_token"]), 401, "refresh_invalido")


async def test_troca_de_senha_de_lojista(client):
    loja = await criar_loja(client, email="loja@example.com")

    resp = await client.put(
        "/me/senha", json={"senha_atual": SENHA, "nova_senha": "nova-senha-123"}, headers=auth(loja)
    )

    assert resp.status_code == 204
    assert (await login(client, "lojas", "loja@example.com", "nova-senha-123")).status_code == 200


@pytest.mark.parametrize(
    ("corpo", "campo"),
    [
        ({"senha_atual": "errada", "nova_senha": "nova-senha-123"}, "senha_atual"),
        ({"senha_atual": SENHA, "nova_senha": "curta"}, "nova_senha"),
    ],
)
async def test_troca_de_senha_invalida_retorna_422(client, corpo, campo):
    cliente = await criar_cliente(client)

    resp = await client.put("/me/senha", json=corpo, headers=auth(cliente))

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert [d["campo"] for d in erro["detalhes"]] == [campo]


async def test_troca_de_senha_exige_token(client):
    resp = await client.put("/me/senha", json={"senha_atual": "a", "nova_senha": "b" * 8})

    assert_erro(resp, 401, "nao_autenticado")
