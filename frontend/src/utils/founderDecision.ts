import type { MentorInterpretation, MentorValidationAction, Student3RankedAction } from "../types/api";

export type FounderDecisionLabel = "Should Build" | "Proceed Carefully" | "Needs Validation" | "High Risk";

export interface FounderDecision {
  label: FounderDecisionLabel;
  reason: string;
  detail: string[];
}

/** Derives one of four founder-facing recommendations from data the backend has already computed
 * (mentor_verdict.readiness_level + founder_guidance_items) — a presentation-only synthesis, never
 * a new prediction or score. The underlying readiness_level/guidance items are unchanged; this only
 * picks which of 4 labels best summarizes them at a glance, and is always paired with the exact
 * reasoning (never a bare label) per the Founder Decision Panel requirement. */
export function deriveFounderDecision(mentor: MentorInterpretation): FounderDecision {
  const { readiness_level, concise_verdict, strongest_signal, biggest_risk, immediate_priority } = mentor.mentor_verdict;
  const confirmedRisks = mentor.founder_guidance_items.filter((i) => i.category === "confirmed_risk");

  const detail = [strongest_signal, biggest_risk, immediate_priority];

  if (confirmedRisks.length > 0) {
    return {
      label: "High Risk",
      reason: `${confirmedRisks[0].title} ${confirmedRisks[0].why_it_matters}`,
      detail,
    };
  }
  if (readiness_level === "ready") {
    return { label: "Should Build", reason: concise_verdict, detail };
  }
  if (readiness_level === "developing") {
    return { label: "Proceed Carefully", reason: `${concise_verdict} ${immediate_priority}`, detail };
  }
  return { label: "Needs Validation", reason: `${concise_verdict} ${immediate_priority}`, detail };
}

export interface RoadmapTask {
  task: string;
  priority: number;
  effort: string;
  outcome: string;
  dependencies: string;
}

export interface RoadmapBuckets {
  firstWeek: RoadmapTask[];
  firstMonth: RoadmapTask[];
  next90Days: RoadmapTask[];
}

function effortFromParticipants(participants: string): string {
  if (participants.startsWith("N/A")) return "Low — internal only, no outside conversations needed";
  return `Low — ${participants}`;
}

function actionToTask(action: MentorValidationAction): RoadmapTask {
  return {
    task: action.method,
    priority: action.priority,
    effort: effortFromParticipants(action.target_participants),
    outcome: action.success_criterion,
    dependencies: action.build_dependency,
  };
}

function rankedActionToTask(action: Student3RankedAction, priority: number): RoadmapTask {
  return {
    task: action.title,
    priority,
    effort: `${action.effort} — ${action.dependency}`,
    outcome: `Impact: ${action.impact}. ${action.evidence_basis[0] ?? ""}`.trim(),
    dependencies: action.dependency,
  };
}

/** Reorganizes the existing `validation_plan` + `roadmap_30_60_90` (both already computed
 * deterministically — see backend/app/agents/mentor_synthesis.py) into the founder-facing
 * First Week / First Month / Next 90 Days buckets Phase 4 asks for. This is a pure client-side
 * regrouping — no new backend field, no changed priority order, no new task invented.
 *
 * `rankedActions` (Phase 5 / Student 3, optional) contributes at most one additional First Week
 * task — its single highest-priority, "now"-urgency action — deduped by title against what's
 * already in First Week so the same recommendation is never shown twice. */
export function buildRoadmapBuckets(mentor: MentorInterpretation, rankedActions: Student3RankedAction[] = []): RoadmapBuckets {
  const plan = mentor.validation_plan;
  const firstWeek = plan.slice(0, 2).map(actionToTask);
  const restOfValidation = plan.slice(2).map(actionToTask);

  const firstWeekTitles = new Set(firstWeek.map((t) => t.task));
  const topRankedAction = rankedActions.find((a) => a.urgency === "now" && !firstWeekTitles.has(a.title));
  if (topRankedAction) {
    firstWeek.push(rankedActionToTask(topRankedAction, firstWeek.length + 1));
  }

  const day1to30 = mentor.roadmap_30_60_90.find((p) => p.period === "days_1_30");
  const validationMethods = new Set(plan.map((a) => a.method));
  const day1to30Extras = (day1to30?.activities ?? [])
    .filter((activity) => !validationMethods.has(activity))
    .map((activity, idx) => ({
      task: activity,
      priority: restOfValidation.length + idx + 1,
      effort: "Medium — requires some build or setup time",
      outcome: day1to30?.focus ?? "Validate before building further.",
      dependencies: "Depends on Days 1-30 validation resolving first.",
    }));
  const firstMonth = [...restOfValidation, ...day1to30Extras];

  const laterPeriods = mentor.roadmap_30_60_90.filter((p) => p.period !== "days_1_30");
  const next90Days = laterPeriods.flatMap((period, periodIdx) =>
    period.activities.map((activity, idx) => ({
      task: activity,
      priority: periodIdx * 10 + idx + 1,
      effort: period.period === "days_31_60" ? "Medium — a real build effort" : "High — execution and measurement",
      outcome: period.focus,
      dependencies: period.rationale,
    })),
  );

  return { firstWeek, firstMonth, next90Days };
}

export interface ValidationDisplayItem extends MentorValidationAction {
  failure_signal: string;
  estimated_time: string;
  expected_learning: string;
}

function estimatedTimeFor(participants: string): string {
  if (participants.startsWith("N/A (secondary")) return "A few hours of research";
  if (participants.startsWith("N/A (internal")) return "A short internal review";
  return "1-2 weeks to reach and hear back from enough people";
}

/** Adds `failure_signal`/`estimated_time`/`expected_learning` to the existing `validation_plan`
 * (see backend/app/agents/mentor_synthesis.py._build_validation_plan) — a client-side presentation
 * enrichment only; every underlying question/method/participants/success_criterion is unchanged. */
export function buildValidationDisplay(plan: MentorValidationAction[]): ValidationDisplayItem[] {
  return plan.map((item) => ({
    ...item,
    failure_signal: `No clear evidence toward "${item.success_criterion}" after genuinely trying — treat that as a real signal, not bad luck.`,
    estimated_time: estimatedTimeFor(item.target_participants),
    expected_learning: `Whether ${item.source_gap.replace(/_/g, " ")} actually holds for a real buyer, not just an assumption.`,
  }));
}
