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
