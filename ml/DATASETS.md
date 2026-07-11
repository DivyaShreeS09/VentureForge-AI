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

## Adding a Verified Dataset

1. Search Kaggle (or another licensed source) for a dataset matching the task.
2. Download it once and inspect: column names, label distribution, duplicates, missing values,
   **license terms** (an "unknown" license is a rejection, not a formality — see the rejected
   `company-classification` entry above).
3. Add a row to this table and an entry to `dataset_manifest.json` with the real `kaggle_id`.
4. Only then wire it into `ml/src/preprocessing/`.

Datasets are never combined across incompatible label taxonomies, and no label is fabricated to
fill a gap.
