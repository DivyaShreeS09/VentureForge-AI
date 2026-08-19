import type { InputMode } from "../../context/NewAnalysisContext";

interface Props {
  mode: InputMode;
  onChange: (mode: InputMode) => void;
}

const OPTIONS: { value: InputMode; label: string }[] = [
  { value: "beginner", label: "Beginner" },
  { value: "advanced", label: "Advanced" },
];

/** Founder Input Experience Redesign: one persistent, global mode — deliberately not the Tabs
 * primitive (Design System Bible reserves that exclusively for the Bigger Picture pane switcher)
 * and not a fourth Button variant (the Bible caps Button at three). A small two-option radiogroup
 * of its own, styled like a compact pair of ChoiceCards, is the honest fit: this is a persistent
 * setting a founder flips rarely, not a one-time choice or a primary action. Both options always
 * write to the same backend schema — this never changes what's submitted, only what's asked. */
export function ModeToggle({ mode, onChange }: Props) {
  return (
    <div
      role="radiogroup"
      aria-label="Question detail level"
      className="inline-flex rounded-forge-md border border-forge-text/[.16] bg-forge-surface-1 p-1"
    >
      {OPTIONS.map((option) => {
        const selected = mode === option.value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={[
              "min-h-[36px] rounded-forge-sm px-3.5 text-forge-1 font-medium transition-colors",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-accent",
              selected ? "bg-forge-accent/[.16] text-forge-text" : "text-forge-text-tertiary hover:text-forge-text-secondary",
            ].join(" ")}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
