# ML

Training pipeline for the industry classification model. Dataset details:
[DATASETS.md](DATASETS.md). Trained artifacts are written to `ml/models/` (git-ignored) and
loaded by `backend/app/ml/predictor.py` at serving time — training never runs inside the API
request path.

## Structure

```
ml/
├── dataset_manifest.json      — machine-readable dataset list (see DATASETS.md)
├── data/{raw,processed}/       — git-ignored
├── models/                      — git-ignored trained artifacts
├── src/
│   ├── preprocessing/            — clean_data.py: raw -> processed; bootstrap_data.py: synthetic fallback
│   ├── features/                   — build_features.py: processed -> TF-IDF-ready text/labels
│   ├── training/                     — train_industry_classifier.py: fits + evaluates + saves
│   ├── evaluation/                     — classification_metrics.py: shared metric helpers
│   └── explainability/                   — term_contributions.py: linear-model explanations
└── tests/                                  — unit tests against tiny inline fixtures (no live dataset needed)
```

## Workflow

```bash
python scripts/download_datasets.py --list   # see what's configured
python -m ml.src.training.train_industry_classifier
```

Training fits a TF-IDF + Logistic Regression pipeline (compared against Linear SVM and Complement
Naive Bayes baselines via cross-validation), evaluates on a held-out test split, and writes the
winning pipeline plus metadata (metrics, label taxonomy, dataset version, training seed) to
`ml/models/industry_classifier/<version>/`.
