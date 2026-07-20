"""Full Mentor Orchestration phase: coherent MentorInterpretation column on analyses.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("mentor_interpretation", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analyses", "mentor_interpretation")
