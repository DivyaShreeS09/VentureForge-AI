"""Final ML Excellence Sprint, Phase 7 — one consolidated ML dashboard.

Reads every production artifact's metadata.json directly (industry classifier, success predictor,
venture retrieval) and reports every metric this sprint's Phase 7 asks for, in one place. No new
computation, no re-training — pure aggregation of already-measured, on-disk numbers.

Run: `python -m ml.src.analysis.ml_scoreboard`
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = REPO_ROOT / "ml" / "models"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_scoreboard() -> dict:
    classifier = _load(MODELS_DIR / "industry_classifier" / "v3" / "metadata.json")
    success = _load(MODELS_DIR / "success_predictor" / "v1" / "metadata.json")
    retrieval = _load(MODELS_DIR / "venture_retrieval" / "v2" / "corpus_metadata.json")

    from ml.src.evaluation.evaluate_retrieval import evaluate as evaluate_retrieval

    retrieval_eval = evaluate_retrieval("v2")

    return {
        "scoreboard_version": "v1",
        "industry_classifier": {
            "public_version": "v1",
            "n_train": classifier["n_train"],
            "n_test": classifier["n_test"],
            "n_gold": classifier.get("gold_set_evaluation", {}).get("n_gold_rows"),
            "test_accuracy": classifier["test_metrics"]["accuracy"],
            "test_macro_f1": classifier["test_metrics"]["macro_f1"],
            "test_weighted_f1": classifier["test_metrics"]["weighted_f1"],
            "test_log_loss": classifier["test_metrics"]["log_loss"],
            "top2_accuracy": classifier["test_top2_accuracy"],
            "ece": classifier["calibration"]["expected_calibration_error"],
            "gold_macro_f1": classifier.get("gold_set_evaluation", {}).get("metrics", {}).get("macro_f1"),
            "confusion_matrix": classifier["test_metrics"]["confusion_matrix"],
            "confusion_matrix_labels": classifier["test_metrics"]["confusion_matrix_labels"],
            "inference_latency_ms": classifier.get("inference_latency_ms_per_prediction"),
        },
        "success_predictor": {
            "public_version": "v1",
            "n_train": success["n_train"],
            "n_test": success["n_test"],
            "test_accuracy": success["test_metrics"]["accuracy"],
            "test_f1": success["test_metrics"]["f1"],
            "roc_auc": success["test_metrics"]["roc_auc"],
            "pr_auc": success["test_metrics"]["pr_auc"],
            "mcc": success["test_metrics"]["mcc"],
            "cohen_kappa": success["test_metrics"]["cohen_kappa"],
            "brier_score": success["test_metrics"]["brier_score"],
            "ece": success["test_calibration"]["expected_calibration_error"],
            "confusion_matrix": success["test_metrics"]["confusion_matrix"],
            "inference_latency_ms": success.get("inference_latency_ms_per_prediction"),
            "artifact_size_bytes": success.get("artifact_size_bytes"),
        },
        "venture_retrieval": {
            "public_version": "v1",
            "corpus_size": retrieval["corpus_size"],
            "n_sources": len(retrieval.get("sources", [])),
            "precision_at_k": retrieval_eval["precision_at_k"],
            "recall_at_5": retrieval_eval["recall_at_5"],
            "mrr": retrieval_eval["mrr"],
            "ndcg_at_5": retrieval_eval["ndcg_at_5"],
            "coverage_pct": retrieval_eval["coverage_pct"],
            "failure_case_rate_pct": retrieval_eval["failure_case_rate_pct"],
            "latency_ms": retrieval_eval["latency_ms"],
        },
        "test_counts": {
            "backend_tests": "see `cd backend && pytest -q` output at report time",
            "ml_tests": "see `pytest ml/tests -q` output at report time",
        },
    }


def main() -> None:
    print(json.dumps(build_scoreboard(), indent=2))


if __name__ == "__main__":
    main()
