import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { StarField } from "../components/layout/StarField";
import { AboutModelModal } from "../components/layout/AboutModelModal";
import { useMotionTier } from "../motion/transitions";
import landingBackground from "../assets/landing-background.jpg";

/**
 * Act I — Arrival, Scene 1: The Threshold. The hero is now `landing-background.jpg` itself —
 * the artwork already contains the wordmark, headline, tagline, and feature blocks, so this
 * component paints none of that in HTML (that would mean maintaining the same copy twice, and
 * the two would drift). The only real HTML left on top of the artwork is the three controls a
 * static image can never provide: History, About, Get Started.
 *
 * The artwork is shown whole, at its native aspect ratio, full viewport width — never cropped by
 * `object-fit: cover`, never distorted by a forced height. It sits in normal document flow
 * (`w-full h-auto`), so its rendered height is simply whatever full-bleed width implies; when that
 * exceeds the viewport, the page itself becomes the taller "cinematic poster" and scrolls a small
 * amount rather than crop the image to fit. `<main>` still carries `min-h-[100dvh]` so short
 * artwork never leaves a shorter-than-viewport page. The nav and `StarField` are viewport-`fixed`
 * (not scrolling with the poster) so they stay reachable and atmospheric regardless of page length.
 *
 * A soft cursor-driven parallax on the artwork itself (a few px of translate, spring-damped —
 * same `useMotionValue`/`useSpring` pattern `GlassCard`'s tilt already established) plus
 * `StarField`'s drifting/twinkling stars on top give the frame life without ever touching the
 * artwork's own content. Both are inert under `prefers-reduced-motion`.
 */
export function ThresholdPage() {
  const navigate = useNavigate();
  const prefersReduced = useReducedMotion();
  const sceneTransition = useMotionTier("scene");
  const [leaving, setLeaving] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);

  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const springX = useSpring(rawX, { stiffness: 40, damping: 20, mass: 0.6 });
  const springY = useSpring(rawY, { stiffness: 40, damping: 20, mass: 0.6 });
  const parallaxX = useTransform(springX, [-0.5, 0.5], [-14, 14]);
  const parallaxY = useTransform(springY, [-0.5, 0.5], [-10, 10]);

  function handlePointerMove(e: React.MouseEvent<HTMLElement>) {
    if (prefersReduced) return;
    rawX.set(e.clientX / window.innerWidth - 0.5);
    rawY.set(e.clientY / window.innerHeight - 0.5);
  }

  function handleBegin() {
    if (prefersReduced) {
      navigate("/new/idea");
      return;
    }
    setLeaving(true);
    window.setTimeout(() => navigate("/new/idea"), 280);
  }

  return (
    <main
      onMouseMove={handlePointerMove}
      className="relative min-h-[100dvh] font-forge-sans"
    >
      <motion.div
        aria-hidden="true"
        className="relative -z-20"
        style={prefersReduced ? undefined : { x: parallaxX, y: parallaxY }}
      >
        <img
          src={landingBackground}
          alt=""
          draggable={false}
          decoding="sync"
          // The whole artwork, always — never cropped by `object-fit: cover`, never distorted by
          // a forced box height. In normal document flow at full viewport width with height
          // `auto`, so the rendered height is exactly what the artwork's own 3:2 ratio implies;
          // when that's taller than the viewport, the page scrolls (see the `<main>` comment
          // above) rather than the image losing any pixel of logo, tagline, or feature-block text.
          className="block h-auto w-full select-none"
        />
      </motion.div>

      {/* A light readability pass at the very top/bottom only — the artwork is already dark
          and high-contrast almost everywhere, so a full-frame overlay would just dull it. Sized
          to the full scrollable poster (not just one viewport) since `main` is its positioning
          parent and is now exactly as tall as the artwork requires. */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-black/35 via-transparent to-black/25" />

      {/* Fixed to the viewport, not the scrolling poster — the atmosphere should stay put and the
          nav should stay reachable regardless of how tall the artwork makes the page. */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <StarField />
      </div>

      <motion.nav
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: leaving ? 0 : 1, y: 0 }}
        transition={sceneTransition}
        aria-label="Primary"
        className="fixed right-4 top-4 z-20 flex items-center gap-1 rounded-full border border-white/15 bg-white/[.06] p-1.5 pl-4 shadow-[0_8px_32px_-8px_rgba(0,0,0,0.5),0_0_28px_-6px_rgba(139,92,246,0.45),inset_0_1px_0_0_rgba(255,255,255,0.12)] backdrop-blur-xl forge-sm:right-8 forge-sm:top-8"
      >
        <Link
          to="/history"
          className="rounded-full px-4 py-2 text-forge-1 text-white/80 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-accent-2"
        >
          History
        </Link>
        <button
          type="button"
          onClick={() => setAboutOpen(true)}
          className="rounded-full px-4 py-2 text-forge-1 text-white/80 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-accent-2"
        >
          About
        </button>
        <button
          type="button"
          onClick={handleBegin}
          className="cta-border animate-cta-breathe ml-1 flex items-center gap-1.5 rounded-full bg-forge-accent px-5 py-2 text-forge-1 font-semibold text-[#1a0f00] transition-transform hover:scale-[1.03] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-accent-2"
        >
          Get Started
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M5 12h14m-6-6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </motion.nav>

      <AboutModelModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </main>
  );
}
