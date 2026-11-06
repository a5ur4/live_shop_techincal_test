# AGENTS.md

As instruções para agentes (e pessoas) que forem trabalhar neste repositório ficam em
[`CLAUDE.md`](CLAUDE.md), para não manter dois arquivos iguais. Leia-o antes de começar.

Resumo mínimo:

- Requisitos: `docs/desafio.md`. Decisões: `docs/adr/`. Pendências: `BACKLOG.md`.
- Rodar: `make up` · Testar: `make check` (precisa passar antes de todo commit).
- Camadas `app/routes → app/services → app/models`; erros só via `app/core/errors.py`.
- Rotas protegidas usam `ClienteAutenticado`/`LojaAutenticada`; rotas `/me`, `ClienteAtual`/
  `LojaAtual`/`ContaAtual` (`app/routes/deps.py`). Redis é opcional: nunca dependa dele.
- Tudo em português (domínio, JSON, mensagens, commits em Conventional Commits).
