"""Add marking deadlines table

Revision ID: marking_hub_003
Revises: marking_hub_002
Create Date: 2026-02-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'marking_hub_003'
down_revision = 'marking_hub_002'
branch_labels = None
depends_on = None


def upgrade():
    # Create marking_deadlines table
    op.create_table(
        'marking_deadlines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['challenge_id'], ['challenges.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('challenge_id', name='uq_marking_deadlines_challenge_id')
    )


def downgrade():
    op.drop_table('marking_deadlines')
