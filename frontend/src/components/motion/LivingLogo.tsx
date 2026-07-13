import { useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";

interface OrbitDot {
  radius: number;
  duration: number;
  size: number;
  color: string;
  delay: number;
}

const ORBIT_DOTS: OrbitDot[] = [
  { radius: 150, duration: 14, size: 5, color: "#a445ff", delay: 0 },
  { radius: 190, duration: 22, size: 4, color: "#20c7ff", delay: -6 },
  { radius: 170, duration: 30, size: 6, color: "#ffd166", delay: -14 },
];

/** Wraps the hero logo stack with the "living energy reactor" treatment: a slow float, a subtle
 * cursor-parallax lean, and a few orbiting particle dots (violet/blue, one gold) — never a
 * generic static image. Fully inert under `prefers-reduced-motion`: no float, no parallax, no
 * orbit, just the logo itself. */
export function LivingLogo({ children }: { children: ReactNode }) {
  const prefersReduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (prefersReduced) return;
    function onMove(e: MouseEvent) {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) / (window.innerWidth / 2);
      const dy = (e.clientY - cy) / (window.innerHeight / 2);
      setTilt({ x: Math.max(-1, Math.min(1, dx)) * 10, y: Math.max(-1, Math.min(1, dy)) * 8 });
    }
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [prefersReduced]);

  return (
    <div ref={ref} className="relative mx-auto flex justify-center">
      {!prefersReduced && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden="true">
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
      <div
        style={
          prefersReduced
            ? undefined
            : { transform: `translate3d(${tilt.x}px, ${tilt.y}px, 0)`, transition: "transform 0.4s ease-out" }
        }
      >
        <div className={prefersReduced ? "" : "animate-float"}>{children}</div>
      </div>
    </div>
  );
}
