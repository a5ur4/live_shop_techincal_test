# Feed de Novidades

[![CI](https://github.com/a5ur4/live_shop_techincal_test/actions/workflows/ci.yml/badge.svg)](https://github.com/a5ur4/live_shop_techincal_test/actions/workflows/ci.yml)

API REST em que **clientes seguem lojas** e acompanham, num **feed**, as novidades que essas
lojas publicam (produto novo, promoção, aviso de live), da mais recente para a mais antiga.

Stack: **Python 3.14 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL 17 · Redis 7 · Alembic ·
OAuth2/JWT · Docker · uv**. Enunciado completo em [`docs/desafio.md`](docs/desafio.md).

---

## 1. Como rodar do zero

**Pré-requisito:** Docker com Docker Compose v2. Nada mais.

```bash
git clone https://github.com/a5ur4/live_shop_techincal_test.git
cd live_shop_techincal_test
docker compose up -d --build --wait            # Postgres + Redis + API; migrations e seed rodam sozinhos
```

- **Front de teste: <http://localhost:8000/app/>** (a raiz `/` redireciona para lá) — entre
  com uma conta do seed ou crie uma e use a API pela interface.
- API: <http://localhost:8000> · Saúde: <http://localhost:8000/health>
- Swagger (OpenAPI): <http://localhost:8000/docs> — use o botão **Authorize** para logar.

O seed roda no start da API quando o banco está vazio (desligue com `SEED_DB=false`; para
recriar os dados, `docker compose exec api python -m app.seed --reset`). Ele cria 5 lojas,
4 clientes e 12 novidades. **Senha de todas as contas: `senha123`** (só desenvolvimento). Ex.: cliente `elisa@example.com` (segue todas as lojas), lojista
`modadaana@lojas.example.com`.

Nenhum `.env` é necessário: os padrões já funcionam. Para mudar portas, credenciais ou a
chave do JWT, `cp .env.example .env` e edite. Sem `JWT_SECRET`, a API gera uma chave
aleatória a cada start (tokens deixam de valer ao reiniciar). As credenciais padrão do
Postgres (`feed`/`feed`) servem **só para desenvolvimento local**; ele fica exposto apenas
em `127.0.0.1`.

Atalhos: `make help` lista todos (`make up`, `make seed`, `make logs`, `make down`...).

### Rodando a API fora do Docker (desenvolvimento, com reload)

Requer [uv](https://docs.astral.sh/uv/) (ele instala o Python 3.14 se precisar).

```bash
uv sync      # cria .venv com as dependências
make dev     # sobe só o Postgres, aplica migrations e roda com reload
```

## 2. Como rodar os testes

Os testes rodam contra um Postgres real (banco `feed_test`, criado e migrado automaticamente).

```bash
make test-docker   # só precisa de Docker
# ou, com uv instalado:
make test          # sobe o Postgres se precisar e roda `uv run pytest`
make check         # lint (ruff) + testes, o mesmo que o CI
make benchmark     # mede o feed com uma loja de 100 mil seguidores (banco feed_bench separado)
```

Os testes também usam um Redis real (banco 15, esvaziado a cada teste); `make db` sobe
Postgres e Redis.

O CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) roda a cada push: lint, migrations
do zero + `alembic check`, testes com Postgres e Redis e build da imagem Docker.

| Arquivo | O que cobre |
| --- | --- |
| `tests/test_feed.py` | só lojas seguidas, isolamento entre clientes, ordem, desempate por id, limite padrão/informado/máximo/inválido, paginação por cursor (sem repetir/pular, estável com publicação no meio, cursor inválido) |
| `tests/test_seguir.py` | seguir e deixar de seguir: sucesso, loja inexistente (404), duplicado (409), não segue (404), token ausente (401) ou de outro cliente (403) |
| `tests/test_novidades.py` | texto 1–500 (limites e inválidos), preço opcional/positivo/2 casas, token ausente (401), outra loja (403) |
| `tests/test_cadastro.py` | nome, e-mail e senha obrigatórios/válidos, e-mail normalizado e único (409), senha não exposta, campo desconhecido |
| `tests/test_auth.py` | login de cliente e lojista, credenciais inválidas sem revelar o motivo, token malformado/expirado/assinatura errada, troca de tipo (403) |
| `tests/test_sessao.py` | refresh com rotação, reuso derrubando a sessão (sem afetar outras), expirado, só hash no banco, logout idempotente, rate limit por e-mail/IP com `Retry-After`, fallback em memória sem Redis, troca de senha |
| `tests/test_me.py` | perfil, feed, seguir/deixar e novidades pelo `/me`, equivalência com as rotas com `{id}`, tipo de conta errado (403) |
| `tests/test_leitura.py` | `GET /lojas` (ordem, cursor, busca com `%`/`_` escapados), `GET /lojas/{id}` (total de seguidores), novidades da loja, lojas seguidas, cursores forjados (422) |
| `tests/test_editar_novidades.py` | edição parcial (`preco: null` remove), `criado_em` mantido e `editado_em` preenchido, remoção, novidade de outra loja (404), rota de outra loja (403), cliente (403), reflexo no feed |
| `tests/test_conta.py` | editar nome/e-mail (login muda), e-mail ocupado (409), corpo inválido (422), excluir com senha (sessões e refresh encerrados, e-mail liberado), senha errada (422), cascata de novidades/seguidores, cache limpo |
| `tests/test_front.py` | `/` redireciona para `/app/`, arquivos servidos com tipo certo, CSP e cabeçalhos de segurança só no front |
| `tests/test_cache_feed.py` | HIT/MISS/BYPASS, cache por limite e por cliente, invalidação ao seguir/deixar, publicação visível após o TTL, TTL não renovado, sem Redis |
| `tests/test_erros.py` / `test_health.py` / `test_openapi.py` | formato único de erro (rota inexistente, 405, JSON malformado), `/health` 200/503, rotas documentadas e protegidas no OpenAPI |

## 3. Exemplos de chamada

O jeito mais rápido de ver tudo funcionando é o **front de teste em `/app/`**:
- **Cliente**: lê o feed (com o `X-Cache` de cada resposta), busca lojas, segue e deixa de
  seguir.
- **Lojista**: publica, edita e remove novidades.
- **Os dois**: editam o perfil, trocam a senha e excluem a conta.

O rodapé da página lista cada chamada feita à API, com método, caminho, status, tempo e
`X-Cache`.

Todos os endpoints (sucesso e erro) estão em [`requests.http`](requests.http) — abra no VS Code
(extensão REST Client) ou IntelliJ e execute em ordem: os logins guardam o token em variáveis.
Também dá para testar pelo Swagger em `/docs`. Em curl:

```bash
# Cadastros (públicos)
curl -X POST localhost:8000/lojas -H 'Content-Type: application/json' \
     -d '{"nome": "Loja da Ana", "email": "ana@lojadaana.com", "senha": "senha-forte-123"}'
curl -X POST localhost:8000/clientes -H 'Content-Type: application/json' \
     -d '{"nome": "João Silva", "email": "joao@example.com", "senha": "senha-forte-123"}'

# Login (OAuth2 password flow: form com username = e-mail)
LOJA=$(curl -s -X POST localhost:8000/auth/lojas/token \
     -d 'username=ana@lojadaana.com&password=senha-forte-123' | jq -r .access_token)
CLIENTE=$(curl -s -X POST localhost:8000/auth/clientes/token \
     -d 'username=joao@example.com&password=senha-forte-123' | jq -r .access_token)

# Cliente 1 segue a loja 1 (o token precisa ser do cliente 1)
curl -X POST localhost:8000/clientes/1/seguindo/1 -H "Authorization: Bearer $CLIENTE"

# Loja 1 publica (preco é opcional; o token precisa ser da loja 1)
curl -X POST localhost:8000/lojas/1/novidades -H "Authorization: Bearer $LOJA" \
     -H 'Content-Type: application/json' -d '{"texto": "Chegou a coleção de verão!", "preco": "199.90"}'

# Feed do cliente 1 e próxima página
curl 'localhost:8000/clientes/1/feed?limite=20' -H "Authorization: Bearer $CLIENTE"
curl 'localhost:8000/clientes/1/feed?limite=20&cursor=<proximo_cursor>' -H "Authorization: Bearer $CLIENTE"

# Deixar de seguir
curl -X DELETE localhost:8000/clientes/1/seguindo/1 -H "Authorization: Bearer $CLIENTE"

# O mesmo sem id na URL: a conta vem do token
curl localhost:8000/me -H "Authorization: Bearer $CLIENTE"
curl localhost:8000/me/feed -H "Authorization: Bearer $CLIENTE"
curl -X POST localhost:8000/me/novidades -H "Authorization: Bearer $LOJA" \
     -H 'Content-Type: application/json' -d '{"texto": "Live hoje às 20h"}'

# Leitura pública de lojas
curl 'localhost:8000/lojas?q=ana'
curl localhost:8000/lojas/1
curl 'localhost:8000/lojas/1/novidades?limite=10'

# Editar e remover novidade (PATCH parcial; "preco": null remove o preço)
curl -X PATCH localhost:8000/lojas/1/novidades/1 -H "Authorization: Bearer $LOJA" \
     -H 'Content-Type: application/json' -d '{"texto": "Coleção de verão com 20% off!"}'
curl -X DELETE localhost:8000/lojas/1/novidades/1 -H "Authorization: Bearer $LOJA"

# Editar perfil e excluir conta (exclusão exige a senha atual no corpo)
curl -X PATCH localhost:8000/me -H "Authorization: Bearer $CLIENTE" \
     -H 'Content-Type: application/json' -d '{"nome": "João da Silva"}'
curl -X DELETE localhost:8000/me -H "Authorization: Bearer $CLIENTE" \
     -H 'Content-Type: application/json' -d '{"senha": "senha-forte-123"}'

# Renovar a sessão quando o access expirar (o refresh antigo deixa de valer) e sair
curl -X POST localhost:8000/auth/refresh -H 'Content-Type: application/json' \
     -d '{"refresh_token": "<refresh_token do login>"}'
curl -X POST localhost:8000/auth/logout -H 'Content-Type: application/json' \
     -d '{"refresh_token": "<refresh_token atual>"}'
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
      "criado_em": "2026-11-05T22:10:00.123456Z",
      "editado_em": null
    }
  ],
  "proximo_cursor": null
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

| Endpoint | Auth | Sucesso | Erros |
| --- | --- | --- | --- |
| `POST /lojas` | — | 201 | 409 `email_ja_cadastrado`, 422 |
| `POST /clientes` | — | 201 | 409 `email_ja_cadastrado`, 422 |
| `POST /auth/clientes/token` · `POST /auth/lojas/token` | — | 200 | 401 `credenciais_invalidas`, 429 `muitas_tentativas`, 422 |
| `POST /auth/refresh` | refresh token | 200 | 401 `refresh_invalido`, 422 |
| `POST /auth/logout` | refresh token | 204 | 422 |
| `GET /lojas?q=&limite=&cursor=` | — | 200 | 422 |
| `GET /lojas/{id}` | — | 200 | 404 `loja_nao_encontrada` |
| `GET /lojas/{id}/novidades?limite=&cursor=` | — | 200 | 404, 422 |
| `GET /clientes/{id}/seguindo?limite=&cursor=` | cliente `{id}` | 200 | 401, 403, 422 |
| `POST /clientes/{id}/seguindo/{lojaId}` | cliente `{id}` | 201 | 401, 403, 404 `loja_nao_encontrada`, 409 `ja_segue_loja` |
| `DELETE /clientes/{id}/seguindo/{lojaId}` | cliente `{id}` | 204 | 401, 403, 404 `loja_nao_encontrada`/`nao_segue_loja` |
| `POST /lojas/{id}/novidades` | loja `{id}` | 201 | 401, 403, 422 |
| `PATCH /lojas/{id}/novidades/{nid}` | loja `{id}` | 200 | 401, 403, 404 `novidade_nao_encontrada`, 422 |
| `DELETE /lojas/{id}/novidades/{nid}` | loja `{id}` | 204 | 401, 403, 404 `novidade_nao_encontrada` |
| `PATCH /lojas/{id}` · `PATCH /clientes/{id}` | dono do `{id}` | 200 | 401, 403, 409 `email_ja_cadastrado`, 422 |
| `DELETE /lojas/{id}` · `DELETE /clientes/{id}` (corpo `{"senha"}`) | dono do `{id}` | 204 | 401, 403, 422 (senha incorreta) |
| `GET /clientes/{id}/feed?limite=20&cursor=` | cliente `{id}` | 200 | 401, 403, 422 (`limite` fora de 1–50, cursor inválido) |
| `GET /health` | — | 200 | 503 `banco_indisponivel` |
| `GET /me` | cliente ou loja | 200 | 401 |
| `PUT /me/senha` | cliente ou loja | 204 | 401, 422 (senha atual incorreta, nova inválida) |
| `GET /me/feed` · `GET /me/seguindo` · `POST`/`DELETE /me/seguindo/{lojaId}` | cliente | 200/201/204 | iguais às rotas com `{id}` |
| `POST /me/novidades` · `GET /me/novidades` | loja | 201/200 | iguais às rotas com `{id}` |
| `PATCH`/`DELETE /me/novidades/{nid}` | loja | 200/204 | iguais às rotas com `{id}` |
| `PATCH /me` · `DELETE /me` (corpo `{"senha"}`) | cliente ou loja | 200/204 | iguais às rotas com `{id}` |

401 = `nao_autenticado` (sem token, inválido ou expirado) · 403 = `acesso_negado` (token de
outra conta ou de outro tipo).

O feed responde com o header `X-Cache: HIT | MISS | BYPASS` (primeira página em cache por até
30s; seguir/deixar de seguir atualiza na hora).

## 4. Estrutura de pastas

```
app/
  main.py          # cria a app FastAPI, registra rotas, handlers de erro e docs do OpenAPI
  routes/          # camada HTTP: rotas finas, status codes, parâmetros (sem regra de negócio)
    deps.py        #   dependências: sessão do banco e autenticação (ClienteAutenticado, LojaAutenticada)
  services/        # regras de negócio e queries (lojas, clientes/seguir, feed, auth)
  models/          # tabelas SQLAlchemy, um arquivo por entidade, com constraints e índices
  schemas/         # contratos Pydantic de entrada/saída por recurso e validação de formato
  core/            # infraestrutura: config (env), sessão do banco, segurança (JWT/senha), erros
  front/           # front de teste (HTML + JS puro), servido em /app
  seed.py          # dados de exemplo: python -m app.seed [--reset]
scripts/           # benchmark do feed (make benchmark)
migrations/        # Alembic (async); versions/ tem o histórico do schema
tests/             # testes de integração (API + Postgres real); helpers.py monta cenários
docs/
  desafio.md       # enunciado original
  adr/             # decisões técnicas, uma por arquivo
docker/            # entrypoint do container (aplica migrations e inicia a API)
.github/           # CI (GitHub Actions) e template de Pull Request
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
- **Paginação por cursor (keyset)** ([ADR 0006](docs/adr/0006-paginacao-por-cursor.md)): o
  cursor guarda `(criado_em, id)` do último item; a próxima página usa o mesmo índice e não
  repete nem pula itens quando chegam novidades durante a rolagem (o que `offset` faria).
- **Autenticação OAuth2 + JWT** ([ADR 0007](docs/adr/0007-autenticacao-oauth2-jwt.md)):
  password flow com logins separados para clientes e lojistas, JWT HS256 de 30 min, senhas
  em argon2id. As rotas do enunciado foram mantidas: o token precisa ser do dono do `{id}`.
  Completam a auth: rotas `/me`, refresh token opaco com rotação e detecção de reuso, logout,
  rate limit no login e troca de senha que encerra as sessões.
- **Redis para cache e rate limit, com números** ([ADR 0008](docs/adr/0008-redis-cache-e-rate-limit.md)):
  primeira página do feed em cache por 30s, invalidada ao seguir/deixar (publicar não
  invalida: seriam 100 mil `DEL`). Benchmark com loja de 100 mil seguidores: publicar ~6 ms;
  feed ~6 ms (6 lojas) e ~13 ms (~500 lojas) sem cache, ~2 ms com cache. Sem Redis, a API
  segue funcionando e o rate limit cai para contadores em memória.
- **Edição e exclusão** ([ADR 0009](docs/adr/0009-edicao-exclusao-e-front.md)):
  - `PATCH` é parcial e `DELETE` é físico, com cascata no banco.
  - Editar uma novidade mantém o `criado_em`, para ela não "subir" no feed, e preenche o
    `editado_em`.
  - Excluir a conta pede a senha atual e apaga as sessões.
  - O front de teste é HTML + JS puro, servido pela própria API em `/app`. Fica na mesma
    origem (sem CORS), tem CSP restrita e não precisa de build.
- **Modelagem** — 5 tabelas: `refresh_tokens` (hash SHA-256, família, expiração, revogação),
  `lojas` (`email` único + `senha_hash`), `clientes` (`email`
  único + `senha_hash`), `seguidores` (PK composta `(cliente_id, loja_id)`, que impede seguir
  duas vezes no próprio banco), `novidades` (`preco NUMERIC(12,2)`, CHECKs de texto e preço,
  `editado_em`).
  Ids `BIGINT IDENTITY`, datas `timestamptz`.
- **Unicidade sem corrida** — e-mails e seguir usam `INSERT ... ON CONFLICT DO NOTHING`: duas
  requisições simultâneas não passam pela checagem e quebram com 500; uma recebe 409.
- **Camadas `routes → services → models`** ([ADR 0001](docs/adr/0001-stack-e-organizacao.md)):
  rotas só tratam HTTP; regras ficam nos services, que levantam erros de domínio. Cada camada
  é uma pasta com um arquivo por entidade/recurso.
- **Formato único de erro** ([ADR 0003](docs/adr/0003-formato-unico-de-erro.md)):
  `{"erro": {"codigo", "mensagem", "detalhes"}}` com `codigo` estável para o cliente tratar.
  Inclui validação do FastAPI, 401/403, 404/405 de rota e 500.
- **Bibliotecas**: FastAPI (validação + OpenAPI de graça), SQLAlchemy 2 async + asyncpg (ORM
  tipado, `ON CONFLICT`/`LATERAL` sem SQL cru), Alembic (migrations automáticas no start),
  PyJWT + pwdlib/argon2 (recomendação atual da doc do FastAPI), uv (lockfile reprodutível),
  ruff (lint + format), pytest + httpx (testes via ASGI).
- **Testes contra Postgres real** ([ADR 0005](docs/adr/0005-testes-com-postgres-real.md)), já
  que as regras críticas vivem no banco; o banco de teste é criado e migrado sozinho.
- **Proteção do banco**: `statement_timeout` de 5s por query e `limite` máximo de 50.
- **OpenAPI como contrato**: cada rota lista os códigos de erro possíveis com exemplo, e
  testes garantem que rotas, esquemas de segurança e catálogo de erros não fiquem defasados.

### Decisões sobre pontos não definidos no enunciado

Detalhadas em [ADR 0004](docs/adr/0004-regras-de-entrada.md). Principais:

- **Autenticação foi adicionada** apesar de estar fora do escopo do enunciado (decisão do
  time; ADR 0007). Por isso cadastros exigem `senha` (e lojas, `email`), e "cliente/loja
  inexistente" nas rotas protegidas responde 403, não 404.
- `limite` fora de 1–50 retorna **422** em vez de ajustar em silêncio.
- Espaços nas pontas de `nome`/`texto` são removidos; só espaços conta como vazio.
- E-mail salvo em minúsculas: `Ana@x.com` e `ana@x.com` são a mesma conta (409).
- `preco` aceita até 2 casas decimais e volta como string (`"199.90"`) para não perder precisão.
- Campos desconhecidos no corpo dão 422 — um `"preço"` com acento não é ignorado em silêncio.
- Ao seguir uma loja, as novidades antigas dela já aparecem no feed.

## 6. O que ficou de fora e o que eu faria com mais tempo

- **Auth**: recuperação de senha por e-mail, MFA, listar/encerrar sessões ativas, revogação
  imediata de access tokens (hoje valem até expirar, 30 min). Para um produto real, provedor
  de identidade externo (Authorization Code + PKCE, RS256/JWKS) — ver ADR 0007.
- **Escala do feed**: modelo híbrido (fan-out na escrita para lojas pequenas) se o feed sem
  cache passar de algumas dezenas de ms; invalidar o cache dos seguidores de lojas pequenas
  na publicação; contador desnormalizado de seguidores. Ver ADR 0002 e 0008.
- Gestão: soft delete com "desfazer" e exportação dos dados antes de excluir a conta;
  invalidar o cache dos feeds quando uma novidade for removida por conteúdo indevido.
- Front: é ferramenta de teste; um app de verdade teria build, testes de interface
  (Playwright) e tokens em cookie `HttpOnly` em vez de `sessionStorage`.
- Logs estruturados (JSON) com id de requisição, métricas e tracing.
- Teste de carga concorrente (k6/Locust) sobre a API real em rede; o benchmark atual é
  sequencial e em processo.

Pendências e próximos passos ficam em [`BACKLOG.md`](BACKLOG.md).
