import type {
  Analysis,
  CompanyMetrics,
  CustomerRFMInput,
  FundingAnswers,
  MarketEvidence,
  ModelStatus,
  RevenueAssumptions,
  Startup,
  SystemStatus,
  TaxonomyResponse,
} from "../types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed with status ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

const REQUEST_TIMEOUT_MS = 30_000;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "The request took too long to respond. Please try again.");
    }
    throw new ApiError(0, "Could not reach the server. Check that the backend is running.");
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      const body = await response.json();
      detail = body.detail ?? body;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

export function createStartup(payload: {
  name: string;
  description: string;
  funding_answers: FundingAnswers;
  company_metrics?: CompanyMetrics;
  revenue_assumptions?: RevenueAssumptions;
  market_evidence?: MarketEvidence;
  customer_rfm?: CustomerRFMInput | null;
}): Promise<Startup> {
  return request<Startup>("/startups", { method: "POST", body: JSON.stringify(payload) });
}

export function getStartup(startupId: string): Promise<Startup> {
  return request<Startup>(`/startups/${startupId}`);
}

export function analyzeStartup(startupId: string): Promise<Analysis> {
  return request<Analysis>(`/startups/${startupId}/analyze`, { method: "POST" });
}

export function getAnalysis(analysisId: string): Promise<Analysis> {
  return request<Analysis>(`/analyses/${analysisId}`);
}

/** Founder-submitted correction to venture_positioning only, from the controlled taxonomy list —
 * see backend/app/api/v1/analyses.py's `/industry-correction` route. Never touches model_category. */
export function correctIndustry(
  analysisId: string,
  payload: { primary_domain: string; secondary_domains?: string[] },
): Promise<Analysis> {
  return request<Analysis>(`/analyses/${analysisId}/industry-correction`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Live controlled-taxonomy listing — the source of truth for the positioning-correction domain
 * dropdown. See backend/app/api/v1/taxonomy.py. */
export function getTaxonomy(): Promise<TaxonomyResponse> {
  return request<TaxonomyResponse>("/taxonomy");
}

/** Persist an edit to one or more revenue assumptions — see
 * backend/app/api/v1/analyses.py's `/revenue-assumptions` route. Partial: only fields present in
 * `payload` are changed; recomputes scenarios server-side and returns the full updated analysis. */
export function saveRevenueAssumptions(
  analysisId: string,
  payload: Partial<RevenueAssumptions>,
): Promise<Analysis> {
  return request<Analysis>(`/analyses/${analysisId}/revenue-assumptions`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getModelsStatus(): Promise<ModelStatus> {
  return request<ModelStatus>("/models/status");
}

/** Development-only. Returns null (rather than throwing) on a 404, since that's the expected
 * response in production — the overlay component treats null as "signal unavailable", not an
 * error to surface. */
export async function getSystemStatus(): Promise<SystemStatus | null> {
  try {
    return await request<SystemStatus>("/system/status");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}
