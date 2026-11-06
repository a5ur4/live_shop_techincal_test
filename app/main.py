from fastapi import FastAPI

from app.core.errors import register_error_handlers
from app.routes import clientes, health, lojas

DESCRICAO = """
Clientes seguem lojas e acompanham, num feed, as novidades que elas publicam.

**Fluxo típico:** crie uma loja e um cliente → o cliente segue a loja → a loja publica
novidades → o cliente lê o feed.

### Erros

Todo erro tem o mesmo formato. `codigo` é estável e serve para tratar o erro no cliente;
`detalhes` lista os campos inválidos (vazio quando não se aplica).

```json
{"erro": {"codigo": "loja_nao_encontrada", "mensagem": "Loja 7 não encontrada.", "detalhes": []}}
```

### Paginação do feed

O feed vem da novidade mais recente para a mais antiga. Se `proximo_cursor` não for `null`,
repita a chamada com `?cursor=<proximo_cursor>` para buscar a página seguinte.
"""

TAGS = [
    {"name": "Lojas", "description": "Cadastro de lojas e publicação de novidades."},
    {"name": "Clientes", "description": "Cadastro de clientes, lojas seguidas e feed."},
    {"name": "Saúde", "description": "Verificação de disponibilidade (API e banco)."},
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Feed de Novidades",
        version="0.1.0",
        description=DESCRICAO,
        openapi_tags=TAGS,
    )
    register_error_handlers(app)
    app.include_router(lojas.router)
    app.include_router(clientes.router)
    app.include_router(health.router)
    return app


app = create_app()
