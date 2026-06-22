# RISE Schedule Hub backend — FastAPI API + MCP server. Docker-native so the
# same container lifts from Render (pilot) to Azure (production) unchanged.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY . .

EXPOSE 8000

# On boot: apply migrations, seed dummy data only if the DB is empty, then serve.
# Bind to $PORT when the host provides it (Render), else default 8000 locally.
# (MCP server is launched separately: python -m app.mcp.server)
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed.run_seed --if-empty && uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
