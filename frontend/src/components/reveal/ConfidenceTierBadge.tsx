import type { IdeaConfidenceTier } from "../../types/api";

const TIER_LABEL: Record<IdeaConfidenceTier, string> = {
  confirmed_from_evidence: "From your evidence",
  reasonable_hypothesis: "Reasonable hypothesis",
  speculative_future_opportunity: "Speculative — future",
};

/** One quiet, honest confidence-tier label — reused wherever the Reveal surfaces a suggestion
 * that isn't a settled fact (Bigger Picture, Opportunity, Risk). Text only, no color-coded chip
 * system — the Reveal's visual language reserves color for the copper accent alone. */
export function ConfidenceTierBadge({ tier }: { tier: IdeaConfidenceTier }) {
  return <span className="text-forge-1 uppercase tracking-[0.08em] text-forge-text-secondary">{TIER_LABEL[tier]}</span>;
}
