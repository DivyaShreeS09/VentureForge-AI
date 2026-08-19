"""Phase 5: Student 3 growth/strategy intelligence outputs column on analyses.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("student3_outputs", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analyses", "student3_outputs")
