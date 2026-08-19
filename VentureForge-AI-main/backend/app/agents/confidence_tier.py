"""The one shared source of truth for the three-tier epistemic-provenance vocabulary used by
`app.agents.idea_expansion` and `app.agents.strategic_opportunity` (and mirrored, for Gemini's own
schema-bounded output, by `app.ai.schemas.GeminiIdeaConfidenceTier`/`GeminiStrategicConfidenceTier`).

This is deliberately a categorical tag, not a number — see `app.agents.confidence_engine`'s own
module docstring for why "recommendation certainty / epistemic tier" is kept structurally distinct
from the Confidence Engine's [0, 1] evidence-confidence values. Before this module existed, both
`idea_expansion.py` and `strategic_opportunity.py` independently declared identical
`CONFIRMED`/`HYPOTHESIS` string literals (and `idea_expansion.py` additionally used the
`SPECULATIVE` value as an inline literal rather than a named constant) — consolidated here so the
three tier values are defined in exactly one place.

  - `CONFIRMED`: derived directly from this venture's own already-computed deterministic data.
    Reserved for fully deterministic modules only — Gemini's own schema-bounded output can never
    claim this tier (see `app.ai.schemas`, which has no enum value for it).
  - `HYPOTHESIS`: a well-known general pattern applied to this venture's domain, not asserted as a
    fact about the company itself.
  - `SPECULATIVE`: a five-year-horizon or otherwise unconfirmed future possibility.
"""

from __future__ import annotations

CONFIRMED = "confirmed_from_evidence"
HYPOTHESIS = "reasonable_hypothesis"
SPECULATIVE = "speculative_future_opportunity"
