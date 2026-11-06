# Backlog

Checklist das tarefas planejadas para o desafio ([enunciado](docs/desafio.md)).
Marque `[x]` ao concluir e mantenha a ordem: **obrigatório antes de diferencial**.

## 0. Base do repositório

- [x] Repositório Git, `.gitignore`, enunciado em `docs/`
- [ ] Projeto Python com `uv` (`pyproject.toml` + `uv.lock`)
- [ ] Configuração via variáveis de ambiente + `.env.example`
- [ ] `Dockerfile` + `docker-compose.yml` (Postgres + API, migrations automáticas)
- [ ] `Makefile` com atalhos (up, test, seed, lint)

## 1. Banco de dados

- [ ] Modelos SQLAlchemy async: `lojas`, `clientes`, `seguidores`, `novidades`
- [ ] Migration inicial (Alembic) com constraints e índices
  - [ ] `clientes.email` único
  - [ ] PK composta `seguidores(cliente_id, loja_id)` (impede seguir duas vezes)
  - [ ] `CHECK` de `texto` (1–500) e `preco > 0`
  - [ ] Índice `novidades(loja_id, criado_em DESC, id DESC)` para o feed

## 2. API (obrigatório)

- [ ] Formato único de erro `{"erro": {"codigo", "mensagem", "detalhes"}}` (404, 409, 422, 500)
- [ ] `POST /lojas` — `nome` obrigatório
- [ ] `POST /clientes` — `nome` e `email` obrigatórios, `email` único (409)
- [ ] `POST /clientes/{id}/seguindo/{lojaId}` — 404 se cliente/loja não existe, 409 se já segue
- [ ] `POST /lojas/{id}/novidades` — `texto` 1–500, `preco` > 0 quando informado
- [ ] `GET /clientes/{id}/feed?limite=20` — só lojas seguidas, mais recente primeiro, padrão 20, máximo 50

## 3. Testes (obrigatório)

- [ ] Infra de testes: Postgres real, banco de teste criado automaticamente, limpeza entre testes
- [ ] Feed: só novidades de lojas seguidas, ordem correta, limite (padrão, máximo, inválido)
- [ ] Validações de seguir: 404 cliente, 404 loja, 409 duplicado
- [ ] Validações de publicar: texto vazio/longo, preço zero/negativo, loja inexistente
- [ ] Cadastro: nome obrigatório, email inválido, email duplicado
- [ ] Formato de erro igual em todos os casos

## 4. Entrega (obrigatório)

- [ ] Comando de seed
- [ ] `requests.http` com exemplos de todos os endpoints
- [ ] `README.md` (rodar, testar, exemplos, estrutura, decisões, o que ficou de fora)
- [ ] `CLAUDE.md` / `AGENTS.md` para continuidade por pessoas e agentes
- [ ] ADRs em `docs/adr/`
- [ ] Pull Request `feat/feed-api` → `main` com descrição

## 5. Diferenciais (só após o obrigatório)

- [ ] `DELETE /clientes/{id}/seguindo/{lojaId}` (deixar de seguir)
- [ ] Paginação por cursor no feed (`proximo_cursor`)
- [ ] OpenAPI enriquecido (exemplos, respostas de erro documentadas)
- [ ] CI no GitHub Actions (lint + testes com Postgres a cada push)
- [ ] `GET /health` (verifica conexão com o banco)

## Ideias futuras (fora do escopo)

- Feed híbrido (fan-out na escrita para lojas pequenas, na leitura para lojas grandes)
- Cache do feed (Redis) para clientes muito ativos
- Autenticação
- Rate limiting
