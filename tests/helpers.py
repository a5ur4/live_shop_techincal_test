"""Atalhos para montar cenários nos testes via API.

`criar_loja` e `criar_cliente` cadastram, fazem login e devolvem o JSON do cadastro com
a chave extra `token`. Use `auth(conta)` para montar o header Authorization.
"""

from itertools import count

from httpx import AsyncClient

SENHA = "senha-de-teste"
_sequencia = count(1)


def auth(conta: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {conta['token']}"}


async def login(client: AsyncClient, tipo: str, email: str, senha: str = SENHA):
    """tipo: "clientes" ou "lojas". Devolve a resposta crua do token endpoint."""
    return await client.post(f"/auth/{tipo}/token", data={"username": email, "password": senha})


async def _cadastrar_e_logar(client: AsyncClient, tipo: str, corpo: dict) -> dict:
    resp = await client.post(f"/{tipo}", json=corpo)
    assert resp.status_code == 201, resp.text
    conta = resp.json()
    token = await login(client, tipo, corpo["email"], corpo["senha"])
    assert token.status_code == 200, token.text
    return conta | {"token": token.json()["access_token"]}


async def criar_loja(client: AsyncClient, nome: str = "Loja", email: str | None = None) -> dict:
    email = email or f"loja{next(_sequencia)}@example.com"
    return await _cadastrar_e_logar(client, "lojas", {"nome": nome, "email": email, "senha": SENHA})


async def criar_cliente(
    client: AsyncClient, nome: str = "Cliente", email: str | None = None
) -> dict:
    email = email or f"cliente{next(_sequencia)}@example.com"
    return await _cadastrar_e_logar(
        client, "clientes", {"nome": nome, "email": email, "senha": SENHA}
    )


async def seguir(client: AsyncClient, cliente: dict, loja_id: int) -> None:
    resp = await client.post(f"/clientes/{cliente['id']}/seguindo/{loja_id}", headers=auth(cliente))
    assert resp.status_code == 201, resp.text


async def publicar(client: AsyncClient, loja: dict, texto: str, preco=None) -> dict:
    corpo = {"texto": texto} if preco is None else {"texto": texto, "preco": preco}
    resp = await client.post(f"/lojas/{loja['id']}/novidades", json=corpo, headers=auth(loja))
    assert resp.status_code == 201, resp.text
    return resp.json()


def assert_erro(resp, status_code: int, codigo: str) -> dict:
    """Confere status e o formato único de erro; devolve o objeto `erro`."""
    assert resp.status_code == status_code, resp.text
    corpo = resp.json()
    assert set(corpo) == {"erro"}
    assert set(corpo["erro"]) == {"codigo", "mensagem", "detalhes"}
    assert corpo["erro"]["codigo"] == codigo
    assert isinstance(corpo["erro"]["mensagem"], str) and corpo["erro"]["mensagem"]
    return corpo["erro"]
