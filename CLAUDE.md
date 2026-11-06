# CLAUDE.md

Guia para quem for continuar este projeto: pessoa ou agente de IA (Claude Code, Codex,
Cursor...). Leia isto antes de mudar código. O que o produto faz e como rodar está no
[README](README.md); o porquê das decisões, em [`docs/adr/`](docs/adr/README.md); o que falta,
no [BACKLOG](BACKLOG.md).

## Projeto em uma frase

API FastAPI + PostgreSQL em que clientes seguem lojas e leem um feed com as novidades delas.
Desafio técnico; enunciado em `docs/desafio.md`, que é a **fonte da verdade** dos requisitos.

## Comandos

```bash
make up            # Docker: Postgres + API em :8000 (migrations automáticas)
make seed          # dados de exemplo no banco do Docker
make db            # só o Postgres (para rodar API/testes com uv)
make dev           # API local com reload (uv)
make test          # testes com uv (sobe o Postgres se preciso)
make test-docker   # testes só com Docker
make lint          # ruff check + format --check
make format        # corrige lint/format
make check         # lint + testes — rode antes de todo commit
make migration m="descricao"   # gera migration a partir de app/models/
```

Teste específico: `uv run pytest tests/test_feed.py -k limite -q`.

## Arquitetura

```
app/routes/     HTTP fino: rota, status code, parâmetros, `responses=respostas_erro(...)`
app/services/   regra de negócio + queries; levanta AppError; faz commit
app/models/     tabelas SQLAlchemy, um arquivo por entidade (constraints e índices aqui)
app/schemas/    Pydantic por recurso: entrada (`Entrada`, extra="forbid") e saída (`Saida`)
app/core/       config (env), db (engine/sessão), errors (formato único de erro)
```

Dependências só vão para baixo: `routes → services → models`. Rotas **não** acessam o banco
direto; services **não** importam FastAPI (exceto via `app.core.errors`).

## Convenções

- **Idioma**: domínio, rotas, campos JSON, mensagens e docs em **português**
  (`loja`, `novidade`, `criado_em`). Palavras técnicas do framework ficam em inglês.
- **Erros**: nunca `HTTPException`. Levante `NaoEncontradoError` / `ConflitoError` /
  `EntradaInvalidaError` de `app/core/errors.py`, sempre com `codigo=` específico em
  snake_case (ex.: `loja_nao_encontrada`). Novo código → adicionar na tabela do ADR 0003.
- **Unicidade**: use `insert(...).on_conflict_do_nothing(...).returning(...)` e trate `None`
  como 409. Não faça "SELECT para checar e depois INSERT" (tem corrida).
- **Dinheiro**: `Decimal`/`NUMERIC(12,2)`, nunca `float`. Sai como string no JSON.
- **Ordem do feed**: sempre `criado_em DESC, id DESC`. O índice
  `ix_novidades_loja_feed` depende disso; se mudar a ordem, mude o índice.
- **Schema do banco**: só muda via migration Alembic. Altere `app/models/`, rode
  `make migration m="..."`, **revise o arquivo gerado** e rode `make format`.
- **Estilo**: ruff (linha de 100, regras em `pyproject.toml`). Type hints em funções públicas.
- **Comentários**: só para explicar o *porquê*, não o *quê*.

## Como adicionar um endpoint (checklist)

1. Schema de entrada/saída em `app/schemas/<recurso>.py` (herde `Entrada`/`Saida`) e
   exporte em `app/schemas/__init__.py`.
2. Função no service adequado em `app/services/` levantando `AppError` nos casos de erro.
3. Rota em `app/routes/` com `status_code`, `response_model`, `responses=respostas_erro(...)`
   e `summary`.
4. Mudou tabela? Modelo novo em `app/models/<entidade>.py`, importado em
   `app/models/__init__.py` (senão o Alembic não enxerga), e migration (ver acima).
5. Testes em `tests/test_<area>.py`: caminho feliz + cada erro, usando `tests/helpers.py`
   (`criar_loja`, `criar_cliente`, `seguir`, `publicar`, `assert_erro`).
6. Exemplo em `requests.http`, linha na tabela de endpoints do README.
7. Decisão não óbvia? Registre em `docs/adr/` (novo ADR ou tabela do 0004).
8. `make check` verde.

## Testes

- Integração contra **Postgres real** (`TEST_DATABASE_URL`, padrão `feed_test`), via
  `httpx.AsyncClient` + `ASGITransport`. Sem mocks de banco.
- `tests/conftest.py` cria o banco, roda migrations (`downgrade base` + `upgrade head`) e
  faz `TRUNCATE ... RESTART IDENTITY` antes de cada teste — ids sempre começam em 1.
- Testes são `async def` simples (`asyncio_mode = "auto"`), sem decorator.
- Para cenários com horário controlado, insira direto via fixture `engine` (ver
  `test_feed_desempata_pelo_id_quando_horario_e_igual`).

## Armadilhas conhecidas

- `expire_on_commit=False` na sessão: objetos continuam legíveis depois do commit (necessário
  em async, onde lazy load implícito quebra). Relacionamentos usam `lazy="raise"`; carregue
  explicitamente.
- Engine de teste usa `NullPool`: cada teste tem seu event loop e conexões asyncpg não
  atravessam loops. Não troque por pool comum nos testes.
- Valores de `server_default` (ex.: `criado_em`) voltam via `RETURNING` no insert (eager
  defaults do SQLAlchemy 2); não precisa de `refresh`.
- `Preco` é normalizado para 2 casas no schema, para a resposta do POST bater com o banco.
- `alembic.ini` não tem URL: `migrations/env.py` lê `DATABASE_URL`; os testes injetam a URL
  de teste via `sqlalchemy.url`.

## Fluxo de Git

- Nada direto na `main`: trabalho em branch (`feat/...`, `fix/...`, `docs/...`, `chore/...`) e PR.
- Commits pequenos, em português, no formato Conventional Commits:
  `feat: ...`, `fix: ...`, `test: ...`, `docs: ...`, `chore: ...`, `refactor: ...`.
  O corpo explica **o que mudou e por quê**.
- Cada commit deve passar em `make check`.
- Nunca versione `.env`, `.venv/` ou caches (ver `.gitignore`). Novas variáveis de ambiente
  vão em `app/core/config.py` **e** em `.env.example`.
- PR segue `.github/pull_request_template.md` (o que foi feito, como testar, pendências).

## Definição de pronto

Requisito do `docs/desafio.md` atendido · testes cobrindo sucesso e erros · `make check`
verde · README/`requests.http`/ADR atualizados se o comportamento mudou · item marcado no
`BACKLOG.md`.
