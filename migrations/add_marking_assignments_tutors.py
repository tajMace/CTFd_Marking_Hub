"""Add marking_assignments and marking_tutors tables

Revision ID: marking_hub_002
Revises: marking_hub_001
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "marking_hub_002"
down_revision = "marking_hub_001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "marking_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", name="uq_marking_assignments_user_id"),
    )

    op.create_table(
        "marking_tutors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_marking_tutors_user_id"),
    )


def downgrade():
    op.drop_table("marking_tutors")
    op.drop_table("marking_assignments")
