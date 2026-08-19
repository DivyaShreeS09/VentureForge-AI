"""Tests for POST /api/v1/predict/industry — the thin, read-only Discovery preview endpoint.
Proves it never fabricates a prediction (an untrained classifier or too-short description
honestly reports `available: false`) and that its numbers are byte-identical to what
`app.ml.predictor.predict_industry` / `app.ml.positioning_taxonomy.extract_deployment_sectors`
compute directly — i.e. this really is a thin wrapper, not a second prediction path.
"""

import pytest

from app.ml import predictor
from app.ml.positioning_taxonomy import extract_deployment_sectors


@pytest.fixture(autouse=True)
def _skip_if_untrained():
    if not predictor.is_loaded():
        pytest.skip("industry_classifier artifact not trained — run ml/src/training first")


DESCRIPTION = (
    "A restaurant inventory tool that predicts spoilage before it happens and helps hotel "
    "kitchens reorder automatically."
)


def test_matches_predict_industry_exactly(client):
    direct = predictor.predict_industry("WasteLess Kitchen", DESCRIPTION)

    response = client.post(
        "/api/v1/predict/industry", json={"name": "WasteLess Kitchen", "description": DESCRIPTION}
    )
    assert response.status_code == 200
    body = response.json()

    assert body["available"] is True
    assert body["predicted_industry"] == direct["predicted_industry"]
    assert body["confidence"] == pytest.approx(direct["confidence"])
    assert body["is_uncertain"] == direct["is_uncertain"]
    assert body["secondary_industry"] == direct["secondary_industry"]
    assert body["model_version"] == direct["model_version"]


def test_customer_hints_match_extract_deployment_sectors_exactly(client):
    direct_sectors = extract_deployment_sectors(DESCRIPTION)

    body = client.post(
        "/api/v1/predict/industry", json={"name": "WasteLess Kitchen", "description": DESCRIPTION}
    ).json()

    assert [h["sector"] for h in body["customer_hints"]] == [s["sector"] for s in direct_sectors]
    for hint, sector in zip(body["customer_hints"], direct_sectors):
        assert hint["matched_text"] == sector["matched_text"]


def test_detected_keywords_are_drawn_only_from_matched_sector_text(client):
    body = client.post(
        "/api/v1/predict/industry", json={"name": "WasteLess Kitchen", "description": DESCRIPTION}
    ).json()

    all_matched = {kw for sector in extract_deployment_sectors(DESCRIPTION) for kw in sector["matched_text"]}
    assert set(body["detected_keywords"]) == all_matched


def test_too_short_description_is_reported_as_unavailable_not_a_guess(client):
    body = client.post("/api/v1/predict/industry", json={"name": "X", "description": "short"}).json()
    assert body["available"] is False
    assert body["predicted_industry"] is None


def test_untrained_classifier_reports_unavailable_rather_than_500(client, monkeypatch):
    from app.ml.predictor import IndustryClassifierUnavailable

    def _raise(*args, **kwargs):
        raise IndustryClassifierUnavailable("no artifact")

    monkeypatch.setattr("app.api.v1.predict.predict_industry", _raise)

    response = client.post("/api/v1/predict/industry", json={"name": "X", "description": DESCRIPTION})
    assert response.status_code == 200
    assert response.json()["available"] is False


def test_never_creates_a_startup_row(client, db_session):
    from app.models.startup import Startup

    before = db_session.query(Startup).count()
    client.post("/api/v1/predict/industry", json={"name": "X", "description": DESCRIPTION})
    after = db_session.query(Startup).count()
    assert after == before
