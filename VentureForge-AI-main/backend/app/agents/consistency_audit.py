"""Intelligence Consistency Audit (Master Product Differentiation Sprint, Phase 9; extended in the
Startup Domain Intelligence Sprint with unsupported-claim/contradiction checks and a stricter
5-category reclassification).

Runs AFTER the founder report is fully assembled — audits the finished output, never generates new
founder-facing content itself. Five real, computable checks, each with a concrete, disclosed method
(never a vague "looks fine"):

1. Every tagged item carries a valid category (evidence/inference/ai_recommendation/
   market_assumption/experiment_suggestion) — enforced today by app.agents.founder_report._tag's
   assertion at construction time, re-verified here defensively over the assembled dict so a
   future change to that module can't silently regress this guarantee.
2. Near-duplicate text across different sections — the same technique app.agents.mentor_synthesis
   already uses for its founder-description contradiction check (significant-word overlap), applied
   pairwise across every tagged sentence in the report, flagging genuine repeats (not shared common
   words) as a real signal of copy-paste-style duplication.
3. Generic-boilerplate detection — a fixed list of phrases that read as filler regardless of
   venture (e.g. "this could improve your product") flagged if they appear verbatim anywhere in the
   report, so this module doubles as this project's own regression check against generic output.
4. Unsupported-claim detection: any item NOT tagged "evidence" that contains a standalone
   number/percentage/currency figure is flagged for review — a specific figure presented as
   inference/recommendation/assumption reads as more authoritative than its actual evidentiary
   basis, which is exactly the kind of overclaiming this project's five-category tagging exists to
   prevent.
5. A stricter 5-category reclassification (Evidence / Inference / Recommendation / Experiment /
   Unknown) mapped from the existing 5 tags, plus the percentage breakdown this sprint's Phase 1
   knowledge audit also reports — `market_assumption` maps to `Unknown` in this stricter view since,
   by this project's own definition, it is an unconfirmed assumption, not a reasoned inference.
"""

from __future__ import annotations

import re

_VALID_CATEGORIES = {"evidence", "inference", "ai_recommendation", "market_assumption", "experiment_suggestion"}

# Maps this project's existing 5-tag system onto the stricter Evidence/Inference/Recommendation/
# Experiment/Unknown taxonomy this sprint asks for — a relabeling for a stricter audit lens, not a
# second competing tag system (every tagged item still carries only its one original category).
_STRICT_CATEGORY_MAP = {
    "evidence": "Evidence",
    "inference": "Inference",
    "ai_recommendation": "Recommendation",
    "experiment_suggestion": "Experiment",
    "market_assumption": "Unknown",
}

# Deliberately narrow: a bare small integer ("5 people", "week 4", "2-4 weeks") is almost always a
# process/step count in an instruction, not a claim about the world, and flagging it produced
# nothing but noise when this was first tried against a real report. What actually indicates
# false precision or an unstated statistic is: a decimal figure (implies more precision than a
# disclosed heuristic should claim), a percentage, a currency amount, or a number >= 1000.
_NUMBER_PATTERN = re.compile(r"(?<![\w.])(\$\s?\d[\d,]*\.?\d*|\d[\d,]*\.\d+|\d+%|\d{4,})(?![\w.])")

_STOPWORDS = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "that", "this", "at", "your", "you", "is", "are", "it", "be", "as", "not", "yet"}

# Duplicate-flag threshold: two sentences sharing this fraction of their significant words (by the
# smaller sentence's word count) are flagged. Kept high enough that ordinary shared domain
# vocabulary (e.g. two sentences both mentioning "pricing") never trips it.
_DUPLICATE_OVERLAP_THRESHOLD = 0.85
_MIN_WORDS_FOR_DUPLICATE_CHECK = 5

_GENERIC_PHRASES = [
    "this could improve your product",
    "consider adding more features",
    "you should validate your idea",
    "talk to your customers",
    "this is a good opportunity",
    "the market is large",
]


def _significant_words(text: str) -> set[str]:
    return {w.strip(".,!?;:\"'").lower() for w in text.split() if len(w) > 3 and w.lower() not in _STOPWORDS}


def _collect_tagged_items(node, path: str, items: list[tuple[str, dict]]) -> None:
    if isinstance(node, dict):
        if set(node.keys()) >= {"content", "category"} and isinstance(node.get("content"), str):
            items.append((path, node))
            return
        for key, value in node.items():
            _collect_tagged_items(value, f"{path}.{key}", items)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _collect_tagged_items(value, f"{path}[{i}]", items)


def audit_founder_report(founder_report: dict) -> dict:
    """Audits an already-assembled founder_report dict (app.agents.founder_report.build_founder_report's
    output). Returns a report describing what was checked and what, if anything, was found —
    attached to the output as metadata, never used to silently drop or rewrite content."""
    tagged_items: list[tuple[str, dict]] = []
    _collect_tagged_items(founder_report, "founder_report", tagged_items)

    invalid_category_paths = [path for path, item in tagged_items if item.get("category") not in _VALID_CATEGORIES]

    duplicate_pairs: list[dict] = []
    seen: list[tuple[str, str, set[str]]] = []
    for path, item in tagged_items:
        content = item.get("content", "")
        words = _significant_words(content)
        if len(words) < _MIN_WORDS_FOR_DUPLICATE_CHECK:
            continue
        for other_path, other_content, other_words in seen:
            if not words or not other_words:
                continue
            overlap = len(words & other_words) / min(len(words), len(other_words))
            if overlap >= _DUPLICATE_OVERLAP_THRESHOLD and content != other_content:
                duplicate_pairs.append({"path_a": other_path, "path_b": path, "overlap": round(overlap, 2)})
            elif overlap >= _DUPLICATE_OVERLAP_THRESHOLD and content == other_content:
                duplicate_pairs.append({"path_a": other_path, "path_b": path, "overlap": 1.0, "exact_duplicate": True})
        seen.append((path, content, words))

    generic_hits = []
    for path, item in tagged_items:
        content_lower = item.get("content", "").lower()
        for phrase in _GENERIC_PHRASES:
            if phrase in content_lower:
                generic_hits.append({"path": path, "phrase": phrase})

    unsupported_claims = []
    for path, item in tagged_items:
        category = item.get("category")
        if category == "evidence":
            continue
        content = item.get("content", "")
        numbers = _NUMBER_PATTERN.findall(content)
        if numbers:
            unsupported_claims.append(
                {
                    "path": path,
                    "category": category,
                    "numbers_found": numbers,
                    "reason": (
                        f"Tagged '{category}' (not 'evidence') but contains a specific figure "
                        f"({', '.join(numbers)}) — a number reads as more authoritative than its "
                        "tagged evidentiary status supports; verify this is a disclosed heuristic/"
                        "range, not an implied hard fact."
                    ),
                }
            )

    # Contradiction check: two tagged items sharing most of their significant words but disagreeing
    # on a simple negation cue (one asserts something, the other denies the same thing) — a real,
    # narrow signal, not a broad semantic-consistency claim this heuristic can't actually make.
    _NEGATION_CUES = (" not ", " no ", " doesn't ", " don't ", " isn't ", " never ", "n't exist", "not yet")
    contradictions = []
    for i, (path_a, content_a, words_a) in enumerate(seen):
        for path_b, content_b, words_b in seen[i + 1 :]:
            if not words_a or not words_b:
                continue
            overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
            if overlap < 0.5 or content_a == content_b:
                continue
            has_negation_a = any(cue in f" {content_a.lower()} " for cue in _NEGATION_CUES)
            has_negation_b = any(cue in f" {content_b.lower()} " for cue in _NEGATION_CUES)
            if has_negation_a != has_negation_b:
                contradictions.append({"path_a": path_a, "path_b": path_b, "overlap": round(overlap, 2)})

    strict_category_counts: dict[str, int] = {}
    for _, item in tagged_items:
        strict = _STRICT_CATEGORY_MAP.get(item.get("category"), "Unknown")
        strict_category_counts[strict] = strict_category_counts.get(strict, 0) + 1
    total = len(tagged_items) or 1
    strict_category_percentages = {k: round(v / total * 100, 1) for k, v in strict_category_counts.items()}

    return {
        "consistency_audit_version": "v2",
        "n_tagged_items_checked": len(tagged_items),
        "invalid_category_tags": invalid_category_paths,
        "duplicate_or_near_duplicate_pairs": duplicate_pairs,
        "generic_boilerplate_hits": generic_hits,
        "unsupported_claims": unsupported_claims,
        "possible_contradictions": contradictions,
        "strict_category_breakdown": strict_category_counts,
        "strict_category_percentages": strict_category_percentages,
        "passed": not any([invalid_category_paths, duplicate_pairs, generic_hits, unsupported_claims, contradictions]),
        "method": (
            "Category validity: checked against the 5 allowed tags. Duplication: pairwise "
            f"significant-word overlap >= {_DUPLICATE_OVERLAP_THRESHOLD:.0%} between any two tagged "
            "sentences. Genericness: exact match against a fixed list of filler phrases. "
            "Unsupported claims: any non-'evidence'-tagged item containing a standalone number/"
            "percentage/currency figure. Contradictions: item pairs with >=50% significant-word "
            "overlap but a differing negation cue. Category breakdown: the existing 5 tags "
            "relabeled onto Evidence/Inference/Recommendation/Experiment/Unknown. This audit runs "
            "over the assembled report only — it never generates or rewrites content."
        ),
    }
