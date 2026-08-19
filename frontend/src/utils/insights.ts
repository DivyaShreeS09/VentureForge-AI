import type { Analysis, MentorInterpretation } from "../types/api";

export type InsightStatus = "critical" | "developing" | "strong";

export interface Insight {
  id: string;
  title: string;
  status: InsightStatus;
  why: string;
  evidence?: string;
  investorConcern?: string;
  recommendation?: string;
  definitionOfDone?: string;
  timeline?: string;
}

const LEVEL_SCORE: Record<string, number> = { low: 1, medium: 2, high: 3 };

/** The single source of truth for every recurring fact on the Reveal page (biggest risk, biggest
 * strength, immediate priority, each founder mission). Every section (Executive Command Center,
 * Executive Dashboard, Mission Control, Investor Review) reads from this array and links to an
 * insight by `id` instead of independently deriving or re-wording the same sentence — the fix for
 * "the same insight explained three different ways in three different scenes" found in the live
 * Phase 0 read of the previous sprint's Reveal page. Every field here is a direct pass-through of
 * an existing backend value; nothing is fabricated or newly computed beyond picking which already-
 * existing field is the richest source for a given slot (identical to the logic
 * `RiskScene.tsx`/`ExecutiveDashboard.tsx` already used — consolidated here so it exists in
 * exactly one place). */
export function buildInsights(analysis: Analysis, mentor: MentorInterpretation): Insight[] {
  const insights: Insight[] = [];

  const strategicRisks = analysis.strategic_opportunity?.strategic_risks ?? [];
  const confirmedRisk = mentor.founder_guidance_items.find((item) => item.category === "confirmed_risk");
  const topStrategicRisk = [...strategicRisks].sort(
    (a, b) => LEVEL_SCORE[b.likelihood] * LEVEL_SCORE[b.impact] - LEVEL_SCORE[a.likelihood] * LEVEL_SCORE[a.impact],
  )[0];
  const topInvestorRow = mentor.founder_report?.investor_view[0];
  const topDecision = mentor.founder_report?.founder_strategy[0];

  insights.push({
    id: "insight-biggest-risk",
    title: "Biggest Risk",
    status: "critical",
    why: mentor.mentor_verdict.biggest_risk,
    evidence: confirmedRisk?.why_it_matters ?? topStrategicRisk?.why,
    investorConcern: topInvestorRow?.investor_concern.content,
    recommendation: confirmedRisk?.next_step ?? topStrategicRisk?.mitigation,
    definitionOfDone: topDecision?.definition_of_done.content,
    timeline: topDecision?.estimated_duration,
  });

  insights.push({
    id: "insight-biggest-strength",
    title: "Biggest Strength",
    status: "strong",
    why: mentor.mentor_verdict.strongest_signal,
  });

  insights.push({
    id: "insight-immediate-priority",
    title: "Immediate Next Step",
    status: "developing",
    why: mentor.mentor_verdict.immediate_priority,
  });

  if (mentor.founder_report) {
    for (const mission of mentor.founder_report.founder_strategy.slice(0, 3)) {
      insights.push({
        id: `insight-mission-${mission.priority}`,
        title: mission.action.content,
        status: mission.impact === "High" ? "critical" : mission.impact === "Low" ? "strong" : "developing",
        why: mission.reason.content,
        definitionOfDone: mission.definition_of_done.content,
        timeline: mission.estimated_duration,
      });
    }
  }

  return insights;
}

export function findInsight(insights: Insight[], id: string): Insight | undefined {
  return insights.find((i) => i.id === id);
}
