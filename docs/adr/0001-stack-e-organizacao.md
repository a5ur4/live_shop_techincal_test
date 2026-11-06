# 0001. Stack e organização do código em camadas

- Status: Aceito
- Data: 2026-11-05

## Contexto

API pequena (5 endpoints) que precisa ser fácil de continuar por outra pessoa, com banco
relacional subindo via `docker compose up`.

## Decisão

**Stack**

- **FastAPI** (`fastapi[standard]`): validação via Pydantic, OpenAPI/Swagger gerado de graça,
  suporte nativo a async.
- **SQLAlchemy 2 async + asyncpg**: ORM maduro com tipagem (`Mapped[...]`), e o dialeto
  PostgreSQL dá `INSERT ... ON CONFLICT` e `LATERAL` sem SQL cru.
- **Alembic**: migrations versionadas; aplicadas automaticamente no `entrypoint` do container.
- **PostgreSQL 17**: pedido do enunciado; CHECK constraints, índices com ordenação, LATERAL.
- **uv**: gerenciador de dependências rápido, com lockfile (`uv.lock`) reprodutível.
- **pytest + pytest-asyncio + httpx**: testes async chamando a app via ASGI, sem subir servidor.
- **ruff**: lint + formatação numa ferramenta só.

**Organização em camadas**

```
app/api/       → HTTP: rotas, status codes, parâmetros. Sem regra de negócio.
app/services/  → regras de negócio e queries. Levantam AppError. Fazem commit.
app/models.py  → tabelas (SQLAlchemy).
app/schemas.py → contratos de entrada/saída (Pydantic) e validação de formato.
app/core/      → infraestrutura: config, sessão do banco, formato de erro.
```

Regra de dependência: `api → services → models`; `schemas` e `core` podem ser usados por todos.

## Alternativas consideradas

- **Camada de repositório separada dos services**: com 5 endpoints e queries simples, seria
  indireção sem ganho. Se as queries crescerem, extrair repositórios de `services/`.
- **Organização por feature** (`lojas/`, `clientes/` cada um com router/service/schema):
  boa para projetos maiores; aqui os módulos únicos (`models.py`, `schemas.py`) são mais
  fáceis de ler de uma vez.
- **SQLModel**: menos código, mas mistura contrato HTTP e tabela, e é menos flexível para
  queries como o LATERAL do feed.

## Consequências

- Rotas ficam finas e fáceis de revisar; testes de API cobrem tudo de ponta a ponta.
- `models.py` e `schemas.py` devem ser divididos em pacotes se passarem de ~300 linhas.
