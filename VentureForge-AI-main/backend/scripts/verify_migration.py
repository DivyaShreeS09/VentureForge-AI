"""Migration verification for the production-hardening phase's two new Analysis columns
(`positioning_correction_history`, added in 0003; `revenue_assumptions_history`, added in 0004).

This is a REAL PostgreSQL migration test, not the SQLite `Base.metadata.create_all()` shortcut the
test suite's `conftest.py` fixture uses for speed — `create_all` builds tables straight from the
current ORM models and would never catch an actual Alembic migration bug (a wrong column type, a
missing server_default causing a NOT NULL row to fail, an index conflict, etc.). Only running the
real migration chain against a real Postgres engine proves the upgrade path is safe against
already-existing production data.

What this proves, in order:
  1. Create a disposable database, migrate it to the revision immediately BEFORE this phase (0002).
  2. Insert one "existing" analysis row using only 0002-era columns — simulating a real row that
     existed in production before this phase's migrations ever ran.
  3. Run `alembic upgrade head` (0002 -> 0003 -> 0004).
  4. Re-read that same row: both new columns must exist and default to `[]` (a "safe default"),
     and every 0002-era column/value must be unchanged (the row remains fully readable).
  5. Apply one positioning correction through the real application code path
     (app.services.analysis_service.apply_industry_correction) against this disposable database,
     and confirm `positioning_correction_history` persists exactly one entry afterward.

Usage: `python scripts/verify_migration.py` from backend/, with a reachable PostgreSQL server (the
admin connection defaults to the same server VentureForge AI's own DATABASE_URL points at, using a
throw-away database name so it never touches real data). The disposable database is dropped at the
end whether the script succeeds or fails.
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

import psycopg2
import psycopg2.extras

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402

ADMIN_DB_URL = settings.database_url.rsplit("/", 1)[0] + "/postgres"
TEST_DB_NAME = "ventureforge_migration_verify"
TEST_DB_URL = settings.database_url.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"

PREVIOUS_REVISION = "0002"  # last revision before this phase's two new columns


def _run(step: str, fn) -> None:
    print(f"--- {step} ---")
    fn()
    print(f"OK: {step}\n")


def _admin_connect():
    conn = psycopg2.connect(ADMIN_DB_URL)
    conn.autocommit = True  # CREATE/DROP DATABASE cannot run inside a transaction block
    return conn


def create_disposable_database() -> None:
    # Deliberately not using `with conn:` here — psycopg2's connection context manager wraps
    # statements in an implicit transaction block on this driver/server combination even with
    # autocommit=True set, and CREATE/DROP DATABASE cannot run inside one.
    conn = _admin_connect()
    try:
        cur = conn.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
        cur.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        conn.close()


def drop_disposable_database() -> None:
    conn = _admin_connect()
    try:
        cur = conn.cursor()
        # Terminate any lingering connections (e.g. a leaked SQLAlchemy pool) before dropping.
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (TEST_DB_NAME,),
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
    finally:
        conn.close()


def alembic(*args: str) -> None:
    env = {"DATABASE_URL": TEST_DB_URL}
    import os

    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"alembic {' '.join(args)} failed (exit {result.returncode})")


def insert_pre_phase_analysis_row() -> uuid.UUID:
    with psycopg2.connect(TEST_DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO startups (name, description) VALUES (%s, %s) RETURNING id",
            ("Pre-existing Startup", "A startup that existed before this migration phase ran."),
        )
        startup_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO analyses (startup_id, status, judge_summary) VALUES (%s, %s, %s) RETURNING id",
            (startup_id, "COMPLETED", psycopg2.extras.Json({"venture_positioning": {"primary_domain": "EdTech"}})),
        )
        analysis_id = cur.fetchone()[0]
        conn.commit()
        return analysis_id


def verify_row_readable_with_safe_defaults(analysis_id: uuid.UUID) -> None:
    with psycopg2.connect(TEST_DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status, judge_summary, positioning_correction_history, revenue_assumptions_history "
            "FROM analyses WHERE id = %s",
            (str(analysis_id),),
        )
        row = cur.fetchone()
        assert row is not None, "pre-existing row vanished after migration"
        status, judge_summary, positioning_history, revenue_history = row
        assert status == "COMPLETED"
        assert judge_summary == {"venture_positioning": {"primary_domain": "EdTech"}}
        assert positioning_history == [], f"expected safe default [], got {positioning_history!r}"
        assert revenue_history == [], f"expected safe default [], got {revenue_history!r}"


def apply_one_positioning_correction_and_verify_history(analysis_id: uuid.UUID) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.services import analysis_service

    engine = create_engine(TEST_DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        analysis = analysis_service.apply_industry_correction(db, analysis_id, "Enterprise AI", [])
        assert analysis is not None
        assert len(analysis.positioning_correction_history) == 1
        assert analysis.positioning_correction_history[0]["override"]["primary_domain"] == "Enterprise AI"
        assert analysis.judge_summary["venture_positioning"]["primary_domain"] == "Enterprise AI"
    finally:
        db.close()
        engine.dispose()


def main() -> None:
    print(f"Admin connection target: {ADMIN_DB_URL}")
    with _admin_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT version()")
        print(f"PostgreSQL version: {cur.fetchone()[0]}\n")

    try:
        _run(f"Create disposable database {TEST_DB_NAME!r}", create_disposable_database)
        _run(f"Migrate disposable database to revision {PREVIOUS_REVISION} (previous revision)", lambda: alembic("upgrade", PREVIOUS_REVISION))

        analysis_id = None

        def _insert():
            nonlocal analysis_id
            analysis_id = insert_pre_phase_analysis_row()

        _run("Insert a pre-existing analysis row (0002-era schema only)", _insert)
        _run("Run alembic upgrade head (0002 -> 0003 -> 0004)", lambda: alembic("upgrade", "head"))
        _run(
            "Verify positioning_correction_history/revenue_assumptions_history exist with safe defaults, row remains readable",
            lambda: verify_row_readable_with_safe_defaults(analysis_id),
        )
        _run(
            "Apply one positioning correction via the real service layer; verify history persists",
            lambda: apply_one_positioning_correction_and_verify_history(analysis_id),
        )
        print("RESULT: PASS — migration 0002 -> head is safe against pre-existing production rows.")
    finally:
        _run(f"Drop disposable database {TEST_DB_NAME!r}", drop_disposable_database)


if __name__ == "__main__":
    main()
