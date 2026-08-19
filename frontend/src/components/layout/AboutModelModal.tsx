import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { getModelsStatus } from "../../services/api";
import type { ModelStatus } from "../../types/api";
import { GlassCard } from "../../primitives/GlassCard";

interface Props {
  open: boolean;
  onClose: () => void;
}

/** Surfaces the real, live model metadata from `GET /models/status` — version, training
 * timestamp, rubric version. Never invents an accuracy figure or benchmark not returned by the
 * API (see ml/DATASETS.md for why this project treats fabricated metrics as a hard rule).
 *
 * A proper card, not a narrow vertical strip: centered icon badge, a 2-column metrics grid (four
 * tiles read as a small dashboard, not a tall stack you have to scroll past), generous padding,
 * and a 24px corner radius distinct from the rest of the app's normal 6/12/20px scale —
 * deliberately, since this is the one floating utility panel meant to feel like a compact glass
 * tile rather than a page-level surface. `max-h-[85vh]` + internal scroll guarantees the
 * methodology paragraph and Close button are never clipped off-screen on short viewports. */
export function AboutModelModal({ open, onClose }: Props) {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!open) return;
    getModelsStatus()
      .then(setStatus)
      .catch(() => setError(true));
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-forge-canvas/80 p-6 backdrop-blur-md"
          onClick={onClose}
        >
          <GlassCard
            glow="accent-2"
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
            className="flex max-h-[85vh] w-full max-w-[440px] flex-col overflow-y-auto rounded-3xl p-8"
            role="dialog"
            aria-modal="true"
            aria-label="About the industry classification model"
          >
            <div className="flex flex-col items-center text-center">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-forge-accent-2/40 bg-forge-accent-2/10 shadow-glow-forge-accent-2">
                <svg viewBox="0 0 24 24" className="h-7 w-7 text-forge-accent-2-tint" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.35-1 .75-1 1.7" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none" />
                </svg>
              </div>
              <p className="mt-4 text-forge-1 font-medium uppercase tracking-[0.2em] text-forge-label">About Model</p>
              <h2 className="mt-1 font-forge-serif text-forge-4 font-bold text-forge-heading">Industry Classifier</h2>
            </div>

            {error && (
              <p className="mt-6 text-center text-forge-2 text-forge-desc">Model status is unavailable right now.</p>
            )}
            {!error && !status && <p className="mt-6 text-center text-forge-2 text-forge-desc">Loading model status…</p>}
            {status && (
              <dl className="mt-7 grid grid-cols-2 gap-3">
                <div className="rounded-forge-md border border-forge-surface-border bg-forge-surface-2/40 px-4 py-3">
                  <dt className="text-forge-1 uppercase tracking-[0.1em] text-forge-helper">Model loaded</dt>
                  <dd className={`mt-1 text-forge-2 font-semibold ${status.industry_classifier_loaded ? "text-forge-emerald" : "text-forge-rose"}`}>
                    {status.industry_classifier_loaded ? "Yes" : "No"}
                  </dd>
                </div>
                <div className="rounded-forge-md border border-forge-surface-border bg-forge-surface-2/40 px-4 py-3">
                  <dt className="text-forge-1 uppercase tracking-[0.1em] text-forge-helper">Version</dt>
                  <dd className="mt-1 truncate text-forge-2 font-semibold text-forge-heading" title={status.industry_classifier_version ?? "—"}>
                    {status.industry_classifier_version ?? "—"}
                  </dd>
                </div>
                <div className="rounded-forge-md border border-forge-surface-border bg-forge-surface-2/40 px-4 py-3">
                  <dt className="text-forge-1 uppercase tracking-[0.1em] text-forge-helper">Trained at</dt>
                  <dd className="mt-1 text-forge-2 font-semibold text-forge-heading">
                    {status.industry_classifier_trained_at
                      ? new Date(status.industry_classifier_trained_at).toLocaleString()
                      : "—"}
                  </dd>
                </div>
                <div className="rounded-forge-md border border-forge-surface-border bg-forge-surface-2/40 px-4 py-3">
                  <dt className="text-forge-1 uppercase tracking-[0.1em] text-forge-helper">Funding rubric</dt>
                  <dd className="mt-1 truncate text-forge-2 font-semibold text-forge-heading" title={status.funding_rubric_version}>
                    {status.funding_rubric_version}
                  </dd>
                </div>
              </dl>
            )}

            <p className="mt-6 text-forge-1 leading-relaxed text-forge-helper">
              TF-IDF + Logistic Regression, trained on real Y Combinator company descriptions.
              Funding readiness is a deterministic rubric, not a trained probability. See the
              project README for the full methodology.
            </p>

            <div className="mt-7 flex justify-center">
              <button
                onClick={onClose}
                className="w-full rounded-forge-md border border-forge-surface-border px-6 py-2.5 text-forge-2 font-medium text-forge-desc transition-colors hover:border-forge-accent-2/50 hover:bg-forge-surface-2/60 hover:text-forge-heading focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-accent-2"
              >
                Close
              </button>
            </div>
          </GlassCard>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
