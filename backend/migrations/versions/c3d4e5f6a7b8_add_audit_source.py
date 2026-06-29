"""add audit_log.source (web | chat)

Distinguishes a change made from the web app vs. through the Claude.ai (MCP)
connector, so the Activity feed can show a "via Claude" badge.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-29 21:15:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: str | None = 'b2c3d4e5f6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'audit_log',
        sa.Column('source', sa.String(), nullable=False, server_default='web'),
    )


def downgrade() -> None:
    op.drop_column('audit_log', 'source')
