"""Tests for the embedding disk cache (ml/src/features/embedding_cache.py).

A fake `SentenceTransformer` is injected in place of the real (heavy, network/model-loading)
one so these tests are fast and deterministic — they test the caching mechanics (hit/miss/
invalidation), not sentence-transformers itself.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from ml.src.features import embedding_cache


class _FakeSentenceTransformer:
    """Deterministic stand-in: embeds each text as a fixed-length vector derived from its hash,
    and counts how many times `encode` was actually called (to prove cache hits skip it)."""

    call_count = 0

    def __init__(self, model_name: str):
        self.model_name = model_name

    def encode(self, texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True):
        _FakeSentenceTransformer.call_count += 1
        rng = np.random.RandomState(0)
        return np.array([rng.rand(8) + (hash(t) % 1000) / 1000.0 for t in texts])


@pytest.fixture(autouse=True)
def _reset_call_count():
    _FakeSentenceTransformer.call_count = 0
    yield


@pytest.fixture()
def fake_sentence_transformers(monkeypatch):
    import sentence_transformers

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", _FakeSentenceTransformer)
    return _FakeSentenceTransformer


def test_same_input_returns_same_cached_output(tmp_path, fake_sentence_transformers):
    texts = ["A payments platform for small businesses.", "A telehealth app for patients."]
    first = embedding_cache.get_or_compute_embeddings(texts, "fake-model", tmp_path)
    assert fake_sentence_transformers.call_count == 1

    second = embedding_cache.get_or_compute_embeddings(texts, "fake-model", tmp_path)
    # Cache hit: no second call to the (fake) encoder, and identical output.
    assert fake_sentence_transformers.call_count == 1
    np.testing.assert_array_equal(first, second)


def test_cache_invalidates_on_different_text(tmp_path, fake_sentence_transformers):
    embedding_cache.get_or_compute_embeddings(["text a"], "fake-model", tmp_path)
    assert fake_sentence_transformers.call_count == 1

    embedding_cache.get_or_compute_embeddings(["text b"], "fake-model", tmp_path)
    # Different text list -> different hash -> cache miss -> encoder called again.
    assert fake_sentence_transformers.call_count == 2


def test_cache_invalidates_on_different_model_name(tmp_path, fake_sentence_transformers):
    texts = ["the same text"]
    embedding_cache.get_or_compute_embeddings(texts, "model-a", tmp_path)
    assert fake_sentence_transformers.call_count == 1

    embedding_cache.get_or_compute_embeddings(texts, "model-b", tmp_path)
    # Same text, different model name -> different hash -> cache miss.
    assert fake_sentence_transformers.call_count == 2


def test_cache_writes_npy_and_json_sidecar(tmp_path, fake_sentence_transformers):
    texts = ["one", "two", "three"]
    embedding_cache.get_or_compute_embeddings(texts, "fake-model", tmp_path, persist=True)

    npy_files = list(tmp_path.glob("*.npy"))
    json_files = list(tmp_path.glob("*.json"))
    assert len(npy_files) == 1
    assert len(json_files) == 1

    sidecar = json.loads(json_files[0].read_text())
    assert sidecar["model_name"] == "fake-model"
    assert sidecar["text_count"] == 3


def test_persist_false_does_not_write_cache_files(tmp_path, fake_sentence_transformers):
    embedding_cache.get_or_compute_embeddings(["ephemeral text"], "fake-model", tmp_path, persist=False)
    assert list(tmp_path.glob("*.npy")) == []
    assert list(tmp_path.glob("*.json")) == []


def test_corrupted_sidecar_triggers_recompute_not_crash(tmp_path, fake_sentence_transformers):
    texts = ["some text"]
    embedding_cache.get_or_compute_embeddings(texts, "fake-model", tmp_path)
    assert fake_sentence_transformers.call_count == 1

    # Corrupt the sidecar JSON on disk.
    for json_path in tmp_path.glob("*.json"):
        json_path.write_text("{not valid json")

    # Must recompute gracefully rather than raising or trusting the corrupted sidecar.
    result = embedding_cache.get_or_compute_embeddings(texts, "fake-model", tmp_path)
    assert fake_sentence_transformers.call_count == 2
    assert result.shape[0] == 1
