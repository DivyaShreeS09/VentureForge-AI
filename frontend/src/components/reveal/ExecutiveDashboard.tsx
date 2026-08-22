import { GlassCard } from "../../primitives/GlassCard";
import type { Analysis } from "../../types/api";
import { GaugeChart } from "./charts/GaugeChart";
import { FundingRadarChart } from "./charts/FundingRadarChart";
import { RevenueBarChart } from "./charts/RevenueBarChart";
import { RiskGrid } from "./charts/RiskGrid";

function DashboardSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div id={id} className="scroll-mt-24">
      <p className="text-forge-1 uppercase tracking-[0.2em] text-forge-label">
        {title}
      </p>

      <div className="mt-4">{children}</div>
    </div>
  );
}

/**
 * Section 2 of 5 — Executive Dashboard.
 *
 * Speech is handled globally by Reveal.tsx.
 * This component contains no local speaker buttons.
 */
export function ExecutiveDashboard({
  analysis,
}: {
  analysis: Analysis;
}) {
  const funding =
    analysis.funding_assessment;

  const success =
    analysis.success_prediction;

  const industry =
    analysis.industry_prediction;

  const revenueScenarios =
    analysis.revenue_estimate?.scenarios;

  const strategicRisks =
    analysis.strategic_opportunity?.strategic_risks ?? [];

  const hasKpis =
    Boolean(
      funding ||
      success ||
      industry,
    );

  const hasVisuals =
    Boolean(
      funding &&
      funding.breakdown.length > 0,
    ) ||
    Boolean(revenueScenarios) ||
    strategicRisks.length > 0;

  const fundingCaption =
    funding
      ? funding.level.replace(
          /_/g,
          " ",
        )
      : "";

  const successPercent =
    success
      ? Math.round(
          success.success_probability *
            100,
        )
      : null;

  const industryPercent =
    industry
      ? Math.round(
          (
            industry.primary_confidence ??
            industry.confidence
          ) * 100,
        )
      : null;

  const industryName =
    industry?.primary_industry ??
    industry?.predicted_industry ??
    "";

  return (
    <section
      id="section-dashboard"
      className="mx-auto w-full max-w-[1100px] space-y-16 px-6 py-16 forge-sm:px-10"
    >
      {hasKpis && (
        <DashboardSection
          id="dashboard-kpis"
          title="Executive Dashboard"
        >
          <div className="grid grid-cols-1 gap-4 forge-sm:grid-cols-3">
            {/* Funding Readiness */}
            {funding && (
              <GlassCard
                interactive
                glow="accent"
                className="p-6"
              >
                <div className="mb-4">
                  <p className="text-forge-2 font-medium text-forge-text">
                    Funding Readiness
                  </p>

                  <p className="mt-1 text-forge-1 text-forge-text-secondary">
                    {
                      funding.overall_score
                    }
                    /100
                  </p>
                </div>

                <GaugeChart
                  value={
                    funding.overall_score
                  }
                  label="Funding Readiness"
                  caption={
                    fundingCaption
                  }
                  color="#ffb020"
                />
              </GlassCard>
            )}

            {/* Success Probability */}
            {success && (
              <GlassCard
                interactive
                glow="accent-2"
                className="p-6"
              >
                <div className="mb-4">
                  <p className="text-forge-2 font-medium text-forge-text">
                    Success Probability
                  </p>

                  <p className="mt-1 text-forge-1 text-forge-text-secondary">
                    {
                      successPercent
                    }
                    %
                  </p>
                </div>

                <GaugeChart
                  value={
                    success.success_probability *
                    100
                  }
                  label="Success Probability"
                  caption={
                    success.pattern_signal_display
                  }
                  color="#6fa287"
                />
              </GlassCard>
            )}

            {/* Industry Confidence */}
            {industry && (
              <GlassCard
                interactive
                glow="accent-2"
                className="p-6"
              >
                <div className="mb-4">
                  <p className="text-forge-2 font-medium text-forge-text">
                    Industry Confidence
                  </p>

                  <p className="mt-1 text-forge-1 text-forge-text-secondary">
                    {
                      industryPercent
                    }
                    %
                  </p>
                </div>

                <GaugeChart
                  value={
                    (
                      industry.primary_confidence ??
                      industry.confidence
                    ) * 100
                  }
                  label="Industry Confidence"
                  caption={
                    industryName
                  }
                  color="#5b9dff"
                />
              </GlassCard>
            )}
          </div>
        </DashboardSection>
      )}

      {hasVisuals && (
        <DashboardSection
          id="dashboard-visual-intelligence"
          title="Visual Intelligence"
        >
          <div className="grid grid-cols-1 gap-4 forge-lg:grid-cols-2">
            {/* Funding breakdown */}
            {funding &&
              funding.breakdown.length >
                0 && (
                <GlassCard className="p-6">
                  <p className="text-forge-2 font-medium text-forge-text">
                    Funding readiness
                    breakdown
                  </p>

                  <FundingRadarChart
                    breakdown={
                      funding.breakdown
                    }
                  />
                </GlassCard>
              )}

            {/* Revenue scenarios */}
            {revenueScenarios && (
              <GlassCard className="p-6">
                <p className="text-forge-2 font-medium text-forge-text">
                  Revenue scenarios,
                  12 months
                </p>

                <RevenueBarChart
                  scenarios={
                    revenueScenarios
                  }
                />
              </GlassCard>
            )}

            {/* Risk matrix */}
            {strategicRisks.length >
              0 && (
              <GlassCard className="p-6 forge-lg:col-span-2">
                <p className="text-forge-2 font-medium text-forge-text">
                  Risk matrix
                </p>

                <div className="mt-4">
                  <RiskGrid
                    risks={
                      strategicRisks
                    }
                  />
                </div>
              </GlassCard>
            )}
          </div>
        </DashboardSection>
      )}
    </section>
  );
}