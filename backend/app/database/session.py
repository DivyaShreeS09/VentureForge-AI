"""SQLAlchemy engine/session setup."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# A short connect_timeout means an unreachable/misconfigured database fails fast (a few seconds)
# instead of hanging on the OS-level TCP timeout — SQLite (used by the test suite) ignores this
# connect_args key harmlessly since it targets the postgres/psycopg2 driver specifically.
_connect_args = {"connect_timeout": 5} if settings.database_url.startswith("postgresql") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory() -> sessionmaker:
    """A FastAPI dependency (not a plain import) so a background thread outside the request
    lifecycle (see `analysis_service._execute_analysis_stream`) can create its own independent
    `Session` bound to the *same* engine the current request is using — production code gets the
    real `SessionLocal`; the test suite overrides this exactly like `get_db`, pointing it at the
    same ephemeral per-test in-memory engine, so a background thread's session sees the same
    database the test's own session does."""
    return SessionLocal
