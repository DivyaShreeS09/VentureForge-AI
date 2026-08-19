"""Best-effort, never-raising wrapper around the optional Gemini positioning reviewer (Phase
0.5). Mirrors app.agents.orchestrator._try_llm_narrative's fallback philosophy: returns None
whenever no provider is configured, the call fails, times out, or returns something that fails
schema validation — every one of those is a normal, expected outcome, not an error that should
affect the deterministic taxonomy resolution in app.agents.venture_positioning.
"""

from __future__ import annotations

import logging

from app.ai.base import LLMUnavailable
from app.ai.factory import get_llm_provider
from app.ai.schemas import GeminiPositioningRecommendation, PositioningReviewContext

logger = logging.getLogger(__name__)


def review_positioning_safely(
    startup_description: str,
    model_category: dict | None,
    taxonomy_candidate_domains: list[str],
) -> GeminiPositioningRecommendation | None:
    provider = get_llm_provider()
    if provider is None:
        return None

    try:
        context = PositioningReviewContext(
            startup_description=startup_description,
            model_category_label=(model_category or {}).get("label", "unknown"),
            model_category_confidence=(model_category or {}).get("confidence", 0.0),
            model_category_is_uncertain=(model_category or {}).get("is_uncertain", True),
            taxonomy_candidate_domains=taxonomy_candidate_domains,
        )
        return provider.review_positioning(context)
    except LLMUnavailable as exc:
        logger.info("Gemini positioning reviewer unavailable, falling back to taxonomy-only: %s", exc)
        return None
    except Exception:
        # Same intentional bare-except rationale as _try_llm_narrative: this layer is additive and
        # optional by design and must never take down the deterministic pipeline.
        logger.exception("Unexpected error calling the Gemini positioning reviewer; falling back")
        return None
