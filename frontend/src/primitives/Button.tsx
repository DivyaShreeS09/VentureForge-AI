import { forwardRef } from "react";
import { motion } from "framer-motion";
import { useMotionTier } from "../motion/transitions";

export type ButtonVariant = "primary" | "secondary" | "ghost";

// Native button drag/animation event handlers conflict with Framer Motion's own
// (differently-typed) props of the same name on `motion.button` — omitted here since
// this product never needs native drag events on a button.
type NativeButtonProps = Omit<
  React.ButtonHTMLAttributes<HTMLButtonElement>,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart" | "onAnimationEnd" | "onAnimationIteration"
>;

export interface ButtonProps extends NativeButtonProps {
  variant?: ButtonVariant;
}

// Design System Bible §7 — the one button component in the product. `primary` is the
// single forward action per screen (solid Forge Copper fill); `secondary` carries one
// hairline border; `ghost` is text-only. No fourth variant exists — a screen needing a
// fourth kind of action is a sign it wants a different scene, not a new button style.
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", className = "", children, disabled, ...rest },
  ref,
) {
  const transition = useMotionTier("micro");

  const base =
    "inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-forge-md " +
    "px-6 py-3 text-forge-3 font-medium transition-colors " +
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 " +
    "focus-visible:outline-forge-accent disabled:cursor-not-allowed";

  // Disabled `primary` does NOT reuse the gradient fill at reduced opacity — dimming a
  // saturated amber-to-orange gradient down to ~24% renders as a muddy dark brown blob
  // against the near-black canvas (confirmed via a real screenshot), reading as broken
  // rather than intentionally inactive. A plain opacity-dimmed fill went too far the
  // other way in a second real screenshot check — with no fill and no border at all, it
  // stopped reading as a button shape entirely. A visible (if faint) bordered pill,
  // matching `secondary`'s own resting silhouette, is what actually reads as "a real
  // button, just not ready yet" rather than either broken or invisible.
  const disabledPrimary = "border border-forge-text/[.12] bg-forge-text/[.05] text-forge-text-tertiary shadow-none";

  const variants: Record<ButtonVariant, string> = {
    // `text-forge-canvas` looked right (it's near-black in dark mode, on the still-
    // amber accent) but silently fails WCAG AA in light mode: `forge-canvas` flips to
    // near-white there, sitting on the *same* mid-tone accent — confirmed via a real
    // in-browser axe-core scan (jsdom's color-contrast check can't catch this; it needs
    // actual rendered/painted colors). The accent is a mid-tone in both themes, so the
    // fix is a foreground that's always dark rather than theme-reactive — pinned as a
    // literal (matching dark mode's own canvas value) rather than invented ad hoc.
    // Confirmed against both new gradient stops via the relative-luminance formula:
    // amber-bg 10.91:1, orange-bg 7.65:1 — both comfortably pass.
    primary: disabled
      ? disabledPrimary
      : "bg-gradient-to-r from-forge-accent to-forge-accent-secondary text-[#0B0710] " +
        "hover:brightness-110 active:brightness-95",
    secondary:
      "border border-forge-text/[.16] bg-transparent text-forge-text hover:border-forge-text/[.32] disabled:opacity-[0.4]",
    ghost: "bg-transparent text-forge-text-secondary hover:text-forge-text disabled:opacity-[0.4]",
  };

  // Only the primary CTA lifts on hover — a secondary/ghost action doesn't compete for
  // attention with the one forward action on a screen (Rule of Subtraction).
  const hoverLift = !disabled && variant === "primary" ? { y: -2 } : undefined;

  return (
    <motion.button
      ref={ref}
      type="button"
      whileHover={hoverLift}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={transition}
      disabled={disabled}
      className={`${base} ${variants[variant]} ${
        variant === "primary" && !disabled ? "shadow-[0_4px_20px_-8px_rgba(255,176,32,0.35)]" : ""
      } ${className}`}
      {...rest}
    >
      {children}
    </motion.button>
  );
});
