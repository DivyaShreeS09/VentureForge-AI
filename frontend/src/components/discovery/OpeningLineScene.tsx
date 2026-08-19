import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TextField } from "../../primitives";
import { useMotionTier } from "../../motion/transitions";
import { ConfidenceNote } from "./ConfidenceNote";
import type { IndustryPreview } from "../../types/api";
<<<<<<< HEAD
=======
import { useLanguage } from "../../context/LanguageContext";
>>>>>>> master

interface Props {
  description: string;
  name: string;
  onDescriptionChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onSubmit: () => void;
  error: string | null;
  preview: IndustryPreview | null;
  previewLoading: boolean;
  previewError: string | null;
}

const MIN_DESCRIPTION_LENGTH = 10;

<<<<<<< HEAD
/** Product Bible screenplay, "INT. THE OPENING LINE": the founder's first real input. The name
 * prompt is deliberately absent until the description clears the same minimum length the backend
 * itself requires (progressive disclosure — one question at a time, never two blank fields at
 * once). The live industry read sits in the periphery, low-opacity, exactly as the screenplay
 * describes it: "unbothered by being noticed or not." */
=======
>>>>>>> master
export function OpeningLineScene({
  description,
  name,
  onDescriptionChange,
  onNameChange,
  onSubmit,
  error,
  preview,
  previewLoading,
  previewError,
}: Props) {
<<<<<<< HEAD
=======
  const { t } = useLanguage();

>>>>>>> master
  const sceneTransition = useMotionTier("scene");
  const nameRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const showNamePrompt = description.trim().length >= MIN_DESCRIPTION_LENGTH;
  const namePreviouslyShown = useRef(false);

  useEffect(() => {
    if (showNamePrompt && !namePreviouslyShown.current) {
      namePreviouslyShown.current = true;
<<<<<<< HEAD
      // Bible: the founder's attention should move to the next open question the moment it
      // appears, without requiring a manual click — a real accessibility win here (keyboard
      // users never need to Tab past a field they can already see is complete).
=======
>>>>>>> master
      nameRef.current?.focus();
    }
  }, [showNamePrompt]);

  function handleNameKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      onSubmit();
    }
  }

  return (
    <div className="flex w-full max-w-[560px] flex-col gap-8">
      <div>
        <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
<<<<<<< HEAD
          What are you building?
=======
          {t("idea.opening.question")}
>>>>>>> master
        </h1>

        <div className="relative mt-5">
          <TextField
            multiline
<<<<<<< HEAD
            label="What are you building?"
            // This is the very first, only field on the very first Discovery screen — there is
            // nothing else on screen yet to steal focus from (unlike CommandCapsule's palette,
            // this isn't reclaiming focus from content the founder was already reading).
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus
            maxLength={2000}
            placeholder="A restaurant inventory tool that predicts spoilage before it happens…"
=======
            label={t("idea.opening.label")}
            autoFocus
            maxLength={2000}
            placeholder={t("idea.opening.placeholder")}
>>>>>>> master
            value={description}
            onChange={onDescriptionChange}
            className="text-forge-4"
          />
<<<<<<< HEAD
          <div className="pointer-events-none absolute -right-2 top-1 hidden max-w-[11rem] translate-x-full pl-4 forge-lg:block">
            <div className="pointer-events-auto opacity-80">
              <ConfidenceNote preview={preview} loading={previewLoading} error={previewError} />
=======

          <div className="pointer-events-none absolute -right-2 top-1 hidden max-w-[11rem] translate-x-full pl-4 forge-lg:block">
            <div className="pointer-events-auto opacity-80">
              <ConfidenceNote
                preview={preview}
                loading={previewLoading}
                error={previewError}
              />
>>>>>>> master
            </div>
          </div>
        </div>

<<<<<<< HEAD
        {/* Below the field on narrower viewports, where there's no periphery to place it in. */}
        <div className="mt-3 forge-lg:hidden">
          <ConfidenceNote preview={preview} loading={previewLoading} error={previewError} />
=======
        <div className="mt-3 forge-lg:hidden">
          <ConfidenceNote
            preview={preview}
            loading={previewLoading}
            error={previewError}
          />
>>>>>>> master
        </div>
      </div>

      <AnimatePresence>
        {showNamePrompt && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={sceneTransition}
          >
            <h2 className="font-forge-serif text-forge-5 font-semibold text-forge-text">
<<<<<<< HEAD
              And what should I call it?
            </h2>
            <TextField
              ref={nameRef}
              label="What should I call it?"
              placeholder="WasteLess Kitchen"
=======
              {t("idea.opening.nameQuestion")}
            </h2>

            <TextField
              ref={nameRef}
              label={t("idea.opening.nameLabel")}
              placeholder={t("idea.opening.namePlaceholder")}
>>>>>>> master
              value={name}
              onChange={onNameChange}
              onKeyDown={handleNameKeyDown}
              className="mt-3 text-forge-4"
            />
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <p role="alert" className="text-forge-2 text-forge-risk">
          {error}
        </p>
      )}
    </div>
  );
<<<<<<< HEAD
}
=======
}
>>>>>>> master
