import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useNewAnalysis } from "../context/NewAnalysisContext";
import { useIndustryPreview } from "../hooks/useIndustryPreview";
import { useMotionTier } from "../motion/transitions";
import { Button } from "../primitives";
import { AutosavedIndicator } from "../components/shared/AutosavedIndicator";
import { OpeningLineScene } from "../components/discovery/OpeningLineScene";
import {
  WhoItsForScene,
  MAX_SEGMENTS,
} from "../components/discovery/WhoItsForScene";
import { WhereYouAreScene } from "../components/discovery/WhereYouAreScene";
import { useLanguage } from "../context/LanguageContext";

const MIN_DESCRIPTION_LENGTH = 10;

type Step = 1 | 2 | 3;

export function IdeaSubmissionPage() {
  const navigate = useNavigate();

  const { idea, updateIdea } = useNewAnalysis();

  const { t } = useLanguage();

  const [step, setStep] = useState<Step>(1);

  const [error, setError] = useState<string | null>(null);

  const [isSpeaking, setIsSpeaking] = useState(false);

  const sceneTransition = useMotionTier("scene");

  const {
    preview,
    loading: previewLoading,
    error: previewError,
  } = useIndustryPreview(
    idea.name,
    idea.problemSolution,
  );

  /*
   * Stop speech whenever we move to another scene.
   */
  useEffect(() => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }

    setIsSpeaking(false);
  }, [step]);

  /*
   * Stop speech if the user leaves this page.
   */
  useEffect(() => {
    return () => {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  /*
   * Backspace navigation.
   */
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Backspace" || step === 1) {
        return;
      }

      const active = document.activeElement;

      const isTextInput =
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement;

      if (
        isTextInput &&
        active.value.length > 0
      ) {
        return;
      }

      e.preventDefault();

      setStep((s) => (s - 1) as Step);
    }

    document.addEventListener(
      "keydown",
      onKeyDown,
    );

    return () =>
      document.removeEventListener(
        "keydown",
        onKeyDown,
      );
  }, [step]);

  /*
   * Build the speech for ONLY the currently visible scene.
   *
   * ONE speaker reads everything important on that scene.
   */
  function getCurrentPageSpeech() {
    /*
     * STEP 1
     * Opening idea page
     */
    if (step === 1) {
      const speechParts = [
        t("idea.opening.question"),

        idea.problemSolution.trim()
          ? `Current answer is ${idea.problemSolution}.`
          : "No answer entered yet.",
      ];

      /*
       * The startup-name question only appears after
       * the description is long enough.
       */
      if (
        idea.problemSolution.trim().length >=
        MIN_DESCRIPTION_LENGTH
      ) {
        speechParts.push(
          t("idea.opening.nameQuestion"),
        );

        speechParts.push(
          idea.name.trim()
            ? `Current answer is ${idea.name}.`
            : "No startup name entered yet.",
        );
      }

      return speechParts.join(" ");
    }

    /*
     * STEP 2
     * Customer page
     */
    if (step === 2) {
      const selectedSegments =
        idea.customerSegments.length > 0
          ? idea.customerSegments.join(", ")
          : "No customer segment selected yet";

      const customerAnswer =
        idea.targetCustomer.trim()
          ? idea.targetCustomer
          : "No customer answer entered yet";

      return [
        t("whoItsFor.title"),
        t("whoItsFor.hintsQuestion"),
        `Selected customer segments are ${selectedSegments}.`,
        t("whoItsFor.question"),
        `Current answer is ${customerAnswer}.`,
      ].join(" ");
    }

    /*
     * STEP 3
     * Current-stage page
     */
    const stageOptions = [
      t("whereYouAre.stage.idea"),
      t("whereYouAre.stage.validating"),
      t("whereYouAre.stage.building"),
      t("whereYouAre.stage.earlyCustomers"),
      t("whereYouAre.stage.growing"),
    ];

    const selectedStage =
      idea.currentStage
        ? stageOptions[
            [
              "Just an idea",
              "Validating",
              "Building",
              "Early customers",
              "Growing",
            ].indexOf(idea.currentStage)
          ] || idea.currentStage
        : "";

    return [
      t("whereYouAre.question"),

      `Options are ${stageOptions.join(", ")}.`,

      selectedStage
        ? `Selected answer is ${selectedStage}.`
        : "No answer selected yet.",
    ].join(" ");
  }

  /*
   * ONE speaker button for the current scene.
   */
  function toggleSpeech() {
    if (!("speechSynthesis" in window)) {
      setError(
        "Speech is not supported in this browser.",
      );

      return;
    }

    /*
     * Clicking while speaking = STOP.
     */
    if (isSpeaking) {
      window.speechSynthesis.cancel();

      setIsSpeaking(false);

      return;
    }

    const speechText =
      getCurrentPageSpeech();

    if (!speechText.trim()) {
      return;
    }

    window.speechSynthesis.cancel();

    const utterance =
      new SpeechSynthesisUtterance(
        speechText,
      );

    /*
     * Natural slower speaking speed.
     */
    utterance.rate = 0.85;

    utterance.pitch = 1;

    utterance.volume = 1;

    /*
     * Try to use an English voice.
     */
    const voices =
      window.speechSynthesis.getVoices();

    const preferredVoice =
      voices.find(
        (voice) =>
          voice.lang
            .toLowerCase()
            .includes("en-in"),
      ) ||
      voices.find(
        (voice) =>
          voice.lang
            .toLowerCase()
            .startsWith("en"),
      );

    if (preferredVoice) {
      utterance.voice =
        preferredVoice;

      utterance.lang =
        preferredVoice.lang;
    } else {
      utterance.lang = "en-US";
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(
      utterance,
    );
  }

  /*
   * Continue button.
   */
  function goNext() {
    if (step === 1) {
      if (!idea.name.trim()) {
        setError(
          t("idea.error.name"),
        );

        return;
      }

      if (
        idea.problemSolution.trim().length <
        MIN_DESCRIPTION_LENGTH
      ) {
        setError(
          t(
            "idea.error.description",
          ).replace(
            "{min}",
            String(
              MIN_DESCRIPTION_LENGTH,
            ),
          ),
        );

        return;
      }
    }

    setError(null);

    if (step < 3) {
      setStep(
        (s) => (s + 1) as Step,
      );
    } else {
      navigate("/new/evidence");
    }
  }

  /*
   * Customer segment selection.
   */
  function toggleSegment(
    segment: string,
  ) {
    const current =
      idea.customerSegments;

    if (current.includes(segment)) {
      updateIdea({
        customerSegments:
          current.filter(
            (s) => s !== segment,
          ),
      });

      return;
    }

    const next =
      current.length >= MAX_SEGMENTS
        ? current.slice(1)
        : current;

    updateIdea({
      customerSegments: [
        ...next,
        segment,
      ],
    });
  }

  return (
    <main className="flex min-h-[100dvh] w-full flex-col items-center justify-center px-6 py-20 font-forge-sans forge-sm:px-10">
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center">

        {/* =========================================
            SINGLE GLOBAL SPEAKER FOR CURRENT SCENE
            ========================================= */}

        <div className="mb-5 flex w-full max-w-[680px] justify-end">
          <button
            type="button"
            onClick={toggleSpeech}
            aria-label={
              isSpeaking
                ? "Stop speaking"
                : "Read this page aloud"
            }
            title={
              isSpeaking
                ? "Stop speaking"
                : "Read this page aloud"
            }
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-xl transition hover:bg-white/10 active:scale-95"
          >
            {isSpeaking
              ? "🔇"
              : "🔊"}
          </button>
        </div>

        {/* =========================================
            CURRENT SCENE
            ========================================= */}

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{
              opacity: 0,
              y: 8,
            }}
            animate={{
              opacity: 1,
              y: 0,
            }}
            exit={{
              opacity: 0,
            }}
            transition={
              sceneTransition
            }
            className="flex w-full flex-col items-center"
          >

            {/* STEP 1 */}

            {step === 1 && (
              <OpeningLineScene
                description={
                  idea.problemSolution
                }
                name={idea.name}
                onDescriptionChange={(
                  value,
                ) =>
                  updateIdea({
                    problemSolution:
                      value,
                  })
                }
                onNameChange={(
                  value,
                ) =>
                  updateIdea({
                    name: value,
                  })
                }
                onSubmit={
                  goNext
                }
                error={error}
                preview={preview}
                previewLoading={
                  previewLoading
                }
                previewError={
                  previewError
                }
              />
            )}

            {/* STEP 2 */}

            {step === 2 && (
              <WhoItsForScene
                preview={preview}
                previewLoading={
                  previewLoading
                }
                previewError={
                  previewError
                }
                targetCustomer={
                  idea.targetCustomer
                }
                customerSegments={
                  idea.customerSegments
                }
                onTargetCustomerChange={(
                  value,
                ) =>
                  updateIdea({
                    targetCustomer:
                      value,
                  })
                }
                onToggleSegment={
                  toggleSegment
                }
              />
            )}

            {/* STEP 3 */}

            {step === 3 && (
              <WhereYouAreScene
                stage={
                  idea.currentStage
                }
                onSelect={(
                  stage,
                ) =>
                  updateIdea({
                    currentStage:
                      stage,
                  })
                }
              />
            )}
          </motion.div>
        </AnimatePresence>

        {/* =========================================
            NAVIGATION
            ========================================= */}

        <div className="mt-10 flex w-full max-w-[560px] items-center justify-between forge-sm:max-w-[680px]">
          <Button
            variant="ghost"
            onClick={() =>
              setStep(
                (s) =>
                  Math.max(
                    1,
                    s - 1,
                  ) as Step,
              )
            }
            disabled={
              step === 1
            }
          >
            {t("common.back")}
          </Button>

          <Button
            variant="primary"
            onClick={goNext}
          >
            {t(
              "common.continue",
            )}
          </Button>
        </div>

        <AutosavedIndicator />
      </div>
    </main>
  );
}