import { motion } from "framer-motion";
import { useMotionTier } from "../motion/transitions";

export interface ChoiceCardProps {
  label: string;
  selected: boolean;
  onSelect: () => void;
  mode?: "single" | "multi";
  description?: string;
}

// Design System Bible §7 — every multiple-choice moment (Who's It For, the Evidence
// Conversation's answers) uses this one card. `surface-1` at rest, an accent-tinted
// (16% opacity) background plus a 2px lift on selection — never a color flash, never a
// bounce (Design Bible §8: motion always settles).
export function ChoiceCard({ label, selected, onSelect, mode = "single", description }: ChoiceCardProps) {
  const transition = useMotionTier("scene");

  return (
    <motion.button
      type="button"
      role={mode === "multi" ? "checkbox" : "radio"}
      aria-checked={selected}
      onClick={onSelect}
      animate={{ y: selected ? -2 : 0 }}
      transition={transition}
      className={[
        "min-h-[44px] w-full rounded-forge-md border px-4 py-3 text-left text-forge-3",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-accent",
        selected
          ? "border-forge-accent-2 bg-forge-accent-2/[.16] text-forge-text"
          : "border-forge-text/[.16] bg-forge-surface-1 text-forge-text-secondary hover:border-forge-text/[.32]",
      ].join(" ")}
    >
      <span className="block font-medium">{label}</span>
      {description && selected && (
        <span className="mt-1 block text-forge-1 text-forge-text-tertiary">{description}</span>
      )}
    </motion.button>
  );
}
