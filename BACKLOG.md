# Backlog

Checklist das tarefas planejadas para o desafio ([enunciado](docs/desafio.md)).
Marque `[x]` ao concluir e mantenha a ordem: **obrigatório antes de diferencial**.

## 0. Base do repositório

- [x] Repositório Git, `.gitignore`, enunciado em `docs/`
- [x] Projeto Python com `uv` (`pyproject.toml` + `uv.lock`)
- [x] Configuração via variáveis de ambiente + `.env.example`
- [x] `Dockerfile` + `docker-compose.yml` (Postgres + API, migrations automáticas)
- [x] `Makefile` com atalhos (up, test, seed, lint)

## 1. Banco de dados

- [x] Modelos SQLAlchemy async: `lojas`, `clientes`, `seguidores`, `novidades`
- [x] Migration inicial (Alembic) com constraints e índices
  - [x] `clientes.email` único
  - [x] PK composta `seguidores(cliente_id, loja_id)` (impede seguir duas vezes)
  - [x] `CHECK` de `texto` (1–500) e `preco > 0`
  - [x] Índice `novidades(loja_id, criado_em DESC, id DESC)` para o feed

## 2. API (obrigatório)

- [x] Formato único de erro `{"erro": {"codigo", "mensagem", "detalhes"}}` (404, 409, 422, 500)
- [x] `POST /lojas` — `nome` obrigatório
- [x] `POST /clientes` — `nome` e `email` obrigatórios, `email` único (409)
- [x] `POST /clientes/{id}/seguindo/{lojaId}` — 404 se cliente/loja não existe, 409 se já segue
- [x] `POST /lojas/{id}/novidades` — `texto` 1–500, `preco` > 0 quando informado
- [x] `GET /clientes/{id}/feed?limite=20` — só lojas seguidas, mais recente primeiro, padrão 20, máximo 50

## 3. Testes (obrigatório)

- [x] Infra de testes: Postgres real, banco de teste criado automaticamente, limpeza entre testes
- [x] Feed: só novidades de lojas seguidas, ordem correta, limite (padrão, máximo, inválido)
- [x] Validações de seguir: 404 cliente, 404 loja, 409 duplicado
- [x] Validações de publicar: texto vazio/longo, preço zero/negativo, loja inexistente
- [x] Cadastro: nome obrigatório, email inválido, email duplicado
- [x] Formato de erro igual em todos os casos

## 4. Entrega (obrigatório)

- [x] Comando de seed
- [x] `requests.http` com exemplos de todos os endpoints
- [x] `README.md` (rodar, testar, exemplos, estrutura, decisões, o que ficou de fora)
- [x] `CLAUDE.md` / `AGENTS.md` para continuidade por pessoas e agentes
- [x] ADRs em `docs/adr/`
- [x] Pull Request `feat/feed-api` → `main` com descrição ([#1](https://github.com/a5ur4/live_shop_techincal_test/pull/1))

## 5. Diferenciais (só após o obrigatório)

- [x] `statement_timeout` nas conexões (proteção contra queries caras — ADR 0002)
- [x] `DELETE /clientes/{id}/seguindo/{lojaId}` (deixar de seguir)
- [x] Paginação por cursor no feed (`proximo_cursor`) — ADR 0006
- [x] OpenAPI enriquecido (exemplos por código de erro, tags, testes de contrato)
- [x] CI no GitHub Actions (lint + migrations + testes com Postgres + build da imagem)
- [x] `GET /health` (verifica conexão com o banco) + healthcheck no compose
- [x] Reorganização em `app/routes/`, `app/models/` e `app/schemas/` (um arquivo por entidade)
- [x] Autenticação OAuth2 (password flow) + JWT para clientes e lojistas — ADR 0007

## 6. Segunda etapa (branch `feat/me-leitura-escala`)

- [x] Leitura: `GET /lojas` (busca e cursor), `GET /lojas/{id}`, `GET /lojas/{id}/novidades`,
      `GET /clientes/{id}/seguindo`
- [x] Rotas `/me` (perfil, feed, seguindo, novidades) pelo tipo do token
- [x] Redis no compose e no CI
- [x] Refresh token com rotação e detecção de reuso, logout — ADR 0007
- [x] Rate limit no login (Redis, fallback em memória) — ADR 0008
- [x] Troca de senha (`PUT /me/senha`) encerrando as sessões
- [x] Cache da primeira página do feed (Redis, TTL 30s) — ADR 0008
- [x] Benchmark com loja de 100 mil seguidores (`make benchmark`) — ADR 0008
- [x] Pull Request `feat/me-leitura-escala` → `main` ([#2](https://github.com/a5ur4/live_shop_techincal_test/pull/2))

## 7. Terceira etapa (branch `feat/edicao-exclusao-front`)

- [x] Editar/remover novidade (`PATCH`/`DELETE /lojas/{id}/novidades/{nid}` e `/me/novidades/{nid}`),
      com `editado_em` (migration) — ADR 0009
- [x] Editar perfil (`PATCH /me`, `/lojas/{id}`, `/clientes/{id}`)
- [x] Excluir conta com confirmação por senha (`DELETE /me`, `/lojas/{id}`, `/clientes/{id}`)
- [x] Front de teste em `/app` (HTML + JS, sem build) — ADR 0009
- [x] Pull Request `feat/edicao-exclusao-front` → `main` ([#3](https://github.com/a5ur4/live_shop_techincal_test/pull/3))

## Ideias futuras (fora do escopo)

- Feed híbrido (fan-out na escrita para lojas pequenas) se o feed sem cache ficar lento
- Invalidar cache dos seguidores de lojas pequenas ao publicar
- Recuperação de senha por e-mail, MFA, listar/encerrar sessões ativas
- Limpeza periódica de refresh tokens expirados
- Contador desnormalizado de seguidores por loja
- Teste de carga concorrente (k6/Locust) sobre a API em rede
