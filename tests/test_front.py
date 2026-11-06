"""Front de teste (app/front): servido pela própria API em /app, mesma origem."""

import pytest


async def test_raiz_redireciona_para_o_front(client):
    resp = await client.get("/")

    assert resp.status_code == 307
    assert resp.headers["location"] == "/app/"


@pytest.mark.parametrize(
    ("caminho", "tipo"),
    [("/app/", "text/html"), ("/app/app.js", "text/javascript"), ("/app/estilo.css", "text/css")],
)
async def test_arquivos_do_front_sao_servidos(client, caminho, tipo):
    resp = await client.get(caminho)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(tipo)


async def test_front_envia_cabecalhos_de_seguranca(client):
    resp = await client.get("/app/")

    csp = resp.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["referrer-policy"] == "no-referrer"


async def test_front_nao_fica_no_openapi_e_nao_afeta_o_swagger(client):
    spec = (await client.get("/openapi.json")).json()
    docs = await client.get("/docs")

    assert not any(p == "/" or p.startswith("/app") for p in spec["paths"])
    # O Swagger carrega JS de CDN: a CSP do front não pode valer para ele.
    assert "content-security-policy" not in docs.headers


async def test_arquivo_inexistente_no_front_retorna_404(client):
    resp = await client.get("/app/nao-existe.js")

    assert resp.status_code == 404
