FROM python:3.12-alpine

RUN apk upgrade --no-cache

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies using standalone (non-workspace) resolution
COPY service/pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY service/src/ src/
COPY service/migrations/ migrations/
COPY service/alembic.ini .

RUN adduser -D -u 1000 sentinel
USER sentinel

EXPOSE 9003

CMD [".venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9003", "--no-server-header"]
