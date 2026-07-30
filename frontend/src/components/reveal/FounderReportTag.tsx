import type { FounderReportCategory } from "../../types/api";

const CATEGORY_LABEL: Record<FounderReportCategory, string> = {
  evidence: "Evidence",
  inference: "Inference",
  ai_recommendation: "AI Recommendation",
  market_assumption: "Market Assumption",
  experiment_suggestion: "Experiment Suggestion",
};

// Question/Answer/Evidence/Assumption styling — each of the report's five provenance tags now
// reads as a distinct visual category instead of one uniform gray label: evidence (cyan, the same
// "AI insight" tone used elsewhere), inference (a plain, neutral "answer" reading — heading white,
// not colored, since it's a derived fact, not evidence or a recommendation), assumption (orange,
// italicized — it's explicitly the least certain category), recommendation/suggestion (emerald —
// this is advice to act on, a positive-framed nudge).
const CATEGORY_CLASS: Record<FounderReportCategory, string> = {
  evidence: "text-forge-cyan",
  inference: "text-forge-heading",
  ai_recommendation: "text-forge-emerald",
  market_assumption: "italic text-forge-gold",
  experiment_suggestion: "text-forge-emerald",
};

/** Product Intelligence Sprint, Phase 7: every sentence in the Founder Report is mandatorily
 * tagged with exactly one of five categories server-side (backend/app/agents/founder_report.py) —
 * this is the one place that label becomes visible. */
export function FounderReportTag({ category }: { category: FounderReportCategory }) {
  return (
    <span className={`text-forge-1 whitespace-nowrap font-medium uppercase tracking-[0.08em] ${CATEGORY_CLASS[category]}`}>
      {CATEGORY_LABEL[category]}
    </span>
  );
}
