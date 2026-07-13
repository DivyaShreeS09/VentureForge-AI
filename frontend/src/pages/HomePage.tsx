import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ForgeCore } from "../components/forge/ForgeCore";
import { LivingLogo } from "../components/motion/LivingLogo";
import { MagneticButton } from "../components/motion/MagneticButton";
import { ParticleField } from "../components/layout/ParticleField";
import { Wordmark } from "../components/brand/Wordmark";

const FEATURES = [
  { title: "Real Data", detail: "Backed by real market data", icon: "M12 2v20M2 12h20" },
  { title: "Explainable AI", detail: "Transparent reasoning you can trust", icon: "M12 16v-4m0-4h.01" },
  { title: "Investor Focused", detail: "Built for early-stage venture evaluation", icon: "M3 17l6-6 4 4 8-8" },
  { title: "Secure & Private", detail: "Your data stays in your browser", icon: "M12 2l8 4v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-4Z" },
];

/** The single entry screen: identity, the Forge Core at rest, the pitch, and one CTA into the
 * analysis flow. No login, no fake stats, no plans — anonymous workspace only, per the brief. */
export function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 py-20 text-center sm:px-10">
      <ParticleField connected />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative"
      >
        <LivingLogo>
          <div className="mx-auto flex justify-center">
            <ForgeCore state="idle" progress={0} />
          </div>
          <Wordmark size="hero" className="mx-auto mt-6 flex justify-center" />
        </LivingLogo>

        <h1 className="mt-10 text-display text-4xl leading-[1.05] sm:text-5xl xl:text-6xl">
          Forge an idea into an <span className="text-gold-400">investor-ready venture.</span>
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-lg text-ink-secondary">
          AI-powered venture intelligence that analyzes, validates, and elevates your startup.
        </p>

        <MagneticButton
          onClick={() => navigate("/new/idea")}
          className="btn-energy mt-10 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-signal-600 via-signal-500 to-current-500 px-8 py-4 text-base font-semibold text-ink-primary shadow-glow transition duration-300 hover:brightness-110 hover:shadow-glow-blue focus-visible:outline-none"
        >
          Start New Analysis
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14m-6-6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </MagneticButton>

        <div className="mx-auto mt-14 grid max-w-2xl grid-cols-2 gap-4 sm:grid-cols-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 + i * 0.08 }}
              className="hover-lift rounded-xl border border-white/10 bg-white/[0.03] p-4 text-left"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5 text-signal-400" fill="none" stroke="currentColor" strokeWidth="1.75">
                <path d={f.icon} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="mt-2 text-sm font-medium text-ink-primary">{f.title}</p>
              <p className="mt-0.5 text-xs text-ink-muted">{f.detail}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
