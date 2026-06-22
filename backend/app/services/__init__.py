"""Service layer — the single write + validation + recalc path shared by the
FastAPI API and the MCP server. The API and MCP are thin adapters over these
functions; they never touch repositories or the engine directly (SCOPE §11)."""
