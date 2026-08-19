"""Smoke test: fit the same pipeline shape used in training on a tiny, inline fixture (distinct
from the bootstrap corpus used for the shipped artifact) to prove the pipeline code works,
without touching ml/models/ (the real artifact used by the running backend).
"""

from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline

from ml.src.evaluation.classification_metrics import evaluate_classification, expected_calibration_error
from ml.src.explainability.term_contributions import explain_prediction
from ml.src.features.build_features import build_text_feature

_FIXTURE_TEXTS = [
    "A cloud tool for tracking customer support tickets.",
    "Software that automates support ticket routing for teams.",
    "A dashboard for support agents to manage tickets.",
    "A helpdesk platform for customer support automation.",
    "An online store selling handmade candles.",
    "A shop for artisanal candles and home fragrance.",
    "A storefront selling scented candles direct to consumers.",
    "An e-commerce brand for handcrafted candle products.",
]
_FIXTURE_LABELS = ["saas", "saas", "saas", "saas", "ecommerce", "ecommerce", "ecommerce", "ecommerce"]


def test_tiny_pipeline_fits_and_predicts():
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(min_df=1)),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(_FIXTURE_TEXTS, _FIXTURE_LABELS)

    prediction = pipeline.predict(["A helpdesk app for support teams."])[0]
    assert prediction in {"saas", "ecommerce"}

    proba = pipeline.predict_proba(["A helpdesk app for support teams."])[0]
    assert abs(sum(proba) - 1.0) < 1e-6


def test_evaluate_classification_on_fixture():
    pipeline = Pipeline(
        [("tfidf", TfidfVectorizer(min_df=1)), ("clf", LogisticRegression(max_iter=1000))]
    )
    pipeline.fit(_FIXTURE_TEXTS, _FIXTURE_LABELS)
    preds = pipeline.predict(_FIXTURE_TEXTS)
    metrics = evaluate_classification(_FIXTURE_LABELS, list(preds), labels=["saas", "ecommerce"])
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert set(metrics["per_class"].keys()) == {"saas", "ecommerce"}


def test_explanation_returns_terms_present_in_input():
    pipeline = Pipeline(
        [("tfidf", TfidfVectorizer(min_df=1)), ("clf", LogisticRegression(max_iter=1000))]
    )
    pipeline.fit(_FIXTURE_TEXTS, _FIXTURE_LABELS)
    text = "A helpdesk app for support teams."
    prediction = pipeline.predict([text])[0]

    explanation = explain_prediction(pipeline, text, prediction)
    assert explanation["available"] is True
    for term_info in explanation["terms"]:
        assert term_info["term"] in text.lower() or " " in term_info["term"]


def test_build_text_feature_handles_missing_parts():
    assert build_text_feature("Name", "") == "Name"
    assert build_text_feature("", "Description") == "Description"
    assert build_text_feature("Name", "Description") == "Name. Description"


def test_explanation_unavailable_for_naive_bayes():
    """ComplementNB has no linear coefficients — explanation must be honestly unavailable,
    never approximated or faked."""
    pipeline = Pipeline([("tfidf", TfidfVectorizer(min_df=1)), ("clf", ComplementNB())])
    pipeline.fit(_FIXTURE_TEXTS, _FIXTURE_LABELS)
    text = "A helpdesk app for support teams."
    prediction = pipeline.predict([text])[0]

    explanation = explain_prediction(pipeline, text, prediction)
    assert explanation["available"] is False
    assert explanation["terms"] == []


def test_explanation_unavailable_when_pipeline_has_intermediate_transform():
    """A vectorizer -> SVD -> classifier pipeline changes feature space between the vectorizer
    and the classifier, so exact term attribution would be mathematically invalid — must be
    reported unavailable, never silently computed against the wrong coefficients."""
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(min_df=1)),
            ("svd", TruncatedSVD(n_components=2, random_state=0)),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(_FIXTURE_TEXTS, _FIXTURE_LABELS)
    text = "A helpdesk app for support teams."
    prediction = pipeline.predict([text])[0]

    explanation = explain_prediction(pipeline, text, prediction)
    assert explanation["available"] is False


def test_explanation_strips_feature_union_prefixes():
    """A word+char FeatureUnion vectorizer prefixes feature names ('word__x', 'char__y') —
    explanations shown to users must strip that internal detail but keep the term's kind."""
    word_tfidf = TfidfVectorizer(min_df=1, ngram_range=(1, 1))
    char_tfidf = TfidfVectorizer(min_df=1, analyzer="char_wb", ngram_range=(3, 4))
    pipeline = Pipeline(
        [
            ("tfidf", FeatureUnion([("word", word_tfidf), ("char", char_tfidf)])),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(_FIXTURE_TEXTS, _FIXTURE_LABELS)
    text = "A helpdesk app for support teams."
    prediction = pipeline.predict([text])[0]

    explanation = explain_prediction(pipeline, text, prediction)
    assert explanation["available"] is True
    for term_info in explanation["terms"]:
        assert "__" not in term_info["term"]
        assert term_info["kind"] in ("word", "char")


def test_expected_calibration_error_perfect_calibration():
    # Every prediction at 100% confidence is correct -> zero calibration gap.
    result = expected_calibration_error(correct=[True, True, True], confidences=[1.0, 1.0, 1.0])
    assert result["expected_calibration_error"] == 0.0


def test_expected_calibration_error_detects_overconfidence():
    # High confidence, but wrong half the time -> a large calibration gap.
    result = expected_calibration_error(correct=[True, False, True, False], confidences=[0.95, 0.95, 0.95, 0.95])
    assert result["expected_calibration_error"] > 0.4
