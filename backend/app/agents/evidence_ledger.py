"""Evidence Ledger — the shared reasoning foundation (VentureForge Intelligence Architecture,
implementation Phase A).

A single, typed, additive data structure recording every fact the pipeline currently treats as
"evidence" for a venture, tagged with where it came from and how much it should be trusted. This
does not replace or change any existing scoring (`funding_readiness.py`'s rubric, `judge.py`'s
`confidence_level`) — it is a new, additive lens over data those modules already compute, built so
future phases (Hypothesis Set, Contradiction Detection, Decision Synthesis) have one shared,
auditable structure to read from instead of each inventing its own local notion of "confidence."

As of Phase D, the actual confidence *math* (`SOURCE_TYPE_BASE_CONFIDENCE`, `MODEL_INFERENCE_DISCOUNT`,
`combine_confidence`) lives in `app.agents.confidence_engine` — the one canonical confidence engine
for the whole pipeline — and is imported back in here so every existing caller of this module
(`app.agents.venture_frame`, `app.agents.hypothesis_set`, `app.agents.judge`) keeps working
unchanged. This module now owns only the *evidence-item bookkeeping* (what counts as an item, how
one is built from the rubric/market evidence/industry prediction), not the confidence arithmetic
itself. `EVIDENCE_LEDGER_VERSION` is bumped whenever this module's item-building logic changes;
`confidence_engine.CONFIDENCE_ENGINE_VERSION` is bumped whenever the confidence math itself changes
— the two are versioned independently since they can now change for different reasons.
"""

from __future__ import annotations

from typing import TypedDict

from app.agents.confidence_engine import (
    MODEL_INFERENCE_DISCOUNT,
    SOURCE_TYPE_BASE_CONFIDENCE,
    combine_confidence,
)

EVIDENCE_LEDGER_VERSION = "v1"


class EvidenceItem(TypedDict):
    id: str
    claim: str
    dimension: str | None
    source_type: str
    base_confidence: float
    evidence_state: str | None
    # Populated by a future phase (Contradiction Detection) — always [] today. The field exists now
    # so that phase can extend existing items rather than inventing a second, parallel structure.
    contradicts: list[str]


def _rubric_evidence_items(funding_assessment: dict | None) -> list[EvidenceItem]:
    """One evidence item per applicable funding-readiness dimension. `not_applicable` dimensions
    (and any entry with no recognized state) contribute no item — an opt-out is not evidence of
    anything, positive or negative."""
    items: list[EvidenceItem] = []
    for entry in (funding_assessment or {}).get("breakdown", []):
        state = entry.get("state")
        if state in ("confirmed_positive", "confirmed_negative"):
            source_type = "user_confirmed"
        elif state == "not_sure_yet":
            source_type = "user_not_sure"
        else:
            continue
        items.append(
            {
                "id": f"rubric:{entry['dimension']}",
                "claim": f"{entry['label']}: {entry['scale_description']}",
                "dimension": entry["dimension"],
                "source_type": source_type,
                "base_confidence": SOURCE_TYPE_BASE_CONFIDENCE[source_type],
                "evidence_state": state,
                "contradicts": [],
            }
        )
    return items


_MARKET_EVIDENCE_CLAIMS: dict[str, str] = {
    "customer_type": "Founder-stated buyer/user: {value}",
    "target_market": "Founder-stated target market: {value}",
    "startup_stage": "Founder-stated venture stage: {value}",
    "geography": "Founder-stated geography: {value}",
}


def _market_evidence_items(market_evidence: dict | None) -> list[EvidenceItem]:
    """One user_confirmed item per non-empty founder-supplied market-evidence field. A field the
    founder left blank contributes no item (silence is not evidence), matching the same principle
    `not_applicable` follows for rubric dimensions above."""
    items: list[EvidenceItem] = []
    for field, template in _MARKET_EVIDENCE_CLAIMS.items():
        value = (market_evidence or {}).get(field)
        if not value:
            continue
        items.append(
            {
                "id": f"market_evidence:{field}",
                "claim": template.format(value=value),
                "dimension": None,
                "source_type": "user_confirmed",
                "base_confidence": SOURCE_TYPE_BASE_CONFIDENCE["user_confirmed"],
                "evidence_state": "confirmed_positive",
                "contradicts": [],
            }
        )
    known_competitors = (market_evidence or {}).get("known_competitors") or []
    if known_competitors:
        items.append(
            {
                "id": "market_evidence:known_competitors",
                "claim": f"Founder-named {len(known_competitors)} known competitor(s)/alternative(s).",
                "dimension": None,
                "source_type": "user_confirmed",
                "base_confidence": SOURCE_TYPE_BASE_CONFIDENCE["user_confirmed"],
                "evidence_state": "confirmed_positive",
                "contradicts": [],
            }
        )
    return items


def _industry_prediction_item(industry_prediction: dict | None) -> EvidenceItem | None:
    if not industry_prediction:
        return None
    reported_confidence = float(industry_prediction.get("confidence") or 0.0)
    discounted = round(reported_confidence * MODEL_INFERENCE_DISCOUNT, 4)
    predicted = industry_prediction.get("predicted_industry", "unknown")
    return {
        "id": "model:industry_prediction",
        "claim": f"Industry classifier predicted '{predicted}' (model-reported confidence {reported_confidence:.2f}).",
        "dimension": None,
        "source_type": "model_inference",
        "base_confidence": discounted,
        "evidence_state": None,
        "contradicts": [],
    }


def build_evidence_ledger(
    funding_assessment: dict | None,
    market_evidence: dict | None = None,
    industry_prediction: dict | None = None,
) -> list[EvidenceItem]:
    """Assemble the full Evidence Ledger for one analysis run from data the pipeline already
    computes upstream. Purely additive and read-only with respect to its inputs: nothing produced
    by `app.ml.funding_readiness`, `app.agents.venture_positioning`, or the industry classifier is
    changed by calling this."""
    items = _rubric_evidence_items(funding_assessment)
    items.extend(_market_evidence_items(market_evidence))
    industry_item = _industry_prediction_item(industry_prediction)
    if industry_item is not None:
        items.append(industry_item)
    return items


def confidence_for_dimension(items: list[EvidenceItem], dimension: str) -> float:
    """Combined confidence for every evidence item tied to one specific rubric dimension. Returns
    0.0 if no evidence item exists for that dimension (an honest "unknown," never fabricated)."""
    matching = [item for item in items if item["dimension"] == dimension]
    return combine_confidence(matching)


def summarize_ledger(items: list[EvidenceItem]) -> dict:
    """A small, honest summary of the ledger — never a replacement for `judge.py`'s existing
    `confidence_level`, which stays exactly as-is for backward compatibility. This is a new,
    additive lens: how much of this analysis actually rests on direct founder confirmation versus
    open questions versus inference, plus one overall combined-confidence number computed by the
    disclosed formula above rather than a hardcoded three-bucket rule."""
    by_source_type: dict[str, int] = {}
    for item in items:
        by_source_type[item["source_type"]] = by_source_type.get(item["source_type"], 0) + 1
    return {
        "evidence_ledger_version": EVIDENCE_LEDGER_VERSION,
        "total_items": len(items),
        "items_by_source_type": by_source_type,
        "overall_confidence": combine_confidence(items),
    }
