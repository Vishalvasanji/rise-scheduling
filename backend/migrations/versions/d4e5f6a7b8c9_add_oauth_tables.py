"""add OAuth tables (clients, auth codes, refresh tokens) for the Claude.ai connector

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-01 03:10:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: str | None = 'c3d4e5f6a7b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'oauth_clients',
        sa.Column('client_id', sa.String(), primary_key=True),
        sa.Column('client_secret', sa.String(), nullable=True),
        sa.Column('client_info', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'oauth_auth_codes',
        sa.Column('code', sa.String(), primary_key=True),
        sa.Column('client_id', sa.String(), nullable=False, index=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('redirect_uri', sa.Text(), nullable=False),
        sa.Column('redirect_uri_provided_explicitly', sa.Boolean(), nullable=False),
        sa.Column('code_challenge', sa.String(), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('resource', sa.String(), nullable=True),
        sa.Column('expires_at', sa.Float(), nullable=False),
    )
    op.create_table(
        'oauth_refresh_tokens',
        sa.Column('token', sa.String(), primary_key=True),
        sa.Column('client_id', sa.String(), nullable=False, index=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('expires_at', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('oauth_refresh_tokens')
    op.drop_table('oauth_auth_codes')
    op.drop_table('oauth_clients')
