import type { Analysis } from "../../../types/api";
import { CollapsedScene } from "../CollapsedScene";
import { WorkflowTrace } from "../WorkflowTrace";

/** Scene 7 — Deep Evidence. Only for founders who want proof: workflow trace, evidence, readiness
 * detail, methodology, historical comparison, model explanations. Consolidates what used to be 6
 * scattered disclaimers plus the never-rendered `evidence_and_uncertainty` and correction-history
 * fields into one honest closing section. Never shown by default. */
export function DeepEvidenceScene({ analysis }: { analysis: Analysis }) {
  const { industry_prediction, funding_assessment, success_prediction, judge_summary, mentor_interpretation, customer_personas, competitor_analysis } =
    analysis;

  return (
    <CollapsedScene eyebrow="Deep Evidence" summary="How we got here — for founders who want the proof.">
      <div className="space-y-8 text-forge-2 text-forge-text-secondary">
        {judge_summary?.venture_positioning && (
          <div>
            <p className="font-medium text-forge-text">Venture Positioning</p>
            <p className="mt-1.5">
              {judge_summary.venture_positioning.primary_domain}
              {judge_summary.venture_positioning.is_low_confidence && " (below our confidence threshold)"}
            </p>
            {judge_summary.positioning_correction_rationale && <p className="mt-1 text-forge-text-secondary">{judge_summary.positioning_correction_rationale}</p>}
            {(analysis.positioning_correction_history ?? []).length > 0 && (
              <p className="mt-1 text-forge-1 text-forge-text-secondary">
                Corrected {(analysis.positioning_correction_history ?? []).length} time(s) by the founder.
              </p>
            )}
          </div>
        )}

        {industry_prediction && (
          <div>
            <p className="font-medium text-forge-text">Industry Classification</p>
            <p className="mt-1.5">
              {industry_prediction.predicted_industry} — {(industry_prediction.confidence * 100).toFixed(0)}% confidence,
              model {industry_prediction.model_version}
            </p>
            {industry_prediction.is_uncertain && (
              <p className="mt-1 text-forge-notsure">
                Uncertain classification — treat this as a hypothesis, not a settled fact.
              </p>
            )}
            {industry_prediction.alternatives.length > 0 && (
              <p className="mt-1 text-forge-1 text-forge-text-secondary">
                Other signals: {industry_prediction.alternatives.map((a) => `${a.industry} (${(a.confidence * 100).toFixed(0)}%)`).join(", ")}
              </p>
            )}
          </div>
        )}

        {funding_assessment && (
          <div>
            <p className="font-medium text-forge-text">Investment Readiness — {funding_assessment.overall_score}/100</p>
            {/* eslint-disable-next-line jsx-a11y/no-redundant-roles */}
            <ul role="list" className="mt-2 space-y-1">
              {funding_assessment.breakdown.map((item) => (
                // eslint-disable-next-line jsx-a11y/no-redundant-roles
                <li key={item.dimension} role="listitem" className="text-forge-1">
                  {item.label}: {item.state === "not_applicable" ? "N/A" : `${item.raw_score}/${item.max_score}`}
                </li>
              ))}
            </ul>
          </div>
        )}

        {success_prediction && (
          <div>
            <p className="font-medium text-forge-text">Historical Pattern Comparison</p>
            <p className="mt-1.5">{success_prediction.pattern_signal_sentence}</p>
            <p className="mt-1 text-forge-1 text-forge-text-secondary">
              Model {success_prediction.model_version} · dataset {success_prediction.dataset_version}
              {success_prediction.missing_features.length > 0 && ` · imputed: ${success_prediction.missing_features.join(", ")}`}
            </p>
          </div>
        )}

        {mentor_interpretation?.evidence_and_uncertainty && (
          <div>
            <p className="font-medium text-forge-text">Open Questions</p>
            <p className="mt-1.5">{mentor_interpretation.evidence_and_uncertainty.unresolved_questions.join(" ")}</p>
            <p className="mt-1 text-forge-1 text-forge-text-secondary">
              {mentor_interpretation.evidence_and_uncertainty.user_supplied_vs_suggested_summary}
            </p>
          </div>
        )}

        {customer_personas && customer_personas.personas.length > 0 && (
          <div>
            <p className="font-medium text-forge-text">Customer Personas</p>
            {/* eslint-disable-next-line jsx-a11y/no-redundant-roles */}
            <ul role="list" className="mt-2 space-y-1.5">
              {customer_personas.personas.map((persona) => (
                // eslint-disable-next-line jsx-a11y/no-redundant-roles
                <li key={persona.persona_name} role="listitem" className="text-forge-1">
                  <span className="text-forge-text-secondary">{persona.persona_name}</span> — {persona.role_or_context}, {persona.goal}
                </li>
              ))}
            </ul>
          </div>
        )}

        {competitor_analysis && <p className="text-forge-1 italic text-forge-text-secondary">{competitor_analysis.disclaimer}</p>}

        {judge_summary && (
          <div>
            <p className="font-medium text-forge-text">Judge's Technical Assessment</p>
            <p className="mt-1.5">{judge_summary.overall_assessment}</p>
          </div>
        )}

        <div>
          <p className="font-medium text-forge-text">Workflow Trace</p>
          <div className="mt-2">
            <WorkflowTrace trace={analysis.workflow_trace} />
          </div>
        </div>

        <p className="text-forge-1 italic text-forge-text-secondary">
          Industry model {analysis.industry_model_version ?? "n/a"} · funding rubric{" "}
          {analysis.funding_rubric_version ?? "n/a"}. The industry classifier is trained on real Y Combinator company
          descriptions. Funding readiness is a deterministic, hand-designed rubric, not a trained probability. The
          historical pattern comparison is trained only on companies that had already raised funding — a loose
          comparison, never a prediction of this idea's outcome.
        </p>
      </div>
    </CollapsedScene>
  );
}
