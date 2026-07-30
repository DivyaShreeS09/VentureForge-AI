import { useState } from "react";
import type { Analysis, RevenueEstimate } from "../../types/api";
import { ApiError, saveRevenueAssumptions } from "../../services/api";
import { recalculateScenarios } from "../../utils/revenueRecalculation";

/** Revenue scenario range + per-field assumption provenance, editable — moved unchanged from the
 * old AnalysisResult.tsx (RevenueEstimateBlock), restyled with forge tokens only. Real editing
 * functionality is kept per the Sprint 7 audit; only its presentation and location changed (now
 * lives inside the Bigger Picture scene's Pricing & Business Model subsection). */
export function RevenueScenarios({
  analysisId,
  revenueEstimate,
  onSaved,
}: {
  analysisId: string;
  revenueEstimate: RevenueEstimate;
  onSaved: (updated: Analysis) => void;
}) {
  const fields = revenueEstimate.assumptions;
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const price = overrides.price_per_customer_usd ?? fields?.price_per_customer_usd.value ?? revenueEstimate.assumptions_used?.price_per_customer_usd ?? 0;
  const customers = overrides.initial_customers ?? fields?.initial_customers.value ?? revenueEstimate.assumptions_used?.initial_customers ?? 0;
  const growth = overrides.monthly_growth_rate_pct ?? fields?.monthly_growth_rate_pct.value ?? revenueEstimate.assumptions_used?.monthly_growth_rate_pct ?? 0;
  const margin = overrides.gross_margin_pct ?? fields?.gross_margin_pct.value ?? revenueEstimate.assumptions_used?.gross_margin_pct ?? 100;

  const hasUnsavedEdits = Object.keys(overrides).length > 0;
  const scenarios = hasUnsavedEdits ? recalculateScenarios(price, customers, growth, margin) : revenueEstimate.scenarios!;

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await saveRevenueAssumptions(analysisId, { ...overrides });
      onSaved(updated);
      setOverrides({});
    } catch (err) {
      setSaveError(err instanceof ApiError ? String(err.detail ?? err.message) : "Could not save these assumptions.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="grid grid-cols-1 gap-3 forge-sm:grid-cols-3">
        {(["conservative", "base", "optimistic"] as const).map((key) => {
          const s = scenarios[key];
          return (
            <div key={key} className="border border-forge-text/[.08] p-4">
              <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary capitalize">{key}</p>
              <p className="mt-1.5 font-forge-mono text-forge-4 text-forge-text">${s.annual_revenue_usd.toLocaleString()}</p>
              <p className="text-forge-1 text-forge-text-secondary">annual revenue (12mo)</p>
              <p className="mt-1 text-forge-1 text-forge-text-secondary">${s.annual_gross_profit_usd.toLocaleString()} gross profit</p>
            </div>
          );
        })}
      </div>

      {hasUnsavedEdits && (
        <p className="mt-3 text-forge-1 text-forge-notsure">
          Unsaved preview — reflects your edits locally until you click "Save assumptions" below.
        </p>
      )}

      {fields && (
        <div className="mt-4 grid grid-cols-1 gap-3 forge-sm:grid-cols-2">
          {(
            [
              ["price_per_customer_usd", "Price / customer", price],
              ["initial_customers", "Initial customers", customers],
              ["monthly_growth_rate_pct", "Monthly growth (%)", growth],
              ["gross_margin_pct", "Gross margin (%)", margin],
            ] as const
          ).map(([key, label, value]) => {
            const field = fields[key];
            return (
              <div key={key} className="border border-forge-text/[.08] p-3">
                <div className="flex items-center justify-between">
                  <label htmlFor={`revenue-${key}`} className="text-forge-1 text-forge-text-secondary">
                    {label}
                  </label>
                  <span className="text-forge-1 uppercase tracking-[0.08em] text-forge-text-secondary">
                    {field.assumption_source === "user_supplied" ? "Founder-supplied" : "Suggested default"}
                  </span>
                </div>
                <input
                  id={`revenue-${key}`}
                  type="number"
                  value={value}
                  onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                  className="mt-1.5 w-full border border-forge-text/[.16] bg-transparent px-2 py-1 text-forge-2 text-forge-text"
                />
                <p className="mt-1 text-forge-1 text-forge-text-secondary">{field.explanation}</p>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={!hasUnsavedEdits || saving}
          className="rounded-forge-sm border border-forge-accent/50 px-3 py-1 text-forge-1 font-medium text-forge-accent transition hover:bg-forge-accent/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save assumptions"}
        </button>
        {saveError && (
          <p role="alert" className="text-forge-1 text-forge-risk">
            {saveError} Your edits are still shown above — try saving again.
          </p>
        )}
      </div>

      {revenueEstimate.missing_assumptions.length > 0 && (
        <p className="mt-3 text-forge-1 text-forge-notsure">
          Suggested defaults used for: {revenueEstimate.missing_assumptions.join(", ")}
        </p>
      )}
      <p className="mt-3 text-forge-1 italic text-forge-text-secondary">{revenueEstimate.disclaimer}</p>
    </div>
  );
}
