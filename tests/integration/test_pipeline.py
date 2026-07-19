"""End-to-end integration test: submit a startup over HTTP, run the real orchestrator pipeline
(real trained industry classifier, real deterministic funding rubric, real Judge Agent), persist
to an in-memory database, then verify a second, independent request retrieves the same saved
result — the same round trip a page reload does against real Postgres.

Requires the industry classifier artifact to exist (see ml/README.md); skipped otherwise, not
failed, since training is a separate explicit step.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.ml import predictor  # noqa: E402


@pytest.fixture(autouse=True)
def _skip_if_untrained():
    if not predictor.is_loaded():
        pytest.skip("industry_classifier artifact not trained — run ml/src/training first")


def test_submit_analyze_and_reload_returns_same_persisted_result(client):
    create_response = client.post(
        "/api/v1/startups",
        json={
            "name": "Nova Health",
            "description": "A telehealth platform connecting patients with clinicians for chronic care follow-up.",
            "funding_answers": {"problem_clarity": 2, "product_maturity": 1},
        },
    )
    assert create_response.status_code == 201
    startup = create_response.json()

    analyze_response = client.post(f"/api/v1/startups/{startup['id']}/analyze")
    assert analyze_response.status_code == 201
    first = analyze_response.json()

    assert first["status"] == "COMPLETED"
    # This test verifies the submit -> analyze -> persist -> reload round trip, not classifier
    # accuracy for this specific description — the trained artifact may be the real model or the
    # generated bootstrap corpus (see ml/DATASETS.md), each with a different label set, so only a
    # structurally valid prediction is asserted here, not a specific hardcoded label.
    metadata = predictor.model_metadata()
    assert metadata is not None
    assert first["industry_prediction"]["predicted_industry"] in set(metadata["labels"])
    assert first["funding_assessment"]["overall_score"] > 0
    assert first["judge_summary"]["overall_assessment"]
    assert first["student3_outputs"]["customer_segment"]

    # Simulate a page reload: an independent GET must return the exact same persisted analysis.
    reload_response = client.get(f"/api/v1/analyses/{first['id']}")
    assert reload_response.status_code == 200
    second = reload_response.json()

    assert second["industry_prediction"] == first["industry_prediction"]
    assert second["funding_assessment"] == first["funding_assessment"]
    assert second["judge_summary"] == first["judge_summary"]
    assert second["student3_outputs"] == first["student3_outputs"]
