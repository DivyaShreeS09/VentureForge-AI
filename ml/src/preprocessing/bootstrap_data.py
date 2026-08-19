"""Synthetic bootstrap dataset for the industry classifier.

No verified, schema-inspected, licensed dataset was available in this environment (see
ml/DATASETS.md — Kaggle authentication is not configured here). Rather than fabricate labels on
top of unrelated data, this module *generates* a small, clearly-synthetic corpus of startup
name/description pairs across a fixed industry taxonomy, deterministically (fixed seed, no
randomness that varies across runs).

This is deliberately not passed off as a real-world dataset: every metric computed from it is
reported as measured on this bootstrap corpus only, not as production model performance. It exists
to let the pipeline (cleaning, splitting, training, evaluation, explainability, serving) be built
and tested end-to-end honestly while a real dataset is sourced and approved.

Replace or substantially augment via ml/dataset_manifest.json + this file once a real dataset is
approved in ml/DATASETS.md.
"""

from __future__ import annotations

import random

import pandas as pd

# Canonical label taxonomy for the bootstrap corpus. Documented here since this file is the
# taxonomy's source of truth until a real dataset defines one (see ml/DATASETS.md).
INDUSTRIES: list[str] = [
    "saas",
    "fintech",
    "healthtech",
    "ecommerce",
    "edtech",
    "marketplace",
]

_TEMPLATES: dict[str, list[str]] = {
    "saas": [
        "A cloud platform that helps {audience} automate {task} with configurable workflows.",
        "Subscription software giving {audience} real-time dashboards for {task}.",
        "A B2B tool that lets {audience} manage {task} from a single web console.",
        "An API-first product that integrates with existing tools to streamline {task} for {audience}.",
        "A no-code workspace where {audience} build custom {task} pipelines without engineering help.",
    ],
    "fintech": [
        "A digital banking app that gives {audience} instant insight into {task}.",
        "A payments platform that lets {audience} settle {task} across borders in seconds.",
        "A lending product that scores {audience} for {task} using alternative data.",
        "An investing app that helps {audience} automate {task} with low fees.",
        "A compliance tool that helps {audience} monitor {task} for fraud in real time.",
    ],
    "healthtech": [
        "A telehealth platform connecting {audience} with clinicians for {task}.",
        "A remote monitoring device that tracks {audience} vitals to support {task}.",
        "Software that helps clinics manage {audience} records and {task} scheduling.",
        "An app that reminds {audience} about medication and tracks {task} adherence.",
        "A diagnostics platform using lab data to flag {task} risk for {audience}.",
    ],
    "ecommerce": [
        "An online storefront that lets {audience} sell {task} directly to consumers.",
        "A subscription box service delivering curated {task} to {audience} each month.",
        "A marketplace plugin that helps {audience} manage inventory for {task}.",
        "A direct-to-consumer brand selling {task} with a focus on {audience}.",
        "A checkout optimization tool that increases conversion for {audience} selling {task}.",
    ],
    "edtech": [
        "An online learning platform teaching {audience} {task} through interactive lessons.",
        "A tutoring marketplace connecting {audience} with experts in {task}.",
        "Classroom software that helps teachers track {audience} progress in {task}.",
        "A certification platform helping {audience} upskill in {task} at their own pace.",
        "A gamified app that teaches {audience} {task} through daily practice.",
    ],
    "marketplace": [
        "A two-sided marketplace connecting {audience} with providers of {task}.",
        "A booking platform that lets {audience} discover and reserve {task} nearby.",
        "A peer-to-peer platform where {audience} can rent out {task} to others.",
        "A vetted network matching {audience} with freelancers for {task}.",
        "A local services app connecting {audience} with on-demand {task}.",
    ],
}

_AUDIENCES = [
    "small businesses",
    "enterprise teams",
    "independent contractors",
    "hospitals",
    "college students",
    "retail brands",
    "freelancers",
    "logistics companies",
    "property managers",
    "restaurants",
]

_TASKS = {
    "saas": ["customer support", "project tracking", "data pipelines", "employee onboarding", "invoice approvals"],
    "fintech": ["cash flow", "cross-border payments", "credit risk", "portfolio rebalancing", "transaction monitoring"],
    "healthtech": ["chronic care", "post-surgery follow-up", "appointment", "medication", "diabetes risk"],
    "ecommerce": ["handmade goods", "skincare products", "specialty coffee", "apparel", "home decor"],
    "edtech": ["data science", "spoken English", "algebra", "coding fundamentals", "public speaking"],
    "marketplace": ["home cleaning", "event photography", "equipment rentals", "pet sitting", "tutoring sessions"],
}

_NAME_PREFIXES = ["Nova", "Brightline", "Fern", "Orbit", "Cobalt", "Lumen", "Basecamp", "Wren", "Atlas", "Harbor"]
_NAME_SUFFIXES = ["Labs", "Health", "Pay", "Learn", "Market", "Cloud", "Works", "Hub", "Systems", "Collective"]


def generate_bootstrap_dataset(rows_per_industry: int = 25, seed: int = 42) -> pd.DataFrame:
    """Deterministically generate a synthetic name/description/industry corpus."""
    rng = random.Random(seed)
    records: list[dict[str, str]] = []

    for industry in INDUSTRIES:
        templates = _TEMPLATES[industry]
        tasks = _TASKS[industry]
        for i in range(rows_per_industry):
            template = templates[i % len(templates)]
            audience = rng.choice(_AUDIENCES)
            task = rng.choice(tasks)
            description = template.format(audience=audience, task=task)
            name = f"{rng.choice(_NAME_PREFIXES)}{rng.choice(_NAME_SUFFIXES)}"
            records.append({"name": name, "description": description, "industry": industry})

    df = pd.DataFrame.from_records(records)
    # De-duplicate identical (template, audience, task) collisions from the random draw.
    df = df.drop_duplicates(subset=["description"]).reset_index(drop=True)
    return df
