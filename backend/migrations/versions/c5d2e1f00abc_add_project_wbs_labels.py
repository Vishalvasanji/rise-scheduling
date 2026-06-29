"""add project.wbs_labels

Revision ID: c5d2e1f00abc
Revises: 3a7e1b9c2d04
Create Date: 2026-06-29 14:30:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c5d2e1f00abc'
down_revision: str | None = '3a7e1b9c2d04'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('wbs_labels', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'wbs_labels')
