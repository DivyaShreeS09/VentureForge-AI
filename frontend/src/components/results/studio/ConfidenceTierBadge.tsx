import type { IdeaConfidenceTier } from "../../../types/api";

const TIER_STYLE: Record<IdeaConfidenceTier, { label: string; className: string }> = {
  confirmed_from_evidence: {
    label: "Already part of your analysis",
    className: "border-success-500/30 bg-success-500/10 text-success-400",
  },
  reasonable_hypothesis: {
    label: "Reasonable hypothesis",
    className: "border-signal-500/30 bg-signal-500/10 text-signal-400",
  },
  speculative_future_opportunity: {
    label: "Speculative — future opportunity",
    className: "border-warning-500/30 bg-warning-500/10 text-warning-400",
  },
};

/** Shared confidence-tier chip used across the founder journey (Market Expansion, Risk
 * Dashboard) — one visual vocabulary for "how sure are we" everywhere it appears. */
export function ConfidenceTierBadge({ tier }: { tier: IdeaConfidenceTier }) {
  const style = TIER_STYLE[tier];
  return (
    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] ${style.className}`}>
      {style.label}
    </span>
  );
}
