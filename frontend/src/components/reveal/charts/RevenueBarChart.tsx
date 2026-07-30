import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useReducedMotion } from "framer-motion";
import type { RevenueEstimate } from "../../../types/api";

interface Props {
  scenarios: NonNullable<RevenueEstimate["scenarios"]>;
}

function formatUsd(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${Math.round(v / 1_000)}K`;
  return `$${Math.round(v)}`;
}

/** The 3 real revenue scenarios (`revenue_estimate.scenarios.{conservative,base,optimistic}`) as
 * a grouped bar chart — the at-a-glance view; `RevenueScenarios.tsx`'s existing per-scenario cards
 * stay as the detailed breakdown underneath, not replaced. Only `annual_revenue_usd` is charted
 * here (the headline number); the other 3 fields per scenario remain in the detail cards. */
export function RevenueBarChart({ scenarios }: Props) {
  const prefersReduced = useReducedMotion();
  const data = [
    { name: "Conservative", revenue: scenarios.conservative.annual_revenue_usd },
    { name: "Base", revenue: scenarios.base.annual_revenue_usd },
    { name: "Optimistic", revenue: scenarios.optimistic.annual_revenue_usd },
  ];

  return (
    <div style={{ width: "100%", height: 220 }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="revenue-bar-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#b39dff" stopOpacity={1} />
              <stop offset="100%" stopColor="#6d28d9" stopOpacity={0.75} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(248,249,252,0.08)" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "rgba(248,249,252,0.6)", fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tickFormatter={formatUsd} tick={{ fill: "rgba(248,249,252,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
          <Tooltip
            cursor={{ fill: "rgba(139,92,246,0.06)" }}
            formatter={(v) => [formatUsd(Number(v)), "Annual revenue"]}
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
          <Bar
            dataKey="revenue"
            fill="url(#revenue-bar-fill)"
            radius={[6, 6, 0, 0]}
            isAnimationActive={!prefersReduced}
            animationDuration={700}
            animationEasing="ease-out"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
