import { Fragment, type ReactNode } from "react";

// The fixed business-keyword vocabulary that should never render as plain white inside a
// paragraph. Each word maps to the semantic color-priority bucket it belongs to (see the
// typography color system): critical/risk words in rose, high-priority/action words in gold-
// orange, funding/market/metric words in gold, positive/validated words in emerald, and AI-
// insight/generic-business-noun words in cyan (the catch-all "this is worth noticing" tone).
const WORD_TONE: Record<string, string> = {
  // Critical / risk
  risk: "text-forge-rose",
  problem: "text-forge-rose",
  weakness: "text-forge-rose",
  critical: "text-forge-rose",
  concern: "text-forge-rose",
  threat: "text-forge-rose",
  obstacle: "text-forge-rose",
  missing: "text-forge-rose",
  // High priority / action
  important: "text-forge-accent-secondary",
  immediate: "text-forge-accent-secondary",
  focus: "text-forge-accent-secondary",
  action: "text-forge-accent-secondary",
  improve: "text-forge-accent-secondary",
  required: "text-forge-accent-secondary",
  // Funding / market / metrics
  funding: "text-forge-gold",
  revenue: "text-forge-gold",
  growth: "text-forge-gold",
  opportunity: "text-forge-gold",
  market: "text-forge-gold",
  competition: "text-forge-gold",
  investors: "text-forge-gold",
  investor: "text-forge-gold",
  pricing: "text-forge-gold",
  profit: "text-forge-gold",
  // Positive / validated
  strength: "text-forge-emerald",
  advantage: "text-forge-emerald",
  validated: "text-forge-emerald",
  ready: "text-forge-emerald",
  strong: "text-forge-emerald",
  success: "text-forge-emerald",
  // AI insight / generic business terms
  traction: "text-forge-cyan",
  validation: "text-forge-cyan",
  customers: "text-forge-cyan",
  customer: "text-forge-cyan",
  team: "text-forge-cyan",
  product: "text-forge-cyan",
  execution: "text-forge-cyan",
  strategy: "text-forge-cyan",
  evidence: "text-forge-cyan",
  mvp: "text-forge-cyan",
  ai: "text-forge-cyan",
  startup: "text-forge-cyan",
};

const KEYWORD_PATTERN = new RegExp(`\\b(${Object.keys(WORD_TONE).join("|")})\\b`, "gi");

/** Splits `text` on the fixed keyword vocabulary and wraps each match in its semantic color-
 * priority tone (see `WORD_TONE`) — returns plain text unchanged (as a single string) when no
 * keyword is present, so callers can use this unconditionally on any paragraph without a "does it
 * need highlighting?" check of their own. Never mutates casing — renders exactly what the source
 * text contains. */
export function highlightKeywords(text: string): ReactNode {
  // A single capturing group means `split` alternates [text, match, text, match, ..., text] —
  // every odd index is guaranteed to be a keyword match, so no separate `.test()` call is needed
  // (calling `.test()` on this same global-flagged regex in a loop would itself be buggy, since
  // `test()` advances the regex's own `lastIndex` between calls).
  const parts = text.split(KEYWORD_PATTERN);
  if (parts.length === 1) return text;
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <span key={i} className={`font-medium ${WORD_TONE[part.toLowerCase()] ?? "text-forge-cyan"}`}>
        {part}
      </span>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  );
}
