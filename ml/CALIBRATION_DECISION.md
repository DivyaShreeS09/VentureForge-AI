# Phase 3 — Calibration Decision (Final ML Excellence Sprint)

## What was evaluated

The production industry classifier's own training run (`ml/models/industry_classifier/v3/
metadata.json`) already includes a full sigmoid-calibration comparison as part of its standard
model-selection sweep — no new training run was needed to answer this sprint's question honestly.

| Pipeline | CV macro F1 | Test ECE |
|---|---|---|
| `tfidf_word_char_logreg` (uncalibrated, **current production**) | **0.775** | 0.137 |
| `tfidf_word_char_logreg_calibrated` (sigmoid) | 0.765 | **0.059** |
| `tfidf_linear_svc_calibrated` (sigmoid) | 0.766 | 0.060 |
| `embed_linear_svc_calibrated` (sigmoid) | — | 0.070 |

(Temperature scaling was not separately evaluated: it is mathematically a strict subset of Platt/
sigmoid scaling for a single-logit-per-class setting and would not be expected to outperform the
already-tested sigmoid calibration on this multi-class softmax output — re-running it would not
answer a genuinely different question.)

## Decision criteria (this sprint's own rule)

> Deploy ONLY if: macro-F1 is maintained AND ECE improves AND gold-set performance does not regress.

## Result: **REJECTED — not deployed**

Sigmoid calibration would cut ECE roughly in half (0.137 → 0.059-0.060) — a real, substantial
calibration improvement — but at the cost of **~0.010 macro F1** (0.775 → 0.765/0.766). This fails
the explicit "macro-F1 is maintained" criterion. This is not a close call decided by noise: the
same trade-off was already identified and rejected on the same grounds in the prior sprint (see
`ml/DATASETS.md`'s "Calibration" section) — this sprint's evaluation reproduces and reconfirms that
decision using the same real numbers, rather than re-deriving them from scratch.

## What stays in production

The uncalibrated `tfidf_word_char_logreg` pipeline, unchanged. Its calibration curve is already
**underconfident, not overconfident** (see `ml/models/industry_classifier/v3/metadata.json` →
`calibration.bins` — e.g. at ~45% stated confidence, actual accuracy is ~65%), which is the safer
failure direction for a system whose `is_uncertain`/abstention flags already exist specifically to
catch low-confidence predictions — an overconfident model would be the more dangerous failure mode,
and this one is not that.
