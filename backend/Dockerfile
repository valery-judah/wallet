FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock /app/
COPY backend/pyproject.toml backend/README.md /app/backend/

RUN uv sync --frozen --package wallet --group dev --no-install-workspace

COPY backend/src /app/backend/src
COPY backend/scripts /app/backend/scripts

RUN uv sync --frozen --package wallet --group dev

WORKDIR /app/backend

CMD ["uvicorn", "--factory", "wallet.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
