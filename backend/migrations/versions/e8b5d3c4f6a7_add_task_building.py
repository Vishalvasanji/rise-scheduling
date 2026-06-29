"""add task.building

Revision ID: e8b5d3c4f6a7
Revises: d7a4c9b1e2f3
Create Date: 2026-06-29 17:30:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e8b5d3c4f6a7'
down_revision: str | None = 'd7a4c9b1e2f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('building', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'building')
