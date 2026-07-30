import { ChoiceCard } from "../../primitives";
import { acknowledgmentFor, SKIP_OPTIONS, type EvidenceDimension, type EvidenceOption } from "./evidenceDimensions";
import type { InputMode } from "../../context/NewAnalysisContext";
import type { DimensionEvidence } from "../../types/api";

interface Props {
  dimension: EvidenceDimension;
  answer: DimensionEvidence | undefined;
  stage: string;
  mode: InputMode;
  onAnswer: (value: DimensionEvidence) => void;
}

function isSelected(option: EvidenceOption, answer: DimensionEvidence | undefined): boolean {
  if (!answer) return false;
  if (option.state !== answer.state) return false;
  if (option.state !== "confirmed_positive") return true;
  return (option.severity ?? null) === (answer.severity ?? null);
}

/** Act III, "The Evidence Conversation" — one dimension per screen, matching the same one-
 * question-at-a-time pacing Act II already established (Opening Line / Who It's For / Where You
 * Are). Same `ChoiceCard` primitive the Design System Bible names for this exact moment, same 8
 * dimensions and evidence-quality states `backend/app/ml/funding_readiness.py` scores — only the
 * sequencing, phrasing, and one-at-a-time presentation are new. Selecting an answer immediately
 * shows a short, honest acknowledgment (never a fabricated evaluation) rather than silently
 * accepting the click; advancing to the next question stays an explicit Continue action, matching
 * the rest of the Discovery Act rather than an auto-advance timer. */
export function EvidenceQuestionScene({ dimension, answer, stage, mode, onAnswer }: Props) {
  const stageNote = dimension.stageNote?.(stage) ?? null;
  const tip = mode === "advanced" && dimension.tipAdvanced ? dimension.tipAdvanced : dimension.tip;

  return (
    <div className="flex w-full max-w-[640px] flex-col gap-6">
      <div>
        <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
          {dimension.question}
        </h1>
        <p className="mt-3 text-forge-3 text-forge-text-secondary">{tip}</p>
        {stageNote && <p className="mt-2 text-forge-2 text-forge-text-tertiary">{stageNote}</p>}
      </div>

      {/* One radiogroup for all 5 mutually-exclusive answers — split into two visual rows
          (evidence-quality options, then the two honest-uncertainty options) without splitting
          the a11y group itself, since only one answer is ever selected across all 5. */}
      <div role="radiogroup" aria-label={dimension.question} className="flex flex-col gap-3">
        <div className="grid grid-cols-1 gap-3 forge-sm:grid-cols-3">
          {dimension.options.map((option) => (
            <ChoiceCard
              key={option.label}
              label={option.label}
              selected={isSelected(option, answer)}
              onSelect={() => onAnswer({ state: option.state, severity: option.severity })}
            />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-3 forge-sm:grid-cols-2">
          {SKIP_OPTIONS.map((option) => (
            <ChoiceCard
              key={option.label}
              label={option.label}
              selected={isSelected(option, answer)}
              onSelect={() => onAnswer({ state: option.state, severity: option.severity })}
            />
          ))}
        </div>
      </div>

      {answer && (
        // Neutral tone deliberately, regardless of which answer was given — "no evidence yet" and
        // "not sure yet" are acknowledged exactly as warmly as strong evidence; color here must
        // never read as a grade on the answer itself.
        <p role="status" className="text-forge-2 text-forge-text-secondary">
          {acknowledgmentFor(answer.state, answer.severity ?? null)}
        </p>
      )}
    </div>
  );
}
