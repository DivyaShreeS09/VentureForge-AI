"""Prevent two concurrent RUNNING analyses for the same startup (Priority 3 fix, ML Excellence
Sprint): a rapid double-click on "Analyze"/"Re-analyze" previously had no guard at any layer —
confirmed by audit as a real race (two background threads, two DB rows, both running the full
pipeline concurrently). A blanket unique constraint on startup_id would be wrong (a startup
legitimately accumulates many COMPLETED/FAILED analyses over its lifetime via Re-analyze) — a
PARTIAL unique index scoped to status='RUNNING' is the correct, minimal, DB-enforced guard: at
most one RUNNING row per startup at any moment, with zero effect on historical rows. This is
immune to application-level races (Postgres rejects the second concurrent INSERT outright,
raising IntegrityError, rather than relying on a check-then-act pattern that could itself race).

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-01
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX ux_analyses_one_running_per_startup "
        "ON analyses (startup_id) WHERE status = 'RUNNING'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ux_analyses_one_running_per_startup")
