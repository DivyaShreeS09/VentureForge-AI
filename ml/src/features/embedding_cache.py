"""Disk cache for sentence-transformer embeddings.

Computing sentence embeddings for ~4.4k training documents is comparatively expensive relative to
fitting a TF-IDF+LogReg pipeline, and this repo's training script may be re-run many times during
model comparison/debugging. Caching the embeddings keyed by a hash of the exact text list + model
name means re-running training does not silently recompute embeddings (slow) or silently reuse a
stale cache for a different text set (incorrect) — the sidecar JSON records enough to detect either
mismatch on load.

No label information is used anywhere in this module — embeddings are a fixed function of `texts`
and `model_name` alone, computed once. Reusing the same embedding matrix across every CV fold is
therefore NOT leakage: leakage would require the *test/validation fold's labels* to influence the
representation used to predict them, and nothing here reads a label. This is the standard practice
for frozen (non-fine-tuned) embeddings, exactly analogous to reusing a pretrained word2vec/GloVe
table across folds.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _hash_texts(texts: list[str], model_name: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(model_name.encode("utf-8"))
    hasher.update(b"\x00")
    for text in texts:
        hasher.update(text.encode("utf-8"))
        hasher.update(b"\x00")
    return hasher.hexdigest()


def get_or_compute_embeddings(
    texts: list[str],
    model_name: str,
    cache_dir: Path,
    batch_size: int = 32,
    persist: bool = True,
) -> np.ndarray:
    """Return an (n_texts, dim) float32 embedding matrix for `texts` using `model_name`.

    Looks up a cache keyed by sha256(model_name + exact text list) under `cache_dir`. On a hit,
    loads the `.npy` directly (and sanity-checks the `.json` sidecar's recorded text count and
    hash against the request before trusting it). On a miss, computes fresh embeddings via
    `sentence_transformers.SentenceTransformer` and (if `persist=True`) writes both files.

    `persist=False` is intended for single-item inference-time calls, where writing a new cache
    file per unique prediction text would accumulate unboundedly on disk for no reuse benefit.
    """
    digest = _hash_texts(texts, model_name)
    cache_dir = Path(cache_dir)
    npy_path = cache_dir / f"{digest}.npy"
    json_path = cache_dir / f"{digest}.json"

    if npy_path.exists() and json_path.exists():
        try:
            sidecar = json.loads(json_path.read_text())
            if sidecar.get("model_name") == model_name and sidecar.get("text_count") == len(texts) and sidecar.get("hash") == digest:
                embeddings = np.load(npy_path)
                if embeddings.shape[0] == len(texts):
                    logger.info(
                        "Embedding cache HIT (%s, %d texts, hash=%s)", model_name, len(texts), digest[:12]
                    )
                    return embeddings
                logger.warning(
                    "Embedding cache row-count mismatch for hash=%s — recomputing.", digest[:12]
                )
            else:
                logger.warning("Embedding cache sidecar mismatch for hash=%s — recomputing.", digest[:12])
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Embedding cache read failed for hash=%s (%s) — recomputing.", digest[:12], exc)

    logger.info("Embedding cache MISS (%s, %d texts, hash=%s) — computing.", model_name, len(texts), digest[:12])
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype(np.float32)

    if persist:
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(npy_path, embeddings)
        json_path.write_text(
            json.dumps(
                {
                    "model_name": model_name,
                    "text_count": len(texts),
                    "hash": digest,
                    "dim": int(embeddings.shape[1]),
                }
            )
        )
        logger.info("Wrote embedding cache: %s (%s)", npy_path, embeddings.shape)

    return embeddings
