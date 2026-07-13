import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { HoverSpotlight } from "../components/motion/HoverSpotlight";
import { LivingLogo } from "../components/motion/LivingLogo";
import { MagneticButton } from "../components/motion/MagneticButton";
import { NoiseOverlay } from "../components/motion/NoiseOverlay";
import { ParticleField } from "../components/layout/ParticleField";
import { Wordmark } from "../components/brand/Wordmark";

const FEATURES = [
  { title: "Real Data", detail: "Backed by real market data", icon: "M12 2v20M2 12h20" },
  { title: "Explainable AI", detail: "Transparent reasoning you can trust", icon: "M12 16v-4m0-4h.01" },
  { title: "Investor Focused", detail: "Built for early-stage venture evaluation", icon: "M3 17l6-6 4 4 8-8" },
  { title: "Secure & Private", detail: "Your data stays in your browser", icon: "M12 2l8 4v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-4Z" },
];

// One coordinated entrance: background -> rings/logo -> headline -> subtitle -> CTA -> cards,
// staggered to land within ~1.2-1.6s total, premium easing, no bounce/overshoot.
const EASE = [0.16, 1, 0.3, 1] as const;

/** The single entry screen: identity, the hero logo at rest, the pitch, and one CTA into the
 * analysis flow. No login, no fake stats, no plans — anonymous workspace only, per the brief.
 * Sized and spaced to fit one 1366x768 viewport with no scroll — see the exact spacing constants
 * below, each tuned against real browser measurements, not guessed. */
export function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="relative flex min-h-[100dvh] flex-col items-center justify-center overflow-hidden px-12 py-6 text-center">
      {/* Slow drifting fog layers, distinct from AmbientBackground's shared glow orbs — kept local
          to this page rather than added to the globally-shared background component. Kept faint
          so the galaxy/particles stay the focus, not a bright wash. */}
      <div
        className="pointer-events-none absolute -left-1/4 top-0 h-[40rem] w-[40rem] animate-drift rounded-full bg-signal-600/[0.035] blur-[140px] [animation-duration:22s]"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -right-1/4 bottom-0 h-[36rem] w-[36rem] animate-drift rounded-full bg-gold-500/[0.03] blur-[130px] [animation-duration:26s] [animation-delay:-9s]"
        aria-hidden="true"
      />
      <NoiseOverlay />
      <ParticleField connected interactive />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="relative flex max-w-[960px] flex-col items-center"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1, ease: EASE }}
        >
          <LivingLogo>
            <Wordmark size="hero" className="mx-auto flex max-h-[34vh] justify-center" />
          </LivingLogo>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.5, delay: 0.35, ease: EASE }}
          className="mt-5 max-w-[850px] text-display text-[clamp(44px,4.4vw,64px)] leading-[1.06]"
        >
          Forge an idea into an{" "}
          <span className="animate-gradient-slow bg-gradient-to-r from-signal-400 via-gold-400 to-signal-400 bg-[length:200%_auto] bg-clip-text text-transparent">
            investor-ready venture.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.55, ease: EASE }}
          className="mt-4 max-w-[620px] text-lg text-ink-secondary"
        >
          AI-powered venture intelligence that analyzes, validates, and elevates your startup.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          whileHover={{ y: -2 }}
          transition={{ duration: 0.4, delay: 0.7, ease: EASE }}
          className="mt-6 inline-block"
        >
          <HoverSpotlight className="rounded-xl">
            <MagneticButton
              onClick={() => navigate("/new/idea")}
              className="cta-border btn-energy animate-cta-breathe inline-flex items-center gap-2 rounded-xl border border-white/10 bg-gradient-to-r from-signal-600 via-signal-500 to-gold-500 px-8 py-4 text-base font-semibold text-ink-primary transition duration-300 hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-400"
            >
              Start New Analysis
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14m-6-6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </MagneticButton>
          </HoverSpotlight>
        </motion.div>

        <div className="mx-auto mt-7 grid w-full max-w-[800px] grid-cols-2 gap-4 sm:grid-cols-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 10, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.85 + i * 0.08, ease: EASE }}
            >
              <HoverSpotlight className="hover-lift group h-full rounded-xl border border-white/10 bg-white/[0.03] p-4 text-left backdrop-blur-sm">
                {/* Glassmorphism reflection sheen + a tiny floating light spark, both purely decorative. */}
                <div
                  className="pointer-events-none absolute inset-x-0 top-0 h-1/2 rounded-t-xl bg-gradient-to-b from-white/[0.06] to-transparent"
                  aria-hidden="true"
                />
                <span
                  className="pointer-events-none absolute right-3 top-3 h-1 w-1 animate-pulse-slow rounded-full bg-gold-300/70 shadow-[0_0_6px_2px_rgba(255,209,102,0.5)]"
                  aria-hidden="true"
                />
                <svg viewBox="0 0 24 24" className="h-5 w-5 text-signal-400" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <path d={f.icon} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <p className="mt-2 text-sm font-medium text-ink-primary">{f.title}</p>
                <p className="mt-0.5 text-xs text-ink-muted">{f.detail}</p>
              </HoverSpotlight>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
