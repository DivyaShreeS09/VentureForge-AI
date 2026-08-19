import type { Analysis, MentorInterpretation, VenturePositioning } from "../../../types/api";
import { PositioningCorrection } from "../PositioningCorrection";
import { Scene } from "../Scene";

/** Scene 2 — What We Understood. Reflects the idea back better than the founder described it;
 * assumptions are labeled honestly (low-confidence positioning, secondary domains) rather than
 * presented as settled fact. */
export function UnderstandingScene({
  analysisId,
  mentor,
  positioning,
  onCorrected,
}: {
  analysisId: string;
  mentor: MentorInterpretation;
  positioning: VenturePositioning | null;
  onCorrected: (updated: Analysis) => void;
}) {
  const { summary, target_user, problem, proposed_solution, business_context } = mentor.idea_understanding;

  return (
    <Scene eyebrow="What We Understood">
      <p className="max-w-[58ch] text-balance font-forge-serif text-forge-5 leading-[1.35] text-forge-text forge-sm:text-forge-6">
        {summary}
      </p>

      <div className="mt-10 grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
        <div>
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary">Who it's for</p>
          <p className="mt-1.5 text-forge-2 text-forge-text-secondary">{target_user}</p>
        </div>
        <div>
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary">The problem</p>
          <p className="mt-1.5 text-forge-2 text-forge-text-secondary">{problem}</p>
        </div>
        <div>
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary">What you're building</p>
          <p className="mt-1.5 text-forge-2 text-forge-text-secondary">{proposed_solution}</p>
        </div>
        <div>
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary">Business context</p>
          <p className="mt-1.5 text-forge-2 text-forge-text-secondary">{business_context}</p>
        </div>
      </div>

      {positioning && (
        <div className="mt-10 border-t border-forge-text/[.08] pt-6">
          <p className="text-forge-2 text-forge-text-secondary">
            I'm reading this as <span className="text-forge-text">{positioning.primary_domain}</span>
            {positioning.is_low_confidence && <span className="text-forge-notsure"> — though I'm not fully sure yet</span>}.
          </p>
          {positioning.secondary_domains.length > 0 && (
            <p className="mt-1 text-forge-1 text-forge-text-secondary">
              Could also touch: {positioning.secondary_domains.join(", ")}
            </p>
          )}
          <PositioningCorrection
            analysisId={analysisId}
            currentPrimaryDomain={positioning.primary_domain}
            onCorrected={onCorrected}
          />
        </div>
      )}
    </Scene>
  );
}
