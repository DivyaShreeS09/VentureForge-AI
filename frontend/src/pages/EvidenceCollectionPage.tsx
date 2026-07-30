import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useNewAnalysis } from "../context/NewAnalysisContext";
import { useDiscoveryProgress } from "../app/discoveryProgress";
import { useMotionTier } from "../motion/transitions";
import { Button } from "../primitives";
import { AutosavedIndicator } from "../components/shared/AutosavedIndicator";
import { EvidenceQuestionScene } from "../components/evidence/EvidenceQuestionScene";
import { AdditionalDetailsScene } from "../components/evidence/AdditionalDetailsScene";
import { ConversationTrail } from "../components/evidence/ConversationTrail";
import { UnderstandingMeter } from "../components/evidence/UnderstandingMeter";
import { ModeToggle } from "../components/shared/ModeToggle";
import { EVIDENCE_DIMENSIONS } from "../components/evidence/evidenceDimensions";
import { createStartup } from "../services/api";
import type { DimensionEvidence } from "../types/api";

const TOTAL_STEPS = EVIDENCE_DIMENSIONS.length + 1; // + the final optional-details step
const DETAILS_STEP = EVIDENCE_DIMENSIONS.length;

/** Act III — "The Evidence Conversation". One dimension per screen, a founder-facing mentor
 * dialogue rather than the old 8-dimension accordion form: dynamic sequencing (evidenceDimensions
 * order), context-aware phrasing (stageNote, using the venture stage already collected in
 * Discovery), conversation memory (ConversationTrail), and confidence evolution
 * (UnderstandingMeter) that updates as real answers come in — never a fabricated number. Every
 * dimension and evidence-quality state maps 1:1 to what `backend/app/ml/funding_readiness.py`
 * already scores; nothing here invents a new backend capability. */
export function EvidenceCollectionPage() {
  const navigate = useNavigate();
  const {
    idea,
    fundingAnswers,
    updateFunding,
    companyMetrics,
    revenueAssumptions,
    marketEvidence,
    mode,
    setMode,
    updateCompanyMetrics,
    updateRevenueAssumptions,
    updateMarketEvidence,
    buildDescription,
    buildMarketEvidence,
    reset,
  } = useNewAnalysis();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sceneTransition = useMotionTier("scene");

  useDiscoveryProgress(0.5 + 0.5 * (step / TOTAL_STEPS));

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Backspace" || step === 0) return;
      const active = document.activeElement;
      const isTextInput = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement;
      if (isTextInput && active.value.length > 0) return; // normal editing — don't intercept
      e.preventDefault();
      setStep((s) => s - 1);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [step]);

  const currentDimension = step < DETAILS_STEP ? EVIDENCE_DIMENSIONS[step] : null;
  const canContinue = currentDimension ? fundingAnswers[currentDimension.key] !== undefined : true;

  async function handleSubmit() {
    if (!idea.name.trim() || buildDescription().length < 10) {
      setError("Your idea details look incomplete — go back to Idea Submission first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const startup = await createStartup({
        name: idea.name,
        description: buildDescription(),
        funding_answers: fundingAnswers,
        company_metrics: companyMetrics,
        revenue_assumptions: revenueAssumptions,
        market_evidence: buildMarketEvidence(),
      });
      reset();
      navigate(`/startups/${startup.id}/status`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit this venture for analysis.");
      setSubmitting(false);
    }
  }

  function goNext() {
    if (!canContinue) return;
    setError(null);
    if (step < DETAILS_STEP) setStep((s) => s + 1);
    else void handleSubmit();
  }

  function goBack() {
    if (step === 0) {
      navigate("/new/idea");
      return;
    }
    setStep((s) => s - 1);
  }

  function handleAnswer(value: DimensionEvidence) {
    if (!currentDimension) return;
    updateFunding(currentDimension.key, value);
  }

  return (
    <main className="flex min-h-[100dvh] w-full flex-col items-center justify-center px-6 py-20 font-forge-sans forge-sm:px-10">
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center">
        <div className="mb-8 flex w-full max-w-[720px] justify-end">
          <ModeToggle mode={mode} onChange={setMode} />
        </div>
        <div className="relative w-full flex justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={sceneTransition}
              className="flex w-full flex-col items-center"
            >
              {currentDimension ? (
                <EvidenceQuestionScene
                  dimension={currentDimension}
                  answer={fundingAnswers[currentDimension.key]}
                  stage={idea.currentStage}
                  mode={mode}
                  onAnswer={handleAnswer}
                />
              ) : (
                <AdditionalDetailsScene
                  mode={mode}
                  companyMetrics={companyMetrics}
                  revenueAssumptions={revenueAssumptions}
                  marketEvidence={marketEvidence}
                  onCompanyMetricsChange={updateCompanyMetrics}
                  onRevenueAssumptionsChange={updateRevenueAssumptions}
                  onMarketEvidenceChange={updateMarketEvidence}
                />
              )}
            </motion.div>
          </AnimatePresence>

          {/* Conversation memory + confidence evolution live in the periphery on wide viewports,
              matching Act II's ConfidenceNote placement — present but never competing with the
              current question. */}
          <div className="pointer-events-none absolute -right-2 top-1 hidden max-w-[15rem] translate-x-full flex-col gap-6 pl-6 forge-lg:flex">
            <div className="pointer-events-auto opacity-90">
              <UnderstandingMeter answers={fundingAnswers} />
            </div>
            {currentDimension && (
              <div className="pointer-events-auto opacity-80">
                <ConversationTrail dimensions={EVIDENCE_DIMENSIONS} answers={fundingAnswers} currentIndex={step} />
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 w-full max-w-[640px] forge-lg:hidden">
          <UnderstandingMeter answers={fundingAnswers} />
        </div>

        {error && (
          <p role="alert" className="mt-6 max-w-[640px] text-forge-2 text-forge-risk">
            {error}
          </p>
        )}

        <div className="mt-10 flex w-full max-w-[640px] items-center justify-between">
          <Button variant="ghost" onClick={goBack} disabled={submitting}>
            Back
          </Button>
          <Button variant="primary" onClick={goNext} disabled={!canContinue || submitting}>
            {submitting ? "Submitting…" : step === DETAILS_STEP ? "Review & Analyze" : "Continue"}
          </Button>
        </div>

        <AutosavedIndicator />
      </div>
    </main>
  );
}
