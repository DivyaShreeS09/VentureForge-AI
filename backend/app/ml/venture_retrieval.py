"""Venture Retrieval (ML Differentiator Sprint; corpus rebuilt in the Master Startup Corpus
Expansion Sprint): semantic nearest-neighbor search over a real, merged, licensed corpus of 7,668
company name+description+industry(+country/funding_stage/founding_year where available) rows —
see ml.src.preprocessing.build_retrieval_corpus for the 4-source merge/licensing/dedup pipeline and
ml.src.evaluation.evaluate_retrieval for the measured v1->v2 quality comparison that justified the
switch (VENTURE_RETRIEVAL_VERSION below).

Architecture, and why: this repo already computes and caches sentence-transformer embeddings
(all-MiniLM-L6-v2, frozen, not fine-tuned) for the original, smaller corpus as part of comparing
embedding candidates against TF-IDF for the industry classifier (see
ml/src/features/embedding_cache.py and ml.src.training.train_industry_classifier); this module's v2
corpus reuses that same embedding model and the same cosine-similarity nearest-neighbor logic
already implemented for classifier explainability (ml/src/explainability/nearest_neighbors.py) — no
new embedding model, no new training, no fabricated data. At this corpus scale (7,668 rows x 384
dims ~= 11.8MB), brute-force cosine similarity via a single numpy matrix multiply is exact and takes
under 1ms per query — there is no scientific justification for an approximate nearest-neighbor
index (FAISS/HNSW) at this scale; that tradeoff only pays off at a much larger corpus size.

CRITICAL ANTI-FABRICATION FRAMING: every retrieved "venture" is a REAL company name+description
from real, licensed public datasets (YC public directory exports, 2005-2026, plus one independent
pre-2015 startup directory export — see build_retrieval_corpus for full per-source provenance). It
is NOT a live competitor database — these companies may no longer operate, may have pivoted, and
are not verified as this founder's actual competitors. Every caller MUST surface
`provenance_disclaimer` alongside any use of these results; they are historical pattern-reference
points, never a claim about this venture's real competitive landscape.

Off by default (see app.core.config.Settings.enable_venture_retrieval) because loading the
sentence-transformer model takes ~20-40s on first use — this must never happen as a side effect of
running the test suite or an ordinary request before the corpus/model are confirmed available.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.ml.venture_space_analytics import analyze_venture_space, get_analytics_data

logger = logging.getLogger(__name__)

# Master Startup Corpus Expansion Sprint: promoted v1 -> v2 after ml.src.evaluation.evaluate_retrieval
# showed a real, measured improvement on EVERY precision/ranking metric (leave-one-out
# same-industry agreement, the only non-fabricated proxy available) -- not promoted merely because
# the corpus got bigger. v1's on-disk artifact is left untouched for rollback.
#   precision@1  0.7036 -> 0.7373   |  precision@5  0.6942 -> 0.7107
#   MRR          0.8010 -> 0.8243   |  NDCG@5       0.8326 -> 0.8506
#   coverage%    93.81  -> 94.98    |  failure rate% 6.19  -> 5.02
# recall@5 fell slightly (0.0048 -> 0.0031) -- an expected, disclosed artifact of the corpus
# growing ~78% larger (the same top-5 window now captures a smaller fraction of a bigger
# same-industry pool), not a real quality regression given every other metric improved.
VENTURE_RETRIEVAL_VERSION = "v2"
# Final ML Excellence Sprint, Phase 4 (Version Cleanup): the ONE production-facing label. Internal
# artifact folder versioning (v1/v2 above) is engineering rollback history, never surfaced past
# this module -- this product has never shipped, so there is nothing for "v2" to be a bump FROM
# from a founder's perspective.
PUBLIC_VENTURE_RETRIEVAL_VERSION = "v1"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 5

# Master Startup Corpus Expansion Sprint, Phase 6 — a small, fixed additive boost (not a learned
# weight, not a new model) applied to same-known-industry candidates during ranking. Kept small
# deliberately: it should only break near-ties in favor of industry-coherent neighbors, never
# override a genuinely much more semantically similar cross-industry match. See
# ml.src.evaluation.evaluate_retrieval for the measured effect of this boost.
_INDUSTRY_RERANK_BOOST = 0.05

# A small, generic stopword list for the deterministic "why similar" shared-vocabulary explanation
# below — not used for anything else (no fabricated linguistic claims, just filtering noise words).
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "our", "are", "was", "were",
    "have", "has", "will", "would", "could", "into", "their", "them", "who", "what", "how", "when",
    "where", "which", "using", "used", "based", "than", "then", "also", "more", "most", "some",
    "such", "these", "those", "about", "over", "each", "other", "being", "help", "helps", "helping",
}


class VentureRetrievalIndex:
    """Holds the fitted (pre-embedded) corpus and the embedding model needed to embed a new query
    at request time. Never mutated after construction."""

    def __init__(self, embeddings: np.ndarray, records: list[dict], model) -> None:
        self._embeddings = embeddings.astype(np.float64)
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-12
        self._norms = norms
        self._records = records
        self._model = model

    def compute_similarities(self, description: str) -> tuple[np.ndarray, np.ndarray]:
        """Embed `description` once and return (similarities against every corpus item (n,),
        unit-normalized query vector (dim,)) — shared by `retrieve()` and venture-space analytics
        so a query is never embedded twice."""
        query = self._model.encode([description], show_progress_bar=False, convert_to_numpy=True)
        query = np.asarray(query, dtype=np.float64)
        query_norm = np.linalg.norm(query, axis=1, keepdims=True)
        query_norm[query_norm == 0] = 1e-12

        similarities = (self._embeddings @ query.T).flatten() / (self._norms.flatten() * query_norm.flatten()[0])
        query_normalized = (query / query_norm).flatten()
        return similarities, query_normalized

    def retrieve_from_similarities(
        self, description: str, similarities: np.ndarray, k: int = DEFAULT_TOP_K,
        known_industry: str | None = None,
    ) -> list[dict]:
        # Master Startup Corpus Expansion Sprint, Phase 6 — industry-aware reranking. Reuses this
        # pipeline's OWN already-computed industry prediction (venture_positioning/model_category,
        # produced by the existing, frozen industry classifier — no new classifier, no new model)
        # as a small additive similarity boost for same-industry candidates before taking top-k.
        # This changes WHICH real records get selected, never a record's own real similarity value
        # in what's reported back (the reported `similarity` field below is always the true,
        # unboosted cosine similarity — the boost is search-time ranking only, disclosed via
        # `industry_reranking_applied`).
        if known_industry:
            boost = np.array([
                _INDUSTRY_RERANK_BOOST if r.get("industry") == known_industry else 0.0
                for r in self._records
            ])
            ranking_scores = similarities + boost
        else:
            ranking_scores = similarities

        top_idx = np.argsort(-ranking_scores)[:k]
        results = []
        for i in top_idx:
            record = self._records[i]
            results.append({
                "name": record["name"],
                "description": record["description"],
                "industry": record["industry"],
                "similarity": float(similarities[i]),
                "why_similar": _why_similar(description, record["description"]),
                # Master Startup Corpus Expansion Sprint, Phase 4 — richer per-record metadata,
                # present only for corpus versions that carry it (None for older/v1-style records,
                # never fabricated for a record whose source didn't report it).
                "country": record.get("country"),
                "funding_stage": record.get("funding_stage"),
                "founding_year": record.get("founding_year"),
                "source_dataset": record.get("source"),
            })
        return results

    def retrieve(
        self, description: str, k: int = DEFAULT_TOP_K, known_industry: str | None = None,
    ) -> list[dict]:
        similarities, _ = self.compute_similarities(description)
        return self.retrieve_from_similarities(description, similarities, k=k, known_industry=known_industry)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 3 and w not in _STOPWORDS}


def _why_similar(query_description: str, neighbor_description: str) -> str:
    """Deterministic, non-fabricated explanation: the significant words the query and the
    retrieved neighbor actually share. Dense embedding dimensions are not individually
    interpretable (see ml/src/explainability/nearest_neighbors.py's docstring for why) — shared
    vocabulary is the honest substitute for "why did this get retrieved," not an LLM-generated
    rationale that could invent a connection that isn't really there.
    """
    shared = sorted(_words(query_description) & _words(neighbor_description))[:6]
    if shared:
        return f"Shares these terms with your description: {', '.join(shared)}."
    return "Retrieved by overall semantic similarity (sentence embedding) rather than shared vocabulary."


# Requirement (Intelligence Fusion Sprint): for every requested comparative dimension, state
# explicitly whether the retrieval corpus (name + description + industry label only — see
# corpus_metadata.json) can honestly support a conclusion about it. Four of the seven originally
# requested dimensions cannot — stated here once, reused everywhere, rather than silently omitted
# or weakly guessed at from description text.
#
# Master Startup Corpus Expansion Sprint, Phase 3/7: `common_maturity_pattern` moved OUT of this
# permanently-unsupported dict — the v2 corpus now carries a real `funding_stage` field for a
# genuine majority of records (see corpus_metadata.json's own per-record data), so it is
# conditionally supported (see `common_funding_stage_pattern` in build_comparative_intelligence
# below), not silently upgraded to "always available" — the function still checks per-run whether
# the actually-retrieved neighbors carry it.
UNSUPPORTED_DIMENSIONS = {
    "common_pricing_model": (
        "Not supported: the retrieval corpus contains no pricing or revenue field for any company "
        "— only name, description, and industry label."
    ),
    "common_deployment_strategy": (
        "Not reliably supported: company descriptions rarely state deployment architecture "
        "explicitly, and guessing from incidental wording would be speculation presented as fact."
    ),
    "common_go_to_market_motion": (
        "Not supported: the retrieval corpus contains no sales-channel, GTM, or customer-acquisition "
        "field for any company."
    ),
}


def build_comparative_intelligence(neighbors: list[dict]) -> dict:
    """Reason deterministically over already-retrieved ventures — never re-embeds, never calls an
    LLM. Every field states its `provenance` (retrieved_evidence vs deterministic_reasoning — no
    ai_inference is used anywhere in this module, a deliberate choice: aggregating real retrieved
    facts needs no LLM, and adding one here would only add fabrication risk for zero data-
    availability gain) and lists which named ventures (`citations`) it's based on, so a founder can
    see exactly which real companies produced each observation.
    """
    if not neighbors:
        return {
            "available": False,
            "note": "No retrieved ventures to reason over.",
            "common_geography": {"available": False, "note": "No retrieved ventures to reason over."},
            "common_funding_stage_pattern": {"available": False, "note": "No retrieved ventures to reason over."},
            **{k: {"available": False, "note": v} for k, v in UNSUPPORTED_DIMENSIONS.items()},
        }

    industry_counts = Counter(v["industry"] for v in neighbors)
    top_industry, top_count = industry_counts.most_common(1)[0]
    common_industry_positioning = {
        "available": True,
        "value": top_industry,
        "support": f"{top_count} of {len(neighbors)} retrieved ventures share this industry label",
        "confidence": "high" if top_count / len(neighbors) >= 0.6 else "low",
        "provenance": "deterministic_reasoning_over_retrieved_evidence",
        "citations": [n["name"] for n in neighbors if n["industry"] == top_industry],
    }

    term_counts: Counter = Counter()
    term_to_ventures: dict[str, list[str]] = {}
    for n in neighbors:
        for term in _words(n["description"]):
            term_counts[term] += 1
            term_to_ventures.setdefault(term, []).append(n["name"])
    shared_terms = [(t, c) for t, c in term_counts.most_common(15) if c >= 2]
    common_terminology = {
        "available": bool(shared_terms),
        "terms": [
            {"term": t, "venture_count": c, "citations": term_to_ventures[t]}
            for t, c in shared_terms[:8]
        ],
        "provenance": "deterministic_reasoning_over_retrieved_evidence",
        "note": None if shared_terms else "No single term appeared in 2 or more retrieved ventures' descriptions.",
    }

    # Master Startup Corpus Expansion Sprint, Phase 7 — geography and funding-stage are only
    # computed from neighbors that ACTUALLY carry that field (v1-style records/older sources have
    # neither); `coverage` states exactly how many of the retrieved neighbors the pattern is based
    # on, so a founder never mistakes "2 of 5 neighbors had this field" for "all 5 agree."
    countries = [n["country"] for n in neighbors if n.get("country")]
    if countries:
        country_counts = Counter(countries)
        top_country, top_country_count = country_counts.most_common(1)[0]
        common_geography = {
            "available": True,
            "value": top_country,
            "support": f"{top_country_count} of {len(countries)} retrieved ventures with known country share this value",
            "coverage": f"{len(countries)} of {len(neighbors)} retrieved ventures have a known country",
            "provenance": "deterministic_reasoning_over_retrieved_evidence",
            "citations": [n["name"] for n in neighbors if n.get("country") == top_country],
        }
    else:
        common_geography = {"available": False, "note": "None of the retrieved ventures in this run have a known country field."}

    funding_stages = [n["funding_stage"] for n in neighbors if n.get("funding_stage")]
    if funding_stages:
        stage_counts = Counter(funding_stages)
        top_stage, top_stage_count = stage_counts.most_common(1)[0]
        common_funding_stage_pattern = {
            "available": True,
            "value": top_stage,
            "support": f"{top_stage_count} of {len(funding_stages)} retrieved ventures with known funding stage share this value",
            "coverage": f"{len(funding_stages)} of {len(neighbors)} retrieved ventures have a known funding stage",
            "provenance": "deterministic_reasoning_over_retrieved_evidence",
            "citations": [n["name"] for n in neighbors if n.get("funding_stage") == top_stage],
        }
    else:
        common_funding_stage_pattern = {"available": False, "note": "None of the retrieved ventures in this run have a known funding-stage field."}

    return {
        "available": True,
        "common_industry_positioning": common_industry_positioning,
        "common_terminology": common_terminology,
        "common_geography": common_geography,
        "common_funding_stage_pattern": common_funding_stage_pattern,
        "common_pricing_model": {"available": False, "note": UNSUPPORTED_DIMENSIONS["common_pricing_model"]},
        "common_deployment_strategy": {"available": False, "note": UNSUPPORTED_DIMENSIONS["common_deployment_strategy"]},
        "common_go_to_market_motion": {"available": False, "note": UNSUPPORTED_DIMENSIONS["common_go_to_market_motion"]},
        "citations": [{"name": n["name"], "industry": n["industry"], "similarity": n["similarity"]} for n in neighbors],
    }


@lru_cache(maxsize=1)
def get_retrieval_index() -> VentureRetrievalIndex | None:
    """Lazily loads (once per process, on first call) the corpus artifact and the sentence-
    transformer model. Returns None — never raises — whenever retrieval is disabled, the corpus
    artifact is missing, or `sentence-transformers` isn't installed, mirroring
    app.ai.factory.get_llm_provider()'s optionality pattern so every caller already knows how to
    degrade gracefully."""
    if not settings.enable_venture_retrieval:
        return None

    model_dir = Path(settings.model_dir) / "venture_retrieval" / VENTURE_RETRIEVAL_VERSION
    embeddings_path = model_dir / "corpus_embeddings.npy"
    metadata_path = model_dir / "corpus_metadata.json"
    if not embeddings_path.exists() or not metadata_path.exists():
        logger.info("Venture retrieval artifact not found at %s — retrieval disabled.", model_dir)
        return None

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.info("sentence-transformers not installed — venture retrieval disabled.")
        return None

    try:
        embeddings = np.load(embeddings_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        records = metadata["records"]
        if embeddings.shape[0] != len(records):
            logger.error("Venture retrieval artifact row-count mismatch — retrieval disabled.")
            return None
        # Avoids a slow/unauthenticated network round-trip when the model is already cached
        # locally (measured ~20s difference in this environment) — never overrides an operator's
        # own explicit setting.
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    except Exception:
        logger.exception("Failed to load venture retrieval index — retrieval disabled.")
        return None

    return VentureRetrievalIndex(embeddings, records, model)


def retrieve_similar_ventures(description: str, k: int = DEFAULT_TOP_K, known_industry: str | None = None) -> dict:
    """Always returns a complete dict, never raises. `available=False` (with an honest `note`)
    whenever retrieval is disabled/unavailable — callers must handle both cases, never assume
    `neighbors` is populated."""
    if not description or not description.strip():
        return {"available": False, "neighbors": [], "method": "unavailable", "note": "No description provided."}

    index = get_retrieval_index()
    if index is None:
        return {
            "available": False,
            "neighbors": [],
            "method": "unavailable",
            "note": "Venture retrieval is disabled or its corpus artifact/model is unavailable in this environment.",
        }

    try:
        similarities, query_normalized = index.compute_similarities(description)
        neighbors = index.retrieve_from_similarities(description, similarities, k=k, known_industry=known_industry)
    except Exception:
        logger.exception("Venture retrieval failed unexpectedly; degrading gracefully.")
        return {"available": False, "neighbors": [], "method": "error", "note": "Retrieval failed unexpectedly."}

    comparative_intelligence = build_comparative_intelligence(neighbors)

    venture_space = None
    analytics_data = get_analytics_data()
    if analytics_data is not None:
        try:
            consensus = comparative_intelligence.get("common_industry_positioning") or {}
            consensus_industry = consensus.get("value") if comparative_intelligence.get("available") else None
            venture_space = analyze_venture_space(similarities, query_normalized, consensus_industry, analytics_data)
        except Exception:
            logger.exception("Venture space analytics failed unexpectedly; omitting.")
            venture_space = None

    return {
        "available": True,
        "venture_retrieval_version": PUBLIC_VENTURE_RETRIEVAL_VERSION,
        "method": "semantic_nearest_neighbor_cosine_similarity",
        "embedding_model": EMBEDDING_MODEL_NAME,
        "neighbors": neighbors,
        "industry_reranking_applied": bool(known_industry),
        "comparative_intelligence": comparative_intelligence,
        "venture_space_analytics": venture_space,
        "provenance_disclaimer": (
            "Every venture listed is a REAL company from a historical dataset (YC-backed "
            "companies, 2012-2024), retrieved purely by description similarity. These are NOT "
            "verified as current competitors, may no longer be operating, and are shown as "
            "historical pattern reference only — never a claim about this venture's actual "
            "competitive landscape."
        ),
    }
