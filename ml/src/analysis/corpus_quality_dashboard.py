"""Master Startup Corpus Expansion Sprint, Phase 8 — Corpus Quality Dashboard.

Reads whichever corpus artifact is asked for (defaults to whatever app.ml.venture_retrieval
actually loads) and reports real, computed statistics — no estimates.

Run: `python -m ml.src.analysis.corpus_quality_dashboard --version v2`
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = REPO_ROOT / "ml" / "models" / "venture_retrieval"

# The controlled, cross-source taxonomy shared by every source in this corpus family — distinct
# from the ~170 additional free-text single-source category labels one small source (
# joebeachcapital) contributes, which are reported separately so they don't inflate the headline
# "N industries" number with labels no other source shares.
_CONTROLLED_TAXONOMY = {
    "b2b", "consumer", "healthcare", "fintech", "industrials",
    "real estate and construction", "education",
}


def build_dashboard(version: str) -> dict:
    metadata = json.loads((MODELS_DIR / version / "corpus_metadata.json").read_text(encoding="utf-8"))
    records: list[dict] = metadata["records"]
    n = len(records)

    industries = Counter(r.get("industry") for r in records)
    controlled_industries = {k: v for k, v in industries.items() if k in _CONTROLLED_TAXONOMY}
    long_tail_industries = {k: v for k, v in industries.items() if k not in _CONTROLLED_TAXONOMY}

    countries = Counter(r["country"] for r in records if r.get("country"))
    funding_stages = Counter(r["funding_stage"] for r in records if r.get("funding_stage"))
    sources = Counter(r.get("source", "unknown") for r in records)

    years = [int(r["founding_year"]) for r in records if r.get("founding_year") not in (None, "")]
    year_counts = Counter(years)

    desc_lengths = [len(r.get("description") or "") for r in records]

    def _completeness(field: str) -> float:
        present = sum(1 for r in records if r.get(field) not in (None, ""))
        return round(present / n * 100, 1) if n else 0.0

    metadata_completeness = {
        field: _completeness(field)
        for field in ("country", "funding_stage", "team_size", "founding_year", "subindustry")
    }

    return {
        "dashboard_version": version,
        "total_startups": n,
        "sources": dict(sources),
        "industries": {
            "controlled_taxonomy_counts": controlled_industries,
            "n_controlled_taxonomy_classes": len(controlled_industries),
            "n_additional_long_tail_labels": len(long_tail_industries),
            "note": (
                "The 7-class controlled taxonomy (b2b/consumer/healthcare/fintech/industrials/"
                "real estate and construction/education) is shared across every source in this "
                "corpus. The additional long-tail labels come from ONE source only "
                "(joebeachcapital, free-text multi-value categories) and are not a second "
                "controlled taxonomy — reported separately so they don't inflate the headline "
                "class count."
            ),
        },
        "countries": {
            "n_distinct": len(countries),
            "top_10": dict(countries.most_common(10)),
            "coverage_pct": metadata_completeness["country"],
        },
        "funding_stages": {
            "counts": dict(funding_stages),
            "coverage_pct": metadata_completeness["funding_stage"],
        },
        "coverage_by_year": dict(sorted(year_counts.items())) if year_counts else {},
        "average_description_length_chars": round(sum(desc_lengths) / n, 1) if n else 0.0,
        "metadata_completeness_pct": metadata_completeness,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()
    print(json.dumps(build_dashboard(args.version), indent=2))


if __name__ == "__main__":
    main()
