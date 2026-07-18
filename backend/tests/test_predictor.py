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


def test_primary_secondary_prediction_structure():
    """Additive fields from the V2 upgrade: primary/secondary industry + confidence, always
    present and internally consistent with predicted_industry/alternatives."""
    result = predictor.predict_industry(
        "PayFlux", "A payments platform that lets small businesses settle cross-border payments in seconds."
    )
    assert result["primary_industry"] == result["predicted_industry"]
    assert result["primary_confidence"] == result["confidence"]
    assert "secondary_industry" in result
    assert "secondary_confidence" in result
    if result["secondary_industry"] is not None:
        assert result["secondary_industry"] in _known_taxonomy()
        assert result["secondary_industry"] != result["primary_industry"]
        assert 0.0 <= result["secondary_confidence"] <= result["primary_confidence"]


def test_abstention_fields_present_and_consistent_with_threshold():
    """Additive abstention fields: is_low_confidence must agree with confidence vs. threshold."""
    result = predictor.predict_industry(
        "Nova", "A telehealth platform connecting patients with clinicians."
    )
    assert "is_low_confidence" in result
    assert "abstention_threshold" in result
    assert "abstention_reason" in result
    expected_low_confidence = result["confidence"] < result["abstention_threshold"]
    assert result["is_low_confidence"] == expected_low_confidence
    if result["is_low_confidence"]:
        assert result["abstention_reason"] is not None
    else:
        assert result["abstention_reason"] is None


def test_abstention_fires_on_low_confidence_input():
    """An out-of-vocabulary input should score low confidence and, at the recommended default
    threshold, be flagged for abstention (is_low_confidence=True)."""
    result = predictor.predict_industry("Zzyzx", "Xqlorp fnab worbled the trentization of blipspace.")
    if result["confidence"] < result["abstention_threshold"]:
        assert result["is_low_confidence"] is True
        assert result["abstention_reason"] is not None


def test_deterministic_inference_same_input_twice():
    """The same input must produce an identical prediction both times — no hidden randomness at
    inference time (the model is deterministic once trained)."""
    args = ("Nova", "A telehealth platform connecting patients with clinicians.")
    first = predictor.predict_industry(*args)
    second = predictor.predict_industry(*args)
    assert first["predicted_industry"] == second["predicted_industry"]
    assert first["confidence"] == second["confidence"]
    assert first["alternatives"] == second["alternatives"]
    assert first["primary_industry"] == second["primary_industry"]
    assert first["secondary_industry"] == second["secondary_industry"]


class TestArtifactValidation:
    """Artifact-loading validation must raise a clear, explicit error for a missing artifact
    directory or a corrupted/incompatible metadata.json — never silently mispredict.

    These tests build their own fake artifact directories and must run regardless of whether the
    real industry_classifier artifact happens to be trained on this machine, so the module-level
    `_skip_if_untrained` autouse fixture is overridden here as a no-op.
    """

    @pytest.fixture(autouse=True)
    def _skip_if_untrained(self):
        yield

    def _fresh_predictor_module(self, monkeypatch, model_dir):
        """Reimport-free way to exercise _load_artifact against a fake model_dir: monkeypatch
        _model_dir() and clear the lru_cache so the next call re-reads from disk."""
        monkeypatch.setattr(predictor, "_model_dir", lambda: model_dir)
        predictor._load_artifact.cache_clear()

    def test_missing_artifact_directory_raises_unavailable(self, tmp_path, monkeypatch):
        self._fresh_predictor_module(monkeypatch, tmp_path / "does_not_exist")
        with pytest.raises(predictor.IndustryClassifierUnavailable):
            predictor._load_artifact()
        predictor._load_artifact.cache_clear()

    def test_corrupted_metadata_json_raises_artifact_error(self, tmp_path, monkeypatch):
        model_dir = tmp_path / "v2"
        model_dir.mkdir()
        (model_dir / "model.joblib").write_bytes(b"not a real joblib file")
        (model_dir / "metadata.json").write_text("{not valid json")

        self._fresh_predictor_module(monkeypatch, model_dir)
        with pytest.raises(predictor.IndustryClassifierArtifactError):
            predictor._load_artifact()
        predictor._load_artifact.cache_clear()

    def test_metadata_missing_required_fields_raises_artifact_error(self, tmp_path, monkeypatch):
        import json

        model_dir = tmp_path / "v2"
        model_dir.mkdir()
        (model_dir / "model.joblib").write_bytes(b"not a real joblib file")
        (model_dir / "metadata.json").write_text(json.dumps({"some_other_field": True}))

        self._fresh_predictor_module(monkeypatch, model_dir)
        with pytest.raises(predictor.IndustryClassifierArtifactError):
            predictor._load_artifact()
        predictor._load_artifact.cache_clear()

    def test_metadata_inconsistent_label_schema_raises_artifact_error(self, tmp_path, monkeypatch):
        import json

        model_dir = tmp_path / "v2"
        model_dir.mkdir()
        (model_dir / "model.joblib").write_bytes(b"not a real joblib file")
        (model_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "version": "v2",
                    "selected_pipeline": "tfidf_logreg",
                    "labels": ["a", "b", "c"],
                    "label_schema": {"n_classes": 5, "classes": ["a", "b", "c"]},
                }
            )
        )

        self._fresh_predictor_module(monkeypatch, model_dir)
        with pytest.raises(predictor.IndustryClassifierArtifactError):
            predictor._load_artifact()
        predictor._load_artifact.cache_clear()
