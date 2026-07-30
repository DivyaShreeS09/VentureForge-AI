"""Exploratory experiment (NOT wired into production): does the real `subindustry` field already
present in ml/data/raw/yc_companies_2012_2024_raw.csv support a genuinely finer-grained taxonomy
(30-60 classes) than the current 7-class production taxonomy?

Reuses the exact same description-construction logic as ml/src/preprocessing/prepare_yc_dataset.py
and the already-proven winning architecture (TF-IDF word+char + balanced Logistic Regression) from
ml/DATASETS.md's industry-classifier comparisons. Gold-set rows are excluded from train/test by
exact description match, same as production. Reports CV, held-out test, and gold-subset metrics —
no fabrication, no cherry-picking.

RESULT (see ml/DATASETS.md "Fine-Grained Subindustry Taxonomy — Evaluated and Rejected" for the
full write-up): REJECTED. 34 classes clear a >=50-row minimum from real subindustry labels (a
legitimate, non-fabricated hierarchy: "ParentCategory -> Subcategory"), but CV/test macro-F1 lands
at ~0.44-0.46 (vs 0.738 for the deployed 7-class model) and gold-subset macro-F1 collapses to 0.261
(vs 0.766 for the deployed model) — a genuine, severe generalization gap, not deployed. Run with:
`python -m ml.src.preprocessing.subindustry_taxonomy_experiment` from the repo root.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW = REPO_ROOT / "ml/data/raw/yc_companies_2012_2024_raw.csv"
GOLD = REPO_ROOT / "ml/data/gold/industry_gold_set.csv"
SEED = 42
MIN_CLASS_SAMPLES = 50

raw = pd.read_csv(RAW)
one_liner = raw["one_liner"].fillna("").astype(str).str.strip()
long_description = raw["long_description"].fillna("").astype(str).str.strip()
description = (one_liner + ". " + long_description).str.strip(". ").str.strip()
subind = raw["subindustry"].fillna("unspecified").astype(str).str.strip()

df = pd.DataFrame({"name": raw["name"], "description": description, "subindustry": subind})
df = df[df["description"].str.len() >= 10]

# Exclude gold-set rows by exact description match (same leakage-prevention rule as production).
gold = pd.read_csv(GOLD)
gold_desc = set(gold["description"])
n_before = len(df)
df = df[~df["description"].isin(gold_desc)].reset_index(drop=True)
print(f"Excluded {n_before - len(df)} gold-overlapping rows from training pool.")

# Apply the MIN_CLASS_SAMPLES / exclude-unspecified rule, exactly mirroring prepare_yc_dataset.py.
counts = df["subindustry"].value_counts()
keep_labels = counts[counts >= MIN_CLASS_SAMPLES].index
keep_labels = [l for l in keep_labels if l.lower() != "unspecified"]
df = df[df["subindustry"].isin(keep_labels)].reset_index(drop=True)
print(f"Retained {len(df)} rows across {df['subindustry'].nunique()} subindustry classes (>= {MIN_CLASS_SAMPLES} rows each).")

X_train_text, X_test_text, y_train, y_test = train_test_split(
    df["description"], df["subindustry"], test_size=0.2, random_state=SEED, stratify=df["subindustry"]
)


def make_features(train_texts, test_texts):
    word_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=20000, min_df=2, sublinear_tf=True)
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=8000, min_df=2, sublinear_tf=True)
    Xw_train = word_vec.fit_transform(train_texts)
    Xc_train = char_vec.fit_transform(train_texts)
    Xw_test = word_vec.transform(test_texts)
    Xc_test = char_vec.transform(test_texts)
    return hstack([Xw_train, Xc_train]).tocsr(), hstack([Xw_test, Xc_test]).tocsr(), word_vec, char_vec


# --- 5-fold stratified CV on the training set only (macro F1), 3 candidates for honesty ---
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

# Dummy baseline
dummy_scores = cross_val_score(
    DummyClassifier(strategy="stratified", random_state=SEED), np.zeros((len(y_train), 1)), y_train,
    cv=skf, scoring="f1_macro",
)
print(f"Dummy baseline CV macro-F1: {dummy_scores.mean():.4f} +/- {dummy_scores.std():.4f}")

# Word-only TF-IDF + balanced LogReg
cv_word_scores = []
for train_idx, val_idx in skf.split(X_train_text, y_train):
    tr_t, va_t = X_train_text.iloc[train_idx], X_train_text.iloc[val_idx]
    tr_y, va_y = y_train.iloc[train_idx], y_train.iloc[val_idx]
    word_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=20000, min_df=2, sublinear_tf=True)
    Xtr = word_vec.fit_transform(tr_t)
    Xva = word_vec.transform(va_t)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=SEED)
    clf.fit(Xtr, tr_y)
    cv_word_scores.append(f1_score(va_y, clf.predict(Xva), average="macro"))
cv_word_scores = np.array(cv_word_scores)
print(f"Word-only TF-IDF + LogReg CV macro-F1: {cv_word_scores.mean():.4f} +/- {cv_word_scores.std():.4f}")

# Word+char TF-IDF (the already-proven winning family for this corpus) + balanced LogReg
cv_wc_scores = []
for train_idx, val_idx in skf.split(X_train_text, y_train):
    tr_t, va_t = X_train_text.iloc[train_idx], X_train_text.iloc[val_idx]
    tr_y, va_y = y_train.iloc[train_idx], y_train.iloc[val_idx]
    Xtr, Xva, _, _ = make_features(tr_t, va_t)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=SEED)
    clf.fit(Xtr, tr_y)
    cv_wc_scores.append(f1_score(va_y, clf.predict(Xva), average="macro"))
cv_wc_scores = np.array(cv_wc_scores)
print(f"Word+char TF-IDF + LogReg CV macro-F1: {cv_wc_scores.mean():.4f} +/- {cv_wc_scores.std():.4f}")

# --- Refit winner on full training set, evaluate once on held-out test ---
Xtr_full, Xte_full, word_vec, char_vec = make_features(X_train_text, X_test_text)
clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=SEED)
clf.fit(Xtr_full, y_train)
pred_test = clf.predict(Xte_full)
test_acc = accuracy_score(y_test, pred_test)
test_macro_f1 = f1_score(y_test, pred_test, average="macro")
test_weighted_f1 = f1_score(y_test, pred_test, average="weighted")
test_macro_p = precision_score(y_test, pred_test, average="macro", zero_division=0)
test_macro_r = recall_score(y_test, pred_test, average="macro", zero_division=0)
print(f"\nHeld-out test (n={len(y_test)}): accuracy={test_acc:.4f} macro-F1={test_macro_f1:.4f} "
      f"weighted-F1={test_weighted_f1:.4f} macro-P={test_macro_p:.4f} macro-R={test_macro_r:.4f}")

proba_test = clf.predict_proba(Xte_full)
top1_conf = proba_test.max(axis=1)
print(f"Test top-1 confidence: mean={top1_conf.mean():.3f}, median={np.median(top1_conf):.3f}")

# Per-class F1 on test, sorted worst-first
labels = clf.classes_
from sklearn.metrics import classification_report
report = classification_report(y_test, pred_test, output_dict=True, zero_division=0)
per_class = sorted(((l, report[l]["f1-score"], int(report[l]["support"])) for l in labels), key=lambda x: x[1])
print("\nWorst 8 classes by test F1:")
for l, f1, n in per_class[:8]:
    print(f"  {l}: F1={f1:.3f} (n={n})")
print("Best 5 classes by test F1:")
for l, f1, n in per_class[-5:]:
    print(f"  {l}: F1={f1:.3f} (n={n})")

# --- Independent gold-subset evaluation ---
gold_desc_full = raw.assign(_description=description)
gold_merged = gold.merge(
    gold_desc_full[["name", "_description", "subindustry"]],
    left_on=["name", "description"], right_on=["name", "_description"], how="left",
)
gold_eval = gold_merged[gold_merged["subindustry"].isin(keep_labels)].reset_index(drop=True)
print(f"\nGold set: {len(gold)} rows total, {len(gold_eval)} have a subindustry label that survived "
      f"the >= {MIN_CLASS_SAMPLES}-row taxonomy filter ({len(gold_eval)/len(gold):.1%} coverage).")

Xw_gold = word_vec.transform(gold_eval["description"])
Xc_gold = char_vec.transform(gold_eval["description"])
Xg = hstack([Xw_gold, Xc_gold]).tocsr()
pred_gold = clf.predict(Xg)
gold_acc = accuracy_score(gold_eval["subindustry"], pred_gold)
gold_macro_f1 = f1_score(gold_eval["subindustry"], pred_gold, average="macro", zero_division=0)
print(f"Gold-subset (n={len(gold_eval)}): accuracy={gold_acc:.4f} macro-F1={gold_macro_f1:.4f}")

# Save a compact summary for reporting
summary = {
    "n_classes": int(df["subindustry"].nunique()),
    "n_rows_retained": int(len(df)),
    "n_train": int(len(X_train_text)),
    "n_test": int(len(X_test_text)),
    "cv_dummy_macro_f1": [round(float(dummy_scores.mean()), 4), round(float(dummy_scores.std()), 4)],
    "cv_word_macro_f1": [round(float(cv_word_scores.mean()), 4), round(float(cv_word_scores.std()), 4)],
    "cv_wordchar_macro_f1": [round(float(cv_wc_scores.mean()), 4), round(float(cv_wc_scores.std()), 4)],
    "test_accuracy": round(float(test_acc), 4),
    "test_macro_f1": round(float(test_macro_f1), 4),
    "test_weighted_f1": round(float(test_weighted_f1), 4),
    "gold_n": int(len(gold_eval)),
    "gold_coverage_fraction": round(len(gold_eval) / len(gold), 4),
    "gold_accuracy": round(float(gold_acc), 4),
    "gold_macro_f1": round(float(gold_macro_f1), 4),
    "worst_classes_test_f1": [{"label": l, "f1": round(f1, 4), "n": n} for l, f1, n in per_class[:8]],
}
out_path = REPO_ROOT / "ml/models/industry_classifier/subindustry_taxonomy_experiment_result.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(summary, indent=2))
print(f"\nSaved summary to {out_path}")
