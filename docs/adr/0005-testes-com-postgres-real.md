# 0005. Testes de integração contra Postgres real

- Status: Aceito
- Data: 2026-11-05

## Contexto

As regras mais importantes dependem do banco: unicidade via `ON CONFLICT`, PK composta,
CHECK constraints, `LATERAL` e ordenação por índice. SQLite ou mocks não reproduzem isso.

## Decisão

- Testes chamam a API via `httpx.AsyncClient` + `ASGITransport` (sem subir servidor) contra
  um banco Postgres real, `feed_test`, separado do banco de desenvolvimento.
- `tests/conftest.py`:
  - cria o banco de teste se não existir;
  - aplica as migrations com `downgrade base` + `upgrade head` uma vez por sessão (isso também
    testa que as migrations sobem e descem);
  - antes de cada teste faz `TRUNCATE ... RESTART IDENTITY`, então ids começam em 1;
  - troca a dependência `get_session` por uma sessão ligada ao banco de teste.
- Engine de teste usa `NullPool`, porque cada teste roda no seu próprio event loop e
  conexões asyncpg não podem ser compartilhadas entre loops.

## Alternativas consideradas

- **Transação com rollback por teste**: mais rápido, mas os services fazem `commit`, o que
  exigiria savepoints aninhados e deixaria o teste menos parecido com produção.
- **testcontainers**: sobe um Postgres descartável por execução; adiciona dependência e
  tempo. O `docker compose` já fornece o banco.

## Consequências

- Rodar testes exige o Postgres no ar (`make db`), ou usar `make test-docker`, que precisa só
  de Docker. No CI o Postgres sobe como *service container*.
- Suíte atual: ~60 testes em ~6s.
