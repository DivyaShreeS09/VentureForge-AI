const RADIUS = 78;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** The exact bands the deterministic backend rubric defines (backend/app/ml/funding_readiness.py,
 * LEVEL_THRESHOLDS: ready >= 70, developing >= 40, early_stage otherwise). This component only
 * humanizes that real value for display — it never invents extra bands or finer-grained precision
 * than the backend actually computes. */
const LEVEL_LABEL: Record<string, string> = {
  ready: "Investor Ready",
  developing: "Building Momentum",
  early_stage: "Idea Formation",
};

/** Venture Readiness Reactor: a radial energy display inspired by the logo's forge core. Gold arc
 * intensity represents the real 0-100 score; violet and blue context rings are decorative framing
 * only, not additional data channels. The numeric score and real band label are always rendered as
 * text alongside the visual — never gauge-only, so the value is never conveyed by color alone. */
export function ReadinessReactor({ score, level }: { score: number; level: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  const offset = CIRCUMFERENCE * (1 - clamped / 100);
  const intensity = 0.35 + (clamped / 100) * 0.65;
  const bandLabel = LEVEL_LABEL[level] ?? level.replace("_", " ");

  return (
    <div className="flex flex-wrap items-center gap-6 sm:gap-8">
      <div className="relative flex h-44 w-44 shrink-0 items-center justify-center">
        <div
          className="absolute inset-0 rounded-full blur-xl"
          style={{ backgroundColor: `rgba(255, 157, 28, ${intensity * 0.18})` }}
          aria-hidden="true"
        />
        <svg width="176" height="176" viewBox="0 0 176 176" role="img" aria-label={`Funding readiness score: ${clamped} out of 100, ${bandLabel}`}>
          <circle cx="88" cy="88" r={86} fill="none" stroke="rgba(124,44,255,0.18)" strokeWidth="1" strokeDasharray="2 6" />
          <circle cx="88" cy="88" r={96} fill="none" stroke="rgba(22,139,255,0.14)" strokeWidth="1" strokeDasharray="1 5" />
          <circle cx="88" cy="88" r={RADIUS} fill="none" stroke="rgba(245,247,255,0.07)" strokeWidth="10" />
          <circle
            cx="88"
            cy="88"
            r={RADIUS}
            fill="none"
            stroke="#ff9d1c"
            strokeOpacity={intensity}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            transform="rotate(-90 88 88)"
            className="transition-[stroke-dashoffset] duration-900 ease-out"
            style={{ filter: `drop-shadow(0 0 ${8 + intensity * 10}px rgba(255,157,28,${intensity * 0.7}))` }}
          />
          <text x="88" y="82" textAnchor="middle" className="fill-ink-primary text-display" style={{ fontSize: "34px" }}>
            {clamped}
          </text>
          <text x="88" y="104" textAnchor="middle" className="fill-ink-muted" style={{ fontSize: "12px" }}>
            / 100
          </text>
        </svg>
      </div>
      <div>
        <p className="text-xs uppercase tracking-[0.15em] text-ink-muted">Readiness band</p>
        <p className="mt-1 text-display text-2xl text-ink-primary">{bandLabel}</p>
        <p className="mt-1 text-xs text-ink-muted">See Advanced below for how this was calculated</p>
      </div>
    </div>
  );
}
