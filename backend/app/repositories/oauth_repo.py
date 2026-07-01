"""Data access for the OAuth authorization-server state (clients, auth codes,
refresh tokens). Codes are single-use; codes/tokens carry an expiry we enforce on read."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import OAuthAuthCode, OAuthClient, OAuthRefreshToken

# ---- clients (dynamic registration) ----


def get_client(session: Session, client_id: str) -> OAuthClient | None:
    return session.get(OAuthClient, client_id)


def upsert_client(
    session: Session, client_id: str, client_secret: str | None, client_info: dict
) -> OAuthClient:
    client = session.get(OAuthClient, client_id)
    if client is None:
        client = OAuthClient(client_id=client_id)
        session.add(client)
    client.client_secret = client_secret
    client.client_info = client_info
    session.commit()
    return client


# ---- authorization codes (single-use) ----


def add_code(session: Session, **fields) -> OAuthAuthCode:
    code = OAuthAuthCode(**fields)
    session.add(code)
    session.commit()
    return code


def get_code(session: Session, code: str) -> OAuthAuthCode | None:
    return session.get(OAuthAuthCode, code)


def consume_code(session: Session, code: str) -> None:
    """Delete a code so it can't be replayed."""
    session.execute(delete(OAuthAuthCode).where(OAuthAuthCode.code == code))
    session.commit()


# ---- refresh tokens ----


def add_refresh_token(session: Session, **fields) -> OAuthRefreshToken:
    token = OAuthRefreshToken(**fields)
    session.add(token)
    session.commit()
    return token


def get_refresh_token(session: Session, token: str) -> OAuthRefreshToken | None:
    return session.get(OAuthRefreshToken, token)


def delete_refresh_token(session: Session, token: str) -> None:
    session.execute(delete(OAuthRefreshToken).where(OAuthRefreshToken.token == token))
    session.commit()
