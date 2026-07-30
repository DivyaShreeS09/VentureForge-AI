import { ChoiceCard, TextField } from "../../primitives";
import { ConfidenceNote, formatIndustryLabel } from "./ConfidenceNote";
import type { IndustryPreview } from "../../types/api";

interface Props {
  preview: IndustryPreview | null;
  previewLoading: boolean;
  previewError: string | null;
  targetCustomer: string;
  customerSegments: string[];
  onTargetCustomerChange: (value: string) => void;
  onToggleSegment: (segment: string) => void;
}

export const MAX_SEGMENTS = 2;

/** Product Bible screenplay, "INT. WHO IT'S FOR". The headline reveal uses only real backend
 * output (`IndustryPreview`) — never a fabricated category. The four example customer chips in
 * the screenplay ("Restaurant owners", "Kitchen staff"...) are illustrative copy for a specific
 * example venture, not real backend data; there is no endpoint that predicts customer *roles*.
 * What the backend genuinely computes is `customer_hints` — deployment sectors matched from the
 * founder's own words (e.g. "Hotels", "Restaurants") — so those, not invented role labels, are
 * what's offered as selectable chips here. A free-text answer is always available too, since
 * hints are frequently empty and must never block the founder from being specific. */
export function WhoItsForScene({
  preview,
  previewLoading,
  previewError,
  targetCustomer,
  customerSegments,
  onTargetCustomerChange,
  onToggleSegment,
}: Props) {
  const industry = preview?.available && preview.predicted_industry ? formatIndustryLabel(preview.predicted_industry) : null;
  const hints = preview?.available ? preview.customer_hints : [];

  return (
    <div className="flex w-full max-w-[560px] flex-col gap-8">
      <div>
        <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
          {industry
            ? preview?.is_uncertain
              ? `This might be the ${industry} market.`
              : `You're building for the ${industry} market.`
            : "Who's this for?"}
        </h1>
        <div className="mt-3">
          <ConfidenceNote preview={preview} loading={previewLoading} error={previewError} />
        </div>
      </div>

      {hints.length > 0 && (
        <div>
          <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
            I noticed a few words that might mean something — does either of these fit?
          </h2>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {hints.map((hint) => (
              <ChoiceCard
                key={hint.sector}
                mode="multi"
                label={hint.sector}
                selected={customerSegments.includes(hint.sector)}
                onSelect={() => onToggleSegment(hint.sector)}
              />
            ))}
          </div>
          <p className="mt-2 text-forge-1 text-forge-text-tertiary">
            Picked up on: {hints.flatMap((h) => h.matched_text).join(", ")}
          </p>
        </div>
      )}

      <div>
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          Who specifically buys or uses this?
        </h2>
        <TextField
          label="Who specifically buys or uses this?"
          placeholder="e.g. Independent restaurant owners with 1-3 locations"
          value={targetCustomer}
          onChange={onTargetCustomerChange}
          className="mt-3 text-forge-4"
        />
      </div>
    </div>
  );
}
