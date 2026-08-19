# ML

Training pipelines for two independently trained models: industry classification and startup
success prediction. Dataset details: [DATASETS.md](DATASETS.md). Trained artifacts are written to
`ml/models/` (git-ignored) and loaded by `backend/app/ml/{predictor,success_predictor}.py` at
serving time — training never runs inside the API request path.

## Structure

```
ml/
├── dataset_manifest.json      — machine-readable dataset list (see DATASETS.md)
├── data/{raw,processed}/       — git-ignored
├── models/                      — git-ignored trained artifacts
├── src/
│   ├── preprocessing/            — clean_data.py / prepare_yc_dataset.py / bootstrap_data.py
│   │                                (industry classifier); success_data.py /
│   │                                prepare_success_dataset.py / bootstrap_success_data.py
│   │                                (success predictor)
│   ├── features/                   — build_features.py (industry classifier, TF-IDF text);
│   │                                  success_features.py (success predictor, tabular
│   │                                  ColumnTransformer)
│   ├── training/                     — train_industry_classifier.py; train_success_classifier.py
│   ├── evaluation/                     — classification_metrics.py (multiclass text);
│   │                                      binary_classification_metrics.py (binary tabular)
│   └── explainability/                   — term_contributions.py: linear-model explanations
│                                            (industry classifier only)
└── tests/                                  — unit tests against tiny inline fixtures (no live dataset needed)
```

## Workflow

```bash
python scripts/download_datasets.py --list   # see what's configured

python -m ml.src.preprocessing.prepare_yc_dataset       # industry classifier: raw -> canonical CSV
python -m ml.src.training.train_industry_classifier

python -m ml.src.preprocessing.prepare_success_dataset  # success predictor: raw -> canonical CSV
python -m ml.src.training.train_success_classifier
```

**Industry classifier**: TF-IDF (word+char) + Logistic Regression (compared against Linear SVM,
Complement Naive Bayes, and an LSA/SVD variant via cross-validation), evaluated on a held-out test
split, saved to `ml/models/industry_classifier/<version>/`.

**Success predictor**: a tabular binary classifier (funding history, company age, category,
country) comparing Logistic Regression, Random Forest, and HistGradientBoosting against a dummy
baseline via cross-validated ROC-AUC, evaluated on a held-out test split (accuracy, ROC-AUC,
PR-AUC, Brier score, overfitting gap), saved to `ml/models/success_predictor/<version>/`.

Both write a versioned `model.joblib` + `metadata.json` (metrics, dataset provenance, training
seed, feature/label schema) — never metrics fabricated or rounded up; see DATASETS.md for the full
comparison tables and known limitations of each.
