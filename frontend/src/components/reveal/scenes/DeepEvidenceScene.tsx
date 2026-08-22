import type { Analysis } from "../../../types/api";
import { CollapsedScene } from "../CollapsedScene";
import { WorkflowTrace } from "../WorkflowTrace";
function formatConfidencePct(confidence: number): string {
  return Number.isFinite(confidence)
    ? (confidence * 100).toFixed(0)
    : "0";
}


function SpokenBlock({
  title,
  text,
  className = "",
}: {
  title: string;
  text: string;
  className?: string;
}) {
  if (!text?.trim()) return null;

  return (
    <div className={className}>
      <div className="flex items-center gap-2">
        <p className="font-medium text-forge-text">
          {title}
        </p>

        
      </div>

      <div className="mt-1.5 flex items-start gap-2">
        <p className="flex-1">{text}</p>

        
      </div>
    </div>
  );
}

/**
 * Deep Evidence â€” proof, methodology, model details, and
 * uncertainty. All speech content comes directly from the
 * existing Analysis object.
 */
export function DeepEvidenceScene({
  analysis,
}: {
  analysis: Analysis;
}) {
  const {
    industry_prediction,
    funding_assessment,
    success_prediction,
    judge_summary,
    mentor_interpretation,
    customer_personas,
    competitor_analysis,
  } = analysis;

  const venturePositioningText =
    judge_summary?.venture_positioning
      ? `${judge_summary.venture_positioning.primary_domain}${
          judge_summary.venture_positioning.is_low_confidence
            ? " (below our confidence threshold)"
            : ""
        }`
      : "";

  const positioningCorrection =
    judge_summary?.positioning_correction_rationale ?? "";

  const correctionHistory =
    (analysis.positioning_correction_history ?? []).length > 0
      ? `Corrected ${
          (analysis.positioning_correction_history ?? []).length
        } time(s) by the founder.`
      : "";

  const industryText = industry_prediction
    ? `${industry_prediction.predicted_industry} â€” ${formatConfidencePct(
        industry_prediction.confidence,
      )}% confidence, model ${industry_prediction.model_version}.`
    : "";

  const industryUncertainty =
    industry_prediction?.is_uncertain
      ? "Uncertain classification â€” treat this as a hypothesis, not a settled fact."
      : "";

  const industryAlternatives =
    industry_prediction &&
    industry_prediction.alternatives.length > 0
      ? `Other signals: ${industry_prediction.alternatives
          .map(
            (item) =>
              `${item.industry} (${formatConfidencePct(
                item.confidence,
              )}%)`,
          )
          .join(", ")}`
      : "";

  const fundingTitle = funding_assessment
    ? `Investment Readiness â€” ${funding_assessment.overall_score}/100`
    : "";

  const historicalModelText = success_prediction
    ? `Model ${success_prediction.model_version}. Dataset ${success_prediction.dataset_version}${
        success_prediction.missing_features.length > 0
          ? `. Imputed: ${success_prediction.missing_features.join(
              ", ",
            )}`
          : ""
      }`
    : "";

  const unresolvedQuestions =
    mentor_interpretation?.evidence_and_uncertainty?.unresolved_questions.join(
      " ",
    ) ?? "";

  const suppliedVsSuggested =
    mentor_interpretation?.evidence_and_uncertainty
      ?.user_supplied_vs_suggested_summary ?? "";

  const competitorDisclaimer =
    competitor_analysis?.disclaimer ?? "";

  const judgeAssessment =
    judge_summary?.overall_assessment ?? "";

  const methodologyText = `Industry model ${
    analysis.industry_model_version ?? "n/a"
  }. Funding rubric ${
    analysis.funding_rubric_version ?? "n/a"
  }. The industry classifier is trained on real Y Combinator company descriptions. Funding readiness is a deterministic, hand-designed rubric, not a trained probability. The historical pattern comparison is trained only on companies that had already raised funding â€” a loose comparison, never a prediction of this idea's outcome.`;

  return (
    <CollapsedScene
      eyebrow="Deep Evidence"
      summary="How we got here â€” for founders who want the proof."
    >
      <div className="space-y-8 text-forge-2 text-forge-text-secondary">
        {/* Venture positioning */}
        {judge_summary?.venture_positioning && (
          <div>
            <SpokenBlock
              title="Venture Positioning"
              text={venturePositioningText}
            />

            {positioningCorrection && (
              <SpokenBlock
                title="Positioning correction rationale"
                text={positioningCorrection}
                className="mt-3"
              />
            )}

            {correctionHistory && (
              <SpokenBlock
                title="Correction history"
                text={correctionHistory}
                className="mt-3 text-forge-1"
              />
            )}
          </div>
        )}

        {/* Industry */}
        {industry_prediction && (
          <div>
            <SpokenBlock
              title="Industry Classification"
              text={industryText}
            />

            {industryUncertainty && (
              <SpokenBlock
                title="Classification uncertainty"
                text={industryUncertainty}
                className="mt-2 text-forge-notsure"
              />
            )}

            {industryAlternatives && (
              <SpokenBlock
                title="Alternative industry signals"
                text={industryAlternatives}
                className="mt-2 text-forge-1"
              />
            )}
          </div>
        )}

        {/* Funding */}
        {funding_assessment && (
          <div>
            <SpokenBlock
              title="Investment Readiness"
              text={fundingTitle}
            />

            <ul
              role="list"
              className="mt-2 space-y-1"
            >
              {funding_assessment.breakdown.map(
                (item) => {
                  const scoreText =
                    item.state === "not_applicable"
                      ? `${item.label}: not applicable`
                      : `${item.label}: ${item.raw_score} out of ${item.max_score}`;

                  return (
                    <li
                      key={item.dimension}
                      className="text-forge-1"
                    >
                      <div className="flex items-start gap-2">
                        <span className="flex-1">
                          {scoreText}
                        </span>

                        
                      </div>
                    </li>
                  );
                },
              )}
            </ul>
          </div>
        )}

        {/* Historical comparison */}
        {success_prediction && (
          <div>
            <SpokenBlock
              title="Historical Pattern Comparison"
              text={success_prediction.pattern_signal_sentence}
            />

            <SpokenBlock
              title="Model information"
              text={historicalModelText}
              className="mt-2 text-forge-1"
            />
          </div>
        )}

        {/* Open questions */}
        {mentor_interpretation?.evidence_and_uncertainty && (
          <div>
            <SpokenBlock
              title="Open Questions"
              text={unresolvedQuestions}
            />

            <SpokenBlock
              title="Evidence source summary"
              text={suppliedVsSuggested}
              className="mt-2 text-forge-1"
            />
          </div>
        )}

        {/* Customer personas */}
        {customer_personas &&
          customer_personas.personas.length > 0 && (
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium text-forge-text">
                  Customer Personas
                </p>

                
              </div>

              <ul
                role="list"
                className="mt-2 space-y-1.5"
              >
                {customer_personas.personas.map(
                  (persona) => {
                    const personaText = `${persona.persona_name} â€” ${persona.role_or_context}, ${persona.goal}`;

                    return (
                      <li
                        key={persona.persona_name}
                        className="text-forge-1"
                      >
                        <div className="flex items-start gap-2">
                          <span className="flex-1">
                            <span className="text-forge-text-secondary">
                              {persona.persona_name}
                            </span>{" "}
                            â€” {persona.role_or_context},{" "}
                            {persona.goal}
                          </span>

                          
                        </div>
                      </li>
                    );
                  },
                )}
              </ul>
            </div>
          )}

        {/* Competitor disclaimer */}
        {competitorDisclaimer && (
          <SpokenBlock
            title="Competitor analysis note"
            text={competitorDisclaimer}
            className="text-forge-1 italic"
          />
        )}

        {/* Judge assessment */}
        {judgeAssessment && (
          <SpokenBlock
            title="Judge's Technical Assessment"
            text={judgeAssessment}
          />
        )}

        {/* Workflow trace */}
        <div>
          <div className="flex items-center gap-2">
            <p className="font-medium text-forge-text">
              Workflow Trace
            </p>

            
          </div>

          <div className="mt-2">
            <WorkflowTrace
              trace={analysis.workflow_trace}
            />
          </div>
        </div>

        {/* Methodology */}
        <SpokenBlock
          title="Methodology and uncertainty"
          text={methodologyText}
          className="text-forge-1 italic"
        />
      </div>
    </CollapsedScene>
  );
}


