import { ChoiceCard, TextField } from "../../primitives";
import { ConfidenceNote, formatIndustryLabel } from "./ConfidenceNote";
import type { IndustryPreview } from "../../types/api";
import { useLanguage } from "../../context/LanguageContext";

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

export function WhoItsForScene({
  preview,
  previewLoading,
  previewError,
  targetCustomer,
  customerSegments,
  onTargetCustomerChange,
  onToggleSegment,
}: Props) {
  const { t } = useLanguage();

  const industry =
    preview?.available && preview.predicted_industry
      ? formatIndustryLabel(preview.predicted_industry)
      : null;

  const hints = preview?.available ? preview.customer_hints : [];

  return (
    <div className="flex w-full max-w-[560px] flex-col gap-8">
      <div>
        <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
          {industry
            ? preview?.is_uncertain
              ? t("whoItsFor.mightBeMarket", { industry })
              : t("whoItsFor.buildingForMarket", { industry })
            : t("whoItsFor.title")}
        </h1>

        <div className="mt-3">
          <ConfidenceNote
            preview={preview}
            loading={previewLoading}
            error={previewError}
          />
        </div>
      </div>

      {hints.length > 0 && (
        <div>
          <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
            {t("whoItsFor.hintsQuestion")}
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
            {t("whoItsFor.pickedUpOn")}:{" "}
            {hints.flatMap((h) => h.matched_text).join(", ")}
          </p>
        </div>
      )}

      <div>
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {t("whoItsFor.question")}
        </h2>

        <TextField
          label={t("whoItsFor.question")}
          placeholder={t("whoItsFor.placeholder")}
          value={targetCustomer}
          onChange={onTargetCustomerChange}
          className="mt-3 text-forge-4"
        />
      </div>
    </div>
  );
}