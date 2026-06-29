"""add project.pending_proposal

Revision ID: d7a4c9b1e2f3
Revises: c5d2e1f00abc
Create Date: 2026-06-29 15:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd7a4c9b1e2f3'
down_revision: str | None = 'c5d2e1f00abc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('pending_proposal', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'pending_proposal')
