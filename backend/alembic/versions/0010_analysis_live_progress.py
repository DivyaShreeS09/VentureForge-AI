"""Act IV (The Forging): live-progress columns on analyses for real incremental persistence.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-26
"""

from alembic import op
from sqlalchemy import Column, Text

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", Column("current_node", Text(), nullable=True))
    op.add_column("analyses", Column("current_stage", Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "current_stage")
    op.drop_column("analyses", "current_node")
