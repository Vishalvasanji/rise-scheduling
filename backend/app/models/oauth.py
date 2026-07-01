"""OAuth 2.1 authorization-server state for the Claude.ai connector.

The MCP SDK mounts the OAuth endpoints; these tables persist the state our provider
owns: dynamically-registered clients, single-use authorization codes, and refresh
tokens. Access tokens are stateless JWTs (scope "mcp"), so they need no table. Shared
DB so any MCP instance can serve the flow.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OAuthClient(Base):
    """A connector registered via Dynamic Client Registration (RFC 7591)."""

    __tablename__ = "oauth_clients"

    client_id: Mapped[str] = mapped_column(String, primary_key=True)
    client_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    # Full OAuthClientInformationFull JSON, round-tripped for the SDK.
    client_info: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class OAuthAuthCode(Base):
    """A single-use authorization code minted after the user signs in."""

    __tablename__ = "oauth_auth_codes"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    client_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)  # user email
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    redirect_uri_provided_explicitly: Mapped[bool] = mapped_column(nullable=False)
    code_challenge: Mapped[str] = mapped_column(String, nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    resource: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[float] = mapped_column(nullable=False)  # epoch seconds


class OAuthRefreshToken(Base):
    """A refresh token, so the connector renews access without re-login."""

    __tablename__ = "oauth_refresh_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    client_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)  # user email
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
