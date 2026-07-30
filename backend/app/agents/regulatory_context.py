"""Deterministic regulatory / responsible-use context classifier.

Product Intelligence Refinement Sprint, Critical Fix #1 (context-aware mentor judgment). Recognizes
when a venture touches a regulated industry or a sensitive practice — healthcare, insurance,
consumer finance, activity that reads as legal advice, minors combined with sensitive data
collection, biometric/surveillance/privacy-sensitive data, safety-critical physical systems, or
dual-use technology — using only keyword/taxonomy signals already available (the founder's own
submitted description, plus `venture_positioning.primary_domain`/`deployment_sectors` already
resolved elsewhere in the pipeline). No new agent, model, or endpoint; no ML; no per-idea
special-casing — every match is a category-level keyword rule, and every note is a fixed,
versioned template.

This module never rejects or moralizes about an idea. It surfaces exactly one adaptive caveat (the
single most consequential category that matched, not a stacked checklist) so the mentor
demonstrates judgment, not censorship — see the sprint's own worked examples (healthcare,
insurance, privacy) which this module's templates follow directly.
"""

from __future__ import annotations

import re

REGULATORY_CONTEXT_VERSION = "v1"

# Ordered most-to-least consequential — only the first category that matches is returned.
_CATEGORY_ORDER = (
    "children_and_consent",
    "safety_critical",
    "healthcare",
    "insurance",
    "finance",
    "legal",
    "surveillance_and_privacy",
    "dual_use",
)

_MINOR_KEYWORDS = ("child", "children", "kid ", "kids", "teen", "teens", "teenager", "teenagers", "minor", "minors")
_SENSITIVE_DATA_KEYWORDS = (
    "biometric", "facial recognition", "emotion recognition", "emotion", "mental health",
    "depression", "anxiety", "surveillance", "monitor", "tracking", "track ", "location data",
    "camera", "sensor data", "without consent", "consent",
)
_SAFETY_KEYWORDS = (
    "autonomous vehicle", "self-driving", "surgical robot", "medical device", "life support",
    "life-support", "aircraft", "aviation", "flight control", "industrial robot", "heavy machinery",
    "drone swarm",
)
_HEALTHCARE_DOMAINS = frozenset({"Clinical Decision Support", "Remote Patient Monitoring", "HealthTech Diagnostics"})
_HEALTHCARE_KEYWORDS = (
    "patient", "clinical", "diagnos", "medical", "health condition", "therapy", "treatment",
    "telehealth", "telemedicine", "hospital", "clinician", "pharma", "drug ",
)
_INSURANCE_KEYWORDS = ("insurance", "insurer", "underwrit", "policyholder")
_FINANCE_KEYWORDS = (
    "lending", "loan", "credit score", "bank account", "brokerage", "securities", "investment advice",
    "wage advance", "payroll advance", "money transmi", "stablecoin", "crypto exchange",
)
_LEGAL_KEYWORDS = ("legal advice", "attorney", "law firm", "contract review", "unauthorized practice of law")
_SURVEILLANCE_KEYWORDS = (
    "surveillance", "facial recognition", "biometric", "location tracking", "personal data",
    "without consent", "emotion recognition",
)
_DUAL_USE_KEYWORDS = ("military", "weapon", "defense contractor", "export control", "dual-use", "classified")

_NOTES: dict[str, dict[str, str]] = {
    "children_and_consent": {
        "headline": "This involves collecting sensitive data about minors.",
        "note": (
            "Consider how minors and their guardians will meaningfully understand and consent to "
            "that collection, not just check a box — that consent design is worth working out before "
            "you scale, not after."
        ),
        "mitigation": "Design an explicit, guardian-involved consent flow before collecting any sensitive data from minors.",
        "likelihood": "high", "impact": "high",
    },
    "safety_critical": {
        "headline": "This operates in a safety-critical environment.",
        "note": (
            "Where software or hardware operates near people or in safety-critical settings, "
            "real-world testing and safety validation usually become a major milestone before broad "
            "deployment."
        ),
        "mitigation": "Scope your first pilot around supervised, controlled conditions and build out a safety validation plan alongside the product.",
        "likelihood": "high", "impact": "high",
    },
    "healthcare": {
        "headline": "This operates in a regulated healthcare context.",
        "note": "Clinical validation and regulatory requirements will likely become a major milestone before you can deploy this broadly.",
        "mitigation": "Get clarity on the applicable regulatory pathway before scaling beyond a clinician-reviewed pilot.",
        "likelihood": "high", "impact": "high",
    },
    "insurance": {
        "headline": "This operates in a regulated industry.",
        "note": "Before scaling, verify the licensing and compliance requirements in every market you plan to operate in.",
        "mitigation": "Confirm licensing requirements with a regulatory or legal advisor before you sign your first customer.",
        "likelihood": "high", "impact": "high",
    },
    "finance": {
        "headline": "This handles money on someone else's behalf.",
        "note": "That usually means real regulatory obligations — before scaling, verify what licensing (money transmission, lending, or securities rules) applies to you.",
        "mitigation": "Confirm which financial-services licensing applies to your specific flow of funds before scaling.",
        "likelihood": "high", "impact": "medium",
    },
    "legal": {
        "headline": "This reads as offering legal advice.",
        "note": "That usually triggers unauthorized-practice-of-law rules in many places — worth getting real legal guidance on how to frame this before you scale.",
        "mitigation": "Have a licensed attorney review how the product is framed and marketed before broad release.",
        "likelihood": "medium", "impact": "high",
    },
    "surveillance_and_privacy": {
        "headline": "This concept involves personal data.",
        "note": "Consider how users will understand and consent to its collection — that's worth designing deliberately, not as an afterthought.",
        "mitigation": "Write a plain-language explanation of what's collected and why, and put real consent in front of users before collection starts.",
        "likelihood": "medium", "impact": "medium",
    },
    "dual_use": {
        "headline": "This kind of capability can have both civilian and restricted uses.",
        "note": "Worth understanding what export-control or security-review requirements might apply before you scale distribution.",
        "mitigation": "Check export-control and end-use restrictions relevant to your jurisdiction before scaling distribution.",
        "likelihood": "medium", "impact": "medium",
    },
}


_NEGATION_CUES = ("not ", "n't ", "without offering", "does not", "no longer", "isn't", "never offer")
_NEGATION_WINDOW = 28


def _matches(haystack: str, keywords: tuple[str, ...]) -> bool:
    """True if any keyword appears in `haystack` *and* isn't immediately negated (e.g. "explicitly
    not offering legal advice" must never fire the legal-advice caveat) — a founder who explicitly
    disclaims a sensitive practice deserves to not be flagged for it. A generic negation-window
    check, not a per-idea exception: it applies to every keyword in every category the same way.

    Single-word keywords (no space) require a real word-start boundary (`\\b`) immediately before
    the keyword — not a bare substring — found via the Founder Intelligence sprint's Moat
    Intelligence check, which reused this classifier and surfaced a genuine false positive:
    "canteens" contains "teen"/"teens" as a substring, incorrectly triggering the children-and-
    consent category for ordinary cafeteria/food-service startups. The boundary is checked only on
    the LEADING edge, deliberately not both sides: this still matches intended plural/inflected
    forms the original substring design relied on elsewhere (e.g. "loan" matching "loans", "teen"
    matching "teenager"/"teenagers") while rejecting a match embedded inside a larger word (a
    genuine word boundary can never occur between two letters, so "teen" inside "can|teen|s" is
    correctly rejected — "can" and "teen" are both letters with no boundary between them). Multi-
    word phrases (e.g. "kid ", "without consent") are left as plain substring matches — they're
    already specific enough not to collide with unrelated words.
    """
    for kw in keywords:
        if " " not in kw.strip():
            match = re.search(rf"\b{re.escape(kw.strip())}", haystack)
            start = match.start() if match else -1
        else:
            start = haystack.find(kw)
        if start == -1:
            continue
        window_start = max(0, start - _NEGATION_WINDOW)
        preceding = haystack[window_start:start]
        if not any(cue in preceding for cue in _NEGATION_CUES):
            return True
    return False


def classify_regulatory_context(
    startup_description: str, primary_domain: str | None, deployment_sectors: list[str] | None = None
) -> dict | None:
    """Return the single most consequential regulatory/responsible-use category this venture
    touches, or None if nothing matches. See module docstring for why only one category is ever
    returned."""
    text = (startup_description or "").lower()
    domain_text = " ".join(filter(None, [primary_domain, " ".join(deployment_sectors or [])])).lower()
    haystack = f"{text} {domain_text}"

    matched: set[str] = set()
    if _matches(text, _MINOR_KEYWORDS) and _matches(text, _SENSITIVE_DATA_KEYWORDS):
        matched.add("children_and_consent")
    if _matches(haystack, _SAFETY_KEYWORDS):
        matched.add("safety_critical")
    if (primary_domain in _HEALTHCARE_DOMAINS) or _matches(haystack, _HEALTHCARE_KEYWORDS):
        matched.add("healthcare")
    if _matches(haystack, _INSURANCE_KEYWORDS):
        matched.add("insurance")
    if _matches(haystack, _FINANCE_KEYWORDS):
        matched.add("finance")
    if _matches(haystack, _LEGAL_KEYWORDS):
        matched.add("legal")
    if _matches(haystack, _SURVEILLANCE_KEYWORDS):
        matched.add("surveillance_and_privacy")
    if _matches(haystack, _DUAL_USE_KEYWORDS):
        matched.add("dual_use")

    for category in _CATEGORY_ORDER:
        if category in matched:
            spec = _NOTES[category]
            return {"category": category, **spec}
    return None
