import { useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

interface OrbitDot {
  radius: number;
  duration: number;
  size: number;
  color: string;
  delay: number;
}

const ORBIT_DOTS: OrbitDot[] = [
  { radius: 150, duration: 18, size: 4, color: "#a445ff", delay: 0 },
  { radius: 185, duration: 28, size: 3, color: "#ffd166", delay: -12 },
];

/** The single hero logo's decorative treatment: two faint rings rotating at different, very slow
 * speeds behind the mark, and a soft autonomous orange core pulse — never anything that moves the
 * logo itself. The logo's position is fixed; only the decoration around it animates, and none of
 * it is driven by the cursor (no parallax, no tilt, no float). Fully inert under
 * `prefers-reduced-motion`. */
export function LivingLogo({ children }: { children: ReactNode }) {
  const prefersReduced = useReducedMotion();

  return (
    <div className="relative mx-auto flex justify-center">
      {!prefersReduced && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <div
            className="absolute animate-pulse-slow rounded-full blur-3xl"
            style={{
              width: "70%",
              height: "70%",
              background: "radial-gradient(circle, rgba(255,157,28,0.16), transparent 65%)",
            }}
          />
          <span className="absolute h-[85%] w-[85%] animate-spin-slow rounded-full border border-signal-400/15" />
          <span className="absolute h-[70%] w-[70%] animate-spin-reverse-slow rounded-full border border-gold-400/10" />
          {ORBIT_DOTS.map((dot, i) => (
            <span
              key={i}
              className="absolute animate-orbit rounded-full"
              style={{
                width: dot.size,
                height: dot.size,
                backgroundColor: dot.color,
                boxShadow: `0 0 8px 2px ${dot.color}80`,
                // @ts-expect-error -- custom property consumed by the `orbit` keyframe
                "--orbit-radius": `${dot.radius}px`,
                animationDuration: `${dot.duration}s`,
                animationDelay: `${dot.delay}s`,
              }}
            />
          ))}
        </div>
      )}
      {children}
    </div>
  );
}
