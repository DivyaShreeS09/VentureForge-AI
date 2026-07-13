import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { FundingAnswers } from "../types/api";

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
}

const EMPTY_IDEA: IdeaFields = {
  name: "",
  onePitch: "",
  problemSolution: "",
  industryMarket: "",
  targetCustomer: "",
  currentStage: "",
};

const STORAGE_KEY = "ventureforge.newAnalysis.v1";

function loadInitial(): NewAnalysisState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { idea: EMPTY_IDEA, fundingAnswers: {} };
    const parsed = JSON.parse(raw);
    return {
      idea: { ...EMPTY_IDEA, ...(parsed.idea ?? {}) },
      fundingAnswers: parsed.fundingAnswers ?? {},
    };
  } catch {
    return { idea: EMPTY_IDEA, fundingAnswers: {} };
  }
}

interface Ctx {
  idea: IdeaFields;
  fundingAnswers: FundingAnswers;
  updateIdea: (patch: Partial<IdeaFields>) => void;
  updateFunding: (key: keyof FundingAnswers, value: number | null) => void;
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
      updateIdea: (patch) => setState((prev) => ({ ...prev, idea: { ...prev.idea, ...patch } })),
      updateFunding: (key, val) =>
        setState((prev) => ({ ...prev, fundingAnswers: { ...prev.fundingAnswers, [key]: val } })),
      buildDescription: () => {
        const { onePitch, problemSolution, industryMarket, targetCustomer, currentStage } = state.idea;
        return [onePitch, problemSolution, industryMarket, targetCustomer, currentStage]
          .map((s) => s.trim())
          .filter(Boolean)
          .join(" ");
      },
      reset: () => {
        setState({ idea: EMPTY_IDEA, fundingAnswers: {} });
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
