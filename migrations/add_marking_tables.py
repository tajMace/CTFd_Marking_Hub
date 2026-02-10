"""Add marking_submissions table

Revision ID: marking_hub_001
Revises: 
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa

revision = 'marking_hub_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'marking_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('mark', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('marked_at', sa.DateTime(), nullable=True),
        sa.Column('marked_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['marked_by'], ['users.id']),
        sa.UniqueConstraint('submission_id')
    )

def downgrade():
    op.drop_table('marking_submissions')