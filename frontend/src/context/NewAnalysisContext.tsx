import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { CompanyMetrics, FundingAnswers, MarketEvidence, RevenueAssumptions } from "../types/api";

/** The backend only accepts `name` + `description` + `funding_answers` (see
 * backend/app/schemas/startup.py) — there is no separate industry/target-customer/stage field.
 * The Idea Submission page's guided sections below are a frontend-only authoring aid: each one
 * prompts for a specific kind of detail, and their answers are concatenated into a single,
 * richer `description` string before it's ever sent to the API. This enriches the real
 * classifier input honestly, without inventing a backend field that doesn't exist. */
export interface IdeaFields {
  name: string;
  onePitch: string;
  problemSolution: string;
  industryMarket: string;
  targetCustomer: string;
  currentStage: string;
}

export interface NewAnalysisState {
  idea: IdeaFields;
  fundingAnswers: FundingAnswers;
  companyMetrics: CompanyMetrics;
  revenueAssumptions: RevenueAssumptions;
  marketEvidence: MarketEvidence;
}

const EMPTY_IDEA: IdeaFields = {
  name: "",
  onePitch: "",
  problemSolution: "",
  industryMarket: "",
  targetCustomer: "",
  currentStage: "",
};

const EMPTY_COMPANY_METRICS: CompanyMetrics = {};
const EMPTY_REVENUE_ASSUMPTIONS: RevenueAssumptions = {};
const EMPTY_MARKET_EVIDENCE: MarketEvidence = { known_competitors: [] };

const STORAGE_KEY = "ventureforge.newAnalysis.v1";

function emptyState(): NewAnalysisState {
  return {
    idea: EMPTY_IDEA,
    fundingAnswers: {},
    companyMetrics: EMPTY_COMPANY_METRICS,
    revenueAssumptions: EMPTY_REVENUE_ASSUMPTIONS,
    marketEvidence: EMPTY_MARKET_EVIDENCE,
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
  updateIdea: (patch: Partial<IdeaFields>) => void;
  updateFunding: (key: keyof FundingAnswers, value: number | null) => void;
  updateCompanyMetrics: (patch: Partial<CompanyMetrics>) => void;
  updateRevenueAssumptions: (patch: Partial<RevenueAssumptions>) => void;
  updateMarketEvidence: (patch: Partial<MarketEvidence>) => void;
  buildDescription: () => string;
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
      updateIdea: (patch) => setState((prev) => ({ ...prev, idea: { ...prev.idea, ...patch } })),
      updateFunding: (key, val) =>
        setState((prev) => ({ ...prev, fundingAnswers: { ...prev.fundingAnswers, [key]: val } })),
      updateCompanyMetrics: (patch) =>
        setState((prev) => ({ ...prev, companyMetrics: { ...prev.companyMetrics, ...patch } })),
      updateRevenueAssumptions: (patch) =>
        setState((prev) => ({ ...prev, revenueAssumptions: { ...prev.revenueAssumptions, ...patch } })),
      updateMarketEvidence: (patch) =>
        setState((prev) => ({ ...prev, marketEvidence: { ...prev.marketEvidence, ...patch } })),
      buildDescription: () => {
        const { onePitch, problemSolution, industryMarket, targetCustomer, currentStage } = state.idea;
        return [onePitch, problemSolution, industryMarket, targetCustomer, currentStage]
          .map((s) => s.trim())
          .filter(Boolean)
          .join(" ");
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
