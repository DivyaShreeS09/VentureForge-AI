"""A minimal sklearn-compatible wrapper around a frozen sentence-transformer + classifier.

Unlike the TF-IDF candidates (plain `sklearn.pipeline.Pipeline` objects), an embedding-based
candidate cannot be a normal `Pipeline` with a fitted vectorizer step, because the
`sentence-transformers` encoder is not an sklearn transformer and we deliberately do not want to
pickle the (large, torch-backed) encoder into the saved artifact — only the classifier on top of
it needs to be persisted; the encoder is re-loaded by name at inference time and embeddings are
recomputed (or read back from the same on-disk cache) as needed.

This class exposes the minimal surface the rest of the codebase (training script,
`backend/app/ml/predictor.py`) needs: `.fit(texts, y)`, `.predict(texts)`,
`.predict_proba(texts)` (if the wrapped classifier supports it), and a `.classes_` attribute.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ml.src.features.embedding_cache import get_or_compute_embeddings


class EmbeddingClassifier:
    """Wraps a frozen sentence-transformer encoder + a downstream sklearn classifier."""

    def __init__(self, classifier, model_name: str, cache_dir: Path):
        self.classifier = classifier
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)

    def _embed(self, texts: list[str], persist: bool) -> np.ndarray:
        return get_or_compute_embeddings(
            list(texts), self.model_name, self.cache_dir, persist=persist
        )

    def fit(self, texts: list[str], y, embeddings: np.ndarray | None = None) -> "EmbeddingClassifier":
        X = embeddings if embeddings is not None else self._embed(texts, persist=True)
        self.classifier.fit(X, y)
        return self

    def predict(self, texts: list[str], embeddings: np.ndarray | None = None):
        X = embeddings if embeddings is not None else self._embed(texts, persist=False)
        return self.classifier.predict(X)

    def predict_proba(self, texts: list[str], embeddings: np.ndarray | None = None):
        if not hasattr(self.classifier, "predict_proba"):
            raise AttributeError(f"{type(self.classifier).__name__} has no predict_proba")
        X = embeddings if embeddings is not None else self._embed(texts, persist=False)
        return self.classifier.predict_proba(X)

    @property
    def classes_(self):
        return self.classifier.classes_
