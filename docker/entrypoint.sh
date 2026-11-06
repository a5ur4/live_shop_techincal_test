#!/bin/sh
# Aplica as migrations antes de subir a API, para que `docker compose up`
# deixe o banco pronto sem passo manual.
set -e

alembic upgrade head

# Dados de exemplo para desenvolvimento. O seed é idempotente: com o banco já populado,
# não faz nada. Desligue com SEED_DB=false.
if [ "${SEED_DB:-false}" = "true" ]; then
    python -m app.seed
fi

exec "$@"
