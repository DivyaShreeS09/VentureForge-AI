import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { getModelsStatus } from "../../services/api";
import type { ModelStatus } from "../../types/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

/** Surfaces the real, live model metadata from `GET /models/status` — version, training
 * timestamp, rubric version. Never invents an accuracy figure or benchmark not returned by the
 * API (see ml/DATASETS.md for why this project treats fabricated metrics as a hard rule). */
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
          className="fixed inset-0 z-50 flex items-center justify-center bg-void-950/80 p-6 backdrop-blur-md"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            onClick={(e) => e.stopPropagation()}
            className="panel panel-glow w-full max-w-md p-7"
            role="dialog"
            aria-modal="true"
            aria-label="About the industry classification model"
          >
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-signal-400">About Model</p>
            <h2 className="mt-2 text-display text-xl text-ink-primary">Industry Classifier</h2>

            {error && (
              <p className="mt-4 text-sm text-ink-muted">Model status is unavailable right now.</p>
            )}
            {!error && !status && <p className="mt-4 text-sm text-ink-muted">Loading model status…</p>}
            {status && (
              <dl className="mt-5 space-y-3 text-sm">
                <div className="flex justify-between border-b border-white/5 pb-2">
                  <dt className="text-ink-muted">Model loaded</dt>
                  <dd className={status.industry_classifier_loaded ? "text-success-400" : "text-danger-400"}>
                    {status.industry_classifier_loaded ? "Yes" : "No"}
                  </dd>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-2">
                  <dt className="text-ink-muted">Version</dt>
                  <dd className="text-ink-primary">{status.industry_classifier_version ?? "—"}</dd>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-2">
                  <dt className="text-ink-muted">Trained at</dt>
                  <dd className="text-ink-primary">
                    {status.industry_classifier_trained_at
                      ? new Date(status.industry_classifier_trained_at).toLocaleString()
                      : "—"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-ink-muted">Funding rubric version</dt>
                  <dd className="text-ink-primary">{status.funding_rubric_version}</dd>
                </div>
              </dl>
            )}

            <p className="mt-5 text-xs leading-relaxed text-ink-muted">
              TF-IDF + Logistic Regression, trained on real Y Combinator company descriptions.
              Funding readiness is a deterministic rubric, not a trained probability. See the
              project README for the full methodology.
            </p>

            <button
              onClick={onClose}
              className="mt-6 rounded-lg border border-white/15 px-4 py-2 text-sm font-medium text-ink-secondary transition hover:border-signal-400/50 hover:bg-white/5 focus-visible:outline-none"
            >
              Close
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
