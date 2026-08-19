# Final ML Audit

Final ML Excellence Sprint, Phase 1. One complete audit of every ML/retrieval component in the
system, before the architecture is permanently frozen.

## Industry Classifier

- **Purpose**: predict a startup's industry (7 classes) from name+description.
- **Training data**: 3-source YC merge, 7,227 cleaned rows, 140-row gold holdout (see
  `ml/MODEL_CARDS.md` for full provenance).
- **Evaluation protocol**: stratified train/test + 5-fold CV for model selection + independent
  gold set, never touched during training.
- **Metrics**: test macro F1 0.769, gold macro F1 0.780, top-2 accuracy 0.960, ECE 0.137.
- **Limitations**: YC-only population; b2b/consumer confusion; small education/real-estate classes.
- **Production usage**: `backend/app/ml/predictor.py`, feeds `venture_positioning`/`model_category`
  throughout the mentor pipeline (industry-flavored knowledge packs, GTM vocab, retrieval reranking).
- **Unused components**: `industry_classifier/v1` (synthetic bootstrap corpus, 100% "accuracy" —
  not representative of anything real) and `industry_classifier/v2` (superseded by v3 on every CV/
  test/gold metric) — both dead weight, removed in Phase 8.
- **Technical debt**: no artifact-size tracking in metadata (unlike success_predictor); DistilBERT
  fine-tuning was evaluated as infeasible on this hardware (documented, not attempted) and remains
  a legitimate future option if hardware constraints ever lift — out of scope now that the ML
  architecture is frozen.

## Success Predictor

- **Purpose**: "Historical Pattern Signal" comparing submitted metrics against historical outcome
  patterns — never a prediction about this specific idea.
- **Training data**: 13,334-row resolved Crunchbase outcome set (see `ml/MODEL_CARDS.md`).
- **Evaluation protocol**: stratified train/test, RepeatedStratifiedKFold CV for model selection,
  leakage-checked, overfitting-gap-checked, learning curve, permutation importance, subgroup
  fairness metrics.
- **Metrics**: test ROC-AUC 0.855, MCC 0.546, Cohen's Kappa 0.545, ECE 0.019.
- **Limitations**: funding-history features carry timing bias; no free-text pitch input.
- **Production usage**: `backend/app/ml/success_predictor.py`, surfaced as "Historical Pattern
  Signal" (never Success/Failure), explicitly excluded from `biggest_risk`/top-action-list framing.
- **Unused components**: `success_predictor/_smoke_test` artifact — a fixture used only by
  `ml/tests`, not a real candidate; kept (test dependency), documented so it's not mistaken for a
  second production candidate.
- **Technical debt**: none identified this pass — this model's metadata/governance is the most
  complete of the three (artifact size, full calibration comparison, subgroup metrics all present).

## Venture Retrieval

- **Purpose**: real-company nearest-neighbor search over a merged 7,668-row corpus.
- **Training data**: not trained — a fitted, frozen sentence-transformer embedding index (see
  `ml/MODEL_CARDS.md`).
- **Evaluation protocol**: leave-one-out same-industry agreement (honest proxy, no fabricated
  ground truth).
- **Metrics**: Precision@1 0.737, MRR 0.824, NDCG@5 0.851 (internal v2 artifact, exposed as v1).
- **Limitations**: proxy metric measures industry-coherence, not verified competitor relevance;
  90.1%/85.5% country/funding-stage coverage (not 100%).
- **Production usage**: `backend/app/ml/venture_retrieval.py`, feeds `startup_benchmark.py`,
  `founder_intelligence.py`'s feature-gap/investor-intelligence sections, and
  `go_to_market_intelligence.py`'s customer-acquisition-channel/objection fields.
- **Unused components**: none — v1 corpus artifact kept intentionally as the most recent rollback
  candidate (promoted from v1→v2 only last sprint); this is a deliberate, disclosed exception to
  the "delete dead experiments" rule given how recently the promotion happened.
- **Technical debt**: the `_dedupe_robustly` near-duplicate check is O(candidates²) within each
  inverted-index bucket — fine at this corpus size (7,668 rows), would need revisiting only if the
  corpus grew an order of magnitude larger, which is out of scope now that the corpus is frozen.

## Comparative Intelligence (`app.ml.venture_retrieval.build_comparative_intelligence`)

- **Purpose**: deterministic aggregation over already-retrieved real neighbors (industry
  positioning, shared terminology, geography, funding-stage pattern) — no LLM, no new inference.
- **Training data**: none — pure aggregation logic over retrieval output.
- **Evaluation protocol**: unit-tested directly (`test_venture_retrieval.py`), no separate metric
  suite needed since it performs no prediction.
- **Limitations**: `common_pricing_model`/`common_deployment_strategy`/`common_go_to_market_motion`
  remain permanently unsupported — the corpus structurally has no data for them, disclosed
  explicitly rather than guessed.
- **Production usage**: feeds `founder_report.py`'s comparative-pattern-summary and
  `startup_benchmark.py` directly.
- **Technical debt**: none identified.

## Knowledge Audit (`app.agents.knowledge_audit`)

- **Purpose**: classifies every founder_report tagged item's knowledge source (retrieved_evidence /
  deterministic_reasoning / ai_reasoning / startup_knowledge / unsupported_generic_advice) and
  reports category coverage — an audit tool, not a predictive model.
- **Training data**: none — deterministic path-matching against this pipeline's own known
  architecture.
- **Evaluation protocol**: unit-tested (`test_knowledge_audit.py`); real numbers verified via a live
  Smart Canteen run each sprint.
- **Metrics**: last measured — 61.3% deterministic reasoning, 38.1% startup knowledge, 0.6%
  retrieved evidence, 0% unsupported, 0% AI reasoning (honestly reported, not assumed).
- **Limitations**: `possible_contradictions` (in the related `consistency_audit` module) has a
  documented false-positive class (complementary problem/solution sentence pairs flagged as if
  disagreeing).
- **Production usage**: attached to every `mentor_result` as `knowledge_audit`.
- **Technical debt**: none identified this pass.

## Unused / Exploratory-Only Component: Survival Model

- **Purpose**: Cox Proportional Hazards survival analysis (Track 2 of the success-predictor upgrade
  pass) — models time-to-outcome rather than a binary success/failure classification.
- **Status**: built, trained, evaluated (concordance index reported in
  `ml/models/survival_model/v1/metadata.json`), and explicitly documented in `ml/DATASETS.md` as
  "an honest, exploratory diagnostic" — **never wired into any backend/frontend production path**
  (confirmed: zero references to `survival_model`/`survival_analysis` anywhere in `backend/app/`).
- **Decision this sprint**: keep the artifact and its documentation (real, small, informative
  research output) but explicitly flag it here as unused — matches this sprint's "document unused
  components" requirement rather than silently deleting a real trained model with a legitimate
  scientific rationale.

## Founder Intelligence Inputs

- **Purpose**: not itself an ML model — a re-projection of already-computed signals (funding
  rubric, venture_signals, capability_library, regulatory_context, industry knowledge packs,
  retrieval comparative intelligence) into founder-facing coaching content.
- **Training data**: N/A (deterministic reasoning over other components' outputs).
- **Evaluation protocol**: unit-tested per function (`test_founder_intelligence.py`, 24+ tests
  including genericness-regression tests).
- **Limitations**: entirely dependent on the quality of its inputs — a weakness in the industry
  classifier or retrieval corpus propagates here, not a separate failure mode.
- **Production usage**: `critical_blind_spots`, `investor_questions`, `founder_challenge_mode`,
  `moat_intelligence`, `feature_gap_vs_market`, `funding_stage_ladder`, `founder_iq_report`,
  `investor_intelligence`, `explainability_index`.
- **Technical debt**: none identified — this module was the most recently audited/tested prior to
  this sprint.
