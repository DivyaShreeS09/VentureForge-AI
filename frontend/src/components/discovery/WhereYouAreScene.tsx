import { ChoiceCard } from "../../primitives";

const STAGES = ["Just an idea", "Validating", "Building", "Early customers", "Growing"] as const;

interface Props {
  stage: string;
  onSelect: (stage: string) => void;
}

/** Product Bible screenplay, "INT. WHERE YOU ARE": "A single horizontal track, five labels, no
 * numbers... No judgment implied by position — every label rendered with equal visual weight."
 * Reuses the existing single-select ChoiceCard (Design System Bible §7 already names this as one
 * of its two intended uses) rather than the Tabs/segmented-control primitive — Tabs is reserved
 * exclusively for the Bigger Picture scene's pane switcher (§7: "the only place tabs are used in
 * the entire product"), and a segmented control's sliding-indicator affordance implies a single
 * current state being *changed*, not a one-time, equally-weighted self-placement. */
export function WhereYouAreScene({ stage, onSelect }: Props) {
  return (
    <div className="flex w-full max-w-[680px] flex-col gap-6">
      <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
        Where are you right now?
      </h1>
      <div
        role="radiogroup"
        aria-label="Where are you right now?"
        className="grid grid-cols-1 gap-3 forge-sm:grid-cols-5"
      >
        {STAGES.map((label) => (
          <ChoiceCard key={label} label={label} selected={stage === label} onSelect={() => onSelect(label)} />
        ))}
      </div>
    </div>
  );
}
