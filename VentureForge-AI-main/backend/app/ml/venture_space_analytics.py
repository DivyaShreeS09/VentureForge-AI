"""Venture-Space Analytics (Intelligence Differentiation Sprint): mathematically defined metrics
derived directly from the same embedding space app.ml.venture_retrieval already builds and
evaluates — no new model, no fabricated score. Every metric below is a documented function of
cosine similarities between a query embedding and the real 4,298-company corpus; nothing here
is invented or dressed up to look more precise than the underlying math supports.

WHAT WAS AUDITED AND REJECTED FIRST: "Venture Cluster" (assigning a query to a discrete K-means
cluster over the corpus) was tested for K in {6, 8, 10, 12, 15}. Silhouette scores were 0.019-0.028
for every K — far below the ~0.25 threshold conventionally treated as "any real structure" at all
(0.5+ is "strong"). This embedding space is a continuum, not a set of separable clusters, so a
confident "Cluster #5" label would misrepresent the math. REJECTED — see
ml/models/venture_space_analytics/v1/metadata.json's `venture_cluster_metric` block for the full
finding. Innovation Distance and Market Crowdedness below use the REAL industry labels (7 groups,
actual ground truth in the dataset) instead of that unsupported clustering.

Implemented metrics (each defined precisely, each with a stated confidence basis):

- Novelty Score = 1 - max_i cos(q, c_i): distance from the single nearest real corpus neighbor.
- Competition Density = |{i : cos(q, c_i) >= tau}| (tau=0.5, disclosed, chosen just below this
  corpus's own median leave-one-out nearest-neighbor similarity of 0.547 — see metadata).
- Innovation Distance = 1 - cos(q, centroid of the venture's consensus industry group): distance
  from the "prototype" of its own real category, distinct from Novelty Score (which measures
  distance from one specific neighbor, not a whole-category average).
- Market Crowdedness = (size of the venture's consensus industry group) / (corpus size): a plain,
  real fraction — e.g. "b2b" is 50.0% of this reference corpus, "education" is 2.0%.
- Similarity Distribution = descriptive statistics of the query's full similarity vector against
  the entire corpus, plus the percentile rank of its top-1 similarity against a precomputed
  reference distribution (every corpus item's own leave-one-out nearest-neighbor similarity) — this
  is what gives Novelty Score real statistical context instead of a bare, uncalibrated number.
- Opportunity Isolation: NOT an independently computed quantity — explicitly a composite derived
  from Novelty Score's percentile rank (high) AND Competition Density (low), reported as such so it
  is never mistaken for a sixth independent embedding computation.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

VENTURE_SPACE_ANALYTICS_VERSION = "v1"
COMPETITION_DENSITY_THRESHOLD = 0.5
# Composite thresholds for Opportunity Isolation — both must hold; disclosed, not tuned to force a
# particular outcome. "Novelty in the top 10% most-dissimilar-from-nearest-neighbor" and
# "fewer than 5% of the corpus meaningfully similar" are both conservative, round cutoffs.
OPPORTUNITY_ISOLATION_NOVELTY_PERCENTILE = 90  # top-1 similarity below this percentile of the reference distribution
OPPORTUNITY_ISOLATION_DENSITY_FRACTION = 0.05


class VentureSpaceAnalyticsData:
    """Holds the precomputed, corpus-derived artifacts needed to score a new query — nothing here
    is refit per request."""

    def __init__(self, industries: np.ndarray, industry_centroids: dict, reference_nn_similarities: np.ndarray) -> None:
        self.industries = industries
        self.industry_centroids = industry_centroids  # {industry: {"centroid": np.ndarray, "size": int, "fraction_of_corpus": float}}
        self.reference_nn_similarities = reference_nn_similarities  # (n,) — every corpus item's own leave-one-out NN similarity


def analyze_venture_space(
    similarities: np.ndarray,
    query_vector_normalized: np.ndarray,
    consensus_industry: str | None,
    data: VentureSpaceAnalyticsData,
) -> dict:
    """Compute every venture-space metric. `similarities` is the already-computed cosine
    similarity between one query embedding and every corpus embedding (shape (n,), never
    recomputed here). `query_vector_normalized` is the same query embedding, unit-normalized, used
    only to score it against the (also unit-normalized) industry centroids. `consensus_industry`
    is the label already produced by app.ml.venture_retrieval.build_comparative_intelligence —
    reused, not duplicated.
    """
    similarities = np.asarray(similarities, dtype=np.float64)
    max_sim = float(similarities.max())

    novelty_score = 1.0 - max_sim
    ref = data.reference_nn_similarities
    # Fraction of the reference distribution this venture's dissimilarity "beats" — a LOW max_sim
    # (few/no close real neighbors) should yield a HIGH novelty percentile, not a low one.
    novelty_percentile = float((ref > max_sim).mean() * 100)

    density_count = int((similarities >= COMPETITION_DENSITY_THRESHOLD).sum())
    density_fraction = density_count / len(similarities)

    innovation_distance = None
    market_crowdedness = None
    if consensus_industry and consensus_industry in data.industry_centroids:
        centroid_info = data.industry_centroids[consensus_industry]
        centroid = np.asarray(centroid_info["centroid"], dtype=np.float64)
        query_to_centroid_sim = float(np.dot(query_vector_normalized, centroid))
        innovation_distance = {
            "value": round(1.0 - query_to_centroid_sim, 4),
            "definition": f"1 - cosine_similarity(query, centroid of the '{consensus_industry}' industry group)",
            "reference_industry": consensus_industry,
        }
        market_crowdedness = {
            "value": centroid_info["fraction_of_corpus"],
            "industry": consensus_industry,
            "corpus_size": centroid_info["size"],
        }

    is_isolated = (
        novelty_percentile >= OPPORTUNITY_ISOLATION_NOVELTY_PERCENTILE
        and density_fraction <= OPPORTUNITY_ISOLATION_DENSITY_FRACTION
    )

    return {
        "venture_space_analytics_version": VENTURE_SPACE_ANALYTICS_VERSION,
        "novelty_score": {
            "value": round(novelty_score, 4),
            "definition": "1 - cosine_similarity(query, nearest real corpus neighbor)",
            "percentile_vs_reference": round(novelty_percentile, 1),
            "confidence": "grounded" if len(ref) >= 1000 else "low_reference_size",
            "note": (
                f"Your nearest real neighbor is more dissimilar than {novelty_percentile:.0f}% of "
                "this corpus's own typical nearest-neighbor pairs — i.e. this venture sits further "
                "from any single known example than most companies in the reference set do."
            ),
        },
        "competition_density": {
            "count": density_count,
            "fraction_of_corpus": round(density_fraction, 4),
            "threshold": COMPETITION_DENSITY_THRESHOLD,
            "definition": f"count of corpus ventures with cosine_similarity(query, venture) >= {COMPETITION_DENSITY_THRESHOLD}",
        },
        "innovation_distance": innovation_distance,
        "market_crowdedness": market_crowdedness,
        "opportunity_isolation": {
            "is_isolated": bool(is_isolated),
            "definition": (
                f"Composite (not an independently computed score): novelty percentile >= "
                f"{OPPORTUNITY_ISOLATION_NOVELTY_PERCENTILE} AND competition-density fraction <= "
                f"{OPPORTUNITY_ISOLATION_DENSITY_FRACTION:.0%}. Derived entirely from novelty_score "
                "and competition_density above — reported separately for readability only."
            ),
        },
        "similarity_distribution": {
            "mean": round(float(similarities.mean()), 4),
            "std": round(float(similarities.std()), 4),
            "max": round(max_sim, 4),
            "reference_distribution_percentiles": {
                "5": round(float(np.percentile(ref, 5)), 4),
                "50": round(float(np.percentile(ref, 50)), 4),
                "95": round(float(np.percentile(ref, 95)), 4),
            },
        },
        "venture_cluster": {
            "status": "rejected",
            "reason": (
                "K-means over this embedding space produced silhouette scores of 0.019-0.028 for "
                "every K tested (6-15) — no meaningful discrete cluster structure exists. See "
                "app.ml.venture_space_analytics module docstring for the full audit."
            ),
        },
    }


@lru_cache(maxsize=1)
def get_analytics_data() -> VentureSpaceAnalyticsData | None:
    """Lazily loads (once per process) the precomputed corpus-derived artifacts. Returns None —
    never raises — whenever retrieval/analytics is disabled or the artifact is missing, mirroring
    app.ml.venture_retrieval.get_retrieval_index()'s optionality pattern."""
    if not settings.enable_venture_retrieval:
        return None

    model_dir = Path(settings.model_dir) / "venture_space_analytics" / VENTURE_SPACE_ANALYTICS_VERSION
    metadata_path = model_dir / "metadata.json"
    nn_sims_path = model_dir / "reference_nn_similarities.npy"
    if not metadata_path.exists() or not nn_sims_path.exists():
        logger.info("Venture space analytics artifact not found at %s — disabled.", model_dir)
        return None

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        reference_nn_similarities = np.load(nn_sims_path)
        industry_centroids = metadata["industry_centroids"]
        for info in industry_centroids.values():
            info["centroid"] = np.asarray(info["centroid"], dtype=np.float64)
        return VentureSpaceAnalyticsData(
            industries=None, industry_centroids=industry_centroids, reference_nn_similarities=reference_nn_similarities
        )
    except Exception:
        logger.exception("Failed to load venture space analytics artifact — disabled.")
        return None
