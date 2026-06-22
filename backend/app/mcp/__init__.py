"""MCP server — the chat interface for all users. Thin tool adapters over the
SAME service layer the API uses, so chat and web share one validation + recalc +
audit path (SCOPE §5.3)."""
