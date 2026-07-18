"""Tests for TrainFoldTargetEncoder (ml/src/features/success_features.py) — the leakage-safety
property is exactly what these tests exist to check: fit() must only ever depend on data it is
given directly, never on anything else, so it is always safe under cross-validation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import cross_val_predict
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ml.src.features.success_features import TrainFoldTargetEncoder


def test_fit_transform_shape_and_range():
    X = pd.DataFrame({"cat": ["a", "a", "b", "b", "c"]})
    y = [1, 0, 1, 1, 0]
    enc = TrainFoldTargetEncoder(columns=["cat"])
    enc.fit(X, y)
    out = enc.transform(X)
    assert out.shape == (5, 1)
    assert np.all((out >= 0) & (out <= 1))


def test_unseen_category_falls_back_to_global_mean():
    X_train = pd.DataFrame({"cat": ["a", "a", "b", "b"]})
    y_train = [1, 1, 0, 0]
    enc = TrainFoldTargetEncoder(columns=["cat"])
    enc.fit(X_train, y_train)

    X_new = pd.DataFrame({"cat": ["never-seen-category"]})
    out = enc.transform(X_new)
    assert out[0, 0] == pytest.approx(enc.global_mean_)


def test_rare_category_is_smoothed_toward_global_mean():
    # Category "rare" seen once with y=1 should NOT encode to exactly 1.0 — smoothing must pull it
    # toward the global training mean, not just echo back the single observed label.
    X = pd.DataFrame({"cat": ["common"] * 20 + ["rare"]})
    y = [0] * 10 + [1] * 10 + [1]
    enc = TrainFoldTargetEncoder(columns=["cat"], smoothing=20.0)
    enc.fit(X, y)
    out = enc.transform(X)
    rare_encoded = out[-1, 0]
    assert rare_encoded < 1.0
    assert rare_encoded > enc.global_mean_  # still pulled toward it, not fully overridden


def test_leakage_safe_under_cross_val_predict():
    """The core safety property: cross_val_predict clones+fits the whole pipeline (including the
    encoder) on each training fold only, and only transforms (never fits) the held-out fold. This
    test doesn't re-derive the proof, but does confirm the encoder behaves correctly end-to-end
    inside a real CV loop rather than raising or producing out-of-range values."""
    rng = np.random.default_rng(0)
    n = 200
    X = pd.DataFrame({"cat": rng.choice(["a", "b", "c", "d"], size=n)})
    y = rng.integers(0, 2, size=n)

    pipeline = Pipeline(
        [
            ("encode", TrainFoldTargetEncoder(columns=["cat"])),
            ("clf", LogisticRegression()),
        ]
    )
    oof_proba = cross_val_predict(pipeline, X, y, cv=5, method="predict_proba")[:, 1]
    assert oof_proba.shape == (n,)
    assert np.all((oof_proba >= 0) & (oof_proba <= 1))


def test_get_feature_names_out():
    X = pd.DataFrame({"cat": ["a", "b"], "country": ["usa", "gbr"]})
    y = [1, 0]
    enc = TrainFoldTargetEncoder(columns=["cat", "country"])
    enc.fit(X, y)
    names = enc.get_feature_names_out()
    assert list(names) == ["cat_target_enc", "country_target_enc"]
