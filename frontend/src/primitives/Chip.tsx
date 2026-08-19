import type { ForgeSemanticState } from "../tokens/forge";

export interface ChipProps {
  state: ForgeSemanticState;
  label: string;
}

const stateStyles: Record<ForgeSemanticState, { dot: string; text: string }> = {
  confirmed: { dot: "bg-forge-confirmed", text: "text-forge-confirmed" },
  notSureYet: { dot: "bg-forge-notsure", text: "text-forge-notsure" },
  risk: { dot: "bg-forge-risk", text: "text-forge-risk" },
};

// Design System Bible §7 — small dot + word, never a filled background. Color lives in
// the dot and the text only, so a chip never competes visually with the one
// accent-filled button on screen (Design Bible §11), and color is never the sole
// carrier of meaning (§13 — the word is always present alongside the color).
export function Chip({ state, label }: ChipProps) {
  const { dot, text } = stateStyles[state];
  return (
    <span className="inline-flex items-center gap-2 rounded-forge-sm px-2 py-1 text-forge-1">
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${dot}`} />
      <span className={text}>{label}</span>
    </span>
  );
}
