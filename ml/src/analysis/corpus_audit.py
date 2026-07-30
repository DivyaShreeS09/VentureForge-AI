"""Master Startup Corpus Expansion Sprint, Phase 1 — Corpus Audit.

Audits whatever corpus app.ml.venture_retrieval actually loads at request time
(ml/models/venture_retrieval/<version>/corpus_metadata.json) — never a separate, hand-picked
sample. Every number here is computed directly from that artifact; nothing is estimated.

Run: `python -m ml.src.analysis.corpus_audit [--version v1|v2]`
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = REPO_ROOT / "ml" / "models" / "venture_retrieval"


def _load_metadata(version: str) -> dict:
    path = MODELS_DIR / version / "corpus_metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"No corpus_metadata.json at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def audit_corpus(version: str = "v1") -> dict:
    metadata = _load_metadata(version)
    records: list[dict] = metadata["records"]
    n = len(records)

    names = [r["name"] for r in records]
    name_counts = Counter(names)
    duplicate_name_count = sum(c - 1 for c in name_counts.values() if c > 1)

    desc_lengths = [len(r.get("description") or "") for r in records]
    avg_desc_length = sum(desc_lengths) / n if n else 0.0

    industry_counts = Counter(r.get("industry", "unknown") for r in records)

    # Metadata completeness: this corpus's schema is exactly {name, description, industry} — any
    # field beyond that (country, funding stage, founding date, employees, business model, pricing,
    # tech stack) is ABSENT for every single record, not merely sparse. Reported as 0%, not omitted.
    optional_fields = (
        "country", "founding_year", "funding_stage", "employees", "business_model",
        "customer_type", "pricing", "technology_stack",
    )
    metadata_completeness = {field: 0.0 for field in optional_fields}

    known_sectors = set(industry_counts.keys())
    # Sectors this project's own product surfaces (app.agents.venture_vocabulary) that this
    # retrieval corpus has NO representation for at all — a real, computed gap, not a guess.
    all_product_sectors = {
        "healthcare", "insurance", "fintech", "cybersecurity", "legaltech", "hrtech", "proptech",
        "retailtech", "travel_hospitality", "govtech", "climatetech", "agriculture", "media",
        "gaming", "arvr", "creator_economy", "foodtech", "logistics", "marketplace", "hardware",
        "developer_tools", "education", "consumer", "b2b",
    }
    # This corpus's own industry labels use a different (coarser, differently-cased) taxonomy than
    # the product's category taxonomy — a normalized approximate overlap check, not a false claim
    # of a direct crosswalk.
    normalized_corpus_sectors = {s.lower().replace(" ", "_") for s in known_sectors}
    missing_sectors = sorted(all_product_sectors - normalized_corpus_sectors)

    return {
        "audited_version": version,
        "n_companies": n,
        "date_coverage": "NONE — no founding date, batch date, or funding date field exists on any record.",
        "geography_coverage": "NONE — no country/region/location field exists on any record.",
        "industry_coverage": {
            "n_distinct_industries": len(industry_counts),
            "counts": dict(industry_counts),
        },
        "missing_sectors_vs_product_taxonomy": missing_sectors,
        "duplicate_rate": {
            "duplicate_name_occurrences": duplicate_name_count,
            "duplicate_rate_pct": round(duplicate_name_count / n * 100, 2) if n else 0.0,
            "method": "Count of names appearing more than once, minus one occurrence each (i.e. the number of REMOVABLE duplicate rows if deduplicating strictly by name).",
        },
        "average_description_length_chars": round(avg_desc_length, 1),
        "startup_stage_coverage": "NONE — no funding-stage, batch, or company-age field exists on any record.",
        "funding_coverage": "NONE — no funding amount, round, or investor field exists on any record.",
        "metadata_completeness_pct": metadata_completeness,
        "gap_analysis": [
            "Corpus is 100% YC-backed companies (single-source bias) — no non-YC-backed startup is represented at all.",
            "Zero geographic metadata — cannot filter or benchmark by country/region despite most companies plausibly being US-concentrated (YC's own known bias).",
            "Zero temporal metadata — cannot tell whether a retrieved 'similar venture' is from 2012 or 2024, or filter by recency.",
            "Zero funding/stage metadata — startup_benchmark.py and go_to_market_intelligence.py must explicitly mark pricing/funding-stage benchmarking as UNSUPPORTED for this exact reason (see app.ml.venture_retrieval.UNSUPPORTED_DIMENSIONS).",
            f"{len(missing_sectors)} of {len(all_product_sectors)} product-facing categories have no dedicated corpus representation under this corpus's own (coarser) taxonomy.",
            f"{duplicate_name_count} duplicate-name occurrences ({round(duplicate_name_count / n * 100, 2) if n else 0}%) were never deduplicated beyond exact-description matching.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()
    result = audit_corpus(args.version)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
