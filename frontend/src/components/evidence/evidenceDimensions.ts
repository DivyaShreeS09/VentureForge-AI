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

/**
 * Mentor-conversation order: understand the problem, then who has it, then what's been built,
 * then whether anyone's pulling on it, then the business model, then market size, then the team,
 * then the competitive landscape — each question builds on the last rather than the old
 * accordion's arbitrary list order.
 * 1. Problem clarity
 * 2. Customer pain evidence
 * 3. Product maturity
 * 4. Traction
 * 5. Revenue model
 * 6. Market size
 * 7. Team completeness
 * 8. Competitive differentiation
 *
 * The backend still receives the same 8 funding dimensions `backend/app/ml/funding_readiness.py`
 * scores. The `question`/`tip`/`option.label` strings below are the English fallback used by
 * `useLanguage()`'s `t()` — the dimension `key` (e.g. "problem_clarity") is what actually drives
 * translation lookup in EvidenceQuestionScene, so these strings must stay in sync with the "en"
 * entries in `context/LanguageContext.tsx`.
 */
export const EVIDENCE_DIMENSIONS: EvidenceDimension[] = [
  {
    key: "problem_clarity",
    question: "How well do you understand the problem?",
    tip: "Think about what the problem is, who faces it, and what makes it difficult for them.",
    options: [
      {
        state: "confirmed_negative",
        severity: null,
        label: "I'm still exploring the problem",
      },
      {
        state: "confirmed_negative",
        severity: null,
        label: "I have a general idea",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "I know the specific problem",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "I know who faces it",
      },
      {
        state: "confirmed_positive",
        severity: 2,
        label: "I understand the pain deeply",
      },
    ],
  },

  {
    key: "customer_pain_evidence",
    question: "How do you know people really have this problem?",
    tip: "Think about conversations, surveys, feedback, or anything you've seen from real people.",
    options: [
      {
        state: "confirmed_negative",
        severity: null,
        label: "I haven't checked yet",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "I've talked to a few people",
      },
      {
        state: "confirmed_positive",
        severity: 2,
        label: "I have real feedback or data",
      },
    ],
    stageNote: (stage) =>
      EARLY_STAGES.has(stage)
        ? "It's completely okay if you haven't checked this yet."
        : null,
  },

  {
    key: "product_maturity",
    question: "What have you built so far?",
    tip: "Tell us what someone can actually see, try, or use today.",
    options: [
      {
        state: "confirmed_negative",
        severity: null,
        label: "Just an idea",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "I have a prototype or MVP",
      },
      {
        state: "confirmed_positive",
        severity: 2,
        label: "People can use it now",
      },
    ],
  },

  {
    key: "traction",
    question: "Are people using it yet?",
    tip: "Users, testers, pilot users, or paying customers all count.",
    options: [
      {
        state: "confirmed_negative",
        severity: null,
        label: "Not yet",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "A few people are trying it",
      },
      {
        state: "confirmed_positive",
        severity: 2,
        label: "People are using or paying for it",
      },
    ],
    stageNote: (stage) =>
      EARLY_STAGES.has(stage)
        ? "It's normal not to have users at this stage."
        : null,
  },

  {
    key: "revenue_model_clarity",
    question: "How will you make money?",
    tip: "Tell us how you plan to charge customers or earn revenue.",
    options: [
      {
        state: "confirmed_negative",
        severity: null,
        label: "I haven't decided yet",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "I have a basic plan",
      },
      {
        state: "confirmed_positive",
        severity: 2,
        label: "I know how I'll charge",
      },
    ],
    stageNote: (stage) =>
      EARLY_STAGES.has(stage)
        ? "It's okay if you're still deciding this."
        : null,
  },

  {
    key: "market_size_evidence",
    question: "How big could this opportunity be?",
    tip: "Give us your best estimate or any market information you have.",
    tipAdvanced: "A sourced TAM/SAM/SOM estimate gives the strongest evidence.",
    options: [
      {
        state: "confirmed_negative",
        severity: null,
        label: "I don't know yet",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "I have a rough idea",
      },
      {
        state: "confirmed_positive",
        severity: 2,
        label: "I have research or a market estimate",
      },
    ],
  },

  {
    key: "team_completeness",
    question: "Does your team have the skills you need?",
    tip: "Think about the skills needed to build, run, and grow your venture.",
    options: [
      {
        state: "confirmed_negative",
        severity: null,
        label: "I'm missing some skills",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "We have some of them",
      },
      {
        state: "confirmed_positive",
        severity: 2,
        label: "We have the key skills",
      },
    ],
  },

  {
    key: "competitive_differentiation",
    question: "What makes your idea different?",
    tip: "Think about other solutions and what makes yours better or different.",
    options: [
      {
        state: "confirmed_negative",
        severity: null,
        label: "I'm not sure yet",
      },
      {
        state: "confirmed_positive",
        severity: 1,
        label: "I have some differences",
      },
      {
        state: "confirmed_positive",
        severity: 2,
        label: "I have a clear advantage",
      },
    ],
  },
];

/** Shared alongside every dimension's evidence-quality options — never inferred from silence
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
