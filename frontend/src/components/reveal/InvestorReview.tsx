import { GlassCard } from "../../primitives/GlassCard";
import type {
  FounderReport,
  MentorInterpretation,
} from "../../types/api";
import { deriveFounderDecision } from "../../utils/founderDecision";
import { highlightKeywords } from "../../utils/highlightKeywords";
const DECISION_TONE: Record<string, string> = {
  "Should Build": "text-forge-emerald",
  "Proceed Carefully": "text-forge-notsure",
  "Needs Validation": "text-forge-notsure",
  "High Risk": "text-forge-rose",
};


/**
 * Section 4 of 5 â€” "What would an investor say?"
 *
 * All investor questions, concerns, evidence, and the decision
 * are taken directly from the existing analysis data.
 *
 * No investor text is hard-coded.
 */
export function InvestorReview({
  report,
  mentor,
}: {
  report: FounderReport;
  mentor: MentorInterpretation;
}) {
  const decision = deriveFounderDecision(mentor);
  const tone =
    DECISION_TONE[decision.label] ?? "text-forge-text";

  const rows = report.investor_view.filter(
    (row) => row.investor_question,
  );

  if (rows.length === 0) return null;

  const sectionTitle = "Investor Review";
  const sectionQuestion = "What would an investor say?";
  const decisionText = `Decision: ${decision.label}`;

  return (
    <section
      id="section-investor-review"
      className="mx-auto w-full max-w-[1100px] px-6 py-16 forge-sm:px-10"
    >
      {/* Section heading */}
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-forge-1 uppercase tracking-[0.2em] text-forge-label">
              {sectionTitle}
            </p>

            
          </div>

          <div className="mt-3 flex items-start gap-3">
            <h2 className="flex-1 max-w-[26ch] text-balance font-forge-serif text-forge-5 font-bold leading-[1.25] text-forge-heading [text-shadow:0_0_24px_rgba(139,92,246,0.2)]">
              {sectionQuestion}
            </h2>

            
          </div>
        </div>

        {/* Decision */}
        <div className="text-right">
          <div className="flex items-center justify-end gap-2">
            <p className="text-forge-1 uppercase tracking-[0.15em] text-forge-label">
              Decision
            </p>

            
          </div>

          <div className="mt-1 flex items-center justify-end gap-2">
            <p
              className={`font-forge-serif text-forge-5 font-semibold ${tone}`}
            >
              {decision.label}
            </p>

            
          </div>
        </div>
      </div>

      {/* Dynamic investor analysis */}
      <div className="mt-8 space-y-4">
        {rows.map((row, i) => {
          const question = row.investor_question?.content ?? "";
          const concern = row.investor_concern?.content ?? "";
          const evidence = row.evidence?.content ?? "";

          return (
            <GlassCard key={i} className="p-5">
              {/* Investor question */}
              <div className="flex items-start gap-2">
                <div className="flex-1">
                  <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-label">
                    Question
                  </p>

                  <p className="mt-1 text-forge-3 font-medium text-forge-heading">
                    {highlightKeywords(question)}
                  </p>
                </div>

                
              </div>

              <div className="mt-4 grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
                {/* Concern */}
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-rose">
                      Concern
                    </p>

                    
                  </div>

                  <div className="mt-1 flex items-start gap-2">
                    <p className="flex-1 text-forge-2 text-forge-desc">
                      {highlightKeywords(concern)}
                    </p>

                    
                  </div>
                </div>

                {/* Evidence */}
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-cyan">
                      Evidence
                    </p>

                    
                  </div>

                  <div className="mt-1 flex items-start gap-2">
                    <p className="flex-1 text-forge-2 text-forge-desc">
                      {highlightKeywords(evidence)}
                    </p>

                    
                  </div>
                </div>
              </div>
            </GlassCard>
          );
        })}
      </div>
    </section>
  );
}


