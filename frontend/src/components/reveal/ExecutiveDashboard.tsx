import { GlassCard } from "../../primitives/GlassCard";
import type { Analysis } from "../../types/api";
import { GaugeChart } from "./charts/GaugeChart";
import { FundingRadarChart } from "./charts/FundingRadarChart";
import { RevenueBarChart } from "./charts/RevenueBarChart";
import { RiskGrid } from "./charts/RiskGrid";

function DashboardSection({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <div id={id} className="scroll-mt-24">
      <p className="text-forge-1 uppercase tracking-[0.2em] text-forge-label">{title}</p>
      <div className="mt-4">{children}</div>
    </div>
  );
}

/** Section 2 of 5 — answers exactly one question: "What do I measure?" Charts only, no paragraphs
 * — the biggest-risk narrative used to live here too ("The One Thing To Fix"), but that was the
 * same sentence the Executive Command Center already states in full, so it was deleted from here
 * rather than kept as a second copy (Absolute Rule 1). Every chart is built strictly from fields
 * confirmed to exist on `Analysis` and individually omitted (not placeholder'd) when its backing
 * field is null/empty — no invented Market Confidence/Execution Readiness/Business Maturity
 * metrics. */
export function ExecutiveDashboard({ analysis }: { analysis: Analysis }) {
  const funding = analysis.funding_assessment;
  const success = analysis.success_prediction;
  const industry = analysis.industry_prediction;
  const revenueScenarios = analysis.revenue_estimate?.scenarios;
  const strategicRisks = analysis.strategic_opportunity?.strategic_risks ?? [];

  const hasKpis = funding || success || industry;
  const hasVisuals = (funding && funding.breakdown.length > 0) || revenueScenarios || strategicRisks.length > 0;

  return (
    <section id="section-dashboard" className="mx-auto w-full max-w-[1100px] space-y-16 px-6 py-16 forge-sm:px-10">
      {hasKpis && (
        <DashboardSection id="dashboard-kpis" title="Executive Dashboard">
          <div className="grid grid-cols-1 gap-4 forge-sm:grid-cols-3">
            {/* Semantic color hierarchy: funding reads in the brand gold accent, success in
                emerald (echoes the "confirmed" semantic elsewhere in the app), industry
                confidence in blue — three distinct hues so the eye can tell them apart at a
                glance instead of reading as one undifferentiated purple row. */}
            {funding && (
              <GlassCard interactive glow="accent" className="flex justify-center p-6">
                <GaugeChart value={funding.overall_score} label="Funding Readiness" caption={funding.level.replace(/_/g, " ")} color="#ffb020" />
              </GlassCard>
            )}
            {success && (
              <GlassCard interactive glow="accent-2" className="flex justify-center p-6">
                <GaugeChart
                  value={success.success_probability * 100}
                  label="Success Probability"
                  caption={success.pattern_signal_display}
                  color="#6fa287"
                />
              </GlassCard>
            )}
            {industry && (
              <GlassCard interactive glow="accent-2" className="flex justify-center p-6">
                <GaugeChart
                  value={(industry.primary_confidence ?? industry.confidence) * 100}
                  label="Industry Confidence"
                  caption={industry.primary_industry ?? industry.predicted_industry}
                  color="#5b9dff"
                />
              </GlassCard>
            )}
          </div>
        </DashboardSection>
      )}

      {hasVisuals && (
        <DashboardSection id="dashboard-visual-intelligence" title="Visual Intelligence">
          <div className="grid grid-cols-1 gap-4 forge-lg:grid-cols-2">
            {funding && funding.breakdown.length > 0 && (
              <GlassCard className="p-6">
                <p className="text-forge-2 font-medium text-forge-text">Funding readiness breakdown</p>
                <FundingRadarChart breakdown={funding.breakdown} />
              </GlassCard>
            )}
            {revenueScenarios && (
              <GlassCard className="p-6">
                <p className="text-forge-2 font-medium text-forge-text">Revenue scenarios (12mo)</p>
                <RevenueBarChart scenarios={revenueScenarios} />
              </GlassCard>
            )}
            {strategicRisks.length > 0 && (
              <GlassCard className="p-6 forge-lg:col-span-2">
                <p className="text-forge-2 font-medium text-forge-text">Risk matrix</p>
                <div className="mt-4">
                  <RiskGrid risks={strategicRisks} />
                </div>
              </GlassCard>
            )}
          </div>
        </DashboardSection>
      )}
    </section>
  );
}
