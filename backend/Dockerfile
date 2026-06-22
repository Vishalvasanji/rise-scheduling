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

# Run migrations, then serve. (MCP server is launched separately:
#   python -m app.mcp.server)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.api.main:app --host 0.0.0.0 --port 8000"]
