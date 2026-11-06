from fastapi import FastAPI

from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="Feed de Novidades",
        version="0.1.0",
        description="Clientes seguem lojas e acompanham, num feed, as novidades que elas publicam.",
    )
    register_error_handlers(app)
    return app


app = create_app()
