"""add task.version / updated_by / updated_at (optimistic lock)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-29 20:30:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'tasks',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column('tasks', sa.Column('updated_by', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'updated_at')
    op.drop_column('tasks', 'updated_by')
    op.drop_column('tasks', 'version')
