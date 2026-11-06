# syntax=docker/dockerfile:1
FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Dependências primeiro para aproveitar cache de camadas.
COPY pyproject.toml uv.lock ./

# --- Imagem de desenvolvimento/testes: inclui pytest e ruff -----------------
FROM base AS dev
RUN uv sync --frozen --no-install-project
COPY . .

# --- Imagem de execução: só dependências de produção ------------------------
FROM base AS runtime
RUN uv sync --frozen --no-install-project --no-dev
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && useradd --system --uid 10001 --no-create-home app

# Arquivos ficam do root (somente leitura para a app); o processo roda sem privilégios.
USER app

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
