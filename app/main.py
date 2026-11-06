from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="Feed de Novidades",
        version="0.1.0",
        description="Clientes seguem lojas e acompanham, num feed, as novidades que elas publicam.",
    )
    return app


app = create_app()
