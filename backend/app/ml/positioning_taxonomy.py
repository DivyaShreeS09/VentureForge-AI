"""Controlled venture-positioning taxonomy (Phase 0.5).

Deterministic, versioned, and entirely independent of the trained industry classifier's 7-label
taxonomy (see app.ml.predictor) — that label set is an honest technical signal but too coarse to
serve as a founder-facing identity (e.g. "Industrials" tells a founder building a campus
energy-monitoring product almost nothing useful). This module scores a startup description
against a broader, curated list of founder-facing domains, each carrying:

  - `keywords`: single-token vocabulary -> weight
  - `phrases`: multi-word vocabulary -> weight (matched as literal substrings after normalization)
  - `high_specificity`: the subset of this domain's keywords/phrases that are specific enough that
    a single match is sufficient to make the domain an eligible candidate (see
    `score_taxonomy`'s eligibility rule) — e.g. "diabetic foot" is high-specificity for HealthTech
    Diagnostics, but "platform" is not high-specificity for Enterprise AI.
  - `specificity_rank`: lower = narrower/more specific domain. Used only as a tie-break (see
    `rank_candidates`) — never as a scoring input — so that a narrower, more specific domain wins
    over a broad catch-all (e.g. Enterprise AI) when their weighted scores are otherwise tied.
  - `deployment_sectors`: the deployment-sector tags (see `DEPLOYMENT_SECTOR_KEYWORDS`) this
    domain is typically associated with, used only as a tie-break signal, never for scoring.

Nothing here is invented per input — every candidate, matched term, and tag is drawn from this
fixed, versioned taxonomy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TAXONOMY_VERSION = "v1"

# Below this normalized weighted score, the taxonomy signal is considered weak/inconclusive.
CONFIDENCE_THRESHOLD = 0.35
AMBIGUITY_MARGIN = 0.12

# A normal candidate needs at least this many *distinct* matched concepts (keywords or phrases,
# deduplicated — repeating the same generic word never counts twice). A domain with fewer than
# this many distinct matches is only eligible if at least one of those matches is high-specificity.
MIN_DISTINCT_CONCEPTS = 2


@dataclass(frozen=True)
class DomainSpec:
    name: str
    specificity_rank: int
    keywords: dict[str, float]
    phrases: dict[str, float] = field(default_factory=dict)
    high_specificity: frozenset[str] = frozenset()
    deployment_sectors: frozenset[str] = frozenset()

    def max_weight(self) -> float:
        return sum(self.keywords.values()) + sum(self.phrases.values())


POSITIONING_TAXONOMY: dict[str, DomainSpec] = {
    "Smart Facilities Technology": DomainSpec(
        name="Smart Facilities Technology",
        specificity_rank=2,
        keywords={
            "facilities": 1.0, "building": 0.6, "campus": 0.8, "hotel": 0.8, "occupancy": 1.2,
            "electricity": 1.0, "water": 0.6, "utility": 1.0, "utilities": 1.0, "sensor": 0.8,
            "sensors": 0.8,
        },
        phrases={"real time": 0.8, "resource monitoring": 1.4},
        high_specificity=frozenset({"resource monitoring", "occupancy"}),
        deployment_sectors=frozenset({"Campuses", "Hotels"}),
    ),
    "PropTech": DomainSpec(
        name="PropTech",
        specificity_rank=4,
        keywords={"property": 1.0, "tenant": 1.0, "landlord": 1.2},
        phrases={"real estate": 1.4, "building management": 1.2, "commercial real estate": 1.6},
        high_specificity=frozenset({"real estate", "commercial real estate"}),
        deployment_sectors=frozenset({"Campuses", "Hotels"}),
    ),
    "Sustainability Technology": DomainSpec(
        name="Sustainability Technology",
        specificity_rank=5,
        keywords={
            "sustainability": 1.4, "carbon": 1.2, "emissions": 1.4, "conservation": 1.0,
            "efficiency": 0.6, "waste": 0.5,
        },
        phrases={"carbon footprint": 1.6, "energy efficiency": 1.4},
        high_specificity=frozenset({"carbon footprint", "emissions"}),
        deployment_sectors=frozenset({"Campuses", "Hotels", "Restaurants"}),
    ),
    "Enterprise AI": DomainSpec(
        name="Enterprise AI",
        specificity_rank=7,
        keywords={
            "ai": 0.3, "platform": 0.3, "analytics": 0.6, "automation": 0.6, "autonomous": 0.6,
            "predictive": 0.6,
        },
        phrases={"machine learning": 1.0},
        high_specificity=frozenset(),
        deployment_sectors=frozenset(),
    ),
    "Clinical Decision Support": DomainSpec(
        name="Clinical Decision Support",
        specificity_rank=1,
        keywords={
            "clinical": 1.2, "clinician": 1.2, "patient": 0.6, "medical": 0.8, "screening": 1.0,
        },
        phrases={"risk detection": 1.6, "health risk": 1.2, "clinical decision": 1.8},
        high_specificity=frozenset({"risk detection", "clinical decision"}),
        deployment_sectors=frozenset({"Clinics", "Hospitals"}),
    ),
    "Remote Patient Monitoring": DomainSpec(
        name="Remote Patient Monitoring",
        specificity_rank=2,
        keywords={"patient": 0.6, "remote": 0.8, "wearable": 1.2, "chronic": 1.0},
        phrases={"remote monitoring": 1.8, "patient monitoring": 1.8, "telehealth": 1.4},
        high_specificity=frozenset({"remote monitoring", "patient monitoring"}),
        deployment_sectors=frozenset({"Clinics", "Hospitals"}),
    ),
    "HealthTech Diagnostics": DomainSpec(
        name="HealthTech Diagnostics",
        specificity_rank=1,
        keywords={"diagnostic": 1.2, "diagnosis": 1.2, "detection": 0.8, "screening": 0.8, "wound": 1.4},
        phrases={"diabetic foot": 2.0, "medical imaging": 1.6, "early detection": 1.4},
        high_specificity=frozenset({"diabetic foot", "medical imaging"}),
        deployment_sectors=frozenset({"Clinics", "Hospitals"}),
    ),
    "Campus & Student Services": DomainSpec(
        name="Campus & Student Services",
        specificity_rank=2,
        keywords={"university": 1.0, "students": 0.8, "student": 0.8, "college": 1.0, "academic": 0.8},
        phrases={"hackathon": 1.6, "campus life": 1.4},
        high_specificity=frozenset({"hackathon"}),
        deployment_sectors=frozenset({"Campuses", "Universities"}),
    ),
    "Peer Collaboration Marketplaces": DomainSpec(
        name="Peer Collaboration Marketplaces",
        specificity_rank=2,
        keywords={"marketplace": 1.2, "teammates": 1.2, "collaboration": 0.8},
        phrases={"find teammates": 1.8, "team formation": 1.6},
        high_specificity=frozenset({"find teammates", "team formation"}),
        deployment_sectors=frozenset({"Campuses", "Universities"}),
    ),
    "EdTech": DomainSpec(
        name="EdTech",
        specificity_rank=3,
        keywords={"education": 1.2, "learning": 0.8, "course": 1.0, "curriculum": 1.2, "school": 1.0},
        phrases={},
        high_specificity=frozenset(),
        deployment_sectors=frozenset({"Campuses", "Universities"}),
    ),
    "Restaurant Operations Technology": DomainSpec(
        name="Restaurant Operations Technology",
        specificity_rank=2,
        keywords={"restaurant": 1.4, "restaurants": 1.8, "kitchen": 1.0, "menu": 0.8, "chef": 1.0},
        phrases={"point of sale": 1.4, "food waste": 1.6},
        high_specificity=frozenset({"food waste"}),
        deployment_sectors=frozenset({"Restaurants"}),
    ),
    "Food-Cost Management": DomainSpec(
        name="Food-Cost Management",
        specificity_rank=2,
        keywords={"inventory": 0.6, "cost": 0.5, "spoilage": 1.6},
        phrases={"food waste": 1.6, "food cost": 1.8},
        high_specificity=frozenset({"food cost", "spoilage"}),
        deployment_sectors=frozenset({"Restaurants"}),
    ),
    "Productivity Software": DomainSpec(
        name="Productivity Software",
        specificity_rank=4,
        keywords={"productivity": 1.4, "task": 0.8, "tasks": 0.8, "reminders": 1.2, "planning": 0.8},
        phrases={"to-do": 1.2, "time management": 1.4},
        high_specificity=frozenset(),
        deployment_sectors=frozenset({"Consumer Households"}),
    ),
    "General Consumer App": DomainSpec(
        name="General Consumer App",
        specificity_rank=9,
        keywords={"app": 0.3, "people": 0.3, "users": 0.3, "everyday": 0.5, "personal": 0.5},
        phrases={},
        high_specificity=frozenset(),
        deployment_sectors=frozenset({"Consumer Households"}),
    ),
}

DEPLOYMENT_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Campuses": ["campus", "campuses"],
    "Hotels": ["hotel", "hotels", "hospitality"],
    "Clinics": ["clinic", "clinics", "podiatry"],
    "Hospitals": ["hospital", "hospitals"],
    "Restaurants": ["restaurant", "restaurants", "kitchen"],
    "Universities": ["university", "universities", "college"],
    "Consumer Households": ["household", "households", "everyday", "personal use"],
}


def _normalize(text: str) -> str:
    # Hyphens are treated as word separators (e.g. "diabetic-foot" -> "diabetic foot") so a
    # taxonomy phrase written with a space still matches a hyphenated form in the source text.
    lowered = text.lower().replace("-", " ")
    return re.sub(r"[^a-z0-9\s]", " ", lowered)


def _find_matches(text_norm: str, vocab: dict[str, float]) -> dict[str, float]:
    """Return {matched_term: weight} for every distinct term in `vocab` found in `text_norm` —
    each term counts once regardless of how many times it repeats in the text, so a single
    generic word repeated several times can never masquerade as several matched concepts."""
    matches: dict[str, float] = {}
    for term, weight in vocab.items():
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, text_norm):
            matches[term] = weight
    return matches


def score_domain(text_norm: str, spec: DomainSpec) -> dict:
    """Score one domain against the normalized description text. Returns an explainability-ready
    record: matched terms (with weights) are always retained, whether or not the domain turns out
    to be an eligible candidate.
    """
    keyword_matches = _find_matches(text_norm, spec.keywords)
    phrase_matches = _find_matches(text_norm, spec.phrases)
    all_matches = {**keyword_matches, **phrase_matches}
    high_specificity_matches = {t: w for t, w in all_matches.items() if t in spec.high_specificity}

    distinct_concept_count = len(all_matches)
    eligible = distinct_concept_count >= MIN_DISTINCT_CONCEPTS or len(high_specificity_matches) >= 1

    max_weight = spec.max_weight() or 1.0
    weighted_score = round(sum(all_matches.values()) / max_weight, 6) if eligible else 0.0

    return {
        "domain": spec.name,
        "eligible": eligible,
        "weighted_score": weighted_score,
        "matched_concepts": sorted(all_matches.keys()),
        "high_specificity_matches": sorted(high_specificity_matches.keys()),
        "high_specificity_weight_sum": round(sum(high_specificity_matches.values()), 6),
        "distinct_concept_count": distinct_concept_count,
        "specificity_rank": spec.specificity_rank,
        "deployment_sectors": sorted(spec.deployment_sectors),
    }


def _rank_key(candidate: dict, matched_sectors: set[str]) -> tuple:
    """Deterministic tie-break, applied in this exact order (never dictionary insertion order):
    1. weighted taxonomy score (descending)
    2. count of high-specificity phrase matches, then their summed weight (descending)
    3. number of distinct matched concepts (descending)
    4. narrower-domain specificity rank (ascending — lower rank wins, i.e. more specific wins)
    5. deployment-sector agreement with the description's own extracted sectors (descending)
    6. stable alphabetical fallback on domain name (ascending)
    """
    sector_overlap = len(matched_sectors & set(candidate["deployment_sectors"]))
    return (
        -candidate["weighted_score"],
        -len(candidate["high_specificity_matches"]),
        -candidate["high_specificity_weight_sum"],
        -candidate["distinct_concept_count"],
        candidate["specificity_rank"],
        -sector_overlap,
        candidate["domain"],
    )


def extract_deployment_sectors(description: str) -> list[dict]:
    """Deterministic keyword-tag extraction (no Gemini involvement). Returns one record per
    matched sector with the exact matched text retained for explainability."""
    text_norm = _normalize(description)
    results = []
    for sector, keywords in DEPLOYMENT_SECTOR_KEYWORDS.items():
        matched = [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_norm)]
        if matched:
            results.append({"sector": sector, "matched_text": matched})
    return sorted(results, key=lambda r: r["sector"])


def score_taxonomy(description: str) -> dict:
    """Score every domain in the controlled taxonomy against `description` and rank the eligible
    candidates using the exact deterministic tie-break order in `_rank_key`. Returns every
    domain's raw score record (for explainability/debugging) plus the ranked list of eligible
    candidates only.
    """
    text_norm = _normalize(description)
    sectors = extract_deployment_sectors(description)
    matched_sector_names = {s["sector"] for s in sectors}

    all_scores = [score_domain(text_norm, spec) for spec in POSITIONING_TAXONOMY.values()]
    eligible = [c for c in all_scores if c["eligible"]]
    ranked = sorted(eligible, key=lambda c: _rank_key(c, matched_sector_names))

    return {
        "taxonomy_version": TAXONOMY_VERSION,
        "all_scores": all_scores,
        "candidates": ranked,
        "deployment_sectors": sectors,
    }


def describe_domain(spec: DomainSpec) -> str:
    """Deterministic, non-fabricated description: the domain's own top-weighted keywords/phrases,
    joined into a short sentence. Derived directly from the same vocabulary `score_domain` matches
    against, so it can never assert something the matcher itself doesn't actually look for.
    """
    combined = {**spec.keywords, **spec.phrases}
    top_terms = sorted(combined.items(), key=lambda kv: -kv[1])[:4]
    if not top_terms:
        return ""
    terms = ", ".join(term for term, _ in top_terms)
    return f"Ventures characterized by: {terms}."


def list_taxonomy_domains() -> list[dict]:
    """Every controlled-taxonomy domain as a plain, API-serializable record — the single source of
    truth backing `GET /api/v1/taxonomy`. Sorted alphabetically for a stable response ordering.
    """
    return [
        {
            "id": spec.name,
            "label": spec.name,
            "description": describe_domain(spec),
            "deployment_sectors": sorted(spec.deployment_sectors),
        }
        for spec in sorted(POSITIONING_TAXONOMY.values(), key=lambda s: s.name)
    ]


def taxonomy_is_ambiguous(candidates: list[dict]) -> bool:
    if not candidates:
        return True
    top = candidates[0]["weighted_score"]
    if top < CONFIDENCE_THRESHOLD:
        return True
    runner_up = candidates[1]["weighted_score"] if len(candidates) > 1 else 0.0
    return (top - runner_up) < AMBIGUITY_MARGIN
