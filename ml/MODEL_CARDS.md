# Model Cards

Final ML Excellence Sprint, Phase 5. Every number below is copied directly from a real, on-disk
training artifact's `metadata.json` — never re-derived or rounded for effect. Internal artifact
folder names (e.g. `industry_classifier/v3`) are engineering history; the public-facing version of
every model is **v1** (see each model's own `PUBLIC_MODEL_VERSION`/`PUBLIC_VENTURE_RETRIEVAL_VERSION`
constant) since this product has never shipped a prior version to remove.

---

## Model Card: Industry Classifier

- **Purpose**: classify a startup's industry (one of 7 classes: b2b, consumer, healthcare, fintech,
  industrials, real estate and construction, education) from a short name+description founder pitch,
  to drive downstream market/competitor/persona agents.
- **Public version**: v1. **Internal artifact**: `industry_classifier/v3` (`tfidf_word_char_logreg`).
- **Training data**: merge of three real, licensed YC public-directory exports — 4,522 rows
  (2012-2024, CC BY 4.0), 629 rows (2025, Apache-2.0), 5,884 rows (every batch 2005-2026,
  CC-BY-SA-4.0) — deduplicated on exact description text (never name, per a documented 3.5%
  name-collision rate), 7,227 rows after cleaning, 140-row gold set held out before any
  train/test split. n_train=5,781, n_test=1,446.
- **Training methodology**: TF-IDF (word 1-2gram + char 3-5gram FeatureUnion) → Logistic Regression
  (`class_weight="balanced"`), selected via 5-fold stratified CV macro-F1 against 10 other
  candidates (dummy baseline, ComplementNB, calibrated LinearSVC, LSA/SVD, and a real sentence-
  transformer embedding comparison — none beat this pipeline).
- **Evaluation protocol**: stratified train/test split (seed 42) + independent 140-row gold set
  never touched during training/CV/selection.
- **Metrics** (held-out test set, n=1,446): accuracy 0.793, macro F1 **0.769**, macro precision
  0.738, macro recall 0.813, weighted F1 0.799, top-2 accuracy **0.960**, log loss 0.684, ECE
  **0.137**. **Gold set** (n=140, fully independent): accuracy 0.771, macro F1 0.780, top-2
  accuracy 0.921.
- **Confusion matrix** (test set, labels in order b2b/consumer/education/fintech/healthcare/
  industrials/real estate and construction):
  ```
  [[609  93   4  50  10  23   6]
   [ 17 160   3   6   3   4   2]
   [  1   1  22   0   2   0   0]
   [ 15   5   1 120   2   1   3]
   [  9   8   0   2 135   5   0]
   [  8   3   0   1   3  76   0]
   [  5   1   0   1   0   1  25]]
  ```
- **Limitations**: exclusively YC-backed startups (English-only, YC vocabulary/framing) — has not
  been evaluated against non-YC company descriptions. B2B is ~55% of training data.
- **Biases**: b2b/consumer confusion is the dominant error mode (47 test-set b2b↔consumer
  misclassifications) — ambiguous "platform"-style language biases toward b2b. Education and
  real-estate-and-construction are the smallest classes (weakest per-class support).
- **Known failure cases**: no recognized vocabulary (zero TF-IDF signal) → flagged uncertain;
  confidence <0.35 → flagged uncertain; top-1/top-2 within 0.10 → flagged ambiguous. Non-English
  input produces a low-signal, uncertain prediction rather than a meaningful classification.
- **Deployment decision**: production (unchanged this sprint — see Phase 3 for the calibration
  experiment considered and rejected).
- **Inference latency**: 2.37ms/prediction (measured on this development machine).
- **Memory footprint / artifact size**: TF-IDF vectorizer (word max_features=20k, char
  max_features=8k, both min_df=2) + logistic regression coefficients — small enough to load in
  well under a second; exact artifact byte size not separately tracked in metadata (a documented
  gap — see Remaining Limitations in the sprint report).

---

## Model Card: Success Predictor

- **Purpose**: a "Historical Pattern Signal" — compares a startup's submitted metrics (funding
  history, company age, category, country) against historical company outcome patterns. Explicitly
  **not** a prediction of whether this specific idea will succeed.
- **Public version**: v1 (internal artifact folder is also `v1` — no relabeling needed).
- **Training data**: Crunchbase export (via data.world, CDLA-Sharing-1.0), 66,368 rows, resolved to
  a near-balanced 13,334-row outcome set (`success` = acquired/ipo, `failure` = closed; `operating`
  rows excluded — no resolved outcome, not labeled either way). n_train=10,667, n_test=2,667.
- **Training methodology**: engineered features (`company_age_years`, `funding_span_years`,
  `funding_per_category`, `time_to_first_funding_years`, `funding_recency_years`,
  `primary_category`, `category_count`, `country_code`) → HistGradientBoostingClassifier, selected
  via RepeatedStratifiedKFold CV ROC-AUC against 6 other candidates (dummy, logistic regression,
  random forest, extra trees, gradient boosting, a target-encoded variant, a soft-voting ensemble —
  none beat it). Sigmoid-calibrated (`CalibratedClassifierCV`).
- **Evaluation protocol**: stratified train/test split (seed 42), 0 leakage (verified by permalink
  uniqueness check), overfitting gap checked via train-vs-test ROC-AUC delta.
- **Metrics** (held-out test set, n=2,667): accuracy 0.774, balanced accuracy 0.771, F1 0.795,
  **ROC-AUC 0.855**, PR-AUC 0.856, Brier score 0.154, **MCC 0.546**, **Cohen's Kappa 0.545**, ECE
  **0.019** (well-calibrated).
- **Confusion matrix** (test set, labels [0=failure, 1=success]):
  ```
  [[899 349]
   [253 1166]]
  ```
- **Limitations**: funding-history features are cumulative totals as of the last recorded funding
  event — partly reflect the outcome's own timeline, not purely independent early-stage signal (a
  structural property of any static Crunchbase snapshot). Company-level fields do not include the
  founder's free-text pitch description.
- **Biases**: `funding_total_usd` dominates permutation importance (0.069, by far the largest of 9
  features) — the model leans heavily on capital raised as a proxy for outcome.
- **Known failure cases**: missing input fields are imputed with training-set medians/modes and
  reported via `missing_features` — never presented as a fully-informed estimate from partial data.
  Domain is Crunchbase-tracked companies only — not evaluated against bootstrapped businesses with
  no funding history.
- **Deployment decision**: production, unchanged this sprint.
- **Inference latency**: 254.2ms/prediction (measured on this development machine — includes the
  calibration wrapper's overhead).
- **Artifact size**: 2,446,316 bytes (~2.4MB) on disk.

---

## Model Card: Retrieval Index ("similar ventures" / Startup Benchmark)

- **Purpose**: semantic nearest-neighbor search returning real, historical companies whose
  description resembles the founder's — feeds Startup Benchmark, Competitor Intelligence, and GTM/
  Investor Intelligence's "compared to what?" sections. Explicitly NOT a live competitor database.
- **Public version**: v1 (internal artifact folder is `v2` — promoted last sprint after a measured
  quality improvement; see Known failure cases below for the honest v1-vs-v2 comparison).
- **Training data**: not a trained model — a fitted embedding index over 7,668 real company
  name+description+industry(+country/funding_stage/founding_year where available) rows, merged
  from 4 real, licensed sources (see `ml/src/preprocessing/build_retrieval_corpus.py` for full
  per-source provenance/licensing).
- **Training methodology**: frozen, pretrained `all-MiniLM-L6-v2` sentence-transformer (no
  fine-tuning) embeds every corpus description once, offline; retrieval is exact brute-force cosine
  similarity at request time (no ANN index — unnecessary at this corpus size).
- **Evaluation protocol**: leave-one-out same-industry agreement over the 7-class controlled
  taxonomy subset (the only non-fabricated relevance proxy available — no human relevance
  judgments exist or were fabricated).
- **Metrics** (internal v2 artifact, n=7,173 eligible queries): Precision@1 **0.737**, Precision@3
  0.721, Precision@5 0.711, MRR **0.824**, NDCG@5 **0.851**, coverage 94.98%, failure rate 5.02%.
- **Limitations**: this evaluation measures "does retrieval surface industry-coherent neighbors,"
  not "does retrieval find this founder's true real-world competitors" — no such ground truth
  exists. Country/funding-stage coverage is 90.1%/85.5% (not 100%) — comparative-intelligence
  fields explicitly disclose per-run coverage rather than implying full corpus support.
- **Biases**: corpus is YC-portfolio-shaped (b2b ~50% of controlled-taxonomy rows) — retrieval will
  surface more b2b neighbors than a uniformly-distributed startup population would justify.
- **Known failure cases**: internal v1→v2 corpus-quality experiment (last sprint) showed a real
  measured improvement on every precision/ranking metric except recall@5 (which fell slightly, an
  expected artifact of the larger corpus, not a regression). This sprint's Phase 2 cross-encoder
  second-stage reranking experiment's outcome and deploy/reject decision is recorded in the sprint
  report below (see "Experiments performed").
- **Deployment decision**: v2 corpus is production (promoted last sprint on measured evidence).
- **Inference latency**: similarity-matrix build ~639ms for the full 7,668-row corpus (one-time per
  process/cache); per-query lookup ~0.20ms.
- **Memory footprint / artifact size**: `corpus_embeddings.npy` (11.8MB, float32) +
  `corpus_metadata.json` (5.7MB) — loaded once per process via `lru_cache`.
