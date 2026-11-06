"""A documentação OpenAPI é parte do contrato: garante que ela acompanha o código."""

import re
from pathlib import Path

from app.core.errors import CATALOGO_ERROS
from app.main import app

ROTAS_ESPERADAS = {
    ("post", "/auth/clientes/token"),
    ("post", "/auth/lojas/token"),
    ("post", "/lojas"),
    ("get", "/lojas"),
    ("get", "/lojas/{loja_id}"),
    ("get", "/lojas/{loja_id}/novidades"),
    ("get", "/clientes/{cliente_id}/seguindo"),
    ("post", "/lojas/{loja_id}/novidades"),
    ("post", "/clientes"),
    ("post", "/clientes/{cliente_id}/seguindo/{loja_id}"),
    ("delete", "/clientes/{cliente_id}/seguindo/{loja_id}"),
    ("get", "/clientes/{cliente_id}/feed"),
    ("get", "/health"),
    ("get", "/me"),
    ("get", "/me/feed"),
    ("get", "/me/seguindo"),
    ("post", "/me/seguindo/{loja_id}"),
    ("delete", "/me/seguindo/{loja_id}"),
    ("post", "/me/novidades"),
    ("get", "/me/novidades"),
}


async def test_swagger_e_openapi_disponiveis(client):
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


def test_todas_as_rotas_documentadas_com_erro_no_formato_padrao():
    spec = app.openapi()
    rotas = {(m, p) for p, ops in spec["paths"].items() for m in ops}
    assert rotas == ROTAS_ESPERADAS

    for path, ops in spec["paths"].items():
        for metodo, op in ops.items():
            assert op.get("summary"), f"{metodo} {path} sem summary"
            for status_code, resposta in op["responses"].items():
                if status_code.startswith(("4", "5")):
                    schema = resposta["content"]["application/json"]["schema"]
                    assert schema["$ref"].endswith("/ErroResponse"), (metodo, path, status_code)


ROTAS_PROTEGIDAS = {
    ("get", "/me"): ["Cliente", "Lojista"],  # qualquer um dos dois
    ("get", "/me/feed"): "Cliente",
    ("get", "/me/seguindo"): "Cliente",
    ("post", "/me/seguindo/{loja_id}"): "Cliente",
    ("delete", "/me/seguindo/{loja_id}"): "Cliente",
    ("post", "/me/novidades"): "Lojista",
    ("get", "/me/novidades"): "Lojista",
    ("post", "/lojas/{loja_id}/novidades"): "Lojista",
    ("post", "/clientes/{cliente_id}/seguindo/{loja_id}"): "Cliente",
    ("delete", "/clientes/{cliente_id}/seguindo/{loja_id}"): "Cliente",
    ("get", "/clientes/{cliente_id}/feed"): "Cliente",
    ("get", "/clientes/{cliente_id}/seguindo"): "Cliente",
}


def test_rotas_protegidas_declaram_esquema_oauth2():
    spec = app.openapi()
    esquemas = spec["components"]["securitySchemes"]
    assert esquemas["Cliente"]["flows"]["password"]["tokenUrl"] == "/auth/clientes/token"
    assert esquemas["Lojista"]["flows"]["password"]["tokenUrl"] == "/auth/lojas/token"

    for (metodo, path), esquema in ROTAS_PROTEGIDAS.items():
        op = spec["paths"][path][metodo]
        esquemas_aceitos = esquema if isinstance(esquema, list) else [esquema]
        assert op.get("security") == [{e: []} for e in esquemas_aceitos], (metodo, path)
        assert "401" in op["responses"], (metodo, path)
        if len(esquemas_aceitos) == 1:
            assert "403" in op["responses"], (metodo, path)

    publicas = ROTAS_ESPERADAS - set(ROTAS_PROTEGIDAS)
    for metodo, path in publicas:
        assert "security" not in spec["paths"][path][metodo], (metodo, path)


def test_todo_codigo_de_erro_usado_no_codigo_esta_no_catalogo():
    # Códigos genéricos dos handlers globais (rota inexistente, 500...) não aparecem nas rotas.
    genericos = {
        "requisicao_invalida",
        "nao_encontrado",
        "conflito",
        "rota_nao_encontrada",
        "metodo_nao_permitido",
        "erro_http",
        "erro_interno",
    }
    fonte = "\n".join(p.read_text() for p in Path("app").rglob("*.py"))
    usados = set(re.findall(r'codigo\s*=\s*"([a-z_]+)"', fonte)) - genericos

    assert usados <= set(CATALOGO_ERROS), usados - set(CATALOGO_ERROS)
