FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY db ./db
COPY scripts ./scripts
RUN uv sync --frozen --no-dev
CMD ["sh", "-c", "uv run python scripts/migrate.py && uv run uvicorn counsel.api.main:app --host 0.0.0.0 --port 8000"]
