"""Shared pytest fixtures. Uses an in-memory SQLite database (via app.database.types'
cross-backend JSON/UUID variants) so tests run fast with no external Postgres dependency.
"""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai import factory
from app.database.session import Base, get_db, get_session_factory
from app.main import app


@pytest.fixture(autouse=True)
def _isolate_gemini_from_the_real_network(monkeypatch):
    """Global test isolation (correctness fix, Product Intelligence Sprint): no test may ever
    depend on the real Gemini API or the real GEMINI_API_KEY that may genuinely be configured in
    a developer's backend/.env for local manual testing. Every test in this suite gets three
    guarantees, unconditionally, with no per-test opt-in required:

      1. `settings.gemini_api_key` is forced to `None` for the duration of the test, so
         `app.ai.factory.get_llm_provider()` returns `None` (the fully-deterministic path) no
         matter what is actually configured in the environment. A test that wants to exercise the
         "Gemini configured" path must explicitly `monkeypatch.setattr(...)` this back to a
         non-empty value itself (as tests/test_mentor_reviewer.py, tests/test_positioning_reviewer.py,
         etc. already do) — that per-test override simply layers on top of this fixture and is
         undone at teardown along with everything else monkeypatch tracks.
      2. `get_llm_provider`'s `lru_cache` is cleared before and after every test, so a provider
         instance built in one test (real or fake) can never leak into another.
      3. `httpx.post` at its one real call site (app.ai.gemini_provider — confirmed via
         `grep -rl httpx.post app/` to be the only place this codebase ever makes an outbound
         network call) is replaced with a function that immediately fails the test via
         `pytest.fail(...)` if invoked. A test that wants to simulate a Gemini HTTP response must
         explicitly monkeypatch `app.ai.gemini_provider.httpx.post` itself for that one test (again,
         exactly the pattern the existing Gemini test files already use) — this default only fires
         when no test-level override exists, so an unexpected/forgotten real call fails loudly
         instead of silently reaching the network or (worse) silently succeeding against a real key
         and making the test's outcome depend on live network/quota state.

    This makes every test's outcome independent of whatever is or isn't in backend/.env — verified
    by running the full suite with a valid key, an invalid key, and no key present, and confirming
    identical pass/fail counts in all three cases (see the Product Intelligence Sprint report).
    """
    monkeypatch.setattr("app.core.config.settings.gemini_api_key", None)
    factory.get_llm_provider.cache_clear()

    def _fail_on_unexpected_network_call(*args, **kwargs):
        pytest.fail(
            "A test attempted a real network call via app.ai.gemini_provider.httpx.post. Tests "
            "must never depend on the real Gemini API — mock the provider (monkeypatch "
            "get_llm_provider to return a fake) or mock httpx.post explicitly for this test."
        )

    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", _fail_on_unexpected_network_call)
    yield
    factory.get_llm_provider.cache_clear()


@pytest.fixture
def db_session(tmp_path):
    # A real file-backed SQLite DB, not `sqlite://` in-memory. Act IV's background analysis
    # thread needs its own DB connection genuinely independent of the test's own `db_session` —
    # an in-memory DB forced onto one shared connection (the old `StaticPool` setup) meant two
    # threads fighting over one physical connection's transaction state, which surfaced as a real
    # `PendingRollbackError`/"not found" race once background execution was introduced. A
    # file-backed DB gives each session its own real connection with normal cross-connection
    # commit visibility, exactly like talking to a real Postgres instance.
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
    # A session factory bound to the same file-backed engine as `db_session` — used by the
    # background analysis thread Act IV's `/startups/{id}/analyze` now spawns. Overriding
    # `get_session_factory` the same way `get_db` is overridden is what makes that thread's
    # writes visible to the test's own requests (and vice versa).
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: TestingSessionLocal
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def wait_for_terminal_analysis(client, analysis_id: str, timeout: float = 10.0) -> dict:
    """Act IV (The Forging) runs analysis in a real background thread now — POST
    `/startups/{id}/analyze` returns immediately with status RUNNING. Tests that need the finished
    result poll `GET /analyses/{id}` (the same real endpoint the frontend polls/streams from)
    until it reaches a terminal status, instead of asserting on the POST response body directly.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1/analyses/{analysis_id}").json()
        if body["status"] in ("COMPLETED", "FAILED"):
            return body
        time.sleep(0.02)
    raise TimeoutError(f"Analysis {analysis_id} did not reach a terminal status within {timeout}s")
