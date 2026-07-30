import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import { useReducedMotion } from "framer-motion";
import type { FundingBreakdownItem } from "../../../types/api";

interface Props {
  breakdown: FundingBreakdownItem[];
}

/** The 8 funding-readiness dimensions (`funding_assessment.breakdown`, identical set to
 * `evidenceDimensions.ts`) as a radar — replacing `DeepEvidenceScene`'s plain `label: raw/max`
 * text list with the at-a-glance shape Part 4 asks for. Every point is `raw_score` normalized to
 * its own `max_score` (already known to be 2 per dimension) — no re-weighting, no invented scale.
 * A dimension marked `not_applicable` (`raw_score === null`) plots as 0 rather than being
 * silently omitted, so the shape always reflects all 8 dimensions consistently. */
export function FundingRadarChart({ breakdown }: Props) {
  const prefersReduced = useReducedMotion();
  const data = breakdown.map((item) => ({
    label: item.label,
    score: item.raw_score === null ? 0 : Math.round((item.raw_score / item.max_score) * 100),
  }));

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <RadarChart data={data} outerRadius="72%">
          <defs>
            <radialGradient id="funding-radar-fill" cx="50%" cy="50%" r="70%">
              <stop offset="0%" stopColor="#b39dff" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.18} />
            </radialGradient>
          </defs>
          <PolarGrid stroke="rgba(248,249,252,0.14)" />
          <PolarAngleAxis dataKey="label" tick={{ fill: "rgba(248,249,252,0.6)", fontSize: 11 }} />
          <Radar
            name="Evidence strength"
            dataKey="score"
            stroke="#b39dff"
            strokeWidth={2}
            fill="url(#funding-radar-fill)"
            isAnimationActive={!prefersReduced}
            animationDuration={700}
            animationEasing="ease-out"
          />
          <Tooltip
            formatter={(v) => [`${v}%`, "Evidence strength"]}
            contentStyle={{
              background: "rgba(27,19,51,0.85)",
              backdropFilter: "blur(8px)",
              border: "1px solid rgba(139,92,246,0.35)",
              borderRadius: 10,
              boxShadow: "0 8px 32px -8px rgba(0,0,0,0.5)",
              fontSize: 12,
              color: "#f8f9fc",
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
