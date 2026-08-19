"""Phase 5: optional customer RFM input for trained segmentation, on startups.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-20
"""

from alembic import op
from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "startups",
        Column("customer_rfm", JSON().with_variant(JSONB(), "postgresql"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("startups", "customer_rfm")
