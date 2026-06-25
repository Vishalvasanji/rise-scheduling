"""add task.trade

Revision ID: 3a7e1b9c2d04
Revises: 1cf780a74a82
Create Date: 2026-06-25 03:10:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '3a7e1b9c2d04'
down_revision: str | None = '1cf780a74a82'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('trade', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'trade')
