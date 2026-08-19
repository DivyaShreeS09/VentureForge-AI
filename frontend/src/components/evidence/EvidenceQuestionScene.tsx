import { ChoiceCard } from "../../primitives";
import {
  SKIP_OPTIONS,
  type EvidenceDimension,
  type EvidenceOption,
} from "./evidenceDimensions";
import type { InputMode } from "../../context/NewAnalysisContext";
import type { DimensionEvidence } from "../../types/api";
import { useLanguage } from "../../context/LanguageContext";

interface Props {
  dimension: EvidenceDimension;
  answer: DimensionEvidence | undefined;
  stage: string;
  mode: InputMode;
  onAnswer: (value: DimensionEvidence) => void;
}

function isSelected(
  option: EvidenceOption,
  answer: DimensionEvidence | undefined,
): boolean {
  if (!answer) return false;

  if (option.state !== answer.state) return false;

  if (option.state !== "confirmed_positive") return true;

  return (option.severity ?? null) === (answer.severity ?? null);
}

function getAcknowledgment(
  state: DimensionEvidence["state"],
  severity: number | null,
  t: (key: string) => string,
): string {
  switch (state) {
    case "confirmed_positive":
      return severity === 2 ? t("ack.strong") : t("ack.starting");

    case "confirmed_negative":
      return t("ack.negative");

    case "not_sure_yet":
      return t("ack.unsure");

    case "not_applicable":
      return t("ack.not_applicable");

    default:
      return "";
  }
}

export function EvidenceQuestionScene({
  dimension,
  answer,
  stage,
  mode,
  onAnswer,
}: Props) {
  const { t } = useLanguage();

  const stageNote = dimension.stageNote?.(stage) ?? null;

  const tipKey =
    mode === "advanced" && dimension.tipAdvanced
      ? `${dimension.key}.tipAdvanced`
      : `${dimension.key}.tip`;

  const translatedQuestion = t(`${dimension.key}.question`);
  const translatedTip = t(tipKey);

  return (
    <div className="flex w-full max-w-[640px] flex-col gap-6">
      <div>
        <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
          {translatedQuestion}
        </h1>

        <p className="mt-3 text-forge-3 text-forge-text-secondary">
          {translatedTip}
        </p>

        {stageNote && (
          <p className="mt-2 text-forge-2 text-forge-text-tertiary">
            {stageNote}
          </p>
        )}
      </div>

      <div
        role="radiogroup"
        aria-label={translatedQuestion}
        className="flex flex-col gap-3"
      >
        <div className="grid grid-cols-1 gap-3 forge-sm:grid-cols-3">
          {dimension.options.map((option, index) => (
            <ChoiceCard
              key={option.label}
              label={t(`${dimension.key}.option.${index + 1}`)}
              selected={isSelected(option, answer)}
              onSelect={() =>
                onAnswer({
                  state: option.state,
                  severity: option.severity,
                })
              }
            />
          ))}
        </div>

        <div className="grid grid-cols-1 gap-3 forge-sm:grid-cols-2">
          {SKIP_OPTIONS.map((option) => {
            const translationKey =
              option.state === "not_sure_yet"
                ? "skip.not_sure"
                : "skip.not_applicable";

            return (
              <ChoiceCard
                key={option.label}
                label={t(translationKey)}
                selected={isSelected(option, answer)}
                onSelect={() =>
                  onAnswer({
                    state: option.state,
                    severity: option.severity,
                  })
                }
              />
            );
          })}
        </div>
      </div>

      {answer && (
        <p
          role="status"
          className="text-forge-2 text-forge-text-secondary"
        >
          {getAcknowledgment(
            answer.state,
            answer.severity ?? null,
            t,
          )}
        </p>
      )}
    </div>
  );
}