"""Similarity-based explanation for embedding-based classifiers.

Per-dimension feature importance (the technique `term_contributions.py` uses for the linear
TF-IDF model, where `contribution = tfidf_weight(term) * coefficient(term, class)` is exact and
interpretable) is **not meaningful** for dense sentence-transformer embeddings: each of the 384
dimensions is an opaque, entangled combination learned by the encoder's pretraining objective —
dimension 57 has no human-readable meaning the way a TF-IDF column ("healthcare") does, so
multiplying it by a classifier coefficient would produce a confident-looking but uninterpretable
number, not a real explanation.

The substitute used here is nearest-training-example retrieval: cosine similarity between the
query embedding and every cached training embedding, returning the top-k most similar training
examples (their text + true label) as "similarity-based evidence" — i.e. "this was classified the
way it was because it closely resembles these labeled examples," which is honest and inspectable
even though it does not decompose the decision term-by-term.
"""

from __future__ import annotations

import numpy as np

TOP_K_NEIGHBORS = 3


def nearest_training_examples(
    query_embedding: np.ndarray,
    train_embeddings: np.ndarray,
    train_texts: list[str],
    train_labels: list[str],
    k: int = TOP_K_NEIGHBORS,
) -> dict:
    """Return the top-k most cosine-similar training examples to `query_embedding`.

    Returns {"method": "nearest_training_example_cosine_similarity", "available": True,
    "neighbors": [{"text", "label", "similarity"}], "limitation": <str>}.
    """
    query = np.asarray(query_embedding, dtype=np.float64).reshape(1, -1)
    train = np.asarray(train_embeddings, dtype=np.float64)

    query_norm = np.linalg.norm(query, axis=1, keepdims=True)
    train_norm = np.linalg.norm(train, axis=1, keepdims=True)
    query_norm[query_norm == 0] = 1e-12
    train_norm[train_norm == 0] = 1e-12

    similarities = (train @ query.T).flatten() / (train_norm.flatten() * query_norm.flatten()[0])
    top_k_idx = np.argsort(similarities)[::-1][:k]

    neighbors = [
        {
            "text": train_texts[i],
            "label": train_labels[i],
            "similarity": float(similarities[i]),
        }
        for i in top_k_idx
    ]

    return {
        "method": "nearest_training_example_cosine_similarity",
        "available": True,
        "neighbors": neighbors,
        "limitation": (
            "Per-dimension feature importance is not meaningful for dense sentence-transformer "
            "embeddings (each dimension is an opaque, entangled combination from pretraining, "
            "unlike a TF-IDF column which corresponds to one human-readable term). Nearest-"
            "training-example similarity is reported instead as the substitute explanation "
            "method — it shows which labeled examples the prediction resembles, not which input "
            "features drove it."
        ),
    }
