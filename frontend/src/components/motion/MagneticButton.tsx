import { motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import { useState, type ButtonHTMLAttributes, type ReactNode } from "react";

type NativeButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart" | "onAnimationEnd" | "onAnimationIteration"
>;

interface Props extends NativeButtonProps {
  children: ReactNode;
  className?: string;
}

interface Ripple {
  id: number;
  x: number;
  y: number;
}

const PULL = 0.25;
const MAX_OFFSET = 10;

/** The primary-CTA button treatment: leans slightly toward the cursor, compresses on press, and
 * emits a soft energy ripple from the click point — "hover -> lean -> click -> compress -> ripple
 * -> return". Used deliberately on the small set of primary CTAs, not every button in the app.
 * Fully inert under reduced-motion: no lean, no press-scale, no ripple — just a plain button. */
export function MagneticButton({ children, className = "", onClick, ...rest }: Props) {
  const prefersReduced = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 300, damping: 20, mass: 0.5 });
  const springY = useSpring(y, { stiffness: 300, damping: 20, mass: 0.5 });
  const [ripples, setRipples] = useState<Ripple[]>([]);

  function handleMove(e: React.MouseEvent<HTMLButtonElement>) {
    if (prefersReduced) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const offsetX = e.clientX - (rect.left + rect.width / 2);
    const offsetY = e.clientY - (rect.top + rect.height / 2);
    x.set(Math.max(-MAX_OFFSET, Math.min(MAX_OFFSET, offsetX * PULL)));
    y.set(Math.max(-MAX_OFFSET, Math.min(MAX_OFFSET, offsetY * PULL)));
  }

  function handleLeave() {
    x.set(0);
    y.set(0);
  }

  function handleClick(e: React.MouseEvent<HTMLButtonElement>) {
    if (!prefersReduced) {
      const rect = e.currentTarget.getBoundingClientRect();
      const id = Date.now();
      setRipples((prev) => [...prev, { id, x: e.clientX - rect.left, y: e.clientY - rect.top }]);
      setTimeout(() => setRipples((prev) => prev.filter((r) => r.id !== id)), 650);
    }
    onClick?.(e);
  }

  return (
    <motion.button
      {...rest}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      onClick={handleClick}
      whileTap={prefersReduced ? undefined : { scale: 0.96 }}
      style={prefersReduced ? undefined : { x: springX, y: springY }}
      className={`relative overflow-hidden ${className}`}
    >
      {children}
      {ripples.map((r) => (
        <motion.span
          key={r.id}
          className="pointer-events-none absolute rounded-full bg-white/40"
          style={{ left: r.x, top: r.y, width: 10, height: 10, marginLeft: -5, marginTop: -5 }}
          initial={{ scale: 0, opacity: 0.6 }}
          animate={{ scale: 18, opacity: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      ))}
    </motion.button>
  );
}
