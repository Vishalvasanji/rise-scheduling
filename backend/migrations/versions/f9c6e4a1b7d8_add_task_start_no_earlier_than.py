"""add task.start_no_earlier_than

Revision ID: f9c6e4a1b7d8
Revises: e8b5d3c4f6a7
Create Date: 2026-06-29 18:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f9c6e4a1b7d8'
down_revision: str | None = 'e8b5d3c4f6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('start_no_earlier_than', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'start_no_earlier_than')
