"""add user_projects assignment table

Revision ID: a1b2c3d4e5f6
Revises: f9c6e4a1b7d8
Create Date: 2026-06-29 19:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'f9c6e4a1b7d8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'user_projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column(
            'project_id', sa.Integer(),
            sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.UniqueConstraint('user_id', 'project_id', name='uq_user_project'),
    )
    op.create_index('ix_user_projects_user_id', 'user_projects', ['user_id'])
    op.create_index('ix_user_projects_project_id', 'user_projects', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_user_projects_project_id', table_name='user_projects')
    op.drop_index('ix_user_projects_user_id', table_name='user_projects')
    op.drop_table('user_projects')
