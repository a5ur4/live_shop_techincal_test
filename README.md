# Feed de Novidades

API REST em que **clientes seguem lojas** e acompanham, num **feed**, as novidades que essas
lojas publicam (produto novo, promoção, aviso de live), da mais recente para a mais antiga.

Stack: **Python 3.14 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL 17 · Alembic · Docker · uv**.
Enunciado completo em [`docs/desafio.md`](docs/desafio.md).

---

## 1. Como rodar do zero

**Pré-requisito:** Docker com Docker Compose v2. Nada mais.

```bash
git clone https://github.com/a5ur4/live_shop_techincal_test.git
cd live_shop_techincal_test
docker compose up -d --build        # sobe Postgres + API; as migrations rodam sozinhas
docker compose exec api python -m app.seed   # (opcional) dados de exemplo
```

- API: <http://localhost:8000>
- Swagger (OpenAPI): <http://localhost:8000/docs>

Nenhum `.env` é necessário: os padrões já funcionam. Para mudar portas ou credenciais,
`cp .env.example .env` e edite. As credenciais padrão (`feed`/`feed`) servem **só para
desenvolvimento local**; o Postgres fica exposto apenas em `127.0.0.1`.

Atalhos: `make help` lista todos (`make up`, `make seed`, `make logs`, `make down`...).

### Rodando a API fora do Docker (desenvolvimento, com reload)

Requer [uv](https://docs.astral.sh/uv/) (ele instala o Python 3.14 se precisar).

```bash
uv sync                      # cria .venv com as dependências
make dev                     # sobe só o Postgres, aplica migrations e roda com reload
```

## 2. Como rodar os testes

Os testes rodam contra um Postgres real (banco `feed_test`, criado e migrado automaticamente).

```bash
make test-docker   # só precisa de Docker
# ou, com uv instalado:
make test          # sobe o Postgres se precisar e roda `uv run pytest`
make check         # lint (ruff) + testes, o mesmo que o CI
```

Cobertura por arquivo:

| Arquivo | O que cobre |
| --- | --- |
| `tests/test_feed.py` | só lojas seguidas, isolamento entre clientes, ordem, desempate por id, limite padrão/informado/máximo/inválido, 404 |
| `tests/test_seguir.py` | seguir com sucesso, cliente/loja inexistente (404), seguir duas vezes (409), id inválido |
| `tests/test_novidades.py` | texto 1–500 (limites e inválidos), preço opcional/positivo/2 casas, loja inexistente |
| `tests/test_cadastro.py` | nome obrigatório, e-mail válido/normalizado/único (409), campo desconhecido |
| `tests/test_erros.py` | mesmo formato de erro para rota inexistente, 405, JSON malformado |

## 3. Exemplos de chamada

Todos os endpoints (sucesso e erro) estão em [`requests.http`](requests.http) — abra no VS Code
(extensão REST Client) ou IntelliJ e clique em "Send Request". Também dá para testar pelo
Swagger em `/docs`. Em curl:

```bash
# Cria loja e cliente
curl -X POST localhost:8000/lojas -H 'Content-Type: application/json' -d '{"nome": "Loja da Ana"}'
curl -X POST localhost:8000/clientes -H 'Content-Type: application/json' \
     -d '{"nome": "João Silva", "email": "joao@example.com"}'

# Cliente 1 segue a loja 1
curl -X POST localhost:8000/clientes/1/seguindo/1

# Loja 1 publica (preco é opcional)
curl -X POST localhost:8000/lojas/1/novidades -H 'Content-Type: application/json' \
     -d '{"texto": "Chegou a coleção de verão!", "preco": "199.90"}'

# Feed do cliente 1
curl 'localhost:8000/clientes/1/feed?limite=20'
```

Resposta do feed:

```json
{
  "itens": [
    {
      "id": 1,
      "loja": {"id": 1, "nome": "Loja da Ana"},
      "texto": "Chegou a coleção de verão!",
      "preco": "199.90",
      "criado_em": "2026-11-05T22:10:00.123456Z"
    }
  ]
}
```

Erros — sempre no mesmo formato:

```json
{
  "erro": {
    "codigo": "entrada_invalida",
    "mensagem": "Dados de entrada inválidos.",
    "detalhes": [{"campo": "texto", "mensagem": "Deve ter pelo menos 1 caractere(s)."}]
  }
}
```

| Endpoint | Sucesso | Erros |
| --- | --- | --- |
| `POST /lojas` | 201 | 422 |
| `POST /clientes` | 201 | 409 `email_ja_cadastrado`, 422 |
| `POST /clientes/{id}/seguindo/{lojaId}` | 201 | 404 `cliente_nao_encontrado`/`loja_nao_encontrada`, 409 `ja_segue_loja` |
| `POST /lojas/{id}/novidades` | 201 | 404 `loja_nao_encontrada`, 422 |
| `GET /clientes/{id}/feed?limite=20` | 200 | 404 `cliente_nao_encontrado`, 422 (`limite` fora de 1–50) |

## 4. Estrutura de pastas

```
app/
  main.py          # cria a app FastAPI, registra rotas e handlers de erro
  routes/          # camada HTTP: rotas finas, status codes, parâmetros (sem regra de negócio)
  services/        # regras de negócio e queries (lojas, clientes/seguir, feed)
  models/          # tabelas SQLAlchemy, um arquivo por entidade, com constraints e índices
  schemas/         # contratos Pydantic de entrada/saída por recurso e validação de formato
  core/            # infraestrutura: config (env), sessão do banco, formato único de erro
  seed.py          # dados de exemplo: python -m app.seed [--reset]
migrations/        # Alembic (async); versions/ tem o histórico do schema
tests/             # testes de integração (API + Postgres real); helpers.py monta cenários
docs/
  desafio.md       # enunciado original
  adr/             # decisões técnicas, uma por arquivo
docker/            # entrypoint do container (aplica migrations e inicia a API)
requests.http      # exemplos de chamada de todos os endpoints
BACKLOG.md         # checklist das tarefas planejadas/concluídas
CLAUDE.md          # guia para quem (pessoa ou agente) for continuar o projeto
```

## 5. Decisões técnicas

Resumo — o raciocínio completo, com alternativas, está em [`docs/adr/`](docs/adr/README.md).

- **Feed montado na leitura, com `LATERAL` + índice** ([ADR 0002](docs/adr/0002-feed-fan-out-na-leitura.md)).
  Lojas publicam pouco e algumas têm 100 mil+ seguidores: copiar cada novidade para o feed de
  cada seguidor (fan-out na escrita) faria uma publicação virar 100 mil inserts. Na leitura,
  para cada loja seguida o Postgres busca só as N mais recentes pelo índice
  `novidades(loja_id, criado_em DESC, id DESC)` e para — custo ≈ lojas seguidas × limite,
  independente do volume total. Ordem `criado_em DESC, id DESC` (o id desempata).
- **Modelagem** — 4 tabelas: `lojas`, `clientes` (`email` único), `seguidores` (PK composta
  `(cliente_id, loja_id)`, que impede seguir duas vezes no próprio banco), `novidades`
  (`preco NUMERIC(12,2)`, CHECKs de texto e preço). Ids `BIGINT IDENTITY`, datas `timestamptz`.
- **Unicidade sem corrida** — e-mail e seguir usam `INSERT ... ON CONFLICT DO NOTHING`: duas
  requisições simultâneas não passam pela checagem e quebram com 500; uma recebe 409.
- **Camadas `routes → services → models`** ([ADR 0001](docs/adr/0001-stack-e-organizacao.md)):
  rotas só tratam HTTP; regras ficam nos services, que levantam erros de domínio.
- **Formato único de erro** ([ADR 0003](docs/adr/0003-formato-unico-de-erro.md)):
  `{"erro": {"codigo", "mensagem", "detalhes"}}` com `codigo` estável para o cliente tratar.
  Inclui validação do FastAPI, 404/405 de rota e 500.
- **Bibliotecas**: FastAPI (validação + OpenAPI de graça), SQLAlchemy 2 async + asyncpg (ORM
  tipado, `ON CONFLICT`/`LATERAL` sem SQL cru), Alembic (migrations automáticas no start),
  uv (lockfile reprodutível), ruff (lint + format), pytest + httpx (testes via ASGI).
- **Testes contra Postgres real** ([ADR 0005](docs/adr/0005-testes-com-postgres-real.md)), já
  que as regras críticas vivem no banco; o banco de teste é criado e migrado sozinho.
- **Proteção do banco**: `statement_timeout` de 5s por query e `limite` máximo de 50.

### Decisões sobre pontos não definidos no enunciado

Detalhadas em [ADR 0004](docs/adr/0004-regras-de-entrada.md). Principais:

- `limite` fora de 1–50 retorna **422** em vez de ajustar em silêncio.
- Espaços nas pontas de `nome`/`texto` são removidos; só espaços conta como vazio.
- E-mail salvo em minúsculas: `Ana@x.com` e `ana@x.com` são o mesmo cliente (409).
- `preco` aceita até 2 casas decimais e volta como string (`"199.90"`) para não perder precisão.
- Campos desconhecidos no corpo dão 422 — um `"preço"` com acento não é ignorado em silêncio.
- Ao seguir uma loja, as novidades antigas dela já aparecem no feed.
- O feed é um objeto `{"itens": [...]}`, para crescer (ex.: paginação) sem quebrar clientes.

## 6. O que ficou de fora e o que eu faria com mais tempo

**Fora do escopo por definição:** autenticação/autorização. Hoje qualquer um que souber o id
de um cliente lê o feed dele. Com mais tempo: login (JWT/OAuth), `GET /me/feed` derivando o
cliente do token, e lojistas só publicando na própria loja.

**Com mais tempo:**

- **Escala do feed**: cache curto por cliente (Redis) invalidado na publicação; modelo
  híbrido (fan-out na escrita para lojas pequenas, na leitura para as grandes); limite de
  lojas seguidas por cliente. Detalhes no [ADR 0002](docs/adr/0002-feed-fan-out-na-leitura.md).
- Endpoints de leitura/gestão: `GET /lojas/{id}`, listar quem o cliente segue, editar/remover
  novidade.
- Rate limiting, logs estruturados (JSON) com id de requisição, métricas e tracing.
- Teste de carga (k6/Locust) com uma loja de 100 mil seguidores para validar o ADR 0002.

Pendências e próximos passos ficam em [`BACKLOG.md`](BACKLOG.md).
