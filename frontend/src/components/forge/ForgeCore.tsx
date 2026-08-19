import { motion } from "framer-motion";
import emblem from "../../assets/ventureforge-emblem.webp";
import { useMotionTier } from "../../motion/transitions";

const RADIUS = 88;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export type ForgeCoreState = "running" | "done" | "error";

interface Props {
  state: ForgeCoreState;
  /** Real fraction (0-1) of real founder-facing stages reached so far — see stageOrder.ts.
   * Never a simulated timer. */
  progress: number;
}

// Decorative orbiting sparks around the ring, shown only while `running` — the Analysis
// screen's one hero moment ("living AI command center"), never a substitute for the real
// progress ring itself and never shown once a real terminal state is reached.
const ORBIT_SPARKS = [
  { radius: 118, duration: "9s", delay: "0s", color: "bg-forge-accent-2" },
  { radius: 104, duration: "13s", delay: "-4s", color: "bg-forge-accent-3" },
  { radius: 126, duration: "17s", delay: "-8s", color: "bg-forge-accent" },
];

/** Calm, focused, purposeful — not a loading spinner. One ring carrying the real progress
 * (electric-purple while running — orange is reserved for CTA/warnings/energy, not the app's
 * dominant identity), filling only as real stages complete, using the `threshold` motion tier
 * (a stage boundary is a meaningful state change, not a per-frame animation).
 * `done`/`error` reuse the same semantic confirmed/risk tokens Chip already uses elsewhere.
 * While running, a soft electric-purple glow and a few slow orbiting sparks (aria-hidden,
 * purely decorative) evoke "AI thinking" for this page's one hero moment — the ring's real
 * math (`RADIUS`/`CIRCUMFERENCE`/`strokeDashoffset`) and state contract are untouched. */
export function ForgeCore({ state, progress }: Props) {
  const transition = useMotionTier("threshold");
  const clamped = Math.max(0, Math.min(1, progress));
  const offset = CIRCUMFERENCE * (1 - clamped);
  const ringClass = state === "error" ? "stroke-forge-risk" : state === "done" ? "stroke-forge-confirmed" : "stroke-forge-accent-2";
  const running = state === "running";

  return (
    <div className="relative flex h-56 w-56 items-center justify-center">
      {running &&
        ORBIT_SPARKS.map((spark, i) => (
          <span
            key={i}
            aria-hidden="true"
            className={`absolute h-1.5 w-1.5 rounded-full ${spark.color} animate-orbit opacity-70`}
            style={{
              // @ts-expect-error -- custom property consumed by the `orbit` keyframe in tailwind.config.js
              "--orbit-radius": `${spark.radius}px`,
              animationDuration: spark.duration,
              animationDelay: spark.delay,
            }}
          />
        ))}
      <svg
        width="224"
        height="224"
        viewBox="0 0 224 224"
        aria-hidden="true"
        className={running ? "drop-shadow-[0_0_24px_rgba(139,92,246,0.4)]" : ""}
      >
        {/* Matches the same faint-track opacity already used for "upcoming" stage dots in
            ForgeSequence's checklist (bg-forge-text/[.16]) — a lower value made the unfilled
            ring track nearly invisible against the canvas at low progress, reading as a stray
            floating arc rather than a ring (confirmed via a live screenshot during a prior
            sprint's audit). */}
        <circle cx="112" cy="112" r={RADIUS} fill="none" className="stroke-forge-text/[.16]" strokeWidth="6" />
        <motion.circle
          cx="112"
          cy="112"
          r={RADIUS}
          fill="none"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          initial={false}
          animate={{ strokeDashoffset: offset }}
          transition={transition}
          transform="rotate(-90 112 112)"
          className={ringClass}
        />
      </svg>
      <img src={emblem} alt="" aria-hidden="true" className="absolute w-16 opacity-90" />
    </div>
  );
}
