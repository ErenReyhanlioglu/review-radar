"""add_chart_data_to_tasks

Revision ID: c8f92d3a1b05
Revises: a3f81c2e9d47
Create Date: 2026-06-30
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'c8f92d3a1b05'
down_revision = 'a3f81c2e9d47'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'task_queue',
        sa.Column('chart_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('task_queue', 'chart_data')
