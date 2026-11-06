"""Editar perfil e excluir conta (cliente e lojista), por /me ou pela rota com id."""

import pytest

from tests.helpers import (
    SENHA,
    assert_erro,
    auth,
    criar_cliente,
    criar_loja,
    login,
    publicar,
    seguir,
)

TIPOS = [("clientes", criar_cliente), ("lojas", criar_loja)]


async def _excluir(client, rota: str, conta: dict, senha: str = SENHA):
    return await client.request("DELETE", rota, json={"senha": senha}, headers=auth(conta))


# --- Editar ----------------------------------------------------------------------


@pytest.mark.parametrize(("tipo", "criar"), TIPOS)
@pytest.mark.parametrize("via_me", [False, True])
async def test_edita_nome_e_email(client, tipo, criar, via_me):
    conta = await criar(client, nome="Antigo", email="antigo@example.com")
    rota = "/me" if via_me else f"/{tipo}/{conta['id']}"

    resp = await client.patch(
        rota, json={"nome": "Novo", "email": "NOVO@example.com"}, headers=auth(conta)
    )

    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert (corpo["id"], corpo["nome"], corpo["email"]) == (conta["id"], "Novo", "novo@example.com")
    assert corpo["criado_em"] == conta["criado_em"]
    # O login passa a ser pelo e-mail novo.
    assert (await login(client, tipo, "novo@example.com")).status_code == 200
    assert_erro(await login(client, tipo, "antigo@example.com"), 401, "credenciais_invalidas")


async def test_edicao_parcial_mantem_o_email(client):
    cliente = await criar_cliente(client, nome="Ana", email="ana@example.com")

    resp = await client.patch("/me", json={"nome": "Ana Maria"}, headers=auth(cliente))

    assert resp.json()["nome"] == "Ana Maria"
    assert resp.json()["email"] == "ana@example.com"
    assert resp.json()["tipo"] == "cliente"


@pytest.mark.parametrize(("tipo", "criar"), TIPOS)
async def test_email_de_outra_conta_do_mesmo_tipo_retorna_409(client, tipo, criar):
    await criar(client, email="ocupado@example.com")
    conta = await criar(client)

    resp = await client.patch(
        f"/{tipo}/{conta['id']}", json={"email": "ocupado@example.com"}, headers=auth(conta)
    )

    assert_erro(resp, 409, "email_ja_cadastrado")
    assert (await client.get("/me", headers=auth(conta))).json()["email"] == conta["email"]


async def test_mesmo_email_em_tipos_diferentes_e_permitido(client):
    await criar_loja(client, email="ana@example.com")
    cliente = await criar_cliente(client)

    resp = await client.patch("/me", json={"email": "ana@example.com"}, headers=auth(cliente))

    assert resp.status_code == 200


@pytest.mark.parametrize(
    ("corpo", "campo"),
    [
        ({}, None),
        ({"nome": None}, "nome"),
        ({"nome": "  "}, "nome"),
        ({"email": "invalido"}, "email"),
        ({"senha": "outra-senha"}, "senha"),
    ],
)
async def test_edicao_invalida_retorna_422(client, corpo, campo):
    cliente = await criar_cliente(client)

    resp = await client.patch("/me", json=corpo, headers=auth(cliente))

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == campo


@pytest.mark.parametrize(("tipo", "criar"), TIPOS)
async def test_editar_outra_conta_retorna_403(client, tipo, criar):
    dona = await criar(client)
    outra = await criar(client)

    resp = await client.patch(f"/{tipo}/{dona['id']}", json={"nome": "x"}, headers=auth(outra))

    assert_erro(resp, 403, "acesso_negado")


async def test_editar_sem_token_retorna_401(client):
    assert_erro(await client.patch("/me", json={"nome": "x"}), 401, "nao_autenticado")


# --- Excluir ---------------------------------------------------------------------


@pytest.mark.parametrize(("tipo", "criar"), TIPOS)
@pytest.mark.parametrize("via_me", [False, True])
async def test_exclui_conta_e_encerra_o_acesso(client, tipo, criar, via_me):
    conta = await criar(client, email="sai@example.com")
    sessao = (await login(client, tipo, "sai@example.com")).json()
    rota = "/me" if via_me else f"/{tipo}/{conta['id']}"

    resp = await _excluir(client, rota, conta)

    assert resp.status_code == 204, resp.text
    assert_erro(await login(client, tipo, "sai@example.com"), 401, "credenciais_invalidas")
    refresh = await client.post("/auth/refresh", json={"refresh_token": sessao["refresh_token"]})
    assert_erro(refresh, 401, "refresh_invalido")
    # O access token ainda é um JWT válido até expirar, mas a conta não existe mais.
    nao_encontrada = "cliente_nao_encontrado" if tipo == "clientes" else "loja_nao_encontrada"
    assert_erro(await client.get("/me", headers=auth(conta)), 404, nao_encontrada)
    # O e-mail fica livre para um novo cadastro.
    assert (await criar(client, email="sai@example.com"))["id"] != conta["id"]


@pytest.mark.parametrize("senha", ["senha-errada", ""])
async def test_excluir_exige_a_senha_correta(client, senha):
    cliente = await criar_cliente(client)

    resp = await _excluir(client, "/me", cliente, senha=senha)

    erro = assert_erro(resp, 422, "entrada_invalida")
    assert erro["detalhes"][0]["campo"] == "senha"
    assert (await client.get("/me", headers=auth(cliente))).status_code == 200


async def test_excluir_sem_corpo_retorna_422(client):
    cliente = await criar_cliente(client)

    resp = await client.delete("/me", headers=auth(cliente))

    assert_erro(resp, 422, "entrada_invalida")


@pytest.mark.parametrize(("tipo", "criar"), TIPOS)
async def test_excluir_outra_conta_retorna_403(client, tipo, criar):
    dona = await criar(client)
    outra = await criar(client)

    resp = await _excluir(client, f"/{tipo}/{dona['id']}", outra)

    assert_erro(resp, 403, "acesso_negado")


async def test_excluir_loja_remove_novidades_e_seguidores(client):
    loja = await criar_loja(client, "Sai")
    fica = await criar_loja(client, "Fica")
    cliente = await criar_cliente(client)
    await seguir(client, cliente, loja["id"])
    await seguir(client, cliente, fica["id"])
    await publicar(client, loja, "da loja que sai")
    await publicar(client, fica, "da loja que fica")

    assert (await _excluir(client, "/me", loja)).status_code == 204

    assert_erro(await client.get(f"/lojas/{loja['id']}"), 404, "loja_nao_encontrada")
    seguidas = await client.get("/me/seguindo", headers=auth(cliente))
    assert [i["loja"]["nome"] for i in seguidas.json()["itens"]] == ["Fica"]
    feed = await client.get("/me/feed", headers=auth(cliente))
    assert [i["texto"] for i in feed.json()["itens"]] == ["da loja que fica"]


async def test_excluir_cliente_tira_ele_dos_seguidores_e_limpa_o_cache(client, redis):
    loja = await criar_loja(client)
    cliente = await criar_cliente(client)
    await seguir(client, cliente, loja["id"])
    await client.get("/me/feed", headers=auth(cliente))  # popula o cache do feed

    assert (await _excluir(client, f"/clientes/{cliente['id']}", cliente)).status_code == 204

    assert (await client.get(f"/lojas/{loja['id']}")).json()["total_seguidores"] == 0
    assert await redis.cliente.exists(f"feed:{cliente['id']}") == 0
