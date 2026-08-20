import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useNewAnalysis } from "../context/NewAnalysisContext";
import { useIndustryPreview } from "../hooks/useIndustryPreview";
import { useMotionTier } from "../motion/transitions";
import { Button } from "../primitives";
import { AutosavedIndicator } from "../components/shared/AutosavedIndicator";
import { OpeningLineScene } from "../components/discovery/OpeningLineScene";
import { WhoItsForScene, MAX_SEGMENTS } from "../components/discovery/WhoItsForScene";
import { WhereYouAreScene } from "../components/discovery/WhereYouAreScene";
import { useLanguage } from "../context/LanguageContext";

const MIN_DESCRIPTION_LENGTH = 10;
type Step = 1 | 2 | 3;

/** Act II — Discovery, Scenes 2-4 ("The Opening Line" / "Who It's For" / "Where You Are") — see
 * the Product Bible screenplay. Scene 5 (the Evidence Conversation) stays a separate page/route
 * (EvidenceCollectionPage, untouched this sprint); this page hands off to it exactly as before.
 *
 * One question at a time, full-screen, matching the Evidence Conversation's own pacing rather
 * than the old 4-step form-wizard this file used to be. The live industry/customer signal (see
 * useIndustryPreview) is computed once here and passed down to both scenes that use it, so the
 * real backend call never fires twice for the same description. */
export function IdeaSubmissionPage() {
  const navigate = useNavigate();
  const { idea, updateIdea } = useNewAnalysis();
  const { t } = useLanguage();
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState<string | null>(null);
  const sceneTransition = useMotionTier("scene");

  const { preview, loading: previewLoading, error: previewError } = useIndustryPreview(
    idea.name,
    idea.problemSolution,
  );

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Backspace" || step === 1) return;
      const active = document.activeElement;
      const isTextInput = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement;
      if (isTextInput && active.value.length > 0) return; // normal editing — don't intercept
      e.preventDefault();
      setStep((s) => (s - 1) as Step);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [step]);

  function goNext() {
    if (step === 1) {
      if (!idea.name.trim()) {
        setError(t("idea.error.name"));
        return;
      }
      if (idea.problemSolution.trim().length < MIN_DESCRIPTION_LENGTH) {
        setError(
          t("idea.error.description").replace("{min}", String(MIN_DESCRIPTION_LENGTH)),
        );
        return;
      }
    }
    setError(null);
    if (step < 3) setStep((s) => (s + 1) as Step);
    else navigate("/new/evidence");
  }

  function toggleSegment(segment: string) {
    const current = idea.customerSegments;
    if (current.includes(segment)) {
      updateIdea({ customerSegments: current.filter((s) => s !== segment) });
      return;
    }
    // Design System Bible §7 — multi-select choice cards cap at 2; the oldest selection
    // silently steps aside rather than blocking the new one or requiring a manual deselect.
    const next = current.length >= MAX_SEGMENTS ? current.slice(1) : current;
    updateIdea({ customerSegments: [...next, segment] });
  }

  return (
    <main className="flex min-h-[100dvh] w-full flex-col items-center justify-center px-6 py-20 font-forge-sans forge-sm:px-10">
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={sceneTransition}
            className="flex w-full flex-col items-center"
          >
            {step === 1 && (
              <OpeningLineScene
                description={idea.problemSolution}
                name={idea.name}
                onDescriptionChange={(value) => updateIdea({ problemSolution: value })}
                onNameChange={(value) => updateIdea({ name: value })}
                onSubmit={goNext}
                error={error}
                preview={preview}
                previewLoading={previewLoading}
                previewError={previewError}
              />
            )}
            {step === 2 && (
              <WhoItsForScene
                preview={preview}
                previewLoading={previewLoading}
                previewError={previewError}
                targetCustomer={idea.targetCustomer}
                customerSegments={idea.customerSegments}
                onTargetCustomerChange={(value) => updateIdea({ targetCustomer: value })}
                onToggleSegment={toggleSegment}
              />
            )}
            {step === 3 && (
              <WhereYouAreScene stage={idea.currentStage} onSelect={(stage) => updateIdea({ currentStage: stage })} />
            )}
          </motion.div>
        </AnimatePresence>

        <div className="mt-10 flex w-full max-w-[560px] items-center justify-between forge-sm:max-w-[680px]">
          <Button variant="ghost" onClick={() => setStep((s) => Math.max(1, s - 1) as Step)} disabled={step === 1}>
            {t("common.back")}
          </Button>
          <Button variant="primary" onClick={goNext}>
            {t("common.continue")}
          </Button>
        </div>

        <AutosavedIndicator />
      </div>
    </main>
  );
}
