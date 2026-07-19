"""add optional customer RFM input for trained segmentation

Revision ID: 0003
Revises: 0002
"""

from alembic import op
from sqlalchemy import JSON, Column
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("startups", Column("customer_rfm", JSON().with_variant(JSONB(), "postgresql"), nullable=True))


def downgrade() -> None:
    op.drop_column("startups", "customer_rfm")
