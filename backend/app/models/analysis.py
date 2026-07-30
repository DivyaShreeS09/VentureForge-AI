import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.database.types import JSONVariant, UUIDType


class Analysis(Base):
    """One full orchestrator run for a startup: industry prediction, funding readiness, and the
    Judge Agent's synthesis of both. See docs/ARCHITECTURE.md for the orchestration flow.
    """

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    startup_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("startups.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")

    # Act IV (The Forging) live-progress fields — written incrementally by the background
    # analysis thread after every real orchestrator node completes (see
    # app.services.analysis_service._execute_analysis_stream), not just once at the end. Both
    # null until the first node of a run has completed; both stay at their last real value once
    # status reaches COMPLETED/FAILED (never cleared, so a late page load still shows where the
    # run finished). `current_stage` is `app.agents.stage_labels.stage_label_for(current_node)`.
    current_node: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_stage: Mapped[str | None] = mapped_column(Text, nullable=True)

    industry_model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry_prediction: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    funding_rubric_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    funding_assessment: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    # Student 2 outputs — see docs/ARCHITECTURE.md "Student 2 extension" and each producing
    # module's docstring for schema/versioning/source-attribution details.
    success_model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_prediction: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    revenue_engine_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_estimate: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    market_intelligence: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    competitor_analysis: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    customer_personas: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    business_model: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    judge_summary: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    workflow_trace: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase C: auditable history of founder-initiated venture-positioning corrections — see
    # app.services.analysis_service.apply_industry_correction. Each entry records the previous
    # positioning, the override applied, the taxonomy version active at the time, and a
    # timestamp. Never mutated in place — only appended to.
    positioning_correction_history: Mapped[list | None] = mapped_column(JSONVariant, nullable=True, default=list)

    # Production-hardening phase: auditable history of founder-initiated revenue-assumption edits
    # — see app.services.analysis_service.apply_revenue_assumptions_update. Each entry records the
    # previous and updated assumption dicts, which fields changed, and a timestamp. Never mutated
    # in place — only appended to, exactly like positioning_correction_history above.
    revenue_assumptions_history: Mapped[list | None] = mapped_column(JSONVariant, nullable=True, default=list)

    # Full Mentor Orchestration phase — see app.agents.mentor_synthesis/mentor_reviewer. One
    # coherent MentorInterpretation dict per run; null only for a run whose judge node itself
    # failed, or a pre-existing analysis persisted before this phase.
    mentor_interpretation: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    # Phase 2: Idea Expansion — see app.agents.idea_expansion/idea_expansion_reviewer. One
    # additive, tiered set of alternative-segment/adjacent-industry/feature/pricing/pivot/
    # partnership/go-to-market possibilities per run; null only for a run whose mentor synthesis
    # itself did not run, or a pre-existing analysis persisted before this phase.
    idea_expansion: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    # Phase 3: Strategic Opportunity Discovery — see
    # app.agents.strategic_opportunity/strategic_opportunity_reviewer. One primary_opportunity +
    # adjacent_opportunities + future_expansion + strategic_risks per run; null only for a run
    # whose mentor synthesis itself did not run, or a pre-existing analysis persisted before this
    # phase.
    strategic_opportunity: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    # Phase 5: Student 3 growth/strategy intelligence — see app.agents.student3. Deterministic
    # customer-segment fallback, ranked next actions, innovation opportunities, planning risks,
    # growth strategy, and pitch-deck outline. Additive; null for a pre-Phase-5 analysis or one
    # whose funding_readiness node itself failed upstream.
    student3_outputs: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
