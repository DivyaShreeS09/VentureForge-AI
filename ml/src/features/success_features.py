"""Feature schema and preprocessing pipeline for the startup success-prediction classifier.

Unlike the industry classifier (free text -> TF-IDF), this task's inputs are structured tabular
features already produced by ml/src/preprocessing/success_data.py. This module is the single
source of truth for which columns are used and how they are transformed, so training
(ml/src/training/train_success_classifier.py) and serving (backend/app/ml/success_predictor.py)
apply an identical transform.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

BASE_NUMERIC_FEATURES = [
    "funding_total_usd",
    "funding_rounds",
    "company_age_years",
    "funding_span_years",
    "category_count",
]
# Engineered ratio features (see engineer_features below) — both showed a real, non-trivial
# correlation with the target on the training data (funding_per_round: +0.048, funding_velocity:
# -0.086) when checked before being added here, not assumed to help.
ENGINEERED_NUMERIC_FEATURES = ["funding_per_round", "funding_velocity"]

# v2 additions: date-derived features computed in ml/src/preprocessing/prepare_success_dataset.py
# (time_to_first_funding_years, funding_recency_years — both derived only from founding/funding
# dates, never from the outcome, so neither leaks the target) plus one interaction feature
# computed here (funding_per_category).
DATE_DERIVED_NUMERIC_FEATURES = ["time_to_first_funding_years", "funding_recency_years"]
# Interaction feature: funding_total_usd / (category_count + 1) — "capital concentration per
# listed category". Chosen over a raw product (funding_total_usd * category_count) because the
# product mostly just re-scales funding_total_usd by a small integer (1-10 typically) and is
# highly collinear with funding_total_usd itself (corr aside, it barely changes rank order); the
# per-category ratio instead asks a scale-independent question — is this company's capital
# concentrated in a narrow positioning (few categories) or spread across a broad one (many
# categories)? — which is not already captured by any existing feature.
INTERACTION_NUMERIC_FEATURES = ["funding_per_category"]
ENGINEERED_NUMERIC_FEATURES = ENGINEERED_NUMERIC_FEATURES + INTERACTION_NUMERIC_FEATURES

NUMERIC_FEATURES = BASE_NUMERIC_FEATURES + DATE_DERIVED_NUMERIC_FEATURES + ENGINEERED_NUMERIC_FEATURES
CATEGORICAL_FEATURES = ["primary_category", "country_code"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Skewed monetary/rate features that get log1p-compressed before scaling (see _log1p below).
SKEWED_FEATURES = ["funding_total_usd", "funding_per_round", "funding_velocity", "funding_per_category"]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive ratio features from the base columns. Must be called identically at training
    (train_success_classifier.py) and serving time (success_predictor.py) — this is the single
    place both paths compute them, so they can never drift out of sync.

    - funding_per_round: average capital raised per funding round — a scale-independent signal
      distinct from total funding alone.
    - funding_velocity: funding rounds per year since founding — a pace-of-fundraising signal.
      Left NaN (imputed downstream like any other numeric feature) when company_age_years is
      missing or non-positive, rather than dividing by an invalid denominator.
    """
    df = df.copy()
    df["funding_per_round"] = df["funding_total_usd"] / df["funding_rounds"].replace(0, np.nan)
    age_safe = df["company_age_years"].where(df["company_age_years"] > 0)
    df["funding_velocity"] = df["funding_rounds"] / age_safe
    # funding_per_category: see INTERACTION_NUMERIC_FEATURES docstring above for why this ratio
    # (not a raw product) was chosen. category_count is always >= 0 in the prepared dataset
    # (0 when category_list was entirely absent); +1 avoids dividing by zero without discarding
    # those rows or fabricating a category.
    category_count_safe = df["category_count"].astype("float64").fillna(0.0) + 1
    df["funding_per_category"] = df["funding_total_usd"] / category_count_safe
    return df


def _log1p(x):
    # Heavily right-skewed monetary/rate columns; log1p compresses the range without needing to
    # drop or clip legitimate outliers (see ml/DATASETS.md).
    return np.log1p(np.clip(x, a_min=0, a_max=None))


def build_preprocessor() -> ColumnTransformer:
    """Column-wise preprocessing: median-impute (+log1p for skewed columns) + scale numeric,
    one-hot categorical."""
    numeric_pipeline = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )
    skewed_pipeline = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("log1p", FunctionTransformer(_log1p, feature_names_out="one-to-one")),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    other_numeric = [f for f in NUMERIC_FEATURES if f not in SKEWED_FEATURES]

    return ColumnTransformer(
        transformers=[
            ("skewed", skewed_pipeline, SKEWED_FEATURES),
            ("numeric", numeric_pipeline, other_numeric),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )


class TrainFoldTargetEncoder(BaseEstimator, TransformerMixin):
    """Smoothed mean target-encoding for categorical columns, computed ONLY from whatever data is
    passed to `fit(X, y)`.

    Why this is leakage-safe: this transformer is only ever used as a step inside a scikit-learn
    `Pipeline`. `cross_val_score`/`cross_val_predict`/`RandomizedSearchCV`/the final `.fit()` all
    clone the *entire* pipeline and call `.fit()` on the training portion of each split only,
    then call `.transform()` (never `.fit()`) on the held-out/validation/test portion. Because
    `fit()` here never looks outside the data it is given, the encoding for any fold is always
    derived exclusively from that fold's training rows — never from validation/test rows, and
    never from the full dataset before splitting. This is the safe alternative to computing a
    category -> success-rate lookup once on the whole dataset (which would leak each row's own
    outcome, and its fold-mates' outcomes, into its own encoded feature).

    Smoothing (`smoothing` prior-strength pseudo-count) pulls rare categories' encoded value
    toward the global training-fold mean rather than trusting a category seen only 1-2 times.
    """

    def __init__(self, columns: list[str] | None = None, smoothing: float = 20.0):
        self.columns = columns
        self.smoothing = smoothing

    def fit(self, X, y):
        cols = self.columns or CATEGORICAL_FEATURES
        X = X[cols] if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=cols)
        y_arr = np.asarray(y, dtype=float)
        self.global_mean_ = float(y_arr.mean())
        self.mappings_: dict[str, dict] = {}
        for col in cols:
            stats = pd.DataFrame({"cat": X[col].astype(str).values, "y": y_arr}).groupby("cat")["y"].agg(
                ["mean", "count"]
            )
            smoothed = (stats["count"] * stats["mean"] + self.smoothing * self.global_mean_) / (
                stats["count"] + self.smoothing
            )
            self.mappings_[col] = smoothed.to_dict()
        self.columns_ = cols
        return self

    def transform(self, X):
        cols = self.columns_
        X = X[cols] if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=cols)
        out = np.zeros((len(X), len(cols)), dtype=float)
        for i, col in enumerate(cols):
            mapping = self.mappings_[col]
            out[:, i] = X[col].astype(str).map(mapping).fillna(self.global_mean_).to_numpy()
        return out

    def get_feature_names_out(self, input_features=None):
        return np.array([f"{c}_target_enc" for c in self.columns_])


def build_preprocessor_with_target_encoding() -> ColumnTransformer:
    """Comparison-only variant of `build_preprocessor()` that replaces one-hot categorical
    encoding with `TrainFoldTargetEncoder` (see class docstring for why it is leakage-safe).

    NOT used by default in the production pipeline — kept as a candidate evaluated honestly
    against the one-hot version in `train_success_classifier.py`'s model comparison; only adopted
    if it demonstrably improves cross-validated ROC-AUC.
    """
    numeric_pipeline = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )
    skewed_pipeline = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("log1p", FunctionTransformer(_log1p, feature_names_out="one-to-one")),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("target_encode", TrainFoldTargetEncoder(columns=CATEGORICAL_FEATURES)),
            ("scale", StandardScaler()),
        ]
    )

    other_numeric = [f for f in NUMERIC_FEATURES if f not in SKEWED_FEATURES]

    return ColumnTransformer(
        transformers=[
            ("skewed", skewed_pipeline, SKEWED_FEATURES),
            ("numeric", numeric_pipeline, other_numeric),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )
