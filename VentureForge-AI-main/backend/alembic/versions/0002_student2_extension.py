"""Student 2 extension: company metrics, revenue assumptions, market evidence inputs; success
prediction, revenue estimate, market intelligence, competitor analysis, customer personas, and
business model outputs.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "startups",
        sa.Column("company_metrics", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "startups",
        sa.Column("revenue_assumptions", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "startups",
        sa.Column("market_evidence", postgresql.JSONB(), nullable=False, server_default="{}"),
    )

    op.add_column("analyses", sa.Column("success_model_version", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("success_prediction", postgresql.JSONB(), nullable=True))
    op.add_column("analyses", sa.Column("revenue_engine_version", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("revenue_estimate", postgresql.JSONB(), nullable=True))
    op.add_column("analyses", sa.Column("market_intelligence", postgresql.JSONB(), nullable=True))
    op.add_column("analyses", sa.Column("competitor_analysis", postgresql.JSONB(), nullable=True))
    op.add_column("analyses", sa.Column("customer_personas", postgresql.JSONB(), nullable=True))
    op.add_column("analyses", sa.Column("business_model", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "business_model")
    op.drop_column("analyses", "customer_personas")
    op.drop_column("analyses", "competitor_analysis")
    op.drop_column("analyses", "market_intelligence")
    op.drop_column("analyses", "revenue_estimate")
    op.drop_column("analyses", "revenue_engine_version")
    op.drop_column("analyses", "success_prediction")
    op.drop_column("analyses", "success_model_version")

    op.drop_column("startups", "market_evidence")
    op.drop_column("startups", "revenue_assumptions")
    op.drop_column("startups", "company_metrics")
