"""Deterministic, taxonomy-keyed vocabulary and grammar helpers shared across every mentor-facing
text generator (app.agents.judge, app.agents.founder_guidance, app.agents.hypothesis_engine,
app.agents.mentor_synthesis, app.agents.judge_voice, app.agents.student3).

Product Intelligence Refinement Sprint, Critical Fix #4 (grammar) and #2/#5 (adaptive, diverse
recommendations): rather than duplicating an "a/an" check or a domain-vocabulary lookup in every
module that narrates a venture's category, both live here once. Category resolution is keyed
entirely off signals the pipeline already computes (`venture_positioning.primary_domain`,
`model_category.label`, `venture_positioning.deployment_sectors`) — no new classifier, no per-idea
special-casing, nothing invented about a specific venture.
"""

from __future__ import annotations

_VOWEL_SOUND_START = ("a", "e", "i", "o", "u")


def article_for(word: str) -> str:
    """Return "a" or "an" for the given word, judged by its first letter's sound. Good enough for
    the plain-English category/domain labels this product ever narrates (no silent-h or
    consonant-sounding-vowel edge cases occur in our controlled taxonomy)."""
    stripped = word.strip()
    return "an" if stripped and stripped[0].lower() in _VOWEL_SOUND_START else "a"


def with_article(word: str) -> str:
    """"industrials" -> "an industrials", "b2b" -> "a b2b", "Enterprise AI" -> "an Enterprise AI"."""
    return f"{article_for(word)} {word}"


# Acronyms/initialisms that should render upper-case even though the underlying taxonomy label is
# lower-case (e.g. the industry classifier emits "b2b", not "B2B").
_KNOWN_ACRONYMS = {"b2b", "b2c", "ai", "saas", "iot", "api"}


def readable_label(label: str) -> str:
    """Normalize a raw taxonomy/category label for inline prose: known acronyms render upper-case,
    everything else keeps its existing casing (multi-word taxonomy labels like "Restaurant
    Operations Technology" are already properly cased at the source and must not be re-cased)."""
    if not label:
        return label
    if label.lower() in _KNOWN_ACRONYMS:
        return label.upper()
    return label


# Coarse venture-category buckets, keyed by keyword/phrase tuples. See `resolve_category` below for
# how these are matched (Final AI Quality Sprint, Phase 2: staged, confidence-ranked resolution —
# the venture's own classified industry always outranks the free-text description; "b2b"/"consumer"
# are last-resort catch-alls). `startup_description` still matters because venture_positioning's
# primary_domain and model_category.label are both drawn from a fixed, coarse label set
# (b2b/consumer/fintech/healthcare/education/industrials) — without the founder's own raw
# description text, two very different businesses that both resolve to e.g. "b2b" (a cybersecurity
# pentesting tool and a canteen SaaS) would otherwise get byte-identical GTM/feature/competitor
# guidance. See the Product Intelligence Sprint audit that surfaced this.
_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "healthcare": ("health", "clinical", "patient", "medical", "diagnos", "telemedicine", "hospital", "pharma", "veterinar", "clinic", "biotech"),
    "insurance": ("insurtech", "insurance", "insurer", "underwriting", "claims process", "policyholder", "actuarial"),
    "fintech": ("fintech", "financ", "payment", "lending", "banking", "credit", "crypto", "custody"),
    "cybersecurity": ("cybersecurity", "cyber security", "penetration test", "pentest", "vulnerability", "threat detection", "security audit", "phishing", "malware", "ransomware", "social engineering", "security awareness", "security training"),
    "legaltech": ("legaltech", "legal tech", "contract review", "law firm", "litigation", "e-discovery", "paralegal"),
    "hrtech": ("hrtech", "hr tech", "recruiting", "applicant tracking", "payroll", "employee onboarding", "performance review", "talent management"),
    "proptech": ("proptech", "property management", "real estate", "leasing", "landlord", "tenant", "commercial real estate"),
    "retailtech": ("retailtech", "retail tech", "retail", "point of sale", "pos system", "inventory management", "e-commerce storefront", "e-commerce", "ecommerce", "merchandising", "subscription box", "online store"),
    "travel_hospitality": ("travel", "hospitality", "hotel", "booking engine", "itinerary", "vacation rental", "airline", "guest experience"),
    "govtech": ("govtech", "gov tech", "government agency", "public sector", "municipal", "citizen services", "permitting"),
    "climatetech": ("climatetech", "climate tech", "carbon", "emissions", "sustainability reporting", "renewable energy", "esg reporting", "cleantech"),
    "agriculture": ("agriculture", "agtech", "farm", "crop", "livestock", "precision farming"),
    "media": ("media", "publishing", "newsroom", "content licensing", "streaming platform", "advertising network"),
    "gaming": ("gaming", "game studio", "esports", "in-game", "game engine", "player retention"),
    "arvr": ("augmented reality", "virtual reality", "ar/vr", "mixed reality", "vr headset", "spatial computing"),
    "creator_economy": ("creator economy", "influencer", "content creator", "fan subscription", "monetize content", "newsletter platform"),
    "foodtech": ("restaurant", "canteen", "food waste", "meal kit", "meal-kit", "kitchen", "food service", "food-cost"),
    "logistics": ("logistics", "last-mile", "last mile", "freight", "fleet", "shipping route", "delivery rout", "supply chain"),
    "marketplace": ("marketplace", "two-sided", "connecting", "peer-to-peer", "p2p"),
    "hardware": ("hardware", "robot", "drone", "device", "sensor", "manufactur", "industrial", "iot", "construction tech", "space tech", "energy grid"),
    "developer_tools": ("developer", "api", "infrastructure", "devtools", "sdk", "ci/cd", "code review", "kubernetes", "ai agent"),
    "education": ("education", "edtech", "student", "campus", "classroom", "school"),
    "consumer": ("consumer",),
    "b2b": ("b2b", "enterprise"),
}

# A generic, never-fabricated vocabulary substitution per bucket — every value is a category-level
# word choice (the kind of pilot, the kind of buyer), never a claim about a specific venture.
_VOCAB: dict[str, dict[str, str]] = {
    "healthcare": {
        "pilot_noun": "a clinical pilot", "buyer_noun": "a clinical champion",
        "validation_frame": "a supervised clinical pilot",
    },
    "fintech": {
        "pilot_noun": "a compliance-reviewed pilot", "buyer_noun": "a design partner",
        "validation_frame": "a small, regulation-aware pilot",
    },
    "hardware": {
        "pilot_noun": "a field trial", "buyer_noun": "a pilot site",
        "validation_frame": "a physical field test",
    },
    "cybersecurity": {
        "pilot_noun": "a scoped security assessment pilot", "buyer_noun": "a security lead or CTO",
        "validation_frame": "one scoped engagement with a real environment",
    },
    "foodtech": {
        "pilot_noun": "a single-kitchen/site pilot", "buyer_noun": "a kitchen or operations manager",
        "validation_frame": "a single-location trial",
    },
    "logistics": {
        "pilot_noun": "a single-route or single-hub pilot", "buyer_noun": "an operations or fleet manager",
        "validation_frame": "a small, measurable route/hub trial",
    },
    "marketplace": {
        "pilot_noun": "a two-sided pilot (supply and demand both present)", "buyer_noun": "a supply-side and a demand-side partner",
        "validation_frame": "a small closed marketplace test",
    },
    "developer_tools": {
        "pilot_noun": "a design-partner integration", "buyer_noun": "a design partner",
        "validation_frame": "a real integration with one engineering team",
    },
    "education": {
        "pilot_noun": "a classroom pilot", "buyer_noun": "one teacher or program lead",
        "validation_frame": "a single classroom or cohort pilot",
    },
    "consumer": {
        "pilot_noun": "an early-adopter test group", "buyer_noun": "an early-adopter group",
        "validation_frame": "a small early-adopter cohort",
    },
    "b2b": {
        "pilot_noun": "a design-partner pilot", "buyer_noun": "a design partner",
        "validation_frame": "one paying design partner",
    },
    "insurance": {
        "pilot_noun": "a scoped underwriting/claims pilot", "buyer_noun": "an underwriting or claims lead",
        "validation_frame": "one book-of-business segment reviewed alongside compliance",
    },
    "legaltech": {
        "pilot_noun": "a single-matter pilot", "buyer_noun": "a practicing attorney or general counsel",
        "validation_frame": "one real matter or contract workflow",
    },
    "hrtech": {
        "pilot_noun": "a single-department HR pilot", "buyer_noun": "an HR or people-ops lead",
        "validation_frame": "one hiring cycle or employee cohort",
    },
    "proptech": {
        "pilot_noun": "a single-property pilot", "buyer_noun": "a property or facilities manager",
        "validation_frame": "one building or portfolio segment",
    },
    "retailtech": {
        "pilot_noun": "a single-store pilot", "buyer_noun": "a store or merchandising manager",
        "validation_frame": "one store location or SKU category",
    },
    "travel_hospitality": {
        "pilot_noun": "a single-property or single-route pilot", "buyer_noun": "a property or operations manager",
        "validation_frame": "one property, route, or booking season",
    },
    "govtech": {
        "pilot_noun": "a single-agency pilot", "buyer_noun": "an agency program lead",
        "validation_frame": "one agency or department procurement cycle",
    },
    "climatetech": {
        "pilot_noun": "a single-site measurement pilot", "buyer_noun": "a sustainability or operations lead",
        "validation_frame": "one facility or reporting cycle",
    },
    "agriculture": {
        "pilot_noun": "a single-farm field trial", "buyer_noun": "a farm operator or agronomist",
        "validation_frame": "one growing season on one field",
    },
    "media": {
        "pilot_noun": "a single-title or single-channel pilot", "buyer_noun": "an editorial or content operations lead",
        "validation_frame": "one publication or content channel",
    },
    "gaming": {
        "pilot_noun": "a limited player-cohort playtest", "buyer_noun": "a studio producer or live-ops lead",
        "validation_frame": "one playtest cohort or soft-launch region",
    },
    "arvr": {
        "pilot_noun": "a hardware-constrained field pilot", "buyer_noun": "an early-adopter user or device partner",
        "validation_frame": "one supported device and use-case pairing",
    },
    "creator_economy": {
        "pilot_noun": "a small creator cohort pilot", "buyer_noun": "an individual creator",
        "validation_frame": "a handful of creators testing real monetization",
    },
}

_DEFAULT_VOCAB = {"pilot_noun": "a pilot", "buyer_noun": "a pilot customer", "validation_frame": "one real pilot"}


def all_resolvable_categories() -> list[str]:
    """Every category `resolve_category` can ever return, including the "generic" fallback — used
    by the Master Startup Knowledge Base Sprint's Phase 1/7 coverage audit to measure real category
    coverage against the full taxonomy, not a guessed count."""
    return sorted(list(_CATEGORY_KEYWORDS.keys()) + ["generic"])


# These two buckets match trivially against their own name ("b2b" contains "b2b") and are meant as
# last-resort catch-alls, never a real signal to rank against specific categories — see
# `resolve_category`'s staged resolution below (Final AI Quality Sprint, Phase 2).
_CATCH_ALL_CATEGORIES = ("b2b", "consumer")
_SPECIFIC_CATEGORY_KEYWORDS = {k: v for k, v in _CATEGORY_KEYWORDS.items() if k not in _CATCH_ALL_CATEGORIES}
_CATCH_ALL_CATEGORY_KEYWORDS = {k: v for k, v in _CATEGORY_KEYWORDS.items() if k in _CATCH_ALL_CATEGORIES}


def _normalize_haystack(text: str) -> str:
    # Hyphens treated as word separators, e.g. "security-awareness" matches a keyword written as
    # "security awareness" — the founder's own phrasing shouldn't have to match a keyword's exact
    # punctuation. (Several keyword tuples below still list both a hyphenated and spaced form of
    # the same phrase, e.g. logistics' "last-mile"/"last mile" — a pre-existing workaround for this
    # same gap, kept as-is since either form still matches correctly after this normalization.)
    return text.lower().replace("-", " ")


def _best_matching_category(haystack: str, keyword_table: dict[str, tuple[str, ...]]) -> str | None:
    """The category with the most distinct keyword hits in `haystack` — confidence-ranked, not
    first-dict-entry-wins. Ties broken by `keyword_table`'s own iteration order (deterministic,
    since dicts preserve insertion order), matching the old first-match behavior only when no
    category has more matches than another."""
    best_category: str | None = None
    best_count = 0
    for category, keywords in keyword_table.items():
        count = sum(1 for kw in keywords if kw.replace("-", " ") in haystack)
        if count > best_count:
            best_category, best_count = category, count
    return best_category


def resolve_category(
    primary_domain: str | None,
    model_category_label: str | None,
    deployment_sectors: list[str] | None = None,
    startup_description: str | None = None,
) -> str:
    """Final AI Quality Sprint, Phase 2 fix: the pre-submission audit found a cybersecurity startup
    whose own description happened to mention "healthcare customers" get Healthcare knowledge-pack
    advice instead of Cybersecurity — because the old implementation scanned one combined haystack
    (classified industry + raw founder description) and returned the FIRST dict-ordered category
    with any match at all, so an incidental customer-vertical mention could out-rank the venture's
    actual, already-classified industry.

    Resolution is now staged, classified signal first:
      1. Score every SPECIFIC category (never the generic "b2b"/"consumer" catch-alls) against only
         `primary_domain` + `deployment_sectors` — the venture's own already-resolved, specific
         taxonomy identity (e.g. "Sustainability Technology", "Clinical Decision Support"), never
         `model_category_label` or the free-text description. If anything matches here, that
         already-classified signal wins outright.
         `model_category_label` is deliberately EXCLUDED from this stage even though it is also a
         "classified" signal: it is the raw industry classifier's coarse fallback label set
         (b2b/consumer/fintech/healthcare/education/industrials), and one of those coarse labels —
         "industrials" — substring-matches the hardware category's "industrial" keyword. Letting
         that alone win here regression-tested as a real bug: a ClimateTech pitch ("carbon-
         accounting software... emissions... sustainability disclosures" for "industrials"-labeled
         manufacturers) was pulled into the hardware knowledge pack before the description's far
         more specific "carbon"/"emissions" signal ever got a chance to be counted. Folding
         `model_category_label` into stage 2 instead means it still contributes real signal, but
         only by the same confidence-ranked, most-matches-wins rule as the description — never as
         an outright override.
      2. Only if stage 1 matched nothing does `model_category_label` and the founder's own
         description get folded in, resolved by which category has the MOST matched keywords
         (confidence ranking) across the combined text, not whichever appears first in the dict.
      3. Only if nothing specific matched at all does resolution fall back to the generic "b2b"/
         "consumer" catch-alls, still checked against the full haystack.
    """
    classified_haystack = _normalize_haystack(
        " ".join(filter(None, [primary_domain, " ".join(deployment_sectors or [])]))
    )
    category = _best_matching_category(classified_haystack, _SPECIFIC_CATEGORY_KEYWORDS)
    if category is not None:
        return category

    full_haystack = _normalize_haystack(
        " ".join(
            filter(None, [primary_domain, model_category_label, " ".join(deployment_sectors or []), startup_description])
        )
    )
    category = _best_matching_category(full_haystack, _SPECIFIC_CATEGORY_KEYWORDS)
    if category is not None:
        return category

    category = _best_matching_category(full_haystack, _CATCH_ALL_CATEGORY_KEYWORDS)
    return category or "generic"


def vocab_for(
    primary_domain: str | None,
    model_category_label: str | None,
    deployment_sectors: list[str] | None = None,
    startup_description: str | None = None,
) -> dict[str, str]:
    category = resolve_category(primary_domain, model_category_label, deployment_sectors, startup_description)
    return dict(_VOCAB.get(category, _DEFAULT_VOCAB))
