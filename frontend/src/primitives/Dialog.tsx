import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMotionTier } from "../motion/transitions";
import { Button } from "./Button";

export interface DialogProps {
  open: boolean;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

// Design System Bible §7 / Build Contract §9 — reserved exclusively for destructive or
// hard-to-reverse actions. Always one specific sentence naming exactly what will
// happen, never a generic "Are you sure?", and always two visually asymmetric buttons
// so the safer path is never ambiguous (Implementation Master Plan §9).
export function Dialog({ open, message, confirmLabel, cancelLabel, onConfirm, onCancel }: DialogProps) {
  const transition = useMotionTier("scene");
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus();
    };
  }, [open, onCancel]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={transition}
          className="fixed inset-0 z-50 flex items-center justify-center bg-forge-canvas/[.48]"
        >
          <motion.div
            ref={dialogRef}
            role="alertdialog"
            aria-modal="true"
            aria-label={message}
            tabIndex={-1}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={transition}
            className="w-full max-w-sm rounded-forge-lg border border-forge-text/[.16] bg-forge-surface-2 p-6 shadow-forge-1"
          >
            <p className="text-forge-3 text-forge-text">
              {message}
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <Button variant="ghost" onClick={onCancel}>
                {cancelLabel}
              </Button>
              <Button variant="primary" onClick={onConfirm}>
                {confirmLabel}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
