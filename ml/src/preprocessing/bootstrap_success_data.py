"""Synthetic bootstrap dataset for the startup success-prediction classifier.

Mirrors ml/src/preprocessing/bootstrap_data.py's role for the industry classifier: a fresh
checkout (including CI) never has ml/data/raw/startup_success_raw.csv, since it is git-ignored
(see ml/DATASETS.md). Rather than fail the pipeline outright, this generates a small, clearly
synthetic tabular corpus with the same column schema as the real, approved dataset
(kaggle:yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase), deterministically (fixed seed).

Every metric computed from this corpus is reported as measured on the bootstrap corpus only — never
as production model performance. It exists solely so the pipeline (preprocessing, training,
evaluation, serving) can be built and unit-tested end to end without the real dataset present.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import pandas as pd

CATEGORIES = ["b2b", "fintech", "healthtech", "ecommerce", "edtech", "marketplace"]
COUNTRIES = ["usa", "gbr", "ind", "deu", "unknown"]

# Fixed synthetic "today" so the bootstrap corpus is fully deterministic across runs/machines —
# not wall-clock `datetime.now()`, which would make the generated dates (and anything derived
# from them, e.g. the temporal-split diagnostic) non-reproducible.
_BOOTSTRAP_REFERENCE_DATE = datetime(2024, 1, 1)


def generate_bootstrap_success_dataset(n_per_class: int = 60, seed: int = 42) -> pd.DataFrame:
    """Deterministically generate a synthetic success/failure tabular corpus."""
    rng = random.Random(seed)
    records: list[dict] = []

    for success in (0, 1):
        for i in range(n_per_class):
            # Successful companies are generated with a (deliberately synthetic, not evidence-based)
            # tendency toward more funding/rounds/age so the bootstrap pipeline has *some* separable
            # signal to fit during smoke tests — never used to justify a production metric.
            base_funding = rng.uniform(5e5, 5e7) * (1.8 if success else 1.0)
            company_age_years = round(rng.uniform(0.5, 12.0), 2)
            founded_at = _BOOTSTRAP_REFERENCE_DATE - timedelta(days=int(company_age_years * 365.25) + rng.randint(0, 300))
            time_to_first_funding_years = round(rng.uniform(0.0, min(2.0, company_age_years)), 2)
            first_funding_at = founded_at + timedelta(days=int(time_to_first_funding_years * 365.25))
            last_funding_at = founded_at + timedelta(days=int(company_age_years * 365.25))
            records.append(
                {
                    "permalink": f"/organization/bootstrap-{success}-{i}",
                    "name": f"BootstrapCo{success}{i}",
                    "funding_total_usd": round(base_funding, 2),
                    "funding_rounds": rng.randint(1, 6) + (2 if success else 0),
                    "company_age_years": company_age_years,
                    "funding_span_years": round(rng.uniform(0.0, 6.0), 2),
                    "time_to_first_funding_years": time_to_first_funding_years,
                    "funding_recency_years": round((_BOOTSTRAP_REFERENCE_DATE - last_funding_at).days / 365.25, 2),
                    "primary_category": rng.choice(CATEGORIES),
                    "category_count": rng.randint(1, 4),
                    "country_code": rng.choice(COUNTRIES),
                    "success": success,
                    "founded_at": founded_at.date().isoformat(),
                    "first_funding_at": first_funding_at.date().isoformat(),
                    "last_funding_at": last_funding_at.date().isoformat(),
                }
            )

    df = pd.DataFrame.from_records(records)
    return df.reset_index(drop=True)
