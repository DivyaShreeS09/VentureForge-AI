"""initial schema: startups, analyses

Revision ID: 0001
Revises:
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')

    op.create_table(
        "startups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("funding_answers", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "startup_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("startups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("industry_model_version", sa.Text(), nullable=True),
        sa.Column("industry_prediction", postgresql.JSONB(), nullable=True),
        sa.Column("funding_rubric_version", sa.Text(), nullable=True),
        sa.Column("funding_assessment", postgresql.JSONB(), nullable=True),
        sa.Column("judge_summary", postgresql.JSONB(), nullable=True),
        sa.Column("workflow_trace", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_analyses_startup_id", "analyses", ["startup_id"])


def downgrade() -> None:
    op.drop_index("ix_analyses_startup_id", table_name="analyses")
    op.drop_table("analyses")
    op.drop_table("startups")
