"""Tests for the nearest-training-example explanation substitute used when an embedding-based
model wins (ml/src/explainability/nearest_neighbors.py).
"""

from __future__ import annotations

import numpy as np

from ml.src.explainability.nearest_neighbors import nearest_training_examples


def test_returns_k_nearest_by_cosine_similarity():
    train_embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.9, 0.1],
            [-1.0, 0.0],
        ]
    )
    train_texts = ["close to query", "orthogonal", "also close", "opposite"]
    train_labels = ["fintech", "healthcare", "fintech", "consumer"]

    query = np.array([1.0, 0.0])
    result = nearest_training_examples(query, train_embeddings, train_texts, train_labels, k=2)

    assert result["available"] is True
    assert result["method"] == "nearest_training_example_cosine_similarity"
    returned_texts = [n["text"] for n in result["neighbors"]]
    assert returned_texts == ["close to query", "also close"]
    assert "limitation" in result and "not meaningful" in result["limitation"]


def test_similarity_scores_are_descending():
    train_embeddings = np.array([[1.0, 0.0], [0.7, 0.7], [0.0, 1.0]])
    train_texts = ["a", "b", "c"]
    train_labels = ["x", "y", "z"]
    query = np.array([1.0, 0.0])

    result = nearest_training_examples(query, train_embeddings, train_texts, train_labels, k=3)
    similarities = [n["similarity"] for n in result["neighbors"]]
    assert similarities == sorted(similarities, reverse=True)


def test_handles_zero_vector_without_crashing():
    train_embeddings = np.array([[0.0, 0.0], [1.0, 1.0]])
    result = nearest_training_examples(
        np.array([0.0, 0.0]), train_embeddings, ["zero", "nonzero"], ["a", "b"], k=1
    )
    assert result["available"] is True
    assert len(result["neighbors"]) == 1
