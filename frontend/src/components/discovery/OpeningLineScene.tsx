import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TextField } from "../../primitives";
import { useMotionTier } from "../../motion/transitions";
import { ConfidenceNote } from "./ConfidenceNote";
import type { IndustryPreview } from "../../types/api";
import { useLanguage } from "../../context/LanguageContext";

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
  const { t } = useLanguage();

  const sceneTransition = useMotionTier("scene");
  const nameRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const showNamePrompt = description.trim().length >= MIN_DESCRIPTION_LENGTH;
  const namePreviouslyShown = useRef(false);

  useEffect(() => {
    if (showNamePrompt && !namePreviouslyShown.current) {
      namePreviouslyShown.current = true;
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
          {t("idea.opening.question")}
        </h1>

        <div className="relative mt-5">
          <TextField
            multiline
            label={t("idea.opening.label")}
            autoFocus
            maxLength={2000}
            placeholder={t("idea.opening.placeholder")}
            value={description}
            onChange={onDescriptionChange}
            className="text-forge-4"
          />

          <div className="pointer-events-none absolute -right-2 top-1 hidden max-w-[11rem] translate-x-full pl-4 forge-lg:block">
            <div className="pointer-events-auto opacity-80">
              <ConfidenceNote
                preview={preview}
                loading={previewLoading}
                error={previewError}
              />
            </div>
          </div>
        </div>

        <div className="mt-3 forge-lg:hidden">
          <ConfidenceNote
            preview={preview}
            loading={previewLoading}
            error={previewError}
          />
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
              {t("idea.opening.nameQuestion")}
            </h2>

            <TextField
              ref={nameRef}
              label={t("idea.opening.nameLabel")}
              placeholder={t("idea.opening.namePlaceholder")}
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
}