import { ChoiceCard } from "../../primitives";
import {
  SKIP_OPTIONS,
  type EvidenceDimension,
  type EvidenceOption,
} from "./evidenceDimensions";
import type { InputMode } from "../../context/NewAnalysisContext";
import type { DimensionEvidence } from "../../types/api";
import { useLanguage } from "../../context/LanguageContext";
import { voiceAgent } from "../voice/VoiceAgent";

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

  if (option.state !== "confirmed_positive") {
    return true;
  }

  return (option.severity ?? null) === (answer.severity ?? null);
}

function getAcknowledgment(
  state: DimensionEvidence["state"],
  severity: number | null,
  t: (key: string) => string,
): string {
  switch (state) {
    case "confirmed_positive":
      return severity === 2
        ? t("ack.strong")
        : t("ack.starting");

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

  const stageNote =
    dimension.stageNote?.(stage) ?? null;

  const tipKey =
    mode === "advanced" &&
    dimension.tipAdvanced
      ? `${dimension.key}.tipAdvanced`
      : `${dimension.key}.tip`;

  const translatedQuestion =
    t(`${dimension.key}.question`);

  const translatedTip =
    t(tipKey);

  const acknowledgment = answer
    ? getAcknowledgment(
        answer.state,
        answer.severity ?? null,
        t,
      )
    : "";

  const mainOptions =
    dimension.options.map(
      (option, index) => ({
        ...option,
        translatedLabel: t(
          `${dimension.key}.option.${index + 1}`,
        ),
      }),
    );

  const skipOptions =
    SKIP_OPTIONS.map((option) => {
      const translationKey =
        option.state === "not_sure_yet"
          ? "skip.not_sure"
          : "skip.not_applicable";

      return {
        ...option,
        translatedLabel:
          t(translationKey),
      };
    });

  function getSelectedAnswerText() {
    if (!answer) {
      return "";
    }

    const selectedMain =
      mainOptions.find(
        (option) =>
          isSelected(option, answer),
      );

    if (selectedMain) {
      return selectedMain.translatedLabel;
    }

    const selectedSkip =
      skipOptions.find(
        (option) =>
          isSelected(option, answer),
      );

    return (
      selectedSkip?.translatedLabel ?? ""
    );
  }

  function speakWholePage() {
    const optionTexts = [
      ...mainOptions.map(
        (option) =>
          option.translatedLabel,
      ),
      ...skipOptions.map(
        (option) =>
          option.translatedLabel,
      ),
    ];

    const selectedAnswer =
      getSelectedAnswerText();

    const speechParts = [
      translatedQuestion,

      translatedTip?.trim()
        ? translatedTip
        : "",

      stageNote?.trim()
        ? stageNote
        : "",

      optionTexts.length > 0
        ? `Options are ${optionTexts.join(", ")}.`
        : "",

      selectedAnswer
        ? `Selected answer is ${selectedAnswer}.`
        : "No answer selected yet.",

      acknowledgment?.trim()
        ? acknowledgment
        : "",
    ];

    const speechText =
      speechParts
        .filter(Boolean)
        .join(" ");

    voiceAgent.speak(
      speechText,
      {
        rate: 0.85,
        pitch: 1,
        volume: 1,
        lang: "en-US",
      },
    );
  }

  return (
    <div className="flex w-full max-w-[640px] flex-col gap-6">

      {/* QUESTION + ONE SPEAKER ONLY */}
      <div>
        <div className="flex items-start justify-between gap-3">
          <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
            {translatedQuestion}
          </h1>

          <button
            type="button"
            onClick={speakWholePage}
            aria-label="Read this page aloud"
            title="Read this page aloud"
            className="shrink-0 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-lg transition hover:bg-white/10"
          >
            🔊
          </button>
        </div>

        {translatedTip?.trim() && (
          <p className="mt-3 text-forge-3 text-forge-text-secondary">
            {translatedTip}
          </p>
        )}

        {stageNote &&
          stageNote.trim() && (
            <p className="mt-2 text-forge-2 text-forge-text-tertiary">
              {stageNote}
            </p>
          )}
      </div>

      {/* ANSWER OPTIONS */}
      <div
        role="radiogroup"
        aria-label={
          translatedQuestion
        }
        className="flex flex-col gap-3"
      >
        <div className="grid grid-cols-1 gap-3 forge-sm:grid-cols-3">
          {mainOptions.map(
            (option) => (
              <ChoiceCard
                key={option.label}
                label={
                  option.translatedLabel
                }
                selected={isSelected(
                  option,
                  answer,
                )}
                onSelect={() =>
                  onAnswer({
                    state:
                      option.state,
                    severity:
                      option.severity,
                  })
                }
              />
            ),
          )}
        </div>

        {/* UNCERTAINTY OPTIONS */}
        <div className="grid grid-cols-1 gap-3 forge-sm:grid-cols-2">
          {skipOptions.map(
            (option) => (
              <ChoiceCard
                key={option.label}
                label={
                  option.translatedLabel
                }
                selected={isSelected(
                  option,
                  answer,
                )}
                onSelect={() =>
                  onAnswer({
                    state:
                      option.state,
                    severity:
                      option.severity,
                  })
                }
              />
            ),
          )}
        </div>
      </div>

      {/* ACKNOWLEDGMENT */}
      {acknowledgment && (
        <p
          role="status"
          className="text-forge-2 text-forge-text-secondary"
        >
          {acknowledgment}
        </p>
      )}
    </div>
  );
}