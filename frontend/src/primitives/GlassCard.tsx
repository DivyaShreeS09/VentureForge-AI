import { forwardRef, useState, type HTMLAttributes, type ReactNode } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform, type HTMLMotionProps } from "framer-motion";
import { useMotionTier } from "../motion/transitions";

type MotionOverride = HTMLMotionProps<"div">["initial"];
type AnimateOverride = HTMLMotionProps<"div">["animate"];
type ExitOverride = HTMLMotionProps<"div">["exit"];
type TransitionOverride = HTMLMotionProps<"div">["transition"];

export type GlassCardGlow = "accent" | "accent-2" | "accent-3" | "none";

// Native div drag/animation event handlers conflict with Framer Motion's own
// (differently-typed) props of the same name on `motion.div` — omitted here, matching
// the pattern already established in Button.tsx.
type NativeDivProps = Omit<
  HTMLAttributes<HTMLDivElement>,
  | "onDrag"
  | "onDragStart"
  | "onDragEnd"
  | "onAnimationStart"
  | "onAnimationEnd"
  | "onAnimationIteration"
  | "onMouseMove"
  | "onMouseLeave"
>;

export interface GlassCardProps extends NativeDivProps {
  /** Adds a matching ambient glow shadow. Use sparingly — per the Rule of Subtraction, a
   * glow should mark the one focal element on a screen, not decorate every card. Defaults
   * to "none". */
  glow?: GlassCardGlow;
  /** Subtle lift + brighter border on hover, plus a gentle mouse-tracking tilt, an
   * intensifying edge glow (matching the card's own `glow` color), and a soft shine sweep — reserved for genuinely
   * interactive cards (wraps a button/expandable control), never a purely decorative
   * panel, matching this prop's existing meaning. Also gates whether the mouse-tracking
   * spring machinery is instantiated at all (see `InteractiveGlassCard` below) — a purely
   * decorative card pays zero cost for an interaction it never offers. */
  interactive?: boolean;
  /** Optional overrides for the shell's own mount animation — used by callers (e.g.
   * `HistoryPage`'s list, which needs `AnimatePresence`'s `exit` on each row) that need this
   * particular instance to animate differently from the default fade-and-rise. */
  initial?: MotionOverride;
  animate?: AnimateOverride;
  exit?: ExitOverride;
  transition?: TransitionOverride;
}

const glowClass: Record<GlassCardGlow, string> = {
  accent: "shadow-glow-forge-accent",
  "accent-2": "shadow-glow-forge-accent-2",
  "accent-3": "shadow-glow-forge-accent-3",
  none: "",
};

const SHELL_CLASSES =
  "relative overflow-hidden rounded-forge-lg border border-forge-surface-border bg-forge-surface-1/60 backdrop-blur-md " +
  "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.12),inset_0_-1px_0_0_rgba(0,0,0,0.35),inset_1px_0_0_0_rgba(255,255,255,0.05),inset_-1px_0_0_0_rgba(0,0,0,0.18)] ";

// The "metallic rim" read: a light source from the top-left (bright inset top+left edges, dark
// inset bottom+right edges) — the same cue brushed metal under glass actually has. Combined into
// a single `boxShadow` string (rather than a separate Tailwind class) for the interactive variant
// specifically, because Framer Motion's `animate.boxShadow` fully replaces any CSS box-shadow set
// via className — the edge glow and the bevel have to travel together in one string or the bevel
// would disappear the instant the edge-glow animation takes over.
const BEVEL_SHADOW = "inset 0 1px 0 0 rgba(255,255,255,0.12), inset 0 -1px 0 0 rgba(0,0,0,0.35), inset 1px 0 0 0 rgba(255,255,255,0.05), inset -1px 0 0 0 rgba(0,0,0,0.18)";

const TILT_RANGE = 6; // degrees, small and premium, never gimmicky

// The hover edge-glow's color follows the same `glow` prop as the card's ambient shadow — a card
// asking for a gold ambient glow (`glow="accent"`) gets a gold edge reflection on hover too, not a
// hardcoded purple that ignored the prop. "none" still gets a neutral purple micro-glow on hover
// (interactive cards should always confirm the hover with *something*), just fainter than an
// explicit color choice.
const EDGE_GLOW_RGB: Record<GlassCardGlow, string> = {
  accent: "255,176,32",
  "accent-2": "139,92,246",
  "accent-3": "99,230,232",
  none: "139,92,246",
};

function restEdgeGlow(): string {
  return `0 0 0px 0px rgba(139,92,246,0), ${BEVEL_SHADOW}`;
}
function hoverEdgeGlow(glow: GlassCardGlow): string {
  const intensity = glow === "none" ? 0.28 : 0.5;
  return `0 0 32px -6px rgba(${EDGE_GLOW_RGB[glow]},${intensity}), ${BEVEL_SHADOW}`;
}

interface InnerProps extends NativeDivProps {
  glow: GlassCardGlow;
  className: string;
  children?: ReactNode;
  initial?: MotionOverride;
  animate?: AnimateOverride;
  exit?: ExitOverride;
  transition?: TransitionOverride;
}

/** The plain, static shell — used by the majority of `GlassCard` call sites (chart wrappers,
 * decorative panels). No `useMotionValue`/`useSpring`/`useTransform` at all: a card that never
 * responds to the pointer shouldn't pay for the physics simulation that would drive that
 * response, and mounting dozens of idle springs across a data-dense page like the Reveal
 * dashboard is real, measurable overhead for zero visual benefit. */
const StaticGlassCard = forwardRef<HTMLDivElement, InnerProps>(function StaticGlassCard(
  { glow, className, children, initial, animate, exit, transition, ...rest },
  ref,
) {
  const entranceTransition = useMotionTier("threshold");
  return (
    <motion.div
      ref={ref}
      initial={initial ?? { opacity: 0, y: 10 }}
      animate={animate ?? { opacity: 1, y: 0 }}
      exit={exit}
      transition={transition ?? entranceTransition}
      className={`${SHELL_CLASSES}${glowClass[glow]} ${className}`}
      {...rest}
    >
      {/* Same top-edge inner highlight the interactive variant gets — a physical surface catches
          ambient light along its top rim even when it never responds to the pointer. */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent"
      />
      {children}
    </motion.div>
  );
});

/** The premium micro-interaction variant — a small mouse-tracking tilt (the same rect-relative-
 * offset + spring pattern `MagneticButton.tsx` already established, extended with `useTransform`
 * for rotation rather than translation), an intensifying edge glow (matching the card's own `glow` color), and a soft diagonal
 * shine sweep, all inert under `prefers-reduced-motion` and all keyed off the existing
 * `micro`/`scene` motion tiers. Only mounted when `interactive` is true. */
const InteractiveGlassCard = forwardRef<HTMLDivElement, InnerProps>(function InteractiveGlassCard(
  { glow, className, children, initial, animate, exit, transition, ...rest },
  ref,
) {
  const entranceTransition = useMotionTier("threshold");
  const microTransition = useMotionTier("micro");
  const prefersReduced = useReducedMotion();
  const [hovered, setHovered] = useState(false);

  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const springX = useSpring(rawX, { stiffness: 260, damping: 22, mass: 0.5 });
  const springY = useSpring(rawY, { stiffness: 260, damping: 22, mass: 0.5 });
  const rotateX = useTransform(springY, [-0.5, 0.5], [TILT_RANGE, -TILT_RANGE]);
  const rotateY = useTransform(springX, [-0.5, 0.5], [-TILT_RANGE, TILT_RANGE]);
  // Content shifts a few px opposite the tilt — glass reads as a distinct layer floating above the
  // card's backing surface (a "glass depth" cue) rather than the whole card rotating as one flat
  // plane. Driven by the same tracked pointer position, not a second mechanism.
  const contentX = useTransform(springX, [-0.5, 0.5], [-3, 3]);
  const contentY = useTransform(springY, [-0.5, 0.5], [-3, 3]);
  // The cursor-lighting spotlight: a radial highlight whose *position* (not just opacity) tracks
  // the pointer, so the card reads as a lit physical surface rather than a flat overlay fading in.
  const spotlightX = useTransform(springX, [-0.5, 0.5], ["0%", "100%"]);
  const spotlightY = useTransform(springY, [-0.5, 0.5], ["0%", "100%"]);
  const spotlightBackground = useTransform([spotlightX, spotlightY], ([x, y]) =>
    `radial-gradient(320px circle at ${x} ${y}, rgba(255,255,255,0.10), transparent 70%)`,
  );

  const tiltEnabled = !prefersReduced;

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!tiltEnabled) return;
    const rect = e.currentTarget.getBoundingClientRect();
    rawX.set((e.clientX - rect.left) / rect.width - 0.5);
    rawY.set((e.clientY - rect.top) / rect.height - 0.5);
    setHovered(true);
  }

  function handleMouseLeave() {
    if (!tiltEnabled) return;
    rawX.set(0);
    rawY.set(0);
    setHovered(false);
  }

  return (
    <motion.div
      ref={ref}
      initial={initial ?? { opacity: 0, y: 10 }}
      animate={
        animate ?? {
          opacity: 1,
          y: 0,
          ...(tiltEnabled ? { boxShadow: hovered ? hoverEdgeGlow(glow) : restEdgeGlow() } : null),
        }
      }
      exit={exit}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={tiltEnabled ? { rotateX, rotateY, transformPerspective: 800 } : undefined}
      transition={transition ?? (tiltEnabled ? { ...entranceTransition, boxShadow: microTransition } : entranceTransition)}
      className={`${SHELL_CLASSES}${glowClass[glow]} hover-lift ${className}`}
      {...rest}
    >
      {/* A static inner highlight along the top edge — the "brushed titanium under glass" read:
          a physical surface catches ambient light along its top rim even at rest, not only on
          hover. */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent"
      />
      {tiltEnabled ? <motion.div style={{ x: contentX, y: contentY }}>{children}</motion.div> : children}
      {tiltEnabled && (
        <>
          {/* Cursor-lighting spotlight — its position, not just its opacity, tracks the pointer. */}
          <motion.span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            initial={false}
            animate={{ opacity: hovered ? 1 : 0 }}
            transition={microTransition}
            style={{ background: spotlightBackground }}
          />
          {/* A soft diagonal shine sweep — inner-light/metallic-reflection read, not a gloss
              sticker. Masked to the card's own rounded corners via `overflow-hidden` above. */}
          <motion.span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[.10] via-transparent to-transparent"
            initial={false}
            animate={{ opacity: hovered ? 1 : 0, x: hovered ? "0%" : "-30%" }}
            transition={microTransition}
          />
        </>
      )}
    </motion.div>
  );
});

/**
 * The one glass-panel primitive for the cosmic redesign — a translucent, blurred,
 * bordered surface used to give a single moment real presence (a hero verdict, a
 * decision card) against the ambient starfield behind it. Not a default wrapper for
 * every piece of content: per the Rule of Subtraction, most screens should still read as
 * generous whitespace (see Scene.tsx's own reasoning) — reach for this only where a
 * genuine focal point needs framing.
 *
 * Dispatches to one of two internal implementations based on `interactive` — a stable
 * per-call-site choice, so switching never causes unexpected remounts in practice — so the
 * mouse-tracking spring machinery only exists where it's actually used.
 *
 * Plain `div` by default with no interactive semantics baked in; callers add
 * `role`/`tabIndex` themselves if the card becomes clickable.
 */
export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(function GlassCard(
  { glow = "none", interactive = false, className = "", ...rest },
  ref,
) {
  const Impl = interactive ? InteractiveGlassCard : StaticGlassCard;
  return <Impl ref={ref} glow={glow} className={className} {...rest} />;
});
