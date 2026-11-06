from fastapi import FastAPI

from app.core.errors import register_error_handlers
from app.routes import auth, clientes, health, lojas

DESCRICAO = """
Clientes seguem lojas e acompanham, num feed, as novidades que elas publicam.

**Fluxo típico:** crie uma loja e um cliente → faça login de cada um → o cliente segue a
loja → a loja publica novidades → o cliente lê o feed.

### Autenticação

OAuth2 *password flow* com JWT. Cadastros (`POST /lojas`, `POST /clientes`) são públicos;
o login (`POST /auth/clientes/token` ou `POST /auth/lojas/token`) devolve um
`access_token`, enviado como `Authorization: Bearer <token>`. As rotas mantêm o id na URL,
e o token precisa ser do mesmo cliente/loja: caso contrário, `403 acesso_negado`.
No Swagger, use o botão **Authorize**.

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
    {"name": "Autenticação", "description": "Login (OAuth2 password flow) e emissão de JWT."},
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
    app.include_router(auth.router)
    app.include_router(lojas.router)
    app.include_router(clientes.router)
    app.include_router(health.router)
    return app


app = create_app()
