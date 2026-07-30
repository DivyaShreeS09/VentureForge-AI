"""Cross-module integration test fixtures. Mirrors backend/tests/conftest.py's file-backed-SQLite
test client since this suite exercises the real HTTP app from outside the backend/ package.
"""

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.database.session import Base, get_db, get_session_factory  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_session(tmp_path):
    # A real file-backed SQLite DB, not `sqlite://` in-memory + StaticPool — matches
    # backend/tests/conftest.py's own fixture exactly, and for the same reason: Act IV's
    # background analysis thread needs its own DB connection genuinely independent of the test's
    # own `db_session`. An in-memory DB forced onto one shared connection meant the background
    # thread (using whatever `get_session_factory` resolves to) and the test's own overridden
    # `get_db` were never guaranteed to see each other's writes — in this suite specifically, since
    # only `get_db` was overridden below and `get_session_factory` was left pointing at the real,
    # not-available-in-CI database, the background thread's writes never landed anywhere this
    # suite's `GET /analyses/{id}` could see, so every analysis hung at RUNNING forever (confirmed
    # via a live TimeoutError reproduction, not a hypothetical). A file-backed DB gives each
    # connection normal cross-connection commit visibility, exactly like talking to real Postgres.
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session):
    # Overriding `get_session_factory` the same way `get_db` is overridden is what makes the
    # background analysis thread's writes visible to the test's own requests (and vice versa) —
    # see the `db_session` fixture's comment above for why this was missing before.
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: TestingSessionLocal
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def wait_for_terminal_analysis(client, analysis_id: str, timeout: float = 10.0) -> dict:
    """`POST /startups/{id}/analyze` returns immediately with status RUNNING — the real
    orchestrator run continues in a background thread (Act IV, The Forging). This suite's tests
    predate that change and used to assert COMPLETED on the POST response directly; every call
    site now polls the same real `GET /analyses/{id}` endpoint the frontend does until the row
    reaches a terminal status, exactly matching backend/tests/conftest.py's own helper."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1/analyses/{analysis_id}").json()
        if body["status"] in ("COMPLETED", "FAILED"):
            return body
        time.sleep(0.02)
    raise TimeoutError(f"Analysis {analysis_id} did not reach a terminal status within {timeout}s")
