"""Local explanations for the industry classifier.

The model is a TF-IDF + linear classifier pipeline. For linear models, a term's contribution to a
specific prediction is exactly `tfidf_weight(term) * coefficient(term, predicted_class)` — no
approximation and no SHAP is involved, since SHAP is not appropriate to claim for a plain linear
model when the exact contribution is already computable in closed form. Only terms that actually
appear in the input text are reported (no generic global "top keywords" list).
"""

from __future__ import annotations

from sklearn.pipeline import Pipeline

TOP_N_TERMS = 8


def explain_prediction(pipeline: Pipeline, text: str, predicted_label: str) -> dict:
    """Return the terms in `text` that most influenced the prediction of `predicted_label`.

    Returns {"method": ..., "terms": [{"term", "contribution", "direction"}], "available": bool}.
    If the fitted classifier does not expose linear coefficients (e.g. Naive Bayes), explanation
    is honestly reported as unavailable rather than faked.
    """
    vectorizer = pipeline.named_steps.get("tfidf")
    clf = pipeline.named_steps.get("clf")
    if vectorizer is None or clf is None:
        return {"method": "unavailable", "available": False, "terms": []}

    # Exact term attribution requires the classifier's coefficients to live in the same feature
    # space the vectorizer produces. A pipeline with an intermediate dimensionality-changing step
    # (e.g. tfidf -> SVD -> clf) breaks that assumption — multiplying raw vectorizer weights by
    # coefficients fit on a reduced space would produce confident-looking but meaningless numbers.
    # Only pipelines with exactly [vectorizer, clf] (any TF-IDF/FeatureUnion vectorizer step
    # immediately followed by the classifier) are supported; anything else is honestly unavailable.
    step_names = [name for name, _ in pipeline.steps]
    if step_names != ["tfidf", "clf"]:
        return {
            "method": "unavailable",
            "available": False,
            "terms": [],
            "note": (
                f"Pipeline has intermediate steps ({step_names}) between the vectorizer and "
                "classifier — exact term attribution is not valid in this feature space."
            ),
        }

    classes = list(getattr(clf, "classes_", []))
    if predicted_label not in classes:
        return {"method": "unavailable", "available": False, "terms": []}
    class_idx = classes.index(predicted_label)

    coef = _extract_coefficients(clf, class_idx, n_classes=len(classes))
    if coef is None:
        return {
            "method": "unavailable",
            "available": False,
            "terms": [],
            "note": f"'{type(clf).__name__}' does not expose linear coefficients for exact term attribution.",
        }

    tfidf_vector = vectorizer.transform([text])
    feature_names = vectorizer.get_feature_names_out()
    nonzero_indices = tfidf_vector.nonzero()[1]

    contributions = []
    for idx in nonzero_indices:
        tfidf_weight = tfidf_vector[0, idx]
        contribution = float(tfidf_weight * coef[idx])
        raw_name = feature_names[idx]
        # A FeatureUnion (word+char vectorizer) prefixes feature names with the sub-transformer's
        # name (e.g. "word__health", "char__healt") — strip that internal detail for display, but
        # keep which kind it was: a char n-gram fragment ("healt") is a real, faithful contributor
        # to the model's decision, but it is not a word, and showing it unlabeled next to real
        # words would misrepresent it as one.
        kind = "word"
        display_term = raw_name
        if "__" in raw_name:
            prefix, _, rest = raw_name.partition("__")
            if prefix in ("word", "char"):
                kind = prefix
                display_term = rest
        contributions.append(
            {
                "term": display_term,
                "kind": kind,
                "contribution": contribution,
                "direction": "supports" if contribution > 0 else "opposes",
            }
        )

    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return {
        "method": "linear_coefficient_x_tfidf",
        "available": True,
        "terms": contributions[:TOP_N_TERMS],
    }


def _extract_coefficients(clf, class_idx: int, n_classes: int):
    if hasattr(clf, "coef_"):
        coef = clf.coef_
        # Binary logistic regression stores a single row; multiclass stores one row per class.
        if coef.shape[0] == 1 and n_classes == 2:
            return coef[0] if class_idx == 1 else -coef[0]
        return coef[class_idx]
    return None
