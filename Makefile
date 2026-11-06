.DEFAULT_GOAL := help
.PHONY: help up down logs db dev migrate migration seed test test-docker lint format check

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Sobe Postgres + API (migrations automáticas) em http://localhost:8000
	docker compose up -d --build --wait

down: ## Derruba os containers (mantém os dados)
	docker compose down

logs: ## Acompanha os logs da API
	docker compose logs -f api

db: ## Sobe só o Postgres (para rodar API/testes localmente)
	docker compose up -d --wait db

dev: db migrate ## API local com reload (requer uv)
	uv run fastapi dev app/main.py

migrate: ## Aplica as migrations no banco local
	uv run alembic upgrade head

migration: ## Gera migration a partir dos modelos: make migration m="descricao"
	uv run alembic revision --autogenerate -m "$(m)"

seed: ## Popula o banco da API em Docker com dados de exemplo
	docker compose exec api python -m app.seed

test: db ## Roda os testes localmente (requer uv)
	uv run pytest

test-docker: ## Roda os testes dentro do Docker (só requer Docker)
	docker compose --profile test run --rm --build tests

lint: ## Verifica lint e formatação
	uv run ruff check .
	uv run ruff format --check .

format: ## Corrige lint e formatação
	uv run ruff check --fix .
	uv run ruff format .

check: lint test ## Lint + testes (o mesmo que o CI roda)
