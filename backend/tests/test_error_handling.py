"""Failure-mode tests: the API must degrade gracefully, not crash, when the database or the
industry classifier is unavailable, and must reject malformed requests with a clear 4xx.
"""

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.database.session import get_db
from app.main import app
from tests.conftest import wait_for_terminal_analysis


def test_database_unavailable_returns_503():
    def _broken_get_db():
        raise OperationalError("connection failed", {}, Exception("simulated"))
        yield  # pragma: no cover - unreachable, keeps this a generator

    app.dependency_overrides[get_db] = _broken_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/startups",
                json={"name": "X", "description": "a" * 20, "funding_answers": {}},
            )
        assert response.status_code == 503
        assert "Database unavailable" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_industry_classifier_unavailable_does_not_crash_analyze(client, monkeypatch):
    from app.ml.predictor import IndustryClassifierUnavailable

    def _raise_unavailable(name, description):
        raise IndustryClassifierUnavailable("model not trained")

    monkeypatch.setattr("app.agents.nodes.predict_industry", _raise_unavailable)

    create = client.post(
        "/api/v1/startups",
        json={"name": "Nova", "description": "a" * 20, "funding_answers": {}},
    )
    startup_id = create.json()["id"]

    response = client.post(f"/api/v1/startups/{startup_id}/analyze")
    assert response.status_code == 201
    body = wait_for_terminal_analysis(client, response.json()["id"])
    assert body["status"] == "COMPLETED"
    assert body["industry_prediction"] is None
    assert "couldn't confidently place this in a specific industry" in body["judge_summary"]["overall_assessment"]


def test_malformed_json_body_returns_422(client):
    response = client.post(
        "/api/v1/startups",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_wrong_field_types_return_422(client):
    response = client.post(
        "/api/v1/startups",
        json={"name": 12345, "description": "a" * 20, "funding_answers": {}},
    )
    assert response.status_code == 422


def test_system_status_reports_healthy_database(client):
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["api"]["ok"] is True
    assert body["database"]["ok"] is True
    assert "industry_model" in body
    assert "llm" in body


def test_system_status_reports_database_down(client):
    """A session that yields fine but fails on the first query mirrors a real unreachable
    PostgreSQL: SQLAlchemy sessions connect lazily, so the failure surfaces on `execute()`, not
    when the dependency is constructed."""

    class _BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("connection failed", {}, Exception("simulated"))

    def _broken_get_db():
        yield _BrokenSession()

    from app.database.session import get_db

    app.dependency_overrides[get_db] = _broken_get_db
    try:
        response = client.get("/api/v1/system/status")
        assert response.status_code == 200
        body = response.json()
        assert body["database"]["ok"] is False
        assert "unreachable" in body["database"]["detail"].lower()
    finally:
        pass  # the `client` fixture's own dependency_overrides.clear() restores this after the test


def test_system_status_disabled_outside_development(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.system_status.settings.app_env", "production")
    response = client.get("/api/v1/system/status")
    assert response.status_code == 404
