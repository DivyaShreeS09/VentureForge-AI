"""Deterministic venture-positioning taxonomy matcher (prototype).

Scores a startup description against a broader, curated positioning taxonomy — deliberately
richer than the 7-label ML classifier, since that label set is honest as a model signal but too
coarse to serve as a founder-facing identity (see the approved architecture plan). Also extracts
deployment-sector tags via the same deterministic keyword approach. Nothing here is invented per
input — every candidate/tag is drawn from this fixed, versioned taxonomy, scored by literal
keyword/phrase overlap with the submitted text.
"""

from __future__ import annotations

import re

TAXONOMY_VERSION = "v1-prototype"

# domain -> defining vocabulary (lowercase keywords/phrases). Curated once, not per-input.
POSITIONING_TAXONOMY: dict[str, list[str]] = {
    "Smart Facilities Technology": [
        "facilities", "building", "campus", "hotel", "occupancy", "electricity", "water",
        "utility", "utilities", "monitors", "monitoring", "sensor", "sensors", "autonomous",
        "real time", "real-time", "waste",
    ],
    "PropTech": [
        "property", "real estate", "building management", "facilities", "occupancy", "tenant",
        "landlord", "commercial real estate",
    ],
    "Sustainability Technology": [
        "waste", "energy", "sustainability", "carbon", "efficiency", "resource", "conservation",
        "emissions", "green",
    ],
    "Enterprise AI": [
        "ai", "artificial intelligence", "platform", "analytics", "automation", "autonomous",
        "machine learning", "predictive",
    ],
    "Clinical Decision Support": [
        "clinical", "diagnosis", "diagnostic", "risk detection", "risk", "patient", "clinician",
        "medical", "health risk", "screening",
    ],
    "Remote Patient Monitoring": [
        "monitoring", "patient", "remote", "wearable", "sensor", "vitals", "chronic",
        "telehealth",
    ],
    "HealthTech Diagnostics": [
        "diagnostic", "diagnosis", "detection", "screening", "medical imaging", "health",
        "diabetic", "wound",
    ],
    "Campus & Student Services": [
        "university", "students", "student", "campus", "college", "academic", "hackathon",
        "classmates", "study",
    ],
    "Peer Collaboration Marketplaces": [
        "marketplace", "teammates", "collaboration", "matching", "find teammates", "project",
        "team formation",
    ],
    "EdTech": [
        "education", "learning", "course", "curriculum", "students", "university", "school",
    ],
    "Restaurant Operations Technology": [
        "restaurant", "restaurants", "kitchen", "food waste", "inventory", "menu", "chef",
        "point of sale", "pos",
    ],
    "Food-Cost Management": [
        "food waste", "inventory", "cost", "waste", "restaurants", "food cost", "spoilage",
    ],
    "Productivity Software": [
        "productivity", "task", "tasks", "to-do", "todo", "reminders", "planning", "schedule",
        "time management",
    ],
    "General Consumer App": [
        "app", "people", "users", "everyday", "personal", "individuals",
    ],
}

# domain -> deployment/vertical tags it can surface (kept separate from primary/secondary domain
# scoring — these describe *where* the product runs, not *what category* it is).
DEPLOYMENT_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Campuses": ["campus", "campuses", "university", "college"],
    "Hotels": ["hotel", "hotels", "hospitality"],
    "Clinics": ["clinic", "clinics", "podiatry", "patient", "clinical"],
    "Hospitals": ["hospital", "hospitals", "hospital system"],
    "Restaurants": ["restaurant", "restaurants", "kitchen"],
    "Universities": ["university", "universities", "college"],
    "Consumer Households": ["people", "individuals", "everyday", "personal"],
}

# Below this normalized top-score, the taxonomy signal is considered weak/inconclusive — an
# independent confidence signal from the ML classifier's own confidence, per the prototyping
# finding that a confidently-classified model_category can still sit on a weak taxonomy match.
TAXONOMY_CONFIDENCE_THRESHOLD = 0.35
TAXONOMY_AMBIGUITY_MARGIN = 0.12


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s-]", " ", text.lower())


MIN_KEYWORD_HITS = 2


def _score_domain(text_norm: str, keywords: list[str]) -> float:
    """Normalized keyword-overlap score. Requires at least MIN_KEYWORD_HITS distinct hits (or all
    of a domain's keywords, if it has fewer than that) before scoring above zero — found via
    prototyping that a single generic shared word (e.g. "waste") let a short, tangential keyword
    list outrank a genuinely better-matching, longer one purely by division artifact."""
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in text_norm)
    threshold = min(MIN_KEYWORD_HITS, len(keywords))
    if hits < threshold:
        return 0.0
    return hits / len(keywords)


def score_taxonomy(description: str) -> list[dict]:
    """Return every positioning-taxonomy domain with its normalized match score, ranked
    descending. A real, deterministic signal — never invented per input."""
    text_norm = _normalize(description)
    scored = [
        {"domain": domain, "score": round(_score_domain(text_norm, keywords), 4)}
        for domain, keywords in POSITIONING_TAXONOMY.items()
    ]
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored


def extract_deployment_sectors(description: str) -> list[str]:
    """Deterministic keyword-tag extraction — no Gemini involvement at all."""
    text_norm = _normalize(description)
    return [
        sector
        for sector, keywords in DEPLOYMENT_SECTOR_KEYWORDS.items()
        if any(kw in text_norm for kw in keywords)
    ]


def taxonomy_is_ambiguous(candidates: list[dict]) -> bool:
    if not candidates:
        return True
    top = candidates[0]["score"]
    if top < TAXONOMY_CONFIDENCE_THRESHOLD:
        return True
    runner_up = candidates[1]["score"] if len(candidates) > 1 else 0.0
    return (top - runner_up) < TAXONOMY_AMBIGUITY_MARGIN
