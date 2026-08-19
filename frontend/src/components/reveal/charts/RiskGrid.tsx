import { Fragment } from "react";
import type { StrategicRisk } from "../../../types/api";

interface Props {
  risks: StrategicRisk[];
}

const LEVELS = ["low", "medium", "high"] as const;
const LEVEL_LABEL: Record<(typeof LEVELS)[number], string> = { low: "Low", medium: "Medium", high: "High" };

// Recharts has no native heatmap primitive, so this is a small custom grid using the same
// card/token system as the rest of the dashboard, not a fabricated Recharts chart type. Likelihood
// (rows) × impact (columns) are the two real ordinal axes `strategic_opportunity.strategic_risks`
// already carries — cell severity (top-right = both high) is derived, never a separate score, and
// every cell states its axis values as text (not color-only) for accessibility.
export function RiskGrid({ risks }: Props) {
  const cells = new Map<string, StrategicRisk[]>();
  for (const risk of risks) {
    const key = `${risk.likelihood}-${risk.impact}`;
    const bucket = cells.get(key) ?? [];
    bucket.push(risk);
    cells.set(key, bucket);
  }

  function severity(likelihood: string, impact: string): "high" | "medium" | "low" {
    const score = LEVELS.indexOf(likelihood as never) + LEVELS.indexOf(impact as never);
    if (score >= 3) return "high";
    if (score >= 1) return "medium";
    return "low";
  }

  const TONE: Record<"high" | "medium" | "low", { border: string; wash: string; dot: string; hoverGlow: string }> = {
    high: {
      border: "border-forge-risk/40",
      wash: "bg-[radial-gradient(circle_at_30%_20%,rgba(224,99,122,0.14),transparent_70%)]",
      dot: "bg-forge-risk shadow-[0_0_8px_1px_rgba(224,99,122,0.6)]",
      hoverGlow: "hover:shadow-[0_0_28px_-8px_rgba(224,99,122,0.5)]",
    },
    medium: {
      border: "border-forge-notsure/30",
      wash: "bg-[radial-gradient(circle_at_30%_20%,rgba(201,162,74,0.10),transparent_70%)]",
      dot: "bg-forge-notsure shadow-[0_0_8px_1px_rgba(201,162,74,0.5)]",
      hoverGlow: "hover:shadow-[0_0_24px_-8px_rgba(201,162,74,0.4)]",
    },
    low: {
      border: "border-forge-text/[.1]",
      wash: "bg-[radial-gradient(circle_at_30%_20%,rgba(139,92,246,0.06),transparent_70%)]",
      dot: "bg-forge-text/25",
      hoverGlow: "hover:shadow-[0_0_20px_-8px_rgba(139,92,246,0.3)]",
    },
  };

  return (
    <div role="group" aria-label="Risk matrix: likelihood versus impact" className="w-full">
      <div className="grid grid-cols-[auto_repeat(3,1fr)] gap-1.5 text-forge-1">
        <div />
        {LEVELS.map((impact) => (
          <div key={impact} className="pb-1 text-center text-forge-text-tertiary">
            {LEVEL_LABEL[impact]} impact
          </div>
        ))}
        {[...LEVELS].reverse().map((likelihood) => (
          <Fragment key={`row-${likelihood}`}>
            <div className="flex items-center justify-end pr-2 text-forge-text-tertiary">
              {LEVEL_LABEL[likelihood]} likelihood
            </div>
            {LEVELS.map((impact) => {
              const key = `${likelihood}-${impact}`;
              const bucket = cells.get(key) ?? [];
              const tone = TONE[severity(likelihood, impact)];
              return (
                <div
                  key={key}
                  className={`group relative min-h-[64px] overflow-hidden rounded-forge-sm border p-2 backdrop-blur-sm transition-shadow duration-300 ${tone.border} ${tone.wash} ${tone.hoverGlow}`}
                >
                  {/* A colored severity indicator makes even an empty cell read as a deliberately
                      classified "nothing here" rather than dead unstyled space. */}
                  <span aria-hidden="true" className={`absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full ${tone.dot}`} />
                  {bucket.length === 0 ? (
                    <p className="text-forge-1 text-forge-text-disabled">No flagged risks</p>
                  ) : (
                    bucket.map((risk, i) => (
                      <p key={i} className="truncate text-forge-1 text-forge-text" title={risk.risk}>
                        {risk.risk}
                      </p>
                    ))
                  )}
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
