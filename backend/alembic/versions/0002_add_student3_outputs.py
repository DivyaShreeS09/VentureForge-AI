"""add structured Student 3 analysis output

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("student3_outputs", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "student3_outputs")
