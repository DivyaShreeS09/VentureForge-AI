import type { Analysis, FundingAssessment } from "../types/api";

/** Anonymous, browser-local analysis history — no account, no server-side history endpoint.
 * Distinct from the backend's own Postgres persistence (which just backs `GET /analyses/{id}`
 * for reload-safety); this is purely a client-side convenience list of past runs on this device. */
export interface HistoryEntry {
  analysisId: string;
  startupId: string;
  name: string;
  industry: string | null;
  confidence: number | null;
  score: number | null;
  level: FundingAssessment["level"];
  verdict: string;
  createdAt: string;
}

const STORAGE_KEY = "ventureforge.history.v1";

function readAll(): HistoryEntry[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(entries: HistoryEntry[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // Storage unavailable (private browsing quota, etc.) — history simply won't persist.
  }
}

export function listHistory(): HistoryEntry[] {
  return readAll().sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
}

export function recordAnalysis(startupName: string, analysis: Analysis): void {
  const entries = readAll().filter((e) => e.analysisId !== analysis.id);
  entries.push({
    analysisId: analysis.id,
    startupId: analysis.startup_id,
    name: startupName,
    industry: analysis.industry_prediction?.predicted_industry ?? null,
    confidence: analysis.industry_prediction?.confidence ?? null,
    score: analysis.funding_assessment?.overall_score ?? null,
    level: (analysis.funding_assessment?.level ?? "early_stage") as HistoryEntry["level"],
    verdict: analysis.judge_summary?.confidence_level ?? "low",
    createdAt: analysis.created_at,
  });
  writeAll(entries);
}

export function deleteHistoryEntry(analysisId: string): void {
  writeAll(readAll().filter((e) => e.analysisId !== analysisId));
}

export function clearHistory(): void {
  writeAll([]);
}

export function exportHistoryAsJson(): string {
  return JSON.stringify(listHistory(), null, 2);
}
