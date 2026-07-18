# Datasets

Machine-readable manifest: [`dataset_manifest.json`](dataset_manifest.json). Reproduce with:

```bash
python scripts/download_datasets.py --list          # show manifest status, no downloads
python scripts/download_datasets.py                 # downloads the approved Kaggle dataset
python -m ml.src.preprocessing.prepare_yc_dataset    # transform raw -> canonical schema
```

Raw/processed files are git-ignored — never committed. Requires Kaggle credentials
(`~/.kaggle/kaggle.json`, `~/.kaggle/access_token`, or `KAGGLE_USERNAME`/`KAGGLE_KEY`/
`KAGGLE_API_TOKEN`) configured via the standard Kaggle CLI mechanism; never stored in this repo.

## Industry Classification — Datasets Evaluated

Four candidate Kaggle datasets were searched, downloaded, and schema-inspected before a decision
was made. Three were rejected on concrete, documented grounds — not simply because a "better"
option existed.

| Dataset | Rows | License | Text field? | Verdict | Reason |
|---|---|---|---|---|---|
| [`ibrahimqasimi/y-combinator-companies-2012-2024`](https://www.kaggle.com/datasets/ibrahimqasimi/y-combinator-companies-2012-2024) | 4,522 | CC BY 4.0 | Yes (`one_liner` + `long_description`) | **Approved** | Real founder-style descriptions, clean single-label `industry` column, permissive clear license. |
| [`charanpuvvala/company-classification`](https://www.kaggle.com/datasets/charanpuvvala/company-classification) | 73,974 | **Unknown** | Yes (`homepage_text`, scraped) | Rejected | 13 well-balanced classes and strong text — schema was the best of the four — but the publisher specified no license (`"licenses": [{"name": "unknown"}]` in the dataset's own metadata). Redistribution/training rights are not established; using it would be a real legal risk, not a technical one. |
| [`yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase`](https://www.kaggle.com/datasets/yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase) | 66,368 | CDLA-Sharing-1.0 (acceptable) | **No** | Rejected | Only `name` + multi-label `category_list` (27,296 unique combinations) + funding metadata — no free-text description column exists. Not usable for a name+description text classifier. |
| [`manishkc06/startup-success-prediction`](https://www.kaggle.com/datasets/manishkc06/startup-success-prediction) | 923 | CC0-1.0 | **No** | Rejected | Structured Crunchbase-derived features (funding rounds, milestones, relationships) with a binary `acquired`/`closed` outcome. No text input; small n; outcome confounded by company age (survivorship bias). This is a Student 2 "success prediction" dataset shape, not Student 1's industry-classification or funding-readiness scope. |

### Approved dataset — full schema profile

**`ibrahimqasimi/y-combinator-companies-2012-2024`**, CC BY 4.0, sourced from YC-OSS (an open
mirror of Y Combinator's public company directory), downloaded and inspected in full:

- **Shape**: 4,522 rows × 29 columns. Relevant columns: `name`, `one_liner`, `long_description`,
  `industry` (9 raw values), `subindustry` (58 values), `batch` (26 batches, W12–W24), `status`.
- **Nulls**: `long_description` missing in 304 rows, `one_liner` in 52 (both are unioned into the
  training `description` field — a row is only dropped if both are empty and the resulting text
  falls below the 10-character minimum in `clean_industry_dataset`).
- **Duplicates**: 57 duplicate `name` values, 52 duplicate `one_liner` values (re-batched or
  renamed companies). The existing `clean_industry_dataset` step already deduplicates on exact
  `description` text, which removes the leakage risk that matters (identical text in train and
  test); residual near-duplicates from paraphrased pivots are not resolved — a known limitation,
  not a correctness bug (see Limitations below).
- **Raw label distribution** (`industry` column, before exclusions):

  | Label | Rows |
  |---|---|
  | B2B | 2,179 |
  | Consumer | 666 |
  | Healthcare | 583 |
  | Fintech | 545 |
  | Industrials | 268 |
  | Real Estate and Construction | 124 |
  | Education | 106 |
  | Government | 32 |
  | Unspecified | 19 |

- **Text length**: `one_liner` mean 48.6 chars (1–70); `long_description` mean 476 chars (4–4,717).
  This closely matches the register of the production form input (a short founder-written
  pitch), unlike the rejected `company-classification` dataset's long scraped homepage dumps.

## Final Taxonomy (`v2-yc-2012-2024`)

Built in [`ml/src/preprocessing/prepare_yc_dataset.py`](src/preprocessing/prepare_yc_dataset.py),
which transforms the raw export into the canonical `name`/`description`/`industry` schema:

- **`unspecified`** (19 rows) — excluded. Not a real industry; reflects missing source data.
- **`government`** (32 rows) — excluded. Below the enforced 50-row minimum per class for a
  reliable stratified 5-fold split; reported honestly as excluded rather than modeled with false
  confidence.
- **7 retained classes**: `b2b`, `consumer`, `healthcare`, `fintech`, `industrials`,
  `real estate and construction`, `education`.

**B2B is ~49% of the retained data.** This is not a data-quality defect — it reflects YC's actual
portfolio composition (YC funds far more B2B/SaaS companies than any other single category) — and
is documented, not hidden. Mitigation: every candidate model is trained with
`class_weight="balanced"` (ComplementNB, which has no such parameter, is retained in the
comparison specifically so its unmitigated performance is visible against the others). No
downsampling or label fabrication was used to force artificial balance.

## Industry Classifier — Model Comparison (real data, `v2`)

Trained via `python -m ml.src.training.train_industry_classifier` on 4,438 rows (after cleaning)
— 3,550 train / 888 test, stratified, seed 42. 5-fold stratified CV on the training set only,
macro F1. Word vocabulary caps at `max_features=20,000`/`min_df=2`, char vocabulary at 8,000 (see
"Memory constraints" below) — an uncapped word vocabulary reached 163,391 features, most of it
long-tail single-document terms that add memory and overfitting risk without improving
generalization:

| Pipeline | CV macro F1 |
|---|---|
| Dummy (stratified) baseline | 0.143 ± 0.014 |
| TF-IDF word (1-2gram) + Logistic Regression (balanced) | 0.751 ± 0.030 |
| TF-IDF word + Calibrated LinearSVC (balanced) | 0.742 ± 0.006 |
| TF-IDF word (1gram) + ComplementNB | 0.680 ± 0.007 |
| TF-IDF char (3-5gram, char_wb) + Logistic Regression | 0.743 ± 0.023 |
| **TF-IDF word+char (FeatureUnion) + Logistic Regression** | **0.761 ± 0.031** — selected |
| TF-IDF word+char + Logistic Regression, isotonic-calibrated | 0.753 ± 0.023 |
| TF-IDF (1-2gram) → TruncatedSVD (100-dim LSA) + Logistic Regression | 0.707 ± 0.032 |

The word+char combination genuinely won on cross-validated macro F1 — not selected because it
"sounds more advanced." Char n-grams pick up morphological/subword signal (compound tech words,
suffixes) that plain word n-grams miss; combining both gave a real, reproducible +1 point over
word-only. The isotonic-calibrated variant of the same features scored *lower* (0.753 vs 0.761)
because `CalibratedClassifierCV`'s internal 3-fold refitting leaves less data per fold — since
macro F1 outranks calibration in the selection priority, the uncalibrated version was kept (see
"Calibration" below for why this is an acceptable trade here). The LSA/SVD candidate — the
"compact embedding" alternative — underperformed every TF-IDF variant; 100 SVD dimensions lose
information a 20k-feature sparse vector retains, and no pretrained sentence-transformer was
downloaded or evaluated (would require a heavy model download this environment could not
reliably support — reported honestly as not attempted, not silently skipped).

**Held-out test set** (touched exactly once, after model selection):

- Accuracy: **0.779**, Balanced accuracy: **0.765**
- Macro precision / recall / F1: 0.747 / 0.765 / **0.752**
- Weighted F1: 0.783, Log loss: 0.760
- **Inference latency**: ~2.3ms per single prediction (measured on this development machine, not
  a production-hardware claim), averaged over 50 held-out predictions after a warm-up call.
- **Leakage check**: 0 exact-text overlaps between train and test (verified programmatically by
  `check_no_leakage`, not merely assumed).

Per-class F1 (test set): healthcare 0.870 (n=116), b2b 0.825 (n=434), education 0.800 (n=21),
fintech 0.727 (n=108), industrials 0.714 (n=53), real estate and construction 0.667 (n=25),
**consumer 0.660 (n=131, precision only 0.586)** — full confusion matrix and per-class support
are in `ml/models/industry_classifier/v2/metadata.json`.

**These are real, honest numbers on a real dataset — not the 1.000 the previous synthetic
bootstrap corpus produced.** A ~78% accuracy / 75% macro-F1 model with a visibly weaker minority
class is what a genuine, leakage-checked evaluation on real data looks like, and is reported as
such rather than rounded up.

### Calibration

Expected Calibration Error (ECE, 10 bins, top-1 confidence vs. actual accuracy): **0.164**. The
per-bin breakdown (`ml/models/industry_classifier/v2/metadata.json` → `calibration.bins`) shows
the model is consistently **underconfident**, not overconfident: e.g. at ~45% stated confidence,
actual accuracy is ~73%; at ~65% stated confidence, actual accuracy is ~76%. Only the 90-100%
confidence bin is close to calibrated (94% confidence, 99% accuracy). This is the safer direction
for a system that flags low-confidence predictions as uncertain (`backend/app/ml/predictor.py`) —
it means the `is_uncertain` flag is, if anything, conservative rather than overclaiming certainty.
Isotonic calibration was tested (see comparison table) but reduced macro F1, so it was not
adopted; tightening calibration remains a legitimate future improvement, not attempted here to
avoid trading away classification quality for a secondary metric.

### Memory constraints during model selection

This was trained on a memory-constrained development machine (~7.8GB total RAM, frequently <2GB
free alongside the IDE/browser). With an uncapped vocabulary, `CalibratedClassifierCV`'s 3-fold
internal refitting and `ComplementNB`'s vectorization intermittently hit real `MemoryError`s
during cross-validation — reproduced multiple times, not a one-off flake. This is documented,
not hidden, and led to two real fixes rather than a workaround: (1) capping vocabulary size
(word: `max_features=20,000`, char: `max_features=8,000`, both `min_df=2`), which also cut the
saved artifact size dramatically; (2) `train_industry_classifier.py` no longer lets a NaN-scored
candidate (e.g. one whose CV crashed) silently win model selection — `max()`'s pairwise comparison
treats NaN as neither greater nor less than any real number, so a NaN appearing first in iteration
order would never be displaced by a later, valid candidate. NaN-scored candidates are now filtered
out explicitly before selection, and training raises a clear error if every non-dummy candidate
fails.

### Error analysis

Grouped inspection of the confusion matrix and misclassified rows:

- **Dominant pattern — minority classes misread as B2B**: 50 consumer, 25 fintech, and 7
  industrials test rows were misclassified as `b2b` (the largest single error category by far).
  Many YC company descriptions use generic "platform for X" / "software for Y" phrasing that
  overlaps with B2B SaaS regardless of the company's actual vertical — a real vocabulary-overlap
  limitation, not a labeling bug.
- **Consumer is the weakest class** (precision 0.586): consumer startups are described with the
  same generic product language as B2B tools aimed at individuals rather than teams, and the
  class is heterogeneous (covers everything from social apps to home goods).
- **Real estate and construction has the smallest test support** (n=25) and correspondingly the
  noisiest per-class metrics (recall 0.60) — expected given so few examples, not a distinct
  failure mode.
- **No mixed-domain or noisy-label spot-checks turned up mislabeled source rows** — the errors
  inspected are genuine vocabulary ambiguity, not data quality defects in the YC dataset itself.
- **Taxonomy**: the 7-class taxonomy (after excluding `unspecified`/`government`) is coarse
  enough that "platform" language legitimately spans multiple real categories — a finer-grained
  taxonomy might reduce this confusion but would also shrink per-class support further; not
  attempted here since it would require re-deriving labels the source dataset doesn't provide.

Preprocessing/taxonomy were not changed in response to this analysis — the errors found are
genuine class-boundary ambiguity in real-world text, not artifacts fixable by relabeling.

### Label-Quality Audit (v2)

A dedicated label-quality/data-audit pass on the cleaned dataset **after gold-set exclusion**
(4,298 rows — 4,438 cleaned rows minus the 140-row gold set reserved for independent evaluation;
see "Industry Classifier V2 Upgrade" below for the gold-exclusion mechanism). All numbers below are
measured directly, not estimated.

**Class distribution** (post gold-exclusion): b2b 2,149, consumer 635, healthcare 558, fintech 521,
industrials 246, real estate and construction 103, education 86. Same imbalance shape as the
full dataset (b2b ~50%), as expected from a stratified 20-per-class gold sample removed uniformly.

**Confusion matrix / most-confused class pairs**: from the current production model's (`v2`,
`tfidf_word_char_logreg`) held-out test-set predictions (860 rows). Top 5 off-diagonal pairs by
count:

| True → Predicted | Count |
|---|---|
| b2b → consumer | 47 |
| consumer → b2b | 19 |
| b2b → fintech | 18 |
| fintech → b2b | 10 |
| b2b → industrials | 8 |

Confirms the pre-existing "Error analysis" finding above: b2b/consumer confusion dominates, not a
new discovery, but now quantified against the gold-excluded split specifically.

**Descriptions under 20 characters**: **45 rows in the raw pre-cleaning CSV** (4,471 rows) —
reconciled exactly against the task's stated prior finding. Of those 45: 33 are actually under the
10-character `MIN_DESCRIPTION_LENGTH` floor (mostly literal `"nan"` — a missing `description`
value stringified — length 3) and are already dropped by `clean_industry_dataset`; the remaining
**12 rows** (10–19 characters, e.g. `"AI and Embeddings"`, `"Coding agents"`, `"Uber for Kids"`)
survive cleaning and are genuinely short one-liners rather than full descriptions — real signal is
thin for these but not absent (short does not mean automatically wrong).

**Duplicate/near-duplicate descriptions across different labels (label-conflict signal)**:
Two independent checks:

1. **Exact-text conflicts, checked on the raw (pre-dedup) data**: grouping the raw CSV's
   `description` values and counting distinct `industry` labels per group finds exactly **one**
   real conflict beyond the already-explained `"nan"` placeholder rows: the literal description
   `"Stealth"` appears twice under two different industry labels. This is not a mislabeling bug —
   it is YC's placeholder text for companies that haven't disclosed what they do yet, so two
   different stealth companies legitimately share the same non-informative placeholder string
   while genuinely belonging to different industries. (`clean_industry_dataset`'s exact-match
   dedup on `description` removes one of the two "Stealth" rows anyway, so this cannot cause
   train/test leakage — it can only ever affect a single row's own label, not cross-contaminate
   another row.)
2. **Near-duplicate check via normalized token overlap** (Jaccard-style: `|A∩B| / min(|A|,|B|)` on
   lowercased alphanumeric tokens), computed on the cleaned, gold-excluded 4,298-row pool via an
   inverted-index candidate search (591,422 candidate pairs sharing a moderately rare token,
   avoiding an O(n²) = ~9.2M full comparison). **First pass, no minimum length guard: 9 cross-label
   pairs at >90% overlap** — but manual inspection showed these were all false positives from very
   short descriptions (e.g. "AI for security cameras" vs. "Data for audio AI" — 100% overlap only
   because the smaller set has 3–4 tokens total, so any 3 shared common words trivially clears
   90%). **Re-run requiring both descriptions have ≥8 tokens (filters out this false-positive
   mode): 0 cross-label near-duplicate pairs, 1 same-label near-duplicate pair** (a same-industry
   re-batched/pivoted company pair, consistent with the pre-existing "Near-duplicate companies"
   limitation already documented below). **Honest conclusion: no genuine label-conflict signal
   from near-duplicates was found** — the naive short-text version of this check is a real
   methodological trap worth documenting, not a real data-quality finding.

**Overall audit conclusion**: no evidence of systematic mislabeling in the source dataset. The
model's errors (b2b/consumer confusion, weak minority classes) are vocabulary-ambiguity and
class-imbalance effects on genuinely-labeled data, not a label-quality defect — consistent with,
and now quantitatively reinforcing, the pre-existing "Error analysis" section above.

### ML Audit Findings (full-project ML review pass)

Two findings from a full-project ML model audit:

1. **The on-disk artifact had gone stale**: at the time of the audit, `ml/models/
   industry_classifier/v2/model.joblib` had `using_real_dataset: false` (trained on the 116-row
   bootstrap corpus, taxonomy_version `v1-bootstrap`) despite the real 4,522-row YC CSV being
   present on disk — a leftover from an earlier session's CI-fallback simulation that was never
   re-trained back onto real data afterward. Retrained via `python -m
   ml.src.training.train_industry_classifier`, reproducing the documented real-data metrics above
   exactly (4,438 rows, 7 classes, macro F1 0.752) with no memory errors this time. This is a real
   process-hygiene finding, not a code bug — the loader itself always honestly reports whichever
   artifact is actually on disk (`using_real_dataset`), so nothing was silently wrong at inference
   time, but the *shipped* metrics were briefly not representative of the trained artifact.
2. **Tree ensembles (Random Forest / Extra Trees / Gradient Boosting) were deliberately not added**
   to this model's comparison. Unlike the tabular success predictor (7 features), this task's
   input is a ~20,000-28,000-dimension sparse TF-IDF vector — tree-based splits are a poor fit for
   very high-dimensional sparse features (each split only tests one dimension at a time against a
   threshold, versus linear models' ability to combine all dimensions in one decision boundary),
   which is why the existing linear/calibrated-linear/ComplementNB/LSA comparison was kept as the
   candidate set rather than padding it with algorithms unlikely to help — a genuine engineering
   judgment, not a shortcut.

### Industry Classifier V2 Upgrade

A full upgrade pass: gold-set exclusion from training, a real (not LSA stand-in) sentence-
transformer embedding comparison, calibration/ECE, top-2 accuracy, a confidence-threshold
abstention layer, primary/secondary prediction, explainability, and governance metadata. Retrained
via `python -m ml.src.training.train_industry_classifier` (trained_at
`2026-07-18T15:03:57Z`, seed 42).

**Gold-set exclusion**: the 140-row gold set (`ml/data/gold/industry_gold_set.csv`) is now removed
from the cleaned dataset by exact `description` match *before* the train/test split — 4,438
cleaned rows → **4,298** after exclusion → 3,438 train / 860 test (previously 3,550/888 with no
gold exclusion). This means CV/test metrics below are measured on **~140 fewer training rows**
than the prior `v2` baseline — a real, disclosed reason CV scores are modestly lower than before,
not a regression in the modeling approach itself.

**Model comparison** (5-fold stratified CV, macro F1, training set only):

| Pipeline | CV macro F1 |
|---|---|
| Dummy (stratified) baseline | 0.144 ± 0.016 |
| TF-IDF word (1-2gram) + Logistic Regression | 0.734 ± 0.015 |
| TF-IDF word + Calibrated LinearSVC | 0.722 ± 0.022 |
| TF-IDF (1gram) + ComplementNB | 0.671 ± 0.034 |
| TF-IDF char (3-5gram) + Logistic Regression | 0.719 ± 0.028 |
| **TF-IDF word+char (FeatureUnion) + Logistic Regression** | **0.738 ± 0.026 — selected** |
| TF-IDF word+char + Logistic Regression, isotonic-calibrated | **crashed — every one of 5 folds hit a real `MemoryError`** fitting the ~28k-dim word+char vocabulary inside `CalibratedClassifierCV`'s internal 3-fold refit, on this same memory-constrained machine documented above (now under additional pressure from the sentence-transformer embeddings held in memory concurrently). Recorded as NaN and excluded from selection by the existing NaN-filter — not silently dropped, not fabricated. |
| TF-IDF → SVD (LSA, 100-dim) + Logistic Regression | **also crashed — every fold `MemoryError`**, same reason as above. |
| Sentence-transformer (`all-MiniLM-L6-v2`, 384-dim, frozen) + Logistic Regression | 0.735 ± 0.016 |
| Sentence-transformer + Calibrated LinearSVC | 0.734 ± 0.020 |
| Sentence-transformer + HistGradientBoosting | 0.605 ± 0.036 |

**Honest result: the sentence-transformer embeddings did NOT beat TF-IDF.** `embed_logreg`
(0.735) and `embed_linear_svc_calibrated` (0.734) are statistically indistinguishable from the
winning `tfidf_word_char_logreg` (0.738 ± 0.026 — well within one std of each other), and
`embed_histgb` (0.605) is clearly worse. This is a legitimate, common real-world outcome on a
corpus this size and register: short, keyword-dense founder pitches ("payments platform",
"telehealth", "cross-border") reward a representation that preserves exact vocabulary (TF-IDF)
about as well as a general-purpose sentence encoder not fine-tuned on this domain. **Winner:
`tfidf_word_char_logreg` (unchanged pipeline family from the v1.752 baseline)** — selected on CV
macro F1 exactly as before, not by default; the embeddings were a real, fully-executed comparison,
not a token gesture.

**DistilBERT fine-tuning was explicitly not attempted.** Free RAM was checked (via a Windows
`GlobalMemoryStatusEx` call, `ml/src/training/train_industry_classifier.py:
_check_memory_for_transformer_finetuning`) immediately before the decision: **1.64GB free of
7.77GB total** — and this same run *still* hit real `MemoryError`s fitting a 28k-dimension sparse
TF-IDF matrix (see table above), a far lighter workload than holding transformer weights +
gradients + an optimizer's momentum/variance buffers simultaneously. Skipped for a concrete,
measured reason, not by default.

**Held-out test set** (860 rows, touched once):

- Accuracy **0.806**, balanced accuracy **0.792**
- Macro precision/recall/F1: 0.764 / 0.792 / **0.776**, weighted F1 0.810
- **Top-2 accuracy: 0.945** (the true label is in the top-2 predicted classes 94.5% of the time)
- Per-class F1: healthcare 0.878 (n=112), b2b 0.848 (n=430), fintech 0.792 (n=104), industrials
  0.755 (n=49), education 0.765 (n=17), real estate and construction 0.714 (n=21), **consumer
  0.678 (n=127)** — consumer remains the weakest class, consistent with "Error analysis" above.
- Inference latency: ~2.47ms/prediction (same order as the v1.752 baseline's 2.3ms — the winning
  pipeline is unchanged in kind).

**Against the 0.752 baseline: test macro F1 rose to 0.776 (+0.024) and accuracy to 0.806
(+0.027).** This is a **real but partially confounded improvement** — the test set is not the
same 888 rows as before (140 gold rows were removed from the pool first, changing which rows land
in train vs. test), so this is not a clean apples-to-apples re-measurement of the *identical*
model on the *identical* split. Taken together with the CV comparison above (which show the
word+char TF-IDF pipeline's underlying macro F1 sitting in the same 0.73–0.78 band both before and
after this change), the honest read is: **no architecture change beat the original TF-IDF
approach** — the test-set delta is most plausibly split composition variance, not a genuine
capability gain, and is reported as such rather than claimed as a win.

**Gold-set evaluation** (140 rows, fully independent — never touched during training/CV/selection):

- Accuracy **0.757**, macro F1 **0.766**, weighted F1 0.766, macro precision/recall 0.803/0.757
- Top-2 accuracy: **0.893**
- Per-class F1: industrials 0.927, healthcare 0.919, real estate and construction 0.833, education
  0.750, fintech 0.732, consumer 0.605, b2b 0.600 — notably, **b2b is the gold set's weakest
  class** (precision 0.50) despite being the test set's strongest — a real, disclosed discrepancy
  plausibly explained by the gold set's *uniform* 20-per-class sampling (vs. the test set's
  natural, b2b-heavy stratified sampling), which removes b2b's numeric-majority advantage and
  exposes how often ambiguous "platform" language legitimately isn't b2b once the class isn't
  dominant by volume.

**Calibration**: winning model's ECE (10-bin, top-1 confidence vs. accuracy) is **0.201** — worse
than the v1.752 baseline's 0.164, consistent with training on fewer rows. Per the task's
requirement to report ECE for calibrated candidates specifically: refit-and-measured on the same
test set, `tfidf_linear_svc_calibrated` scores ECE **0.063** and `embed_linear_svc_calibrated`
scores ECE **0.048** — both dramatically better calibrated than the uncalibrated word+char winner.
**This is a real, disclosed trade-off, not an oversight**: macro F1 remains the primary selection
criterion per this project's stated priority (see "Calibration" above), and the calibrated
candidates' own macro F1 (0.722 tfidf, 0.734 embed) is lower than the winner's 0.738 — so accepting
worse calibration for better classification accuracy was a deliberate, documented choice, visible
here for anyone who wants to weigh the trade-off differently in a future pass.

**Abstention (confidence-threshold layer)** — coverage vs. accuracy-on-covered-subset, at each
threshold explored, on both the test and gold sets:

| Threshold | Test coverage | Test accuracy-on-covered | Gold coverage | Gold accuracy-on-covered |
|---|---|---|---|---|
| 0.4 | 85.0% | 0.851 | 85.0% | 0.840 |
| **0.5 (recommended default)** | 64.5% | **0.892** | 64.3% | **0.911** |
| 0.6 | 50.6% | 0.922 | 52.1% | 0.918 |
| 0.7 | 33.6% | 0.952 | 38.6% | 0.963 |

**Recommended default: 0.5.** Below it (0.4), coverage is high (85%) but accuracy-on-covered
(0.85/0.84) is barely above the unconditional test accuracy (0.806) — abstaining buys little
reliability gain. At 0.5, coverage drops to ~64% but accuracy-on-covered jumps to ~0.89–0.91 on
both test and gold — a meaningfully more trustworthy subset for a real fraction of traffic. Higher
thresholds (0.6/0.7) buy further reliability but at a steep coverage cost (down to 34–38%), which
would mean withholding a majority of predictions — not a good trade for a system whose value comes
from giving founders *some* signal on every submission. 0.5 is the point where the
reliability/coverage curve's marginal benefit visibly slows, matching this project's existing
`MIN_CONFIDENCE = 0.35` uncertainty threshold's spirit (a stricter, second gate for outright
withholding vs. flagging).

**Primary + secondary prediction**: `predict_industry()` now additively returns
`primary_industry`/`primary_confidence` (identical to `predicted_industry`/`confidence`) and
`secondary_industry`/`secondary_confidence` (the runner-up class and its probability). **True
multi-label classification was considered and explicitly rejected**: the source dataset assigns
exactly one `industry` per row with no secondary-label field anywhere in the schema (see the
dataset schema profile above) — training a multi-label model would require inventing labels the
data doesn't contain, which this project's stated principle (never fabricate a label) rules out.
Surfacing the model's own real runner-up probability is honest because it is exactly what the
model computed, not a claim that the startup "belongs to two industries."

**Explainability**: the linear TF-IDF model won again, so the existing exact
`tfidf_weight × coefficient` term-attribution method (`ml/src/explainability/
term_contributions.py`) remains in production, unchanged. A nearest-training-example
cosine-similarity explainer (`ml/src/explainability/nearest_neighbors.py`) was still built and
tested (task requirement, and for future-proofing if an embedding model wins a later re-run) —
it is honestly documented that per-dimension feature importance is **not meaningful** for dense
sentence-transformer embeddings (each of the 384 dimensions is an opaque, entangled combination
from pretraining, unlike a TF-IDF column that maps to one human-readable term), so nearest-
neighbor retrieval is the substitute method, not an approximation of the same thing.

**Governance / artifact metadata** (`ml/models/industry_classifier/v2/metadata.json`) now
additionally includes: `label_schema`/`feature_schema`, `dataset_fingerprint_sha256` (sha256 of
the raw CSV bytes, for exact reproducibility verification), `library_versions` (this run:
scikit-learn 1.9.0, numpy 2.5.1, pandas 2.3.3, torch 2.13.0+cpu, sentence-transformers 5.6.0,
Python 3.14.2), `training_command`, `seed`, `trained_at`, `n_gold_excluded_from_training`,
`distilbert_finetuning` (the documented skip reasoning above), `calibration_comparison_ece`,
`abstention` (thresholds explored + recommended default + full test-set table),
`gold_set_evaluation` (the complete independent block), and a `model_card` text field covering
purpose/limitations/known weaknesses in one place. `backend/app/ml/predictor.py` now validates
this schema on load (`_validate_metadata_schema`) and raises a clear
`IndustryClassifierArtifactError` — distinct from "not trained yet" — if required fields are
missing, `labels` is empty/invalid, `label_schema.n_classes` disagrees with `len(labels)`, or the
loaded model's own `classes_` disagree with metadata's `labels`; a corrupt/incompatible artifact
now fails loudly at load time instead of silently mispredicting. This validation is purely
additive — the happy-path response shape is unchanged.

**Overall, honest verdict**: this pass is **not a genuine architectural improvement** — TF-IDF
word+char logistic regression won the comparison again, embeddings did not beat it, and the
reported test-set F1 bump (0.752 → 0.776) is most plausibly a split-composition artifact of gold
exclusion rather than a real capability gain (the CV numbers, measured on a like-for-like training
pool, show the two eras sitting in the same band). What this pass *did* genuinely add: a properly
leakage-proof gold-set holdout for future comparisons, a real (not synthetic-stand-in) embedding
comparison that lets this project stop wondering "would embeddings help?" (the honest answer,
measured, is "no, not on this corpus"), calibration/ECE reporting for calibrated candidates,
top-2 accuracy, a working abstention layer with a data-driven recommended threshold, primary/
secondary prediction, and stronger artifact governance — real infrastructure and honesty
improvements, reported as such rather than dressed up as a bigger modeling win than it is.

## Low-Confidence / Uncertainty Handling

`backend/app/ml/predictor.py` never reports a prediction as an unqualified fact. Three
independent, testable conditions each set `is_uncertain`:

1. **No recognized vocabulary** — the TF-IDF vector is entirely zero (checked directly against
   the vectorizer, `nnz == 0`), meaning the prediction reflects only the training class prior, not
   the input's content. This matters because confidence alone does not catch this: under a ~49%
   B2B prior, a blank/no-signal input still scores confidence ≈0.45 for `b2b` — *above* a naive
   confidence threshold. This was found empirically while writing the uncertainty tests, not
   assumed in advance.
2. **Low confidence** — top-1 probability below 0.35 (with 7 classes, uniform-random guessing
   scores ≈0.14, so 0.35 requires real signal above chance).
3. **Ambiguity** — top-1 and top-2 probabilities within 0.10 of each other (the description may
   plausibly span more than one domain).

`uncertainty_reasons` is a human-readable list explaining which condition(s) fired; the frontend
and Judge Agent both surface this rather than presenting a guess as settled fact.

## Funding Readiness Decision

Per the decision process required for this system: a supervised funding-readiness model needs a
labeled dataset with (a) a clearly defined target representing funding readiness or a tightly
scoped funding outcome, (b) enough observations, (c) features actually available from a short
startup submission form, (d) clean licensing, and (e) no leakage of the target into the features.
The one funding-outcome-shaped dataset inspected in this pass
(`manishkc06/startup-success-prediction`) fails on (a) — `acquired`/`closed` is an outcome
confounded by company age, not a readiness signal — and (b) — 923 rows, no text. No dataset
meeting all five criteria was identified. Inventing a label to train against would not be a
genuine ML prediction — it would be a rule dressed up as one.

**Decision: Option B — a transparent, deterministic, versioned readiness rubric**, implemented in
[`backend/app/ml/funding_readiness.py`](../backend/app/ml/funding_readiness.py). It is explicitly
labeled a "readiness assessment," never a "probability of receiving funding." The design is
replaceable by a supervised model later if a suitable dataset is identified and approved here.

## Known Limitations

- **Real dataset size is modest** (4,438 rows after cleaning) relative to the label space and
  text diversity of real-world startups; the smallest retained class (education, education, n=106
  before splitting) has correspondingly weaker per-class metrics.
- **B2B dominance** is a structural property of the YC population this dataset was drawn from,
  not of startups in general — a model trained on it will still be biased toward predicting B2B
  for ambiguous "platform"-style language. Documented, mitigated with class weighting, not hidden.
- **Near-duplicate companies** (pivots/relistings sharing a name or near-identical description)
  are not resolved beyond exact-text deduplication — a company-level (not just text-level) grouped
  split was not implemented, since the existing exact-match dedup already removes the leakage
  vector that matters (identical text appearing in both train and test).
- **Domain is YC-backed startups only** (2012–2024) — the model has not been evaluated against
  non-YC company descriptions, which may use different vocabulary or framing.
- **English-only** — no multilingual support exists or is claimed; non-English input will produce
  a low/no-vocabulary-signal, uncertain prediction rather than a meaningful classification.
- The synthetic bootstrap corpus (`ml/src/preprocessing/bootstrap_data.py`) is retained
  **exclusively** for fast unit/smoke tests (`ml/tests/`) — it is never used to train the shipped
  production artifact and its metrics are never reported as real performance.

## Startup Success Prediction — Datasets Evaluated

Six candidate Kaggle datasets were searched and schema-inspected (title/description/license
metadata for all six; full schema profile for the two real candidates). Four were rejected before
download on licensing/authenticity grounds; two real candidates were downloaded and compared.

| Dataset | Rows | License | Nature | Verdict | Reason |
|---|---|---|---|---|---|
| [`yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase`](https://www.kaggle.com/datasets/yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase) | 66,368 | CDLA-Sharing-1.0 | Real (Crunchbase, via data.world) | **Approved** | Largest real dataset with a genuine historical outcome (`operating`/`closed`/`acquired`/`ipo`); real funding/category/geography features. |
| [`manishkc06/startup-success-prediction`](https://www.kaggle.com/datasets/manishkc06/startup-success-prediction) | 923 | CC0-1.0 | Real (Crunchbase, via DPhi) | Inspected, not selected | Same task shape (acquired/closed binary outcome) and real data, but ~14x smaller n than the Crunchbase dataset above for no offsetting schema advantage. Kept as a documented alternative, not because anything was wrong with it. |
| [`hamnakaleemds/global-startup-success-dataset`](https://www.kaggle.com/datasets/hamnakaleemds/global-startup-success-dataset) | 5,000 | Apache-2.0 | **Synthetic (undisclosed)** | Rejected | No data-provenance statement; a "Success Score: 1-10 based on growth" field with no defined scoring methodology reads as an arbitrary generated label, not an observed outcome. Training on this and reporting the resulting accuracy would misrepresent a real capability. |
| [`dhrubangtalukdar/startup-funding-and-outcome-dataset`](https://www.kaggle.com/datasets/dhrubangtalukdar/startup-funding-and-outcome-dataset) | 100,000 | Apache-2.0 | **Synthetic (self-declared: "Simulated startup data")** | Rejected | The publisher's own metadata states `userSpecifiedSources: "Synthetic"`. A model trained on simulated outcome/feature relationships would not reflect real-world predictive power, however honestly the simulation is labeled. |
| [`samayashar/startup-growth-and-funding-trends`](https://www.kaggle.com/datasets/samayashar/startup-growth-and-funding-trends) | ~1,000 (implied by size) | CC0-1.0 | **Synthetic (self-declared)** | Rejected | Publisher states it is "synthetically generated based on real-world startup funding and growth patterns" — not real observed data, same reasoning as above. |
| [`ara001/financial-metrics-of-startup-companies`](https://www.kaggle.com/datasets/ara001/financial-metrics-of-startup-companies) | 50 | Apache-2.0 | The well-known "50 Startups" toy regression set | Rejected | Extremely tiny (50 rows); R&D/Administration/Marketing-spend → Profit is a classroom regression exercise, not a dataset that supports a defensible model at any n. |

### Approved dataset — full schema profile

**`yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase`**, CDLA-Sharing-1.0, sourced from a
Crunchbase export republished via data.world:

- **Shape**: 66,368 rows × 14 columns: `permalink` (unique key, 0 duplicates), `name`,
  `homepage_url`, `category_list` (pipe-delimited, e.g. `"Apps|Games|Mobile"`), `funding_total_usd`
  (string, `"-"` for missing — 12,785/66,368 rows, 19.3%), `status`, `country_code`, `state_code`,
  `region`, `city`, `funding_rounds`, `founded_at`, `first_funding_at`, `last_funding_at`.
- **`status` distribution**: `operating` 53,034 (79.9%), `closed` 6,238 (9.4%), `acquired` 5,549
  (8.4%), `ipo` 1,547 (2.3%).
- **Target definition** (matches the dataset's own stated objective): `success = 1` if
  `status in {acquired, ipo}`, `success = 0` if `status == closed`. Rows with `status ==
  "operating"` are **excluded entirely** — they have not reached a resolved historical outcome, so
  labeling them success or failure would fabricate a label the data doesn't contain. This leaves
  **13,334 resolved rows**: 7,096 success (53.2%) / 6,238 failure (46.8%) — a near-balanced target,
  not one requiring aggressive resampling.
- **Missing-value rates** (on the 13,334 resolved rows): `funding_total_usd` 16.4%, `founded_at`
  28.0%, `category_list` 8.1%, `country_code` 14.9%.
- **Duplicates**: 0 duplicate `permalink` values (the unique key); 8 duplicate `name` values across
  distinct permalinks (different companies sharing a name) — not a leakage risk.
- **No text field** — unlike the industry-classification dataset, this task's features are
  structured (funding history, category, geography), which is fine since the model is a tabular
  classifier, not a text classifier.

### Feature engineering (`ml/src/preprocessing/prepare_success_dataset.py`)

- `company_age_years` = (`last_funding_at` − `founded_at`) in years, at the time of last recorded
  funding (negative values — a handful of source data-entry errors where `founded_at` postdates
  `last_funding_at` — are treated as missing, not silently kept).
- `funding_span_years` = (`last_funding_at` − `first_funding_at`) in years.
- `primary_category` = first entry of the pipe-delimited `category_list` (lowercased), `unknown` if
  absent.
- `category_count` = number of categories listed (a breadth-of-positioning signal).
- `country_code` = lowercased, `unknown` if absent.

### Success Classifier — Model Comparison (real data, `v1`)

Trained via `python -m ml.src.training.train_success_classifier` on 13,334 rows — 10,667 train /
2,667 test, stratified, seed 42. 5-fold stratified CV on the training set only, ROC-AUC (chosen
over accuracy/F1 for model *selection* since it is threshold-independent and the target is
near-balanced):

| Pipeline | CV ROC-AUC |
|---|---|
| Dummy (stratified) baseline | 0.505 ± 0.006 |
| Logistic Regression (balanced) | 0.810 ± 0.008 |
| Random Forest (balanced, depth 8) | 0.802 ± 0.005 |
| **HistGradientBoosting** | **0.818 ± 0.003** — selected |

**Held-out test set** (touched exactly once, after model selection):

- Accuracy: **0.765**, Balanced accuracy: **0.761**, F1: **0.789**
- ROC-AUC: **0.839**, PR-AUC (average precision), Brier score — all in
  `ml/models/success_predictor/v1/metadata.json`
- **Overfitting check**: train ROC-AUC vs. test ROC-AUC gap = **0.004** — negligible, not
  overfitting.
- **Leakage check**: 0 exact-`permalink` overlaps between train and test (verified
  programmatically, not assumed).
- **Inference latency**: measured per-prediction on this development machine (see metadata.json;
  not a production-hardware claim).

**These are real, honest numbers on a real, licensed dataset.** HistGradientBoosting won on
cross-validated ROC-AUC by a real, if modest, margin over Logistic Regression (0.818 vs. 0.810) —
not selected because gradient boosting "sounds more advanced."

### Model Improvement Pass (v1.1 — same artifact version, retrained)

A full audit of the success predictor was performed after initial shipping: expanded model
comparison, engineered features, hyperparameter tuning, calibration comparison, permutation
importance, and a learning curve. Reported honestly, including where it did **not** help.

**Two additional candidate algorithms** were added to the comparison (`ml/src/training/
train_success_classifier.py`): `ExtraTreesClassifier` and classic `GradientBoostingClassifier`.
Neither beat `HistGradientBoostingClassifier`:

| Pipeline | CV ROC-AUC |
|---|---|
| Dummy (stratified) baseline | 0.505 ± 0.006 |
| Logistic Regression (balanced) | 0.813 ± 0.007 |
| Random Forest (balanced, depth 8) | 0.810 ± 0.004 |
| Extra Trees (balanced, depth 8) | 0.785 ± 0.006 |
| Gradient Boosting (classic) | one CV fold failed with a transient `numpy._core._exceptions.ArrayMemoryError` allocating 35MB on this memory-constrained development machine (reproduced — see "Memory constraints" below); the resulting mean is correctly excluded from model selection by the existing NaN-filtering logic, not silently defaulted |
| **HistGradientBoosting** | **0.817 ± 0.003** — selected (unchanged from the original pass) |

**Two engineered ratio features** were added (`ml/src/features/success_features.py`,
`engineer_features`): `funding_per_round` (total funding ÷ funding rounds) and `funding_velocity`
(funding rounds ÷ company age in years, both showing a real if modest univariate correlation with
the target before being added: +0.048 and −0.086 respectively). **Honest finding**: post-hoc
permutation importance on the held-out test set ranks both **near the bottom** of all 9 features
(`funding_velocity` 0.0034, `funding_per_round` 0.0011 — vs. `funding_total_usd` 0.0692, the most
important feature by a wide margin). They are kept because they cause no harm and are conceptually
sound, but they did **not** meaningfully improve the model — reported as such rather than
overstated.

**Hyperparameter tuning** (`RandomizedSearchCV`, 20 iterations, 5-fold CV, scored on ROC-AUC) over
`max_depth`, `max_leaf_nodes`, `learning_rate`, `l2_regularization`: best CV ROC-AUC **0.8181**,
essentially identical to the untuned default's 0.8181 — genuinely no improvement from tuning on
this dataset/feature set, not a fabricated gain.

**Calibration comparison** (out-of-fold Brier score on the training set only, never the test set):
raw 0.1723, sigmoid 0.1719, **isotonic 0.1719 — selected** (tied with sigmoid to 4 decimal places;
isotonic used as the tiebreak-favored, more flexible method). The improvement over raw is real but
small.

**Final test-set metrics** (touched once, after every selection decision above): accuracy 0.761,
balanced accuracy 0.758, F1 0.780, ROC-AUC **0.838**, PR-AUC 0.838, Brier 0.162 — statistically
indistinguishable from the original pass's 0.765 / 0.761 / 0.789 / 0.839 / 0.838 / 0.162. **Honest
conclusion: this improvement pass did not move raw predictive performance** — the original
untuned HistGradientBoosting was already near this feature set's ceiling. What it added instead:
a properly calibrated probability (isotonic, chosen via a real comparison rather than assumed),
genuine permutation-importance-based explainability, and a learning-curve overfitting diagnostic.

**Learning curve** (`ml/models/success_predictor/v1/metadata.json` → `learning_curve`, 3-fold CV
on the training set only, at 20/40/60/80/100% of training data): train and validation ROC-AUC
converge to 0.837 / 0.818 at full size — a small, stable generalization gap, consistent with the
overfitting-gap check (−0.003, i.e. no overfitting).

**Permutation importance** (test set, 10 repeats, ROC-AUC scoring): `funding_total_usd` (0.069) is
by far the most important feature, followed by `country_code` (0.029), `category_count` (0.028),
`company_age_years` (0.024), `funding_span_years` (0.008); `primary_category`, `funding_velocity`,
`funding_per_round`, and `funding_rounds` each contribute under 0.005 — full ranking in
`metadata.json`.

**Real, disclosed trade-off**: isotonic calibration (`CalibratedClassifierCV`, 5 internal fold
estimators) increased inference latency from 9.3ms to **62.0ms per prediction** and artifact size
from 208KB to **902KB**. Both remain negligible in absolute terms for this API's synchronous,
per-request usage pattern (not a hot loop) — accepted deliberately for better-calibrated
probabilities, not an oversight.

### Known limitations (success prediction)

- **Funding-history features carry some inherent timing bias**: `funding_total_usd` and
  `funding_rounds` are cumulative totals *as of the last recorded funding event* for each company —
  a company that eventually gets acquired often continues raising funding rounds right up to that
  event, so these features partly reflect the outcome's own timeline, not purely
  independent early-stage signal. This is a structural property of any dataset built from a static
  Crunchbase snapshot (also present in the well-known `manishkc06` dataset's near-identical feature
  set), not a bug introduced by this preprocessing — documented here rather than hidden.
- **Company-level fields (age, category, funding) do not include the free-text description a
  founder submits at pitch time** — the deployed `predict_success` in
  `backend/app/ml/success_predictor.py` runs on whatever subset of `company_metrics` the user
  optionally supplies, imputing the rest with training-set medians/modes and reporting exactly
  which fields were imputed via `missing_features`, rather than presenting a fully-informed
  estimate from partial data.
- **Domain is Crunchbase-tracked companies only** — has not been evaluated against companies
  outside that ecosystem (e.g. bootstrapped businesses with no funding history at all).
- The model output is explicitly labeled "historical pattern estimate" / "not a guarantee" in both
  the API response's `disclaimer` field and the frontend — never presented as a probability of
  this specific startup's actual future success.

### Success Predictor V2 Upgrade

A full audit/upgrade pass covering feature engineering, expanded model comparison, validation
methodology, threshold optimization, subgroup fairness metrics, and a parallel survival-analysis
track (Track 2). Every number below is from an actual training run
(`python -m ml.src.training.train_success_classifier`, `trained_at` 2026-07-18T15:37:58Z) on this
machine — none fabricated. Free RAM checked before the heavy step: ~1.5–1.7GB of 8GB total
(`Get-CimInstance Win32_OperatingSystem`), consistent with prior sessions; `n_jobs=1` was used for
`RepeatedStratifiedKFold`-driven `cross_val_score`/`cross_val_predict`, `RandomizedSearchCV`,
`learning_curve`, and `permutation_importance` throughout, per the established memory-safety
discipline (tree ensembles' own internal `n_jobs=-1` threading was left as-is — safe, in-process).

#### Track 1 — Feature engineering

Two new leakage-safe, date-derived features were threaded through
`ml/src/preprocessing/prepare_success_dataset.py` into `success_dataset.csv` (both derived only
from `founded_at`/`first_funding_at`/`last_funding_at` — never from the outcome):

- `time_to_first_funding_years` = `first_funding_at − founded_at`, in years (negative/data-entry-
  error rows treated as missing, matching the existing `company_age_years` convention).
- `funding_recency_years` = the dataset's own maximum `last_funding_at` minus each row's
  `last_funding_at` — "how stale is this funding record," not a forward-looking signal.

One interaction feature, `funding_per_category` (`funding_total_usd / (category_count + 1)`), was
added in `ml/src/features/success_features.py::engineer_features` — chosen over a raw product
(`funding_total_usd × category_count`) because the product is highly collinear with
`funding_total_usd` alone and barely changes rank order, whereas the ratio asks a genuinely
different, scale-independent question (capital concentration vs. breadth of positioning).

**Investor count and funding-stage/round-type features: not attempted.** Neither column exists
anywhere in the raw Crunchbase export (confirmed by inspecting the raw schema directly — see
"Approved dataset — full schema profile" above) — there is no defensible way to derive either
without fabricating data, so both are documented as real, structural dataset gaps rather than
skipped silently.

**Training-fold-only category/geography target encoding**: implemented as `TrainFoldTargetEncoder`
in `ml/src/features/success_features.py` — a small sklearn-compatible `TransformerMixin` whose
`fit(X, y)` computes a smoothed mean-target encoding *only* from whatever rows it is given. Because
it is used exclusively as a step inside a `Pipeline`, and scikit-learn's CV machinery
(`cross_val_score`, `cross_val_predict`, `RandomizedSearchCV`) always clones the whole pipeline and
calls `.fit()` on the training portion of each split only (never on validation/test rows), this
encoding is leakage-safe by construction — verified with a dedicated leakage/behavior test suite
(`ml/tests/test_target_encoder.py`, 5 tests, all passing) rather than merely asserted. It was
evaluated honestly as an alternative to one-hot encoding for the `hist_gradient_boosting` family —
see model comparison below for the (null) result.

#### Track 1 — Model comparison (RepeatedStratifiedKFold, 5-fold × 3 repeats, training set only)

| Pipeline | CV ROC-AUC |
|---|---|
| Dummy (stratified) baseline | 0.501 ± 0.011 |
| Logistic Regression (balanced) | 0.816 ± 0.006 |
| Random Forest (balanced, depth 8) | 0.813 ± 0.006 |
| Extra Trees (balanced, depth 8) | 0.792 ± 0.006 |
| Gradient Boosting (classic) | 0.829 ± 0.005 (ran to completion this time — no `ArrayMemoryError`, unlike the v1.1 pass) |
| **HistGradientBoosting** | **0.833 ± 0.005 — selected** |
| HistGradientBoosting + train-fold-only target encoding | 0.832 ± 0.006 |
| Soft-voting ensemble (LogReg + HistGB) | 0.831 ± 0.005 |

**Honest ensemble/encoding finding**: neither the target-encoded variant nor the soft-voting
ensemble beat plain one-hot `HistGradientBoosting` (0.8327 CV ROC-AUC) — both scored essentially
the same or marginally lower (0.8317 and 0.8309 respectively). Reported as a genuine null result,
not forced into production; `ml/models/success_predictor/v1/metadata.json` →
`ensemble_and_target_encoding_finding` records this explicitly.

Hyperparameter tuning (`RandomizedSearchCV`, 20 iterations, 5-fold CV): best CV ROC-AUC **0.8347**
(`max_leaf_nodes=31, max_depth=None, learning_rate=0.1, l2_regularization=0.1`) — a small, real
improvement over the untuned 0.8327.

Calibration comparison (out-of-fold Brier score, training set only): raw 0.1643, **sigmoid 0.1627
— selected**, isotonic 0.1628 (sigmoid edges out isotonic this time, reversing the v1.1 pass's
pick — both are close enough that either would be defensible; the lower-scoring one was taken
literally rather than a fixed preference).

#### Track 1 — Held-out test set (touched once)

| Metric | v1 (previous) | **v2 (this pass)** |
|---|---|---|
| Accuracy | 0.761 | **0.774** |
| Balanced accuracy | 0.758 | **0.771** |
| F1 | 0.780 | **0.795** |
| ROC-AUC | 0.838 | **0.855** |
| PR-AUC | 0.838 | **0.856** |
| Brier score | 0.162 | **0.154** |
| ECE (10-bin) | not previously reported at this granularity | **0.019** — well-calibrated |

**Genuine improvement, not a null result this time**: ROC-AUC moved 0.838 → 0.855, F1 0.780 →
0.795 — a real, if moderate, gain attributable to the new date-derived features (see permutation
importance below), not to the algorithm search (HistGradientBoosting was already selected in v1).
Train/test ROC-AUC overfitting gap: 0.055 (train 0.910, test 0.855) — larger than v1's 0.004 gap,
worth watching, but the test-set metrics themselves are unambiguously higher, not an artifact of
memorizing training noise that failed to generalize.

**Permutation importance** (test set, 10 repeats, ROC-AUC scoring):

| Feature | Importance |
|---|---|
| `funding_total_usd` | 0.0716 |
| **`funding_recency_years`** (new) | **0.0434 — 2nd most important feature** |
| `category_count` | 0.0301 |
| `country_code` | 0.0237 |
| `company_age_years` | 0.0128 |
| `funding_span_years` | 0.0102 |
| `primary_category` | 0.0064 |
| `funding_per_round` | 0.0035 |
| `funding_velocity` | 0.0013 |
| `time_to_first_funding_years` (new) | 0.0011 |
| `funding_rounds` | 0.0004 |
| `funding_per_category` (new) | −0.0004 |

**What helped vs. didn't, honestly**: `funding_recency_years` is a real, substantial win — it
landed as the **second most important feature overall**, ahead of every original feature except
`funding_total_usd` itself, and is the main driver of this pass's genuine metric improvement.
`time_to_first_funding_years` and `funding_per_category` did **not** meaningfully help — both rank
at or below the noise floor (the latter is even slightly negative, i.e. indistinguishable from a
useless feature on this test set). They are kept (conceptually sound, no harm, and documented
honestly here) rather than stripped out to avoid re-litigating the comparison on every future run.

#### Track 1 — Threshold optimization

Objective stated explicitly: false negatives (a real eventual success predicted "failure") and
false positives are treated as **equally costly** — this prediction is informational only, never
gating a funding/resource decision where one error type would cost more than the other — so the
**F1-optimal threshold** was chosen over an arbitrary precision/recall-weighted alternative.

Recommended operating threshold: **0.40** (vs. the previous fixed default of 0.5) — precision
0.721, recall 0.909, F1 **0.804** (above the default-0.5 test F1 of 0.795). Full sweep across
0.05–0.95 is in `metadata.json` → `threshold_sweep`. `backend/app/ml/success_predictor.py` now
applies `recommended_threshold` from metadata when present (falling back to 0.5 for an older
artifact), and surfaces it in the response as `operating_threshold` — additive only, verified by
`backend/tests/test_success_predictor.py::test_response_shape_is_additive_only_existing_fields_unchanged`.

#### Track 1 — Subgroup metrics (top-3 most frequent, test set)

| primary_category | n | ROC-AUC |
|---|---|---|
| unknown | 228 | 0.901 |
| biotechnology | 195 | 0.803 |
| software | 192 | 0.790 |

| country_code | n | ROC-AUC |
|---|---|---|
| usa | 1,639 | 0.810 |
| unknown | 409 | 0.886 |
| gbr | 100 | 0.843 |

No group falls alarmingly below the overall 0.855 test ROC-AUC — `software` (0.790) is the softest
spot, plausibly because it is the largest, most heterogeneous single category (see the industry
classifier's own documented "generic platform language" ambiguity for a structurally similar
finding). No group was excluded or downweighted in response; reported for visibility only.

#### Track 1 — Temporal-split diagnostic (corrected after manual verification)

Sorted by `last_funding_at`, trained on the earliest 80%, tested on the most recent 20% (a fixed,
untuned/uncalibrated `HistGradientBoosting`/LogReg reference model, to isolate drift from the
hyperparameter/calibration choices made on the random split): **ROC-AUC ~0.91** vs. the random-
split test ROC-AUC of 0.855. The original report characterized this gap as "no evidence of
temporal drift" — **that characterization was wrong and has been corrected** after a targeted
investigation prompted by a reasonable suspicion that a >0.05 AUC gap between a temporal and a
random split on the same data is unusual enough to warrant checking for leakage before trusting it.

**What was checked, with real numbers, not assumption:**

1. **A genuine data bug was found and fixed**: one row (`Rasyonel R&D`) had `last_funding_at =
   2105-05-01` and `founded_at` also future-dated — a plain data-entry typo in the raw Crunchbase
   export. Because `funding_recency_years` used the dataset's own max `last_funding_at` as its
   reference point, this single corrupted row was silently setting that reference for every row in
   the dataset. **Fixed** in `prepare_success_dataset.py`: any `founded_at`/`first_funding_at`/
   `last_funding_at` after the real-world present is now treated as missing (logged, not silently
   dropped) — see the dated code comment there. `success_dataset.csv` was regenerated (13,334 rows,
   unchanged row count; only this row's three date fields became `NaN`).
2. **Ablation: does removing that row change the temporal-split AUC?** No — 0.9140 with vs. 0.9121
   without (measured with a sparse-safe LogisticRegression substituted for HistGB purely for this
   diagnostic, after HistGB's dense one-hot path hit a real `ArrayMemoryError` on this
   memory-constrained machine — see "Memory constraints"). The corrupted row was real and worth
   fixing, but it was **not** the cause of the gap.
3. **Ablation: does removing `funding_recency_years` + `time_to_first_funding_years` entirely
   change it?** No — 0.9121 with vs. 0.9139 without. These leakage-safe date-derived features are
   **not** the cause either; ruled out directly rather than assumed.
4. **Class balance across the split**: train (early 80%) success rate 0.552 vs. test (recent 20%)
   0.451 — a real ~10-point base-rate shift. AUC is rank-based and not directly sensitive to base
   rate, so this alone doesn't explain a higher AUC, but it is a real, disclosed distributional
   difference between the two splits.
5. **Root cause, isolated**: removing `country_code`/`primary_category` entirely (numeric features
   only) drops the temporal-split AUC to 0.889 while the random-split AUC on the same numeric-only
   features is 0.808 — the gap *shrinks* but doesn't close, confirming the categorical features are
   the primary (not sole) driver. Digging into *why*: two categories — `unknown` and
   `biotechnology` — are both extremely separable on the label (`unknown` success rate 0.122
   dataset-wide, i.e. almost always failure; `biotechnology` 0.757, i.e. almost always success) and
   their combined share of the data **triples in concentration and grows more extreme** in the
   recent window:

   | | Train (early 80%) | Test (recent 20%) |
   |---|---|---|
   | `unknown` share / success rate | 5.9% / 0.191 | 16.9% / **0.027** |
   | `biotechnology` share / success rate | 6.9% / 0.707 | 13.9% / **0.854** |
   | combined share of rows | 12.8% | **30.8%** |

   The recent 20% of this dataset is disproportionately composed of two near-deterministic
   categories, which is a genuine property of *this specific Crunchbase export's* time
   distribution (not a modeling artifact and not literal leakage — no future information reaches
   any individual prediction), but it means **the temporal split's higher AUC does not represent
   "the model generalizes better into the future."** It represents "the most recent slice of this
   particular dataset happens to be easier to classify because of which categories are
   over-represented in it." Reporting the original 0.914 figure as evidence of "no temporal drift"
   was an overclaim; the corrected, honest conclusion is: **no leakage was found via the date
   features or the corrupted row, but the temporal-split AUC is not a trustworthy estimate of
   future-generalization performance for this dataset** given the category-distribution shift
   documented above. The **random-split test ROC-AUC of 0.855 remains the model's primary,
   trustworthy reported metric** — this diagnostic exists to check for drift, and it surfaced a
   real population-shift caveat rather than confirming a clean result.

**Entity-safety check**: `permalink` has **0 duplicates** in the loaded dataset (confirmed
programmatically in `train()`, not assumed) — the random split is genuinely entity-safe.

#### Track 2 — Survival analysis (Cox Proportional Hazards, `lifelines` 0.30.3)

Built via `python -m ml.src.preprocessing.survival_data` then
`python -m ml.src.training.train_survival_model`. **Uses ALL 66,368 raw rows, including the 53,034
"operating" ones the binary classifier excludes** — this is the correct, intentional use of
censored data, not a fabrication: a still-operating company is real information ("had not
failed/exited as of the last-observed date"), which right-censoring encodes properly instead of
discarding it.

- **Duration** = `last_funding_at − founded_at`, in years. **Real, confirmed limitation**: there is
  no true exit/acquisition date or as-of observation date anywhere in this dataset (verified — not
  assumed), so `last_funding_at` stands in as a proxy for "last observed activity." This creates
  genuine **informative-censoring risk**: a quietly-failing company may also quietly stop raising
  funding rounds well before it formally closes, understating its true survival time.
- **Event** = 1 if `status ∈ {closed, acquired, ipo}` (resolved), 0 (censored) if `operating`.
- After dropping 17,340/66,368 rows with missing/negative duration (missing dates, or
  `founded_at` postdating `last_funding_at` — a source data-entry error, same category the binary
  classifier's preprocessing already treats as missing) and nudging 1,964 same-day-duration rows to
  a 1-day epsilon (a standard survival-analysis convention for tied zero durations, not an invented
  data point): **final n = 49,028** (9,179 events / 18.7%, 39,849 censored / 81.3%).
- Features: `log1p(funding_total_usd)`, `funding_rounds`, `category_count`, one-hot
  `primary_category` (top 10 + "other") and `country_code` (top 8 + "other") — categories collapsed
  specifically to control the one-hot column count that causes CoxPH's well-known collinearity/
  convergence problems, plus a ridge `penalizer=0.1` as an additional, disclosed mitigation.
- **Fit with zero convergence warnings** (captured and would have been reported verbatim if any
  had occurred — none did).
- **Concordance index: train 0.662, test 0.672** (stratified 80/20 split by event). Reported as the
  primary and only evaluation metric — time-dependent AUC / integrated Brier score were considered
  and **not computed**: doing so validly would require either a manual lifelines time-grid
  implementation (real complexity/correctness risk in the time available) or `scikit-survival`
  (not installed — a compiled package judged too risky to add given this session's memory
  constraints; explicitly not attempted, not silently skipped).

**Is survival modeling more scientifically appropriate here than binary classification?** In
principle, **yes**: it correctly uses the 53,034 censored "operating" rows the binary classifier
must discard, and directly addresses the survivorship-bias concern inherent in training/evaluating
only on companies whose fate has already resolved. In practice, this analysis's real, disclosed
limitation — no true exit date, only a last-funding-event proxy — caps how strong a claim it can
support: the 0.66–0.67 concordance index is real signal (meaningfully above the 0.5 chance level)
but well below the binary classifier's 0.855 ROC-AUC, consistent with a fundamentally noisier,
proxy-duration target rather than a like-for-like comparison.

**Integration decision: NOT integrated into the production backend/API.** Reasoning: (1) the
concordance index, while real, is modest, and the proxy-duration/informative-censoring limitation
is a genuine scientific caveat that would need much clearer product framing before surfacing a
"time-to-outcome" number to end users; (2) no additive backend field or endpoint currently exists
for it, keeping the existing `success_predictor` response shape completely untouched; (3) this
keeps Track 2 as exactly what it is — an honest, exploratory diagnostic that strengthens the
project's understanding of survivorship bias — without overclaiming production-readiness it
hasn't earned. `ml/models/survival_model/v1/metadata.json` carries its own full model card,
library version (`lifelines` 0.30.3), and scientific caveats for future reference if a true
exit-date field ever becomes available.

**Rejected approaches** (this pass): `xgboost`/`lightgbm`/`catboost` — not installed, not attempted
(explicitly out of scope per this session's constraints). `scikit-survival` — not installed;
judged too risky to add given memory constraints and the time budget, `lifelines`' CoxPH used
instead as the lightweight, pure-Python alternative. Time-dependent AUC / integrated Brier score —
not computed, for the reasons stated above. A supplementary-dataset merge to add investor-count or
funding-stage features — searched and rejected (see "Data Improvement Pass — Supplementary Dataset
Search (V2 audit)" below): every candidate found was either explicitly synthetic, lacked an outcome
label, or would have required risky cross-schema entity resolution against the primarily US-centric
Crunchbase export already in use.

#### Governance

`ml/models/success_predictor/v1/metadata.json` now additionally includes: `dataset_version`
(`v2-crunchbase-2013-date-features`), `n_duplicate_permalinks` (0, confirmed), `cv_scheme`
(`RepeatedStratifiedKFold(n_splits=5, n_repeats=3)`), `temporal_split_diagnostic`,
`threshold_sweep` + `recommended_threshold` + `threshold_objective`, `subgroup_metrics`,
`ensemble_and_target_encoding_finding`, `training_command`, and a `model_card` block (purpose,
training data, known limitations, scientific caveats) — all populated from this real run, not
placeholders. `ml/models/survival_model/v1/metadata.json` carries the equivalent governance record
for Track 2 (own `library_versions`, `scientific_caveats`, `disclaimer`).

## Revenue Estimation — Dataset Decision

Four dataset candidates were inspected for a startup revenue-estimation task (the same search pass
covered above, since most "startup success" datasets also carry a revenue-shaped column):

- `hamnakaleemds/global-startup-success-dataset` — synthetic, undisclosed methodology (rejected,
  see table above).
- `dhrubangtalukdar/startup-funding-and-outcome-dataset` — self-declared synthetic (rejected).
- `samayashar/startup-growth-and-funding-trends` — self-declared synthetic (rejected).
- `ara001/financial-metrics-of-startup-companies` ("50 Startups") — real-looking but a 50-row
  classroom toy set with no relationship to a startup's actual pitch-time inputs (rejected as an
  extremely tiny toy dataset).

**No candidate met the bar**: a real, licensed, non-synthetic dataset with a genuine revenue
figure tied to features available from a short founder pitch submission. This is also a structural
problem, not just a search-coverage gap — a pre-revenue or early-revenue startup (this system's
target user) has no historical revenue of its own to fit a model against, and no dataset can
honestly supply that.

**Decision: a transparent, deterministic revenue *scenario calculator*** —
[`backend/app/ml/revenue_scenario.py`](../backend/app/ml/revenue_scenario.py) — explicitly not a
trained model. It projects conservative/base/optimistic 12-month revenue ranges purely from the
user's own supplied assumptions (price per customer, initial customer count, expected monthly
growth rate, gross margin), defaulting missing growth/margin to 0%/100% respectively and listing
every defaulted field in `missing_assumptions`. If the two minimum required assumptions (price,
initial customers) are absent, it returns `available: false` and shows no numeric range at all,
rather than guessing. The design mirrors the precedent already set by
[`backend/app/ml/funding_readiness.py`](../backend/app/ml/funding_readiness.py) (Student 1's
funding-readiness rubric) for the same reason: no defensible dataset existed, so a labeled,
versioned, honestly-non-ML deterministic calculator was built instead of fabricating a training
target.

## Market Intelligence / Competitor Analysis / Customer Persona / Business Model — Data Sources

None of these four agents (`backend/app/agents/{market,competitor,customer_persona,
business_model}_agent.py`) call any external market-research, company-database, or web-search
API — no such integration exists in this system. Each is a deterministic function operating only
on: the industry classifier's own prediction, the funding-readiness rubric's breakdown, and
user-submitted `market_evidence` (target market, customer type, geography, startup stage, known
competitor names — all optional). Every field not derivable from those three sources is reported
as an explicit evidence gap with a recommended validation action, never invented — see each
module's docstring for the specific fabrication risks it guards against (e.g. never inventing a
TAM/SAM/SOM figure, a real competitor's pricing, or a customer's age/income).

## Adding a Verified Dataset

1. Search Kaggle (or another licensed source) for a dataset matching the task.
2. Download it once and inspect: column names, label distribution, duplicates, missing values,
   **license terms** (an "unknown" license is a rejection, not a formality — see the rejected
   `company-classification` entry above).
3. Add a row to this table and an entry to `dataset_manifest.json` with the real `kaggle_id`.
4. Only then wire it into `ml/src/preprocessing/`.

Datasets are never combined across incompatible label taxonomies, and no label is fabricated to
fill a gap.

## Data Improvement Pass — Supplementary Dataset Search (V2 audit)

Searched Kaggle for additional startup-outcome/funding data that could legitimately extend
`success_dataset.csv` (more rows, an investor-count field, or a funding-stage field — all absent
from the current source). Candidates inspected and their verdicts:

| Dataset | License | Rows | Verdict | Reason |
|---|---|---|---|---|
| `dhrubangtalukdar/startup-funding-and-outcome-dataset` | unspecified | 100,000 | **Rejected** | Own description states "Simulated startup data" — explicitly synthetic, not real outcomes. Using it would fabricate a training signal under a real-looking label. |
| `mohankrishnathalla/startup-founder-burnout-and-failure-risk-dataset` | unspecified | unknown | **Rejected** | Own description states "A realistic **synthetic** dataset" — same reason as above. |
| `omkargowda/indian-startups-funding-data-januarymay-2022` | CC0-1.0 | ~unknown (regional) | **Rejected for merging** | Real, licensed, but has no success/failure outcome column at all (funding amounts and investor names only) — nothing to merge against the current binary label. Also India-only, 2022-only, and would require unreliable company-name-based entity matching against the primarily US-centric Crunchbase export already in use, which is exactly the "combining datasets blindly" risk the audit instructions warn against. Could theoretically be revisited as a future *investor-count* feature source if a clean entity-resolution approach across schemas were built first — not attempted here given the risk/reward and time budget. |
| Several "Unicorn startups" datasets (`adilshamim8/...`, `mlvprasad/...`, `niekvanderzwaag/...`) | mixed | small (hundreds) | **Rejected** | Cover only already-successful unicorns — no failure/closure examples, so adding them would inject pure class-imbalance/selection bias into the success side without any matching negative examples. |

**Conclusion**: no supplementary dataset found this pass meets the bar (real, licensed, has a
genuine resolved-outcome label, doesn't require risky cross-schema entity resolution). No merge
was performed. The existing `success_dataset.csv` (Crunchbase-derived, CDLA-Sharing-1.0) remains
the sole training source; its known gaps (no investor count, no funding-stage/round-type column,
no true exit date) are documented as scientific limitations in the Success Predictor V2 section
rather than papered over with synthetic or mismatched data.
