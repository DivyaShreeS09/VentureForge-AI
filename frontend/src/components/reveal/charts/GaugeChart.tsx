import { useId } from "react";
import { RadialBar, RadialBarChart, PolarAngleAxis } from "recharts";
import { useReducedMotion } from "framer-motion";

interface Props {
  /** 0-100. Caller is responsible for converting whatever real backend field this represents
   * (a 0-100 score, or a 0-1 probability × 100) — this component never invents or clamps toward
   * a "nicer" number. */
  value: number;
  label: string;
  /** Small caption under the number — e.g. the real `level`/`pattern_signal_display` string this
   * score came with, never a fabricated tier. */
  caption?: string;
  color?: string;
}

/** A single circular gauge — Funding Readiness / Success Probability / Industry Confidence, the
 * real 0-100-shaped scores in the analysis payload. Built on Recharts' `RadialBarChart` rather
 * than hand-rolled SVG arc math, since Recharts already ships this exact shape with built-in
 * animation/accessibility. A soft ambient glow (color-matched, blurred, `useId`-scoped so multiple
 * gauges on one page never collide) plus a gradient fill give the arc real depth instead of a flat
 * solid stroke. Renders instantly (no animation) under `prefers-reduced-motion`. */
export function GaugeChart({ value, label, caption, color = "#8b5cf6" }: Props) {
  const prefersReduced = useReducedMotion();
  const clamped = Math.max(0, Math.min(100, value));
  const gradientId = `gauge-gradient-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const data = [{ name: label, value: clamped, fill: `url(#${gradientId})` }];

  return (
    <div className="flex flex-col items-center" role="img" aria-label={`${label}: ${Math.round(clamped)}${caption ? `, ${caption}` : ""}`}>
      <div className="relative h-36 w-36">
        <div
          aria-hidden="true"
          className="absolute inset-2 rounded-full opacity-60 blur-xl"
          style={{ background: `radial-gradient(circle, ${color}55, transparent 70%)` }}
        />
        <RadialBarChart
          width={144}
          height={144}
          innerRadius="72%"
          outerRadius="100%"
          data={data}
          startAngle={90}
          endAngle={-270}
          accessibilityLayer={false}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.65} />
              <stop offset="100%" stopColor={color} stopOpacity={1} />
            </linearGradient>
          </defs>
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar
            background={{ fill: "rgba(248,249,252,0.08)" }}
            dataKey="value"
            cornerRadius={8}
            isAnimationActive={!prefersReduced}
            animationDuration={700}
            animationEasing="ease-out"
          />
        </RadialBarChart>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-forge-serif text-forge-5 font-semibold text-forge-gold">{Math.round(clamped)}</span>
          <span className="text-forge-1 text-forge-helper">/ 100</span>
        </div>
      </div>
      <p className="mt-2 text-forge-2 font-medium text-forge-heading">{label}</p>
      {caption && <p className="text-forge-1 text-forge-helper">{caption}</p>}
    </div>
  );
}
