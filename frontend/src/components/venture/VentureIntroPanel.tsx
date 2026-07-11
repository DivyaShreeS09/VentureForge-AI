import { ParticleField } from "../layout/ParticleField";
import { Wordmark } from "../brand/Wordmark";

const CAPABILITIES = [
  {
    title: "Real-data ML intelligence",
    detail: "Trained on 4,438 real Y Combinator company descriptions — not a hardcoded lookup.",
    accent: "violet",
  },
  {
    title: "Explainable readiness scoring",
    detail: "A transparent, versioned rubric with a factor-level breakdown, not a black-box score.",
    accent: "blue",
  },
  {
    title: "Multi-agent venture synthesis",
    detail: "A deterministic Judge Agent reconciles both outputs — no fabricated confidence.",
    accent: "gold",
  },
] as const;

const ACCENT_STYLES: Record<(typeof CAPABILITIES)[number]["accent"], string> = {
  violet: "border-l-signal-500 shadow-[inset_0_0_24px_-18px_rgba(124,44,255,0.9)]",
  blue: "border-l-current-500 shadow-[inset_0_0_24px_-18px_rgba(22,139,255,0.9)]",
  gold: "border-l-gold-500 shadow-[inset_0_0_24px_-18px_rgba(255,157,28,0.9)]",
};

const DOT_STYLES: Record<(typeof CAPABILITIES)[number]["accent"], string> = {
  violet: "bg-signal-400 shadow-[0_0_10px_2px_rgba(164,69,255,0.6)]",
  blue: "bg-current-400 shadow-[0_0_10px_2px_rgba(32,199,255,0.6)]",
  gold: "bg-gold-400 shadow-[0_0_10px_2px_rgba(255,209,102,0.6)]",
};

/** The left-side identity and pitch panel on the venture-entry screen: the official logo lockup,
 * the brand headline, a connected particle field scoped to this zone only, and three luminous
 * signal modules — real capabilities, not decorative bullet points. No data fetching here; this
 * panel is static brand content. */
export function VentureIntroPanel() {
  return (
    <div className="relative flex h-full flex-col justify-center overflow-hidden px-6 py-16 sm:px-10 lg:px-16 xl:px-24">
      <ParticleField connected />

      <div className="relative">
        <Wordmark size="hero" animate />
        <p className="mt-4 text-xs font-medium uppercase tracking-[0.3em] text-ink-muted">
          Venture Intelligence Engine
        </p>

        <h1 className="mt-8 text-display text-4xl leading-[1.05] sm:text-5xl xl:text-6xl">
          Forge an idea into an <span className="text-gold-400">investor-ready venture.</span>
        </h1>
        <p className="mt-6 max-w-lg text-lg text-ink-secondary">
          Validate the opportunity. Measure readiness. Reveal the path to scale.
        </p>

        <ul className="mt-12 space-y-3">
          {CAPABILITIES.map((c) => (
            <li
              key={c.title}
              className={`rounded-xl border border-white/10 border-l-2 bg-white/[0.03] px-5 py-4 backdrop-blur-sm ${ACCENT_STYLES[c.accent]}`}
            >
              <div className="flex items-center gap-2.5">
                <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT_STYLES[c.accent]}`} aria-hidden="true" />
                <p className="font-medium text-ink-primary">{c.title}</p>
              </div>
              <p className="mt-1 pl-4 text-sm text-ink-muted">{c.detail}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
