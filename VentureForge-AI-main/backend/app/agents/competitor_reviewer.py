"""Best-effort, never-raising wrapper around the optional Gemini competitor-possibilities
reviewer (Phase B). Mirrors app.agents.positioning_reviewer's fallback philosophy exactly: returns
an empty list whenever no provider is configured, the call fails, times out, or returns something
that fails schema validation — app.agents.competitor_agent's deterministic fallback already leaves
`unverified_possibilities` empty in every one of these cases, so this never blocks or degrades the
rest of the competitor analysis.
"""

from __future__ import annotations

import logging

from app.ai.base import LLMUnavailable
from app.ai.factory import get_llm_provider
from app.ai.schemas import CompetitorPossibilitiesContext

logger = logging.getLogger(__name__)


def suggest_competitor_possibilities_safely(
    startup_description: str,
    model_category_label: str | None,
    venture_positioning_primary_domain: str | None,
) -> list[dict]:
    """Returns a list of plain dicts, each `{category, solution_type, reason, source}` — see
    app.ai.schemas.GeminiCompetitorPossibility. Every item returned here has already passed that
    schema's structural safety checks (no URLs/emails/corporate suffixes/likely brand names); an
    empty list means either no provider is configured, the call failed, or every candidate item
    Gemini returned failed validation — never a fabricated fallback.
    """
    provider = get_llm_provider()
    if provider is None:
        return []

    try:
        context = CompetitorPossibilitiesContext(
            startup_description=startup_description,
            model_category_label=model_category_label or "unknown",
            venture_positioning_primary_domain=venture_positioning_primary_domain,
        )
        result = provider.suggest_competitor_possibilities(context)
        return [p.model_dump() for p in result.possibilities]
    except LLMUnavailable as exc:
        logger.info("Gemini competitor-possibilities reviewer unavailable, falling back to empty: %s", exc)
        return []
    except Exception:
        logger.exception("Unexpected error calling the Gemini competitor-possibilities reviewer; falling back")
        return []
