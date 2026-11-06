#!/bin/sh
# Aplica as migrations antes de subir a API, para que `docker compose up`
# deixe o banco pronto sem passo manual.
set -e

alembic upgrade head

exec "$@"
