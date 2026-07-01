"""Application configuration. All config comes from env vars (SCOPE §8)."""

from __future__ import annotations

from datetime import date

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pilot settings, loaded from the environment / a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Data-access layer — the single DB swap point (SQLite -> Turso/Postgres).
    database_url: str = "sqlite:///./rise_schedule.db"

    # Auth (pilot only, behind one swappable module).
    auth_mode: str = "jwt"
    auth_secret: str = "change-me-in-real-deployments-this-is-a-pilot-dummy-secret"
    # Keep users signed in for 30 days so they don't have to log in again often.
    auth_token_ttl_minutes: int = 43_200  # 30 days
    # Long-lived token a user pastes into the Claude.ai custom connector. A year so
    # they don't have to re-mint constantly; regenerate to rotate.
    connector_token_ttl_minutes: int = 525_600  # 365 days

    # Public URL of the hosted MCP (Streamable HTTP) service, shown in the
    # "Connect Claude" panel and used as the connector's resource server URL.
    mcp_public_url: str = "https://rise-schedule-hub-mcp.onrender.com/mcp"
    # Origin of the MCP service — the OAuth issuer, where /authorize, /token,
    # /oauth/login etc. are mounted (mcp_public_url without the /mcp path).
    mcp_issuer_url: str = "https://rise-schedule-hub-mcp.onrender.com"
    # TTL of the OAuth access token issued to the connector (short; refreshed).
    mcp_access_token_ttl_minutes: int = 60

    # Schedule anchor for the pilot (P1 start date).
    pilot_anchor_date: date = date(2026, 6, 22)

    # CORS.
    frontend_origin: str = "http://localhost:5173"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
