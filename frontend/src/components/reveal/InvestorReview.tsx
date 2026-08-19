import { GlassCard } from "../../primitives/GlassCard";
import type { FounderReport, MentorInterpretation } from "../../types/api";
import { deriveFounderDecision } from "../../utils/founderDecision";
import { highlightKeywords } from "../../utils/highlightKeywords";

const DECISION_TONE: Record<string, string> = {
  "Should Build": "text-forge-emerald",
  "Proceed Carefully": "text-forge-notsure",
  "Needs Validation": "text-forge-notsure",
  "High Risk": "text-forge-rose",
};

/** Section 4 of 5 — answers exactly one question: "What would an investor say?" Question /
 * concern / evidence per row; the decision badge is shown exactly once at the section's own top
 * (reusing `deriveFounderDecision`, the same single source the Executive Command Center's badge
 * already reads) rather than being re-derived or restated per row. Only renders when
 * `founder_report.investor_view` genuinely exists — no fabricated investor commentary when it
 * doesn't. */
export function InvestorReview({ report, mentor }: { report: FounderReport; mentor: MentorInterpretation }) {
  const decision = deriveFounderDecision(mentor);
  const tone = DECISION_TONE[decision.label] ?? "text-forge-text";
  const rows = report.investor_view.filter((row) => row.investor_question);

  if (rows.length === 0) return null;

  return (
    <section id="section-investor-review" className="mx-auto w-full max-w-[1100px] px-6 py-16 forge-sm:px-10">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <p className="text-forge-1 uppercase tracking-[0.2em] text-forge-label">Investor Review</p>
          <h2 className="mt-3 max-w-[26ch] text-balance font-forge-serif text-forge-5 font-bold leading-[1.25] text-forge-heading [text-shadow:0_0_24px_rgba(139,92,246,0.2)]">
            What would an investor say?
          </h2>
        </div>
        <div className="text-right">
          <p className="text-forge-1 uppercase tracking-[0.15em] text-forge-label">Decision</p>
          <p className={`mt-1 font-forge-serif text-forge-5 font-semibold ${tone}`}>{decision.label}</p>
        </div>
      </div>

      <div className="mt-8 space-y-4">
        {rows.map((row, i) => (
          <GlassCard key={i} className="p-5">
            <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-label">Question</p>
            <p className="mt-1 text-forge-3 font-medium text-forge-heading">{highlightKeywords(row.investor_question?.content ?? "")}</p>
            <div className="mt-4 grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
              <div>
                <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-rose">Concern</p>
                <p className="mt-1 text-forge-2 text-forge-desc">{highlightKeywords(row.investor_concern.content)}</p>
              </div>
              <div>
                <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-cyan">Evidence</p>
                <p className="mt-1 text-forge-2 text-forge-desc">{highlightKeywords(row.evidence.content)}</p>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>
    </section>
  );
}
