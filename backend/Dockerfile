FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

WORKDIR /app

# install dependencies
COPY backend/pyproject.toml backend/pyproject.toml
RUN cd backend && uv sync --no-dev --no-install-project

# dev target — used by dev.docker-compose.yaml
FROM base AS dev
WORKDIR /app/backend

# prod target
FROM base AS prod
COPY backend/ backend/
COPY frontend/ frontend/
WORKDIR /app/backend
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
