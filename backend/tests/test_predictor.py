"""Tests against whatever trained artifact is present in ml/models/industry_classifier/v2/
(produced by `python -m ml.src.training.train_industry_classifier` — see ml/README.md). Skipped if
the artifact hasn't been trained yet, rather than failing — training is a separate, explicit step.

The artifact may have been trained on the real YC dataset OR the generated bootstrap corpus (see
ml/DATASETS.md) — whichever `ml/data/raw/industry_dataset.csv` was present at training time. A
fresh checkout (including CI) never has that file, since it's gitignored, so these tests must
validate predictions against the model's own recorded label set rather than assuming the real
dataset's 7-class taxonomy — hardcoding that taxonomy here previously made
`test_unknown_vocabulary_still_returns_a_prediction` fail on any machine that hadn't separately
trained on the real dataset, since the bootstrap corpus uses a different 6-class taxonomy.
"""

import pytest

from app.ml import predictor


@pytest.fixture(autouse=True)
def _skip_if_untrained():
    if not predictor.is_loaded():
        pytest.skip("industry_classifier artifact not trained — run ml/src/training first")


def _known_taxonomy() -> set[str]:
    metadata = predictor.model_metadata()
    assert metadata is not None
    return set(metadata["labels"])


def test_predicts_reasonable_structure():
    result = predictor.predict_industry(
        "PayFlux", "A payments platform that lets small businesses settle cross-border payments in seconds."
    )
    assert result["predicted_industry"] in _known_taxonomy()
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["alternatives"]) <= 3
    assert result["model_version"] == "v2"
    assert "is_uncertain" in result and "uncertainty_reasons" in result


def test_blank_input_does_not_crash():
    result = predictor.predict_industry("", "")
    assert "predicted_industry" in result


def test_blank_input_is_flagged_uncertain():
    # No text at all carries no class signal — the vectorizer sees an all-zero vector, so the
    # prediction must never be presented as a confident fact.
    result = predictor.predict_industry("", "")
    assert result["is_uncertain"] is True


def test_very_short_description():
    result = predictor.predict_industry("X", "app")
    assert "predicted_industry" in result


def test_unknown_vocabulary_still_returns_a_prediction():
    result = predictor.predict_industry("Zzyzx", "Xqlorp fnab worbled the trentization of blipspace.")
    assert result["predicted_industry"] in _known_taxonomy()
    assert 0.0 <= result["confidence"] <= 1.0


def test_malformed_input_types_are_coerced_not_crashed():
    result = predictor.predict_industry(None, None)  # type: ignore[arg-type]
    assert "predicted_industry" in result


def test_explanation_terms_are_serializable():
    import json

    result = predictor.predict_industry("Nova", "A telehealth platform connecting patients with clinicians.")
    json.dumps(result)  # raises if not serializable
