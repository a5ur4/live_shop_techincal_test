"""Front de teste servido pela própria API (arquivos estáticos em app/front).

Mesma origem da API: sem CORS e sem build. A CSP vale só para /app (o Swagger em /docs
carrega JS de CDN e ficaria quebrado com ela).
"""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

PASTA_FRONT = Path(__file__).resolve().parent.parent / "front"

CABECALHOS_FRONT = {
    # Só scripts/estilos do próprio servidor e chamadas à própria API; o front monta o
    # HTML com textContent (nunca innerHTML com dados), e a CSP é a segunda barreira.
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

router = APIRouter(include_in_schema=False)


@router.get("/")
async def raiz() -> RedirectResponse:
    return RedirectResponse("/app/")


class _ArquivosDoFront(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        resposta = await super().get_response(path, scope)
        resposta.headers.update(CABECALHOS_FRONT)
        return resposta


def montar_front(app: FastAPI) -> None:
    app.include_router(router)
    app.mount("/app", _ArquivosDoFront(directory=PASTA_FRONT, html=True), name="front")
