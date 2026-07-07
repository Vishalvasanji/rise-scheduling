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

# Serve immediately. Migrations + idempotent seeds (dummy data only if empty, plus
# the Lake Jackson demo project and admin account — created once, never clobbering
# edits) run in a background task inside the app (see app/api/main.py lifespan), so a
# cold/cross-region Turso can't fail the boot; DB routes return 503 until it's ready.
# Bind to $PORT when the host provides it (Render), else 8000. (MCP server is launched
# separately: python -m app.mcp.server)
CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
