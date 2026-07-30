import type { EvidenceState, FundingAnswers } from "../../types/api";

export interface EvidenceOption {
  state: EvidenceState;
  severity: 1 | 2 | null;
  label: string;
}

export interface EvidenceDimension {
  key: keyof FundingAnswers;
  question: string;
  tip: string;
  /** Shown instead of `tip` only in Advanced mode — reserved for the one dimension (market
   * sizing) whose plain-language tip and precise/jargon tip genuinely differ (Founder Input
   * Experience Redesign, task 6: TAM/SAM/SOM never appears in Beginner mode). Every other
   * dimension's `tip` is already plain language and needs no Advanced variant. */
  tipAdvanced?: string;
  options: EvidenceOption[];
  /** A brief, honest acknowledgment shown only when the founder's already-chosen `currentStage`
   * (collected in Discovery, Sprint 4) makes a "no evidence yet" answer to this question entirely
   * expected — never a judgment, never shown as a reason to change the answer. `null` when no
   * stage makes this question particularly less or more expected than any other. */
  stageNote?: (stage: string) => string | null;
}

const EARLY_STAGES = new Set(["Just an idea", "Validating"]);

/** Mentor-conversation order: understand the problem, then who has it, then what's been built,
 * then whether anyone's pulling on it, then the business model, then market size, then the team,
 * then the competitive landscape — each question builds on the last rather than the old
 * accordion's arbitrary list order. Same 8 dimensions `backend/app/ml/funding_readiness.py`
 * scores, same 3 evidence-quality options per dimension — only the sequencing and presentation
 * are new this sprint. */
export const EVIDENCE_DIMENSIONS: EvidenceDimension[] = [
  {
    key: "problem_clarity",
    question: "Can you state the problem in one clear sentence?",
    tip: "Who has this problem, and what does it cost them today?",
    options: [
      { state: "confirmed_negative", severity: null, label: "Not yet — still fuzzy" },
      { state: "confirmed_positive", severity: 1, label: "Roughly, but it's broad" },
      { state: "confirmed_positive", severity: 2, label: "Yes — specific and well-defined" },
    ],
  },
  {
    key: "customer_pain_evidence",
    question: "How do you know this pain is real for them?",
    tip: "Interviews, surveys, or support tickets count as real evidence — a hunch doesn't yet.",
    options: [
      { state: "confirmed_negative", severity: null, label: "No evidence yet — it's a hypothesis" },
      { state: "confirmed_positive", severity: 1, label: "Anecdotal — a few conversations" },
      { state: "confirmed_positive", severity: 2, label: "Documented — interviews or real data" },
    ],
    stageNote: (stage) =>
      EARLY_STAGES.has(stage)
        ? "Totally normal to still be gathering this at this stage — it's the next thing worth doing, not a mark against the idea."
        : null,
  },
  {
    key: "product_maturity",
    question: "What can someone actually try today?",
    tip: "A live prototype counts even if it's rough — a plan on paper doesn't yet.",
    options: [
      { state: "confirmed_negative", severity: null, label: "Idea only — nothing built yet" },
      { state: "confirmed_positive", severity: 1, label: "A prototype or MVP" },
      { state: "confirmed_positive", severity: 2, label: "A live product with real users" },
    ],
  },
  {
    key: "traction",
    question: "Is anyone actually using or paying for it yet?",
    tip: "Real usage, not projected usage — pilots and paying customers both count.",
    options: [
      { state: "confirmed_negative", severity: null, label: "No users or customers yet" },
      { state: "confirmed_positive", severity: 1, label: "Early pilot users" },
      { state: "confirmed_positive", severity: 2, label: "Paying customers or recurring usage" },
    ],
    stageNote: (stage) =>
      EARLY_STAGES.has(stage)
        ? "Most founders at this stage don't have traction yet — that's expected, not a red flag."
        : null,
  },
  {
    key: "revenue_model_clarity",
    question: "How will this actually make money?",
    tip: "Pricing and unit economics — not just \"we'll figure it out later.\"",
    options: [
      { state: "confirmed_negative", severity: null, label: "Not defined yet" },
      { state: "confirmed_positive", severity: 1, label: "Roughly defined" },
      { state: "confirmed_positive", severity: 2, label: "Clear pricing and unit economics" },
    ],
    stageNote: (stage) =>
      EARLY_STAGES.has(stage) ? "Perfectly fine to still be working this out this early." : null,
  },
  {
    key: "market_size_evidence",
    question: "How big is the opportunity, and how do you know?",
    tip: "A real source beats a guessed billion-dollar figure — even a rough, well-reasoned estimate counts.",
    tipAdvanced: "A sourced TAM/SAM/SOM estimate scores highest — a guessed billion-dollar figure doesn't.",
    options: [
      { state: "confirmed_negative", severity: null, label: "No sizing yet" },
      { state: "confirmed_positive", severity: 1, label: "A rough estimate" },
      { state: "confirmed_positive", severity: 2, label: "A sourced TAM/SAM/SOM estimate" },
    ],
  },
  {
    key: "team_completeness",
    question: "Does your team cover what this venture needs to build and sell it?",
    tip: "Be honest about gaps — this shapes what to prioritize next, not a pass/fail grade.",
    options: [
      { state: "confirmed_negative", severity: null, label: "Solo, missing key skills" },
      { state: "confirmed_positive", severity: 1, label: "Partial coverage" },
      { state: "confirmed_positive", severity: 2, label: "Founding team covers the core skills" },
    ],
  },
  {
    key: "competitive_differentiation",
    question: "What makes you different from the closest alternatives?",
    tip: "Name the 2-3 closest alternatives and what genuinely sets you apart.",
    options: [
      { state: "confirmed_negative", severity: null, label: "Not stated yet" },
      { state: "confirmed_positive", severity: 1, label: "Some differentiation" },
      { state: "confirmed_positive", severity: 2, label: "Clear, defensible differentiation" },
    ],
  },
];

/** Shared alongside every dimension's 3 evidence-quality options — never inferred from silence
 * (Build Contract: honest uncertainty). Kept identical in meaning to the pre-Sprint-5 accordion's
 * "Not sure yet"/"Not applicable" buttons, just voiced in first person for the conversation. */
export const SKIP_OPTIONS: EvidenceOption[] = [
  { state: "not_sure_yet", severity: null, label: "I'm not sure yet" },
  { state: "not_applicable", severity: null, label: "Not applicable to my venture" },
];

const ACKNOWLEDGMENTS: Record<EvidenceState, (severity: number | null) => string> = {
  confirmed_positive: (severity) =>
    severity === 2 ? "That's strong evidence — noted." : "Good — that's a real starting point.",
  confirmed_negative: () => "Noted — that's a clear next step to work on, not a flaw in the idea.",
  not_sure_yet: () => "Fair enough — I'll treat that as something worth exploring, not a weakness.",
  not_applicable: () => "Got it — skipping that one for your venture.",
};

export function acknowledgmentFor(state: EvidenceState, severity: number | null): string {
  return ACKNOWLEDGMENTS[state](severity);
}

const MAX_SEVERITY = 2;

/** Identical renormalization to `backend/app/ml/funding_readiness.py`: a dimension marked
 * `not_applicable` is excluded from both the numerator and denominator, so opting out of a
 * question never lowers the achievable percentage. This is the same real evidence-strength
 * computation the pre-Sprint-5 accordion used — confidence evolution here mirrors an actual
 * scoring rule, never a fabricated number. */
export function computeEvidenceStrength(answers: FundingAnswers): number {
  const entries = Object.values(answers).filter((entry): entry is NonNullable<typeof entry> => entry !== undefined);
  const applicable = entries.filter((entry) => entry.state !== "not_applicable");
  if (applicable.length === 0) return 0;
  const total = applicable.reduce(
    (sum, entry) => sum + (entry.state === "confirmed_positive" ? (entry.severity ?? 1) : 0),
    0,
  );
  return Math.round((total / (applicable.length * MAX_SEVERITY)) * 100);
}
