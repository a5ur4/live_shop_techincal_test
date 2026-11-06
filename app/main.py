from fastapi import FastAPI

from app.api import clientes, health, lojas
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="Feed de Novidades",
        version="0.1.0",
        description="Clientes seguem lojas e acompanham, num feed, as novidades que elas publicam.",
    )
    register_error_handlers(app)
    app.include_router(lojas.router)
    app.include_router(clientes.router)
    app.include_router(health.router)
    return app


app = create_app()
