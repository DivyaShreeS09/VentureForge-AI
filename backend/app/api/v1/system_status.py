"""Development-only aggregate health check for the frontend's system-status overlay.

Combines four real, independently-checked signals — API, database, industry model, and optional
LLM provider — into one response so the frontend can tell the user *which* service is down instead
of a single opaque "Database unavailable" banner. Every field reflects real application state;
nothing here is simulated. Disabled outside development (returns 404) since it runs an extra DB
round-trip and reads local migration state purely for developer convenience.

Uses the same `get_db` dependency as every other route (not the module-level `engine` directly) so
this endpoint is testable against the test suite's in-memory SQLite override like everything else.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.ai.factory import get_llm_provider
from app.core.config import settings
from app.database.session import get_db
from app.ml import predictor

router = APIRouter(tags=["system"])


def _database_status(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"ok": True, "detail": None}
    except OperationalError:
        return {
            "ok": False,
            "detail": "Database unreachable. Check that PostgreSQL is running and DATABASE_URL is correct.",
        }


def _migration_status(db: Session) -> dict:
    """Compares the DB's current Alembic revision to the newest revision on disk.

    Never raises: an unreadable migration history (including the test suite's SQLite database,
    which has no Alembic history at all) is reported as unknown, not a crash, since this is a
    convenience signal, not something the app depends on to serve requests.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)
        head_revision = script.get_current_head()
        current_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        return {"up_to_date": current_revision == head_revision, "detail": None}
    except Exception:
        return {"up_to_date": None, "detail": "Could not determine migration state."}


@router.get("/system/status")
def system_status(db: Session = Depends(get_db)) -> dict:
    if settings.app_env == "production":
        raise HTTPException(status_code=404, detail="Not found")

    database = _database_status(db)
    model_metadata = predictor.model_metadata()

    return {
        "api": {"ok": True},
        "database": database,
        "migrations": _migration_status(db) if database["ok"] else {"up_to_date": None, "detail": None},
        "industry_model": {
            "ok": model_metadata is not None,
            "version": model_metadata.get("version") if model_metadata else None,
            "detail": None if model_metadata else "No trained artifact — run the training command (see README).",
        },
        "llm": {
            "configured": get_llm_provider() is not None,
            "detail": "Optional — the Judge Agent is fully functional without it.",
        },
    }
