import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type {
  CompanyMetrics,
  DimensionEvidence,
  FundingAnswers,
  MarketEvidence,
  RevenueAssumptions,
} from "../types/api";

/** The backend only accepts `name` + `description` + `funding_answers` (see
 * backend/app/schemas/startup.py) — there is no separate industry/target-customer/stage field.
 * The Idea Submission page's guided sections below are a frontend-only authoring aid: each one
 * prompts for a specific kind of detail, and their answers are concatenated into a single,
 * richer `description` string before it's ever sent to the API. This enriches the real
 * classifier input honestly, without inventing a backend field that doesn't exist. */
export interface IdeaFields {
  name: string;
  problemSolution: string;
  targetCustomer: string;
  /** Real, backend-derived deployment-sector hints (see IndustryPreview.customer_hints) the
   * founder confirmed apply — capped at 2, oldest deselects first (Design System Bible §7's
   * multi-select choice-card rule). Never a fabricated "customer segment" — only sectors the
   * classifier's own keyword extraction actually matched in this founder's own description. */
  customerSegments: string[];
  currentStage: string;
}

export interface NewAnalysisState {
  idea: IdeaFields;
  fundingAnswers: FundingAnswers;
  companyMetrics: CompanyMetrics;
  revenueAssumptions: RevenueAssumptions;
  marketEvidence: MarketEvidence;
  mode: "beginner" | "advanced";
}

const EMPTY_IDEA: IdeaFields = {
  name: "",
  problemSolution: "",
  targetCustomer: "",
  customerSegments: [],
  currentStage: "",
};

const EMPTY_COMPANY_METRICS: CompanyMetrics = {};
const EMPTY_REVENUE_ASSUMPTIONS: RevenueAssumptions = {};
const EMPTY_MARKET_EVIDENCE: MarketEvidence = { known_competitors: [] };

/** Founder Input Experience Redesign: a single global mode, not a per-screen setting. Beginner
 * (the default) never shows a field or a term the audit flagged as jargon-only-useful-when-known
 * (funding history, growth-rate/margin percentages, TAM/SAM/SOM); Advanced reveals them for a
 * founder who already knows these numbers. Both modes write to the exact same backend schema —
 * switching modes never changes what gets submitted, only what's asked to produce it. */
export type InputMode = "beginner" | "advanced";

const STORAGE_KEY = "ventureforge.newAnalysis.v2";

function emptyState(): NewAnalysisState {
  return {
    idea: EMPTY_IDEA,
    fundingAnswers: {},
    companyMetrics: EMPTY_COMPANY_METRICS,
    revenueAssumptions: EMPTY_REVENUE_ASSUMPTIONS,
    marketEvidence: EMPTY_MARKET_EVIDENCE,
    mode: "beginner",
  };
}

function loadInitial(): NewAnalysisState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyState();
    const parsed = JSON.parse(raw);
    return {
      idea: { ...EMPTY_IDEA, ...(parsed.idea ?? {}) },
      fundingAnswers: parsed.fundingAnswers ?? {},
      companyMetrics: parsed.companyMetrics ?? EMPTY_COMPANY_METRICS,
      revenueAssumptions: parsed.revenueAssumptions ?? EMPTY_REVENUE_ASSUMPTIONS,
      marketEvidence: parsed.marketEvidence ?? EMPTY_MARKET_EVIDENCE,
      mode: parsed.mode === "advanced" ? "advanced" : "beginner",
    };
  } catch {
    return emptyState();
  }
}

interface Ctx {
  idea: IdeaFields;
  fundingAnswers: FundingAnswers;
  companyMetrics: CompanyMetrics;
  revenueAssumptions: RevenueAssumptions;
  marketEvidence: MarketEvidence;
  mode: InputMode;
  setMode: (mode: InputMode) => void;
  updateIdea: (patch: Partial<IdeaFields>) => void;
  updateFunding: (key: keyof FundingAnswers, value: DimensionEvidence) => void;
  updateCompanyMetrics: (patch: Partial<CompanyMetrics>) => void;
  updateRevenueAssumptions: (patch: Partial<RevenueAssumptions>) => void;
  updateMarketEvidence: (patch: Partial<MarketEvidence>) => void;
  buildDescription: () => string;
  /** The final `market_evidence` payload to submit — merges the structural fields Discovery
   * already collected (`customer_type` from "who buys this", `startup_stage` from "where are you
   * right now", `target_market` from the confirmed sector chips) with whatever Additional Details
   * added, so a founder is never asked the same real-world question twice on two different screens
   * (Founder Input Experience Redesign audit finding #1). */
  buildMarketEvidence: () => MarketEvidence;
  reset: () => void;
}

const NewAnalysisContext = createContext<Ctx | null>(null);

export function NewAnalysisProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<NewAnalysisState>(loadInitial);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Storage unavailable — autosave silently degrades to in-memory only.
    }
  }, [state]);

  const value = useMemo<Ctx>(
    () => ({
      idea: state.idea,
      fundingAnswers: state.fundingAnswers,
      companyMetrics: state.companyMetrics,
      revenueAssumptions: state.revenueAssumptions,
      marketEvidence: state.marketEvidence,
      mode: state.mode,
      setMode: (mode) => setState((prev) => ({ ...prev, mode })),
      updateIdea: (patch) => setState((prev) => ({ ...prev, idea: { ...prev.idea, ...patch } })),
      updateFunding: (key, value) =>
        setState((prev) => ({ ...prev, fundingAnswers: { ...prev.fundingAnswers, [key]: value } })),
      updateCompanyMetrics: (patch) =>
        setState((prev) => ({ ...prev, companyMetrics: { ...prev.companyMetrics, ...patch } })),
      updateRevenueAssumptions: (patch) =>
        setState((prev) => ({ ...prev, revenueAssumptions: { ...prev.revenueAssumptions, ...patch } })),
      updateMarketEvidence: (patch) =>
        setState((prev) => ({ ...prev, marketEvidence: { ...prev.marketEvidence, ...patch } })),
      buildDescription: () => {
        const { problemSolution, targetCustomer, currentStage } = state.idea;
        return [problemSolution, targetCustomer, currentStage]
          .map((s) => s.trim())
          .filter(Boolean)
          .join(" ");
      },
      buildMarketEvidence: () => {
        const { targetCustomer, customerSegments, currentStage } = state.idea;
        return {
          ...state.marketEvidence,
          customer_type: state.marketEvidence.customer_type || targetCustomer.trim() || null,
          target_market: state.marketEvidence.target_market || (customerSegments.length > 0 ? customerSegments.join(", ") : null),
          startup_stage: state.marketEvidence.startup_stage || currentStage || null,
        };
      },
      reset: () => {
        setState(emptyState());
        try {
          window.localStorage.removeItem(STORAGE_KEY);
        } catch {
          // no-op
        }
      },
    }),
    [state],
  );

  return <NewAnalysisContext.Provider value={value}>{children}</NewAnalysisContext.Provider>;
}

export function useNewAnalysis(): Ctx {
  const ctx = useContext(NewAnalysisContext);
  if (!ctx) throw new Error("useNewAnalysis must be used within NewAnalysisProvider");
  return ctx;
}
