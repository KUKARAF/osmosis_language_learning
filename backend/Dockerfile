FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# install dependencies
COPY backend/pyproject.toml backend/uv.lock backend/
RUN cd backend && uv sync --no-dev --no-install-project --frozen

# dev target — used by dev.docker-compose.yaml
FROM base AS dev
WORKDIR /app/backend
ENTRYPOINT []
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]

# prod target
FROM base AS prod
COPY backend/ backend/
COPY frontend/ frontend/
WORKDIR /app/backend
ENTRYPOINT []
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
