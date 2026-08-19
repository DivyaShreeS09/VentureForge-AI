import type { Analysis, MentorInterpretation, Student3RankedAction, VenturePositioning } from "../../types/api";
import { CollapsedScene } from "./CollapsedScene";
import { UnderstandingScene } from "./scenes/UnderstandingScene";
import { OpportunityScene } from "./scenes/OpportunityScene";
import { FirstThirtyDaysScene } from "./scenes/FirstThirtyDaysScene";
import { BiggerPictureScene } from "./scenes/BiggerPictureScene";
import { FounderReportScene } from "./scenes/FounderReportScene";
import { DeepEvidenceScene } from "./scenes/DeepEvidenceScene";
import { InsightDetailCard } from "./InsightDetailCard";
import { findInsight, type Insight } from "../../utils/insights";

interface Props {
  effective: Analysis;
  mentor: MentorInterpretation;
  positioning: VenturePositioning | null;
  insights: Insight[];
  rankedActions: Student3RankedAction[];
  onCorrected: (updated: Analysis) => void;
  onSaved: (updated: Analysis) => void;
}

/** Section 5 of 5 — the one and only "Why?" section. Everything that isn't above-the-fold
 * decision-making detail lives here, collapsed by default, so it never competes with the four
 * decision-focused sections above it — but nothing is deleted, only reorganized. Consolidates
 * what used to be five separate collapsed accordions (Full Verdict / What We Understood /
 * Primary Opportunity / Risk Detail / Bigger Picture / Full Founder Report / Deep Evidence) into
 * one, since Absolute Rule 2 wants exactly 5 visible top-level sections. The literal duplicate
 * sentences that used to live in `VerdictScene`/`RiskScene` (biggest risk, strongest signal,
 * immediate priority — all already stated in full in the Executive Command Center) were deleted
 * outright rather than kept in a second, merely-hidden copy; the one genuinely new piece of depth
 * for the biggest risk (evidence/investor concern/recommendation/timeline) is shown here exactly
 * once via `InsightDetailCard`. */
export function DeepAnalysis({ effective, mentor, positioning, insights, rankedActions, onCorrected, onSaved }: Props) {
  const biggestRisk = findInsight(insights, "insight-biggest-risk");

  return (
    <CollapsedScene eyebrow="Deep Analysis" summary="Full methodology, evidence, and the complete report — for anyone who wants the proof.">
      <div className="space-y-16">
        <UnderstandingScene
          analysisId={effective.id}
          mentor={mentor}
          positioning={positioning}
          onCorrected={onCorrected}
        />

        {effective.strategic_opportunity && (
          <OpportunityScene opportunity={effective.strategic_opportunity.primary_opportunity} />
        )}

        {biggestRisk && (
          <div>
            <p className="text-forge-1 uppercase tracking-[0.25em] text-forge-text-secondary">Risk — full detail</p>
            <div className="mt-4">
              <InsightDetailCard insight={biggestRisk} />
            </div>
          </div>
        )}

        {/* The full near-term validation plan (every task, not just Mission Control's top 3) —
            a fuller zoom level of the same plan, not a second copy of the same 3 sentences. */}
        <FirstThirtyDaysScene mentor={mentor} rankedActions={rankedActions} />

        <BiggerPictureScene
          analysisId={effective.id}
          ideaExpansion={effective.idea_expansion ?? null}
          strategicOpportunity={effective.strategic_opportunity ?? null}
          competitorAnalysis={effective.competitor_analysis}
          marketIntelligence={effective.market_intelligence}
          businessModel={effective.business_model}
          revenueEstimate={effective.revenue_estimate}
          growthStrategy={effective.student3_outputs?.growth_strategy ?? []}
          onSaved={onSaved}
        />

        {mentor.founder_report && <FounderReportScene report={mentor.founder_report} />}

        <DeepEvidenceScene analysis={effective} />
      </div>
    </CollapsedScene>
  );
}
