import type { IdeaConfidenceTier, Student3Risk, StrategicRisk, StrategicRiskLevel } from "../../../types/api";
import { Section } from "../Section";
import { ConfidenceTierBadge } from "./ConfidenceTierBadge";

const LEVEL_WEIGHT: Record<StrategicRiskLevel, number> = { low: 1, medium: 2, high: 3 };
const LEVEL_STYLE: Record<StrategicRiskLevel, string> = {
  low: "text-success-400",
  medium: "text-signal-400",
  high: "text-danger-400",
};

interface DisplayRisk {
  key: string;
  title: string;
  categoryLabel: string;
  why: string;
  likelihood: StrategicRiskLevel;
  impact: StrategicRiskLevel;
  mitigation: string;
  confidenceTier: IdeaConfidenceTier | null;
}

function fromStrategicRisks(risks: StrategicRisk[]): DisplayRisk[] {
  return risks.map((risk, idx) => ({
    key: `strategic-${idx}`,
    title: risk.risk,
    categoryLabel: `${risk.category} risk`,
    why: risk.why,
    likelihood: risk.likelihood,
    impact: risk.impact,
    mitigation: risk.mitigation,
    confidenceTier: risk.confidence_tier,
  }));
}

// Student 3's planning risks are a fixed checklist grounded in readiness evidence, not a
// confirmed/hypothesis/speculative claim about the venture's specific situation — so no
// ConfidenceTierBadge is shown for these; the "Planning risk" label says what it is instead.
function fromPlanningRisks(risks: Student3Risk[]): DisplayRisk[] {
  return risks.map((risk, idx) => ({
    key: `planning-${idx}`,
    title: risk.title,
    categoryLabel: `${risk.category.replace("_", " ")} risk`,
    why: risk.evidence_basis[0] ?? "",
    likelihood: risk.probability_band,
    impact: risk.impact_band,
    mitigation: risk.mitigation,
    confidenceTier: null,
  }));
}

/** Section 7 — Risk Dashboard: combines the existing `strategic_risks` (Phase 3 — market/timing/
 * regulatory/technology/competition/adoption, distinct from founder execution gaps) with Phase 5
 * (Student 3)'s deterministic planning-risk checklist. Sorted by likelihood x impact for visual
 * priority — highest-priority risk first. `owner`/`status` are simple, always-true defaults for a
 * fresh analysis (every risk starts unowned and open) — not a new backend field or fabricated
 * claim. */
export function RiskDashboardSection({ risks, planningRisks = [] }: { risks: StrategicRisk[]; planningRisks?: Student3Risk[] }) {
  const combined = [...fromStrategicRisks(risks), ...fromPlanningRisks(planningRisks)];
  const sorted = combined.sort(
    (a, b) => LEVEL_WEIGHT[b.likelihood] * LEVEL_WEIGHT[b.impact] - LEVEL_WEIGHT[a.likelihood] * LEVEL_WEIGHT[a.impact],
  );

  return (
    <Section id="risk-dashboard" title="Risk Dashboard">
      {sorted.length > 0 ? (
        <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {sorted.map((risk) => (
            <li key={risk.key} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-ink-primary">{risk.title}</p>
                  <p className="mt-0.5 text-[11px] uppercase tracking-[0.08em] text-ink-muted">{risk.categoryLabel}</p>
                </div>
                {risk.confidenceTier ? <ConfidenceTierBadge tier={risk.confidenceTier} /> : (
                  <span className="shrink-0 rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] text-ink-muted">
                    Planning risk
                  </span>
                )}
              </div>
              <p className="mt-2 text-xs text-ink-secondary">{risk.why}</p>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                <span>Likelihood: <span className={LEVEL_STYLE[risk.likelihood]}>{risk.likelihood}</span></span>
                <span>Impact: <span className={LEVEL_STYLE[risk.impact]}>{risk.impact}</span></span>
                <span className="text-ink-muted">Owner: Founder</span>
                <span className="text-ink-muted">Status: Open</span>
              </div>
              <p className="mt-2 text-xs text-ink-secondary">
                <span className="text-ink-muted">Mitigation: </span>
                {risk.mitigation}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-ink-muted">No strategic risks identified for this run.</p>
      )}
    </Section>
  );
}
