"""Phase 3: Strategic Opportunity Discovery column on analyses.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("strategic_opportunity", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analyses", "strategic_opportunity")
