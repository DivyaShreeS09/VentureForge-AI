"""Master Startup Corpus Expansion Sprint, Phase 3/4: fit and save the venture-retrieval embedding
index that backend/app/ml/venture_retrieval.py loads at request time.

Same embedding model, same brute-force cosine-similarity design as the existing v1 artifact (see
that module's own docstring for why brute-force is still correct at this corpus scale) -- this
script only re-embeds a richer, larger, better-audited corpus (ml/src/preprocessing.
build_retrieval_corpus) and preserves each record's newly-carried metadata (country, industry,
subindustry, funding_stage, team_size, founding_year, source) instead of the v1 schema's bare
name/description/industry.

Run: `python -m ml.src.training.build_venture_retrieval_index`
Writes ml/models/venture_retrieval/v2/{corpus_embeddings.npy,corpus_metadata.json}. The existing
v1 artifact is left untouched -- app.ml.venture_retrieval keeps loading v1 by default until Phase 5's
evaluation is reviewed and a version switch is made deliberately (see VENTURE_RETRIEVAL_VERSION in
that module).
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_PATH = REPO_ROOT / "ml" / "data" / "processed" / "retrieval_corpus_v2.csv"
OUTPUT_DIR = REPO_ROOT / "ml" / "models" / "venture_retrieval" / "v2"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def _clean(value):
    """NaN/None -> None so json.dumps never emits an illegal `NaN` token."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def build_index() -> None:
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"{CORPUS_PATH} not found -- run ml.src.preprocessing.build_retrieval_corpus first.")

    df = pd.read_csv(CORPUS_PATH)
    logger.info("Loaded %d rows from %s", len(df), CORPUS_PATH)

    import torch
    from sentence_transformers import SentenceTransformer

    # This memory-constrained development machine (~8GB total, often <2GB free -- the same
    # constraint already documented in ml/DATASETS.md for the classifier/success-predictor
    # training runs) segfaulted at the default thread count/batch size on first attempt.
    # Single-threaded + a small batch size is the same fix already applied elsewhere in this
    # project for the identical class of crash.
    torch.set_num_threads(1)
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    descriptions = df["description"].astype(str).tolist()
    logger.info("Embedding %d descriptions with %s ...", len(descriptions), EMBEDDING_MODEL_NAME)
    embeddings = model.encode(descriptions, show_progress_bar=True, convert_to_numpy=True, batch_size=8)
    logger.info("Embeddings shape: %s", embeddings.shape)

    records = []
    for _, row in df.iterrows():
        records.append({
            "name": _clean(row["name"]),
            "description": _clean(row["description"]),
            "industry": _clean(row["industry"]),
            "subindustry": _clean(row.get("subindustry")),
            "country": _clean(row.get("country")),
            "funding_stage": _clean(row.get("funding_stage")),
            "team_size": _clean(row.get("team_size")),
            "founding_year": _clean(row.get("founding_year")),
            "source": _clean(row.get("source")),
        })

    corpus_bytes = CORPUS_PATH.read_bytes()
    fingerprint = hashlib.sha256(corpus_bytes).hexdigest()

    metadata = {
        "venture_retrieval_version": "v2",
        "embedding_model_name": EMBEDDING_MODEL_NAME,
        "embedding_dim": int(embeddings.shape[1]),
        "corpus_size": len(records),
        "source_dataset": "ml/data/processed/retrieval_corpus_v2.csv (real company name+description+industry+country+funding_stage+team_size+founding_year, merged from 4 real, licensed sources -- see ml.src.preprocessing.build_retrieval_corpus module docstring for full provenance/licensing per source)",
        "sources": sorted(df["source"].dropna().unique().tolist()),
        "provenance_note": (
            "Every record here is a REAL company from a real, licensed public dataset (YC public "
            "directory exports, 2005-2026, plus one independent pre-2015 startup directory export). "
            "This corpus is NOT a live competitor database -- these companies may no longer operate, "
            "may have pivoted, and are not verified as any given founder's actual competitors. "
            "Retrieval surfaces the closest HISTORICAL reference point by description similarity "
            "only; downstream consumers must always frame results as historical pattern reference, "
            "never as verified live competitor facts."
        ),
        "dataset_fingerprint_sha256": fingerprint,
        "records": records,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUTPUT_DIR / "corpus_embeddings.npy", embeddings.astype(np.float32))
    (OUTPUT_DIR / "corpus_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Wrote v2 retrieval index (%d records) to %s", len(records), OUTPUT_DIR)


if __name__ == "__main__":
    build_index()
