"""Atalhos para montar cenários nos testes via API."""

from httpx import AsyncClient


async def criar_loja(client: AsyncClient, nome: str = "Loja") -> dict:
    resp = await client.post("/lojas", json={"nome": nome})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def criar_cliente(
    client: AsyncClient, nome: str = "Cliente", email: str = "cliente@example.com"
) -> dict:
    resp = await client.post("/clientes", json={"nome": nome, "email": email})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def seguir(client: AsyncClient, cliente_id: int, loja_id: int) -> None:
    resp = await client.post(f"/clientes/{cliente_id}/seguindo/{loja_id}")
    assert resp.status_code == 201, resp.text


async def publicar(client: AsyncClient, loja_id: int, texto: str, preco=None) -> dict:
    corpo = {"texto": texto} if preco is None else {"texto": texto, "preco": preco}
    resp = await client.post(f"/lojas/{loja_id}/novidades", json=corpo)
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
