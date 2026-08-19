# VentureForge AI — Project Technical Guide

*Version 1.0 — written 2026-08-01, current as of commit `759b8a3` (main). This is the project's technical handbook: architecture, ML models, AI agents, APIs, database, frontend, deployment, testing, honest limitations, and viva/defense preparation. No marketing language — every claim here is either verified against the actual source code or explicitly flagged as inference.*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Complete System Architecture](#2-complete-system-architecture)
3. [ML Models](#3-ml-models)
4. [AI Agents](#4-ai-agents)
5. [Backend APIs](#5-backend-apis)
6. [Database](#6-database)
7. [Frontend](#7-frontend)
8. [Project Flow](#8-project-flow)
9. [Deployment](#9-deployment)
10. [Testing](#10-testing)
11. [Limitations](#11-limitations)
12. [Future Improvements](#12-future-improvements)
13. [Viva Preparation — FAQ](#13-viva-preparation--faq)

---

## 1. Project Overview

### Purpose

VentureForge AI takes a founder's raw startup idea (a short description plus answers to an 8-dimension evidence questionnaire) and produces a structured, evidence-grounded analysis: industry classification, funding readiness, a success-likelihood signal, market/competitor/customer intelligence, a revenue estimate, risk assessment, and a synthesized "Judge" verdict — all assembled into a founder-facing report with an investor view.

### Problem Solved

Early-stage founders (and hackathon/accelerator applicants) usually get one of two things: a generic AI chatbot that will validate almost anything they type, or a slow, expensive human mentor/investor conversation. VentureForge tries to sit between those: deterministic, explainable scoring (a funding-readiness rubric, a trained success-prediction model, a keyword-weighted taxonomy) wherever a defensible signal exists, and LLM assistance only where a rule can't reasonably substitute — never presenting an LLM's fluency as evidence.

### Target Users

- Founders/hackathon participants wanting a fast, structured gut-check on an idea before pitching.
- Judges/mentors wanting a consistent artifact (the founder report) to review multiple ventures against the same rubric.

### Architecture (one-line summary)

React SPA (Vite) → FastAPI REST + SSE → PostgreSQL → a LangGraph multi-node pipeline (ML models + deterministic agents + optional Gemini calls) → a deterministic "Judge" synthesis → a deterministic founder report.

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript (strict), Vite 5, react-router-dom 6, Recharts 3, framer-motion 11, pdf-lib, Tailwind CSS |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, uvicorn |
| Orchestration | LangGraph (`StateGraph`) |
| ML | scikit-learn, pandas, numpy, joblib (persisted artifacts) |
| LLM (optional) | Google Gemini (`gemini-flash-latest`) via a hand-written REST client, JSON mode |
| Database | PostgreSQL 17 (JSONB columns), SQLite for tests |
| Deployment | Render (backend + Postgres), Vercel (frontend), GitHub Actions (CI) |

### Folder Structure

```
VentureForge AI/
├── backend/
│   ├── app/
│   │   ├── agents/       47 files — LangGraph orchestrator + all deterministic/LLM agents
│   │   ├── ai/            Gemini client, prompt schemas, provider factory
│   │   ├── api/v1/        7 route modules (health, startups, analyses, models_status,
│   │   │                  system_status, taxonomy, predict)
│   │   ├── core/          settings/config
│   │   ├── database/      SQLAlchemy session, custom JSON/JSONB column type
│   │   ├── ml/            serving-time wrappers: predictor, success_predictor,
│   │   │                  positioning_taxonomy, segmentation, funding_readiness,
│   │   │                  revenue_scenario, venture_retrieval, venture_space_analytics
│   │   ├── models/        SQLAlchemy ORM models (Startup, Analysis)
│   │   ├── schemas/       Pydantic request/response models
│   │   ├── services/      analysis_service (DB + background-thread orchestration),
│   │   │                  analysis_events (SSE pub/sub)
│   │   └── main.py
│   ├── alembic/versions/  11 linear migrations
│   └── tests/             backend unit/integration tests
├── frontend/
│   └── src/
│       ├── app/           RootLayout, BareLayout, DiscoveryLayout, error boundary
│       ├── components/    reveal/ (scenes + charts), evidence/, forge/, threshold/, ...
│       ├── context/       NewAnalysisContext (draft persistence)
│       ├── hooks/         useAsync, useAnalysisProgress, useIndustryPreview, ...
│       ├── motion/        fixed transition tiers + Act classification
│       ├── pages/         one component per route
│       ├── services/      api.ts (backend client), localHistory.ts
│       └── utils/         generatePdf.ts
├── ml/
│   ├── src/
│   │   ├── features/, preprocessing/, training/, evaluation/, explainability/, analysis/
│   │   └── (each has both library modules and standalone `python -m` CLI scripts)
│   ├── models/            committed trained artifacts (see §3)
│   └── DATASETS.md        the canonical dataset-provenance/licensing decision log
├── render.yaml            Render Blueprint (backend service + Postgres)
└── .github/workflows/ci.yml
```

---

## 2. Complete System Architecture

```
React (Vite SPA, Vercel)
   │  fetch() + EventSource (SSE)
   ▼
FastAPI (Render) — 7 routers under /api/v1
   │  SQLAlchemy ORM
   ▼
PostgreSQL (Render) — 2 tables: startups, analyses (JSONB-heavy)
   │
   │  a background daemon thread per analysis calls:
   ▼
LangGraph orchestrator (StateGraph, ~24 nodes, linear + 1 conditional branch)
   │
   ├─▶ ML models (industry classifier, success predictor, customer segmentation,
   │    venture-positioning taxonomy — all served in-process from joblib artifacts)
   │
   ├─▶ Deterministic agents (funding readiness rubric, revenue scenario, market/
   │    competitor/persona/business-model heuristics, mentor synthesis, founder
   │    report composer, 6 "Intelligence Architecture" reasoning modules)
   │
   ├─▶ Optional Gemini calls (6 specific "advisory" wrappers — see §4 — every one
   │    has a deterministic fallback and never blocks the pipeline if unavailable)
   │
   ▼
Judge (judge.py + judge_voice.py) — deterministic synthesis of everything above
   into strengths/weaknesses/next_actions/overall_assessment
   │
   ▼
Founder Report (founder_report.py) — composes the Judge + mentor output into
   a 10-section consulting narrative, every claim tagged evidence/inference/
   ai_recommendation/market_assumption/experiment_suggestion
   │
   ▼
Persisted back to `analyses` row → served to the Reveal page (SSE progress
   during the run, then a final GET) → React renders Executive Command Center,
   dashboard charts, mission control, investor review, deep analysis, PDF export
```

**Every connection explained:**

- **React → FastAPI**: plain `fetch()` for all mutations/reads (`services/api.ts`), plus one native `EventSource` connection per in-progress analysis for live progress (no `fetch`-based streaming — SSE requires the browser's native client).
- **FastAPI → Database**: SQLAlchemy 2 ORM, one session per request (`get_session_factory`), synchronous (not async) driver (`psycopg2-binary`).
- **FastAPI → LangGraph**: `POST /startups/{id}/analyze` returns immediately (row inserted as `RUNNING`) and spawns a **daemon background thread** running `stream_pipeline` — the HTTP response is not held open for the ~30-90s a real analysis takes. This is why an SSE channel exists: the frontend needs another way to learn when the background thread finishes.
- **LangGraph → ML models**: nodes call the `backend/app/ml/*` serving wrappers directly, in-process (no separate ML microservice/network call) — the trained `joblib` artifacts are loaded once at import time.
- **LangGraph → Judge → Founder Report**: strictly one-directional data flow; the Judge never re-invokes an earlier node, and the founder report never recomputes anything the Judge already decided (only re-narrates it).
- **Persistence**: after **every node**, `analysis_service._persist_progress` writes the partial state back to the `analyses` row and publishes an event to the in-process SSE pub/sub (`analysis_events.py`) — so a browser refresh mid-analysis reloads a real, current partial state from the database, not stale client memory.

---

## 3. ML Models

VentureForge has **two trained ML models actually on the serving path**, one trained-but-dormant model, two semantic-retrieval components (off by default), and two **deterministic, non-ML** scoring systems that are easy to mistake for ML if you only read the founder-facing copy. All of this is disclosed here explicitly because a viva question like "is this really machine learning?" deserves an honest, specific answer per component, not one blanket "yes."

### 3.1 Industry Classifier (live, on every analysis)

- **Purpose**: classify a startup's industry (7 classes) from its name + description.
- **Dataset**: 3 merged, licensed Kaggle YC-directory datasets (YC batches 2005–2026): `ibrahimqasimi/y-combinator-companies-2012-2024` (CC BY 4.0, 4,522 rows), `mohamedasak/y-combinator-startup-directory-2025` (Apache-2.0, 629 rows), `alibekmamyrbay/y-combinator-startups-full-directory-20052026` (CC-BY-SA-4.0, 5,884 rows). Deduplicated on exact description text. Several candidate datasets were evaluated and rejected in `ml/DATASETS.md` for unknown licensing or wrong schema.
- **Classes**: `b2b` (~55% of data), `consumer`, `education`, `fintech`, `healthcare`, `industrials`, `real estate and construction`. `unspecified`/`government` excluded (too few rows).
- **Features**: a single text field, `f"{name}. {description}"`, must be built identically at train and serve time (`ml/src/features/build_features.py`).
- **Preprocessing**: TF-IDF word (1-2gram, max 20,000 features) + char (3-5gram, max 8,000 features) `FeatureUnion`, no numeric scaling needed.
- **Algorithm**: `tfidf_word_char_logreg` — logistic regression, `class_weight="balanced"`, over the TF-IDF FeatureUnion. Beat: dummy baseline, TF-IDF-word-only, calibrated LinearSVC, ComplementNB, TF-IDF-char-only, TF-IDF+LSA(100-dim), and three sentence-transformer (`all-MiniLM-L6-v2`) embedding variants (embeddings scored 0.605–0.735 CV macro-F1 vs. the winner's 0.775 — **embeddings did not beat TF-IDF here**). DistilBERT fine-tuning was not attempted (measured free RAM below a safe margin on the dev machine).
- **Training**: 5,781 train / 1,446 test / 140 independent gold rows (excluded before split). 5-fold stratified CV, macro-F1, seed 42.
- **Evaluation (real numbers, current artifact)**: CV macro-F1 **0.7751 ± 0.0135**; held-out test accuracy **0.7932**, macro-F1 **0.7688**, top-2 accuracy **0.9599**; independent gold-set accuracy **0.7714**. Weakest class: consumer (F1 0.687, mostly confused with b2b — "platform for X" language is genuinely ambiguous). Calibration ECE **0.1371** (uncalibrated — a calibrated alternative scored better ECE but lower macro-F1, and macro-F1 was prioritized). Inference latency ~2.4ms.
- **Serving**: `predict_industry()` returns `predicted_industry`, `confidence`, top-3 `alternatives`, and two independent uncertainty signals (`is_uncertain` — no-vocabulary / low-confidence / ambiguous-margin; `is_low_confidence` — a separate abstention threshold) plus a nearest-training-example explanation.
- **Known limitations**: YC-backed, English-only startups only. A 34-class sub-industry taxonomy was tried and explicitly rejected (CV macro-F1 collapsed to 0.44) — documented in the repo, not hidden.

### 3.2 Success Predictor (live, on every analysis — retrained this week for a real bug fix)

- **Purpose**: estimate how similar a startup's funding/category/geography profile is to companies that historically reached a resolved exit (acquisition/IPO) vs. shutdown, in Crunchbase's historical record. Explicitly **never** shown to a founder as a binary verdict — the founder-facing text is a hedged `pattern_signal_label` (e.g. `stronger_comparison` / `insufficient_input_reliability`).
- **The fix that just happened**: three features — `funding_span_years`, `time_to_first_funding_years`, `funding_recency_years` — were derived from funding-round *dates* that the startup submission form never collects, so every live prediction fabricated them as permanently missing (a real train/serve distribution shift). A controlled experiment that simulated real serving conditions (wiping those fields on the held-out test set) showed removing them **raised served ROC-AUC 0.812→0.827** and cut the oracle-vs-served label-flip rate from 11.3% to 2.9%. The model was retrained on the corrected 9-feature set.
- **Dataset**: `yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase` (CDLA-Sharing-1.0), 66,368 raw rows → **13,334 rows with a resolved outcome** (acquired/IPO = success 53.2%, closed = failure 46.8%; `operating` rows excluded as unresolved — a real survivorship-bias risk, see §11).
- **Features (current)**: `funding_total_usd`, `funding_rounds`, `company_age_years`, `category_count`, `funding_per_round`, `funding_velocity`, `funding_per_category`, `primary_category`, `country_code` — 9 total.
- **Preprocessing**: `ColumnTransformer` — skewed numeric columns get median-impute + missing-indicator → `log1p` → `StandardScaler`; other numeric columns get median-impute + indicator → `StandardScaler`; categoricals get most-frequent-impute → one-hot (`handle_unknown="ignore"`). `engineer_features()` is called identically at train and serve time (single shared function, explicit anti-drift design).
- **Algorithm**: `voting_ensemble` (soft-voting LogisticRegression + HistGradientBoosting), wrapped in `CalibratedClassifierCV(method="isotonic")`. Compared via `RepeatedStratifiedKFold(5×3)` against 8 other candidates (best rival: `hist_gradient_boosting` alone at 0.8166 CV ROC-AUC vs. the ensemble's 0.8200).
- **Evaluation (real numbers, current artifact, trained 2026-07-31)**: test accuracy **0.7574**, balanced accuracy 0.7548, F1 **0.7771**, MCC 0.5119, ROC-AUC **0.8384**, PR-AUC 0.8393, Brier score 0.1619, calibration ECE **0.0148** (well-calibrated). Train ROC-AUC 0.8514 (overfitting gap only 0.013). Recommended F1-optimal operating threshold: **0.40**. Top permutation-importance feature: `funding_total_usd` (0.2356). A temporal-split diagnostic (train on earliest 80%, test on most recent 20%) scored a misleadingly high 0.9112 ROC-AUC — the docs explicitly flag this as **not trustworthy** (the recent slice is skewed toward two near-deterministic categories) and the random-split 0.8384 is the metric actually reported.
- **Serving**: `predict_success()` imputes missing inputs via the trained pipeline (never guesses), returns the pattern-signal label plus technical fields (`success_probability`, `operating_threshold`), global permutation importances, and a genuinely local (per-prediction) SHAP-free explanation via `app.ml.local_success_explainer`.
- **Known limitations**: no investor-count or funding-round-type field exists anywhere in the source data; `funding_total_usd`/`funding_rounds` are cumulative totals as of the last recorded event, so they partly encode the outcome's own timeline; Crunchbase-tracked companies only; excluding "operating" rows is a real survivorship-bias risk (a separate Cox survival model addresses this partially but is **not integrated** into serving — see §3.3.1).

### 3.3 Customer Segmentation (live, conditional on caller supplying RFM data)

- **Purpose**: assign a real customer (given recency/frequency/monetary inputs) to a behavioral segment for growth-planning agents.
- **Dataset**: UCI Online Retail (CC BY 4.0), 541,909 transactions, Dec 2010–Dec 2011, real UK non-store online retailer.
- **Preprocessing**: drop duplicates/missing-`CustomerID`/cancellations/non-positive quantity or price; fixed snapshot date; build RFM; winsorize at 1st/99th percentile; `log1p`; `RobustScaler`.
- **Algorithm**: compares `KMeans`, `MiniBatchKMeans`, `AgglomerativeClustering` (Ward), `GaussianMixture` over k=2–8, selected by a rank-sum across silhouette / Davies-Bouldin / Calinski-Harabasz **plus adjusted-Rand stability on 4-seed resamples** — not accuracy (unsupervised).
- **Status**: this artifact was "fully implemented but never trained" until this week — every real request previously fell back to `"unavailable"`. Now trained and committed. Consumed by `app.agents.student3.customer_segment()`, which still explicitly falls back to an `unavailable` `CustomerSegment` object if the caller supplied no RFM data at all (real, not dormant, code path).

#### 3.3.1 Other artifacts under `ml/models/` — status honestly disclosed

| Artifact | Status |
|---|---|
| `survival_model/v1/` (Cox Proportional Hazards) | **Trained, not integrated.** Uses all 66,368 rows including censored "operating" companies. Concordance index only 0.662–0.672; duration is a proxy (`last_funding_at − founded_at`, not a true exit date). Documented as a deliberate non-integration decision pending clearer product framing — no backend endpoint exists for it. |
| `venture_retrieval/v1`/`v2` (semantic nearest-neighbor search, frozen `all-MiniLM-L6-v2` embeddings) | **Live, off by default** (`settings.enable_venture_retrieval`) — loading the sentence-transformer takes 20-40s on first use, so it must never fire as a side effect of an ordinary request or test. v2 measured precision@1 0.7373 / MRR 0.8243 vs. v1's 0.7036 / 0.8010. Every result carries a provenance disclaimer (real historical record, not a live database). |
| `venture_space_analytics/v1` | **Live**, supports venture_retrieval. K-means over the embedding space was tested and **rejected** as a standalone metric (silhouette 0.019–0.028 — the space is a continuum, not discrete clusters); uses the real 7-class industry labels for "innovation distance"/"market crowdedness" instead. |

### 3.4 Venture Positioning Taxonomy — **deterministic, not a trained model**

- **File**: `backend/app/ml/positioning_taxonomy.py`.
- **What it actually is**: a fixed, versioned (`v1`), hand-curated **keyword+phrase weighted-scoring system** — not a classifier, no training, no dataset. Deliberately independent of the trained 7-class industry classifier, whose labels are "too coarse to serve as a founder-facing identity."
- **Mechanism**: each domain has `keywords`/`phrases` with weights, a `high_specificity` subset (one match is enough for eligibility), and a `specificity_rank` used only as a tie-break. A domain is eligible if it has ≥2 distinct matched concepts or ≥1 high-specificity match. `weighted_score` = matched weight ÷ that domain's max possible weight.
- **This week's fix**: a pre-submission audit found real Robotics/Logistics/Retail pitches confidently mislabeled as "Enterprise AI" — the only pre-existing broad catch-all for AI-adjacent wording, since no domain existed for those verticals. Added **Robotics & Industrial Hardware**, **Logistics & Supply Chain**, **Retail & E-commerce** (14 domains total now), reusing vocabulary already validated in the separate knowledge-pack system rather than inventing new categories.
- **No metrics section** — this module's own docstring states "nothing here is invented per input"; there is nothing to evaluate the way a trained model is evaluated. Verified via 6 unit tests and a 10-startup live regression run (see §10).

### 3.5 Two more deterministic, non-ML scoring systems

- **Funding Readiness** (`app.ml.funding_readiness`) — a versioned rubric over the founder's own evidence-questionnaire answers, not a trained model.
- **Revenue Scenario** (`app.ml.revenue_scenario`) — a calculator over user-supplied assumptions (price, initial customers, growth rate, margin), never a projection model.

Both exist as deterministic rules specifically because, per the codebase's own rationale, **no defensible labeled dataset was found** for either — an honest, documented decision not to force a trained model where the data didn't support one.

---

## 4. AI Agents

VentureForge's orchestrator is a **LangGraph `StateGraph`**, ~24 nodes, strictly linear except one conditional branch at the start (`input_validation` → `industry_classification` or `invalid_input`). `recursion_limit=100` (LangGraph's default 25 was hit once node count grew past it).

### 4.1 Real node sequence

```
input_validation → (valid) industry_classification → resolve_venture_positioning
→ funding_readiness → predict_success → estimate_revenue → analyze_market
→ analyze_competitors → build_customer_persona → evaluate_business_model
→ segment_customers → rank_actions → surface_innovation → assess_risks
→ plan_growth_strategy → build_pitch_deck → evidence_confidence_check
→ judge → mentor_synthesis → expand_ideas → discover_strategic_opportunities
→ synthesize_decision → reason_causally → simulate_counterfactuals
→ persistence → final_response → END
```

`resolve_venture_positioning` deliberately runs right after `industry_classification` (not at the end) so every downstream agent can key off it.

### 4.2 Which agents are genuinely LLM-backed (call Gemini) vs. purely deterministic

This distinction matters for defending "is this really AI" in a viva. **Only 6 of the ~47 agent modules ever make a network call to an LLM.** Every one of the 6 follows the identical safe pattern: `get_llm_provider()` returns `None` if `GEMINI_API_KEY` is unset (zero network I/O), and any `LLMUnavailable`/generic exception is caught and logged, never propagated — the pipeline always falls back to its deterministic baseline.

| # | Module | Gemini call | Trigger condition | What it can/can't change |
|---|---|---|---|---|
| 1 | `orchestrator._try_llm_narrative` | `generate_narrative` | Always attempted (optional) | Adds a narrative paragraph; schema has no field for industry/confidence/score |
| 2 | `positioning_reviewer` | `review_positioning` | Only when taxonomy is ambiguous | Advisory only — `venture_positioning.py`'s typed rule set decides whether to use it |
| 3 | `competitor_reviewer` | `suggest_competitor_possibilities` | Only when founder named no competitors | Category-level suggestions only, prompt forbids naming real companies |
| 4 | `mentor_reviewer` | `generate_mentor_advice` | Always attempted (optional) | Appends bounded `mentor_advice_items`; never rewrites the deterministic baseline |
| 5 | `idea_expansion_reviewer` | `generate_idea_expansion` | Always attempted (optional) | Appends items; schema forbids the "confirmed_from_evidence" tier for Gemini items |
| 6 | `strategic_opportunity_reviewer` | `generate_strategic_opportunity` | Always attempted (optional) | Appends to adjacent-opportunity lists only, never `primary_opportunity` |

**Purely deterministic (no LLM anywhere in the call chain)**, despite some docstrings mentioning Gemini (only to explain what does *not* touch them): `judge.py`/`judge_voice.py` (the Judge core), `venture_positioning.py` (the final-authority resolver — see below), `venture_vocabulary.py`, `mentor_synthesis.py`'s baseline builder, `founder_report.py`, `competitor_agent.py`/`market_agent.py`/`customer_persona_agent.py`/`business_model_agent.py` ("no live data source, never invents a figure"), `student3.py` (customer segmentation uses the trained clustering artifact, not an LLM), `competitor_intelligence.py`/`feature_intelligence.py`/`go_to_market_intelligence.py`/`pricing_intelligence.py`/`industry_knowledge_packs.py` (category-keyed reference dictionaries), `consistency_audit.py`/`knowledge_audit.py` (post-hoc regex/keyword auditors), and the 8 "Intelligence Architecture" reasoning modules (`evidence_ledger.py`, `venture_frame.py`, `hypothesis_set.py`, `contradiction_engine.py`, `alternative_explanation_engine.py`, `decision_synthesis.py`, `causal_reasoning.py`, `counterfactual_simulation.py`).

### 4.3 The Judge Agent — the core synthesis

`judge.synthesize()` (raises `ValueError` only if `funding_assessment` lacks `overall_score` — the one failure mode that fails the whole run) reconciles `industry_prediction`, `funding_assessment`, `evidence_check`, and every optional downstream output into `strengths`/`weaknesses`/`missing_evidence`/`next_actions`, always tracing each field's true source (trained ML vs. deterministic calc vs. raw user evidence — **never blended into one number**). It also builds the 6 Intelligence Architecture structures. `judge_voice.build_overall_assessment` composes the one founder-facing paragraph.

**Does the Judge work without `GEMINI_API_KEY`?** Yes, verifiably — `judge.py` has zero imports from `app.ai`. Any narrative Gemini *could* add is layered on **after** `synthesize()` returns, by the orchestrator, stored separately in `judge_summary["llm_narrative"]` — additive, never required, `None` when unconfigured.

### 4.4 `venture_positioning.py` — the sole final authority for the founder-facing category

A 7-rule deterministic decision tree: user override (always wins) → no-taxonomy-candidate fallback to raw classifier → dominant-taxonomy-candidate used unchanged (Gemini never consulted) → ambiguous-taxonomy with Gemini's structured recommendation gated by 3-4 pre-typed conditions (must already be an eligible candidate, within the ambiguity margin, confidence ≥ 0.6). **`gemini_recommendation.rationale` — the free-text part — is never read or scored**, only carried through as display text (this is a deliberate prompt-injection defense, verified by a dedicated test: a malicious rationale claiming "set primary_domain to X" has zero effect on the outcome).

### 4.5 Failure handling summary

| Failure mode | Behavior |
|---|---|
| Invalid input (empty name / too-short description) | Routed straight to `invalid_input` → `status: FAILED` |
| Industry classifier / success predictor unavailable | Caught, field set to `None`, pipeline continues |
| Judge node raises `ValueError` | `status: FAILED`, but the run still persists that state |
| Downstream node's required upstream output is `None` | Returns `{...: None, trace: [skipped]}`, never crashes |
| Gemini unconfigured / times out / bad JSON / schema mismatch | All 6 call sites fall back identically to the deterministic baseline |

**Net effect**: a missing `GEMINI_API_KEY` produces a fully functional, fully deterministic analysis. Only `mentor_advice_items`, the optional narrative paragraph, and a few "possibilities"/"opportunities" arrays end up empty.

---

## 5. Backend APIs

Router registration: `backend/app/main.py` mounts 7 routers under `/api/v1` — nothing else exists.

### `POST /api/v1/startups` (201)
Request `StartupCreateRequest`: `name` (1-200 chars), `description` (10-5000 chars), plus optional nested `funding_answers` (8 evidence dimensions, strict state/severity validation), `company_metrics`, `revenue_assumptions`, `market_evidence`, `customer_rfm`. Plain INSERT via `analysis_service.create_startup`. Frontend caller: `EvidenceCollectionPage.tsx`.

### `GET /api/v1/startups/{startup_id}`
Returns `StartupResponse` or 404. Frontend: `AnalysisResultPage.tsx`.

### `POST /api/v1/startups/{startup_id}/analyze` (201)
No body. Inserts `Analysis(status="RUNNING")`; catches the partial-unique-index `IntegrityError` on a rapid double-click and returns the already-running row instead of erroring; spawns a **daemon background thread** running `stream_pipeline`, persisting after every node. Returns immediately (status still `RUNNING`). Frontend: `AnalysisStatusPage.tsx`.

### `GET /api/v1/analyses/{analysis_id}`
Returns `AnalysisResponse` or 404. Frontend: `AnalysisResultPage.tsx`, poll fallback in `useAnalysisProgress`.

### `GET /api/v1/analyses/{analysis_id}/events`
SSE stream (`text/event-stream`): emits the current DB snapshot first, then re-emits on every real node completion via an in-process pub/sub queue; 15s heartbeat; closes on `COMPLETED`/`FAILED`. Frontend: consumed by the browser's native `EventSource`, wired through `useAnalysisProgress.ts`.

### `POST /api/v1/analyses/{analysis_id}/industry-correction`
Request validates `primary_domain`/`secondary_domains` against the real taxonomy (422 if unknown). Reruns `resolve_venture_positioning` with `user_override` (always wins), regenerates mentor/idea-expansion/strategic-opportunity so nothing downstream goes stale. Frontend: `PositioningCorrection.tsx`.

### `PATCH /api/v1/analyses/{analysis_id}/revenue-assumptions`
Fields use `allow_inf_nan=False` — a NaN/Infinity payload gets a clean 422, not a crash (the custom `RequestValidationError` handler in `main.py` specifically sanitizes floats before echoing the rejected body, since Starlette's default JSON encoder would otherwise crash trying to serialize a NaN back). Only fields present in the request are changed (`exclude_unset=True`); an explicit `null` clears that assumption. Frontend: `RevenueScenarios.tsx`.

### `POST /api/v1/predict/industry`
Read-only preview, no DB write, calls the **exact same** `predict_industry`/`extract_deployment_sectors` functions the real pipeline uses — explicitly documented as not a second prediction path. Frontend: `useIndustryPreview.ts`, used live while typing on `IdeaSubmissionPage.tsx`.

### `GET /api/v1/taxonomy`
Full domain list, source of truth for the industry-correction validators. Frontend: `PositioningCorrection.tsx`.

### `GET /api/v1/models/status`
Model versions/trained-at/test-metrics/CV-results read straight from each artifact's `metadata.json`, never fabricated. Frontend: `AboutModelModal.tsx`.

### `GET /api/v1/system/status`
**Dev-only — 404s in production** (`app_env == "production"` check). Aggregates DB connectivity, Alembic migration head check, model load state, LLM configuration. Frontend `SystemStatusOverlay.tsx` treats a 404 as expected/`null`, not an error — this is why the production console-error log shows harmless 404s on this exact endpoint.

### `GET /api/v1/health`
Trivial `{"status": "ok"}`, no DB touch. This is the always-on endpoint Render's health check actually targets (not `/system/status`, which is intentionally environment-gated).

### Global error handling
`RequestValidationError` → 422 (NaN-sanitized); `OperationalError` (DB down) → 503 with a fixed, safe message — never echoes the raw driver exception (which can contain the connection string).

---

## 6. Database

Two tables, PostgreSQL (`pgcrypto`'s `gen_random_uuid()` for PKs), `JSON().with_variant(JSONB(), "postgresql")` so the same models run against real Postgres in production and SQLite in tests.

### `startups`
`id` (UUID PK) · `name`, `description` (Text, NOT NULL) · `funding_answers`, `company_metrics`, `revenue_assumptions`, `market_evidence` (JSONB, default `{}`) · `customer_rfm` (JSONB, nullable) · `created_at`/`updated_at`.

### `analyses`
`id` (UUID PK) · `startup_id` (FK → `startups.id ON DELETE CASCADE`, indexed) · `status` (`PENDING`/`RUNNING`/`COMPLETED`/`FAILED`) · `industry_prediction`, `funding_assessment`, `judge_summary`, `success_prediction`, `revenue_estimate`, `market_intelligence`, `competitor_analysis`, `customer_personas`, `business_model`, `mentor_interpretation`, `idea_expansion`, `strategic_opportunity`, `student3_outputs` (all JSONB) · `positioning_correction_history`, `revenue_assumptions_history` (JSONB, default `[]`) · `current_node`, `current_stage` (live-progress text fields) · `workflow_trace`, `error_message` · timestamps.

### The partial unique index (this sprint's race-condition fix)

```sql
CREATE UNIQUE INDEX ux_analyses_one_running_per_startup
  ON analyses (startup_id) WHERE status = 'RUNNING';
```

A **blanket** `UNIQUE(startup_id)` would break re-analyze (a startup legitimately accumulates many historical `COMPLETED`/`FAILED` rows). Scoping the uniqueness to `WHERE status = 'RUNNING'` means Postgres enforces "at most one row with this startup_id" only among rows currently in flight — historical rows are invisible to the index. It's DB-level, not application-level: the service layer relies on catching the real `IntegrityError` from a genuine concurrent `INSERT` conflict, which is race-proof by construction (unlike a "check if one exists, then insert" pattern in app code, which has a TOCTOU race window under real concurrent requests).

### Full migration list (11, linear, no branches)

1. `0001_initial` — creates both tables, `pgcrypto`, `ix_analyses_startup_id`
2. `0002_student2_extension` — company_metrics/revenue_assumptions/market_evidence + success/revenue/market/competitor/persona/business-model outputs
3. `0003_positioning_correction_history`
4. `0004_revenue_assumptions_history`
5. `0005_mentor_interpretation`
6. `0006_idea_expansion`
7. `0007_strategic_opportunity`
8. `0008_student3_outputs`
9. `0009_customer_rfm`
10. `0010_analysis_live_progress` — `current_node`/`current_stage` for SSE
11. `0011_one_running_analysis_per_startup` — the partial unique index above

### Why PostgreSQL — honest assessment

No standalone rationale document exists in the repo explaining this choice explicitly — it's asserted (in the README) not argued. What follows is inference from actual usage, not documented fact: 11 of `analyses`'s ~24 columns are JSONB, storing large semi-structured agent outputs that don't need relational decomposition — Postgres's binary, indexable `JSONB` is materially better here than SQLite's text-based JSON; the partial-unique-index concurrency guard relies on Postgres's real row-level constraint enforcement under concurrent background threads; `pgcrypto`'s `gen_random_uuid()` is Postgres-specific. If asked "why Postgres" in a viva, the honest answer is "the schema was designed around JSONB and pgcrypto from migration 0001, and the team never documented a formal alternatives comparison" — not a claim that a scale/cost evaluation exists.

---

## 7. Frontend

### Routing (`App.tsx`)
`react-router-dom` v6 `BrowserRouter`. `/` (Threshold, eager) → `/new/idea` → `/new/evidence` (both `DiscoveryLayout`, lazy) → `/startups/:id/status` → `/analyses/:id` → `/history` (all `BareLayout`, lazy) → `*` (catch-all `NotFoundPage`, eager, added this sprint — an unmatched URL previously rendered a completely blank page). One `SceneTransition` wraps `<Routes>` at the top level (not per-layout) because React Router unmounts a route's element tree atomically across layout boundaries — a per-layout exit animation would never see the outgoing element.

### State management
Deliberately **hooks-only** — no Redux/Zustand, confirmed absent from `package.json`. One real Context: `NewAnalysisContext` (holds the in-progress idea/evidence draft, auto-persists to `localStorage` on every change). Two smaller providers: `CommandCapsuleProvider` (page nav sections) and `DockActionsProvider` (floating dock's contextual action). `ThemeProvider` for light/dark. Everything else is local `useState`/`useMemo`/`useCallback`.

### Reveal (results) page — 5 sections + a closing scene
`ExecutiveCommandCenter` → `ExecutiveDashboard` (charts only) → `MissionControl` → `InvestorReview` (conditional) → `DeepAnalysis` (collapsed, wraps 6 sub-scenes) → `ContinueBuildingScene` (re-analyze/export/history). Charts use **Recharts 3.10.1** (`GaugeChart`=RadialBarChart, `FundingRadarChart`=RadarChart, `RevenueBarChart`=BarChart); `RiskGrid` is a hand-built CSS grid (Recharts has no heatmap primitive). All chart components guard `Number.isFinite()` so a missing/non-finite value never renders literal "NaN". `insights.ts` derives recurring facts exactly once; every section references them by anchor id rather than restating text.

### Animation
Three fixed tiers only (`micro`=120ms, `scene`=280ms, `threshold`=560ms) — "no component may define an inline duration." `prefers-reduced-motion` collapses `scene`/`threshold` to a 150ms linear crossfade.

### PDF export (`utils/generatePdf.ts`)
**`pdf-lib`**, not jsPDF (jsPDF's bundle statically pulls in html2canvas/dompurify/canvg regardless of usage — measured ~260KB gzipped for zero benefit). Manually-drawn text/lines (not a screenshot): Cover → Executive Summary → Dashboard → Top 3 Priorities → Investor Review → Appendix. Dynamically `import()`ed only on the user clicking Export — never loads for the ~99% of visits that don't.

### History / localStorage (`services/localHistory.ts`)
Key `ventureforge.history.v1`. `recordAnalysis` dedupes by `analysisId`. Self-healing: `AnalysisResultPage.tsx` watches for a 404 (`errorStatus === 404`) and prunes the matching local History row automatically, so a stale link never lingers.

### API client (`services/api.ts` + `hooks/useAsync.ts`)
`ApiError` carries `status`/`detail`; `useAsync`'s error-message resolution only trusts `detail` when it's actually a string (this sprint's fix — FastAPI 422 errors send `detail` as an array of Pydantic error objects, which used to stringify to the literal text `"[object Object]"`).

### Testing
**Vitest** + **React Testing Library** + `jest-axe`. 37 test files, 190 tests. **2 pre-existing, confirmed-unrelated failures** in `AnalysisStatusPage.test.tsx` (an `EventSource` mock-isolation issue across test files — reproduced identically with and without this sprint's changes via `git stash`).

### Build tooling
Vite 5, TypeScript 5.5 (`strict: true`), ESLint 9 flat config with `jsx-a11y` recommended rules run as **errors, not warnings** ("accessibility failures are merge blockers, not follow-up tickets").

---

## 8. Project Flow — the complete startup journey

```
1. Founder lands on "/" (Threshold) → clicks Get Started
2. "/new/idea" — describes the idea, names the venture, answers 2 quick
   classification questions; a live industry preview calls
   POST /predict/industry as they type (debounced, read-only)
3. "/new/evidence" — one funding-readiness dimension per screen (problem
   clarity, customer pain evidence, market size evidence, product maturity,
   traction, team completeness, competitive differentiation, revenue model
   clarity), plus optional pricing/customer-count/geography details
4. "Review & Analyze" → POST /startups (creates the row) →
   POST /startups/{id}/analyze (starts the background pipeline, returns
   immediately) → navigate to "/startups/{id}/status"
5. AnalysisStatusPage subscribes via SSE (GET /analyses/{id}/events),
   showing real per-node progress (not a fake timer) — falls back to
   polling GET /analyses/{id} if SSE is unavailable
6. LangGraph pipeline runs: industry classification → venture positioning
   → funding readiness → success prediction → revenue estimate → market/
   competitor/persona/business-model analysis → customer segmentation →
   ranked actions → innovation surfacing → risk assessment → growth
   strategy → pitch deck → evidence confidence check → Judge synthesis
   → mentor synthesis → idea expansion → strategic opportunities →
   decision synthesis → causal reasoning → counterfactual simulation
   → persisted after every single node
7. The instant status flips to COMPLETED, the frontend navigates to
   "/analyses/{id}" (Reveal)
8. Reveal renders: Executive Command Center → Dashboard (3 gauges, radar,
   revenue bars, risk grid) → Mission Control (3 ranked actions) →
   Investor Review (decision badge + question/concern/evidence) →
   collapsed Deep Analysis → Continue Building (Re-analyze / Export PDF /
   History / Start another venture)
9. Export PDF: dynamically imports pdf-lib, builds a 6-page document from
   the exact same data already on screen
10. Re-analyze: routes back through AnalysisStatusPage (creates a NEW
    analysis row for the same startup, not a mutation of the old one)
11. History: pure localStorage read, self-healing on stale/404'd entries
```

---

## 9. Deployment

- **GitHub**: single repo, `main` branch. No branch protection rules verified/assumed beyond what CI enforces by running on every push/PR to `main`.
- **CI** (`.github/workflows/ci.yml`): 3 parallel jobs — `ml` (installs `ml/requirements.txt`, runs `pytest ml/tests`), `backend` (installs backend+ml deps, **trains a real industry classifier on a generated bootstrap corpus** so the API/orchestrator tests exercise a genuine artifact end to end — never a real production dataset — then runs `pytest` + `pytest tests/integration`), `frontend` (`npm ci && npm run test && npm run build`). No deploy step lives in CI itself — deployment is triggered separately by Render/Vercel's own GitHub integrations reacting to the same push.
- **Render** (backend + Postgres, `render.yaml` Blueprint): `buildCommand: pip install -r backend/requirements.txt`; `startCommand: cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` — **migrations run automatically on every deploy**, before the server starts serving. `healthCheckPath: /api/v1/health` (deliberately not `/system/status`, which 404s in production by design). Free-tier: the service spins down after inactivity — the first request after idle takes ~30s to cold-start (measured directly against the live backend this sprint).
- **Vercel** (frontend): `buildCommand: npm run build`, SPA rewrite (`"source": "/(.*)", "destination": "/index.html"`) so client-side routing works on a hard refresh of any deep link. Two live domains observed for this project: a per-deployment hash URL (changes every push, e.g. `ventureforge-kwi12uuwu-....vercel.app`) and a stable project alias (`ventureforge-ai-divyashrees09s-projects.vercel.app`) — **the CORS allowlist on the backend is configured for the stable alias, not the ephemeral per-deployment URL**, which is expected Vercel/Render behavior, not a misconfiguration (verified directly this sprint — see §10).
- **Environment variables**: `DATABASE_URL` (from Render's managed Postgres), `APP_ENV=production`, `API_V1_PREFIX=/api/v1`, `BACKEND_CORS_ORIGINS` (comma-separated, set manually to the real Vercel domain(s) — `sync: false` in `render.yaml`, i.e. not committed), `GEMINI_API_KEY` (optional — the system is fully functional without it, see §4), `GEMINI_MODEL=gemini-flash-latest`, `MODEL_DIR=../ml/models`.
- **Health checks**: `/api/v1/health` (always-on, trivial) is what Render actually polls; `/api/v1/system/status` (DB + migration + model + LLM diagnostics) is dev-only by design and is never the health-check target.

---

## 10. Testing

- **Backend**: `pytest` under `backend/tests/` — **724 tests, all passing** (as of this sprint's final run). Includes unit tests for every agent/ML-serving module and integration tests (`tests/integration`) exercising real API + real orchestrator + a real (bootstrap-trained) ML artifact.
- **Frontend**: Vitest + RTL, 37 files / 190 tests, **188 passing, 2 pre-existing failures** (confirmed unrelated to any recent change — see §7).
- **ML**: `pytest ml/tests` — covers feature engineering, preprocessing, and evaluation-metric helper correctness.
- **Integration**: `backend/tests/integration` runs the real LangGraph pipeline against a real (test) database and a real trained artifact, not mocks.
- **Playwright / live-browser verification** (used this sprint, not a permanent CI step): a real end-to-end run was driven against **the live production deployment** — landing page → idea submission → evidence questionnaire → analyze → SSE-driven status page → Reveal → PDF export → Re-analyze → History → refresh-persistence → mobile viewport (390×844). Results:

| Step | Result |
|---|---|
| Landing page load | 2,244ms |
| Full analysis completion (real Gemini calls) | 57,163ms |
| PDF export | 782ms, download triggered |
| Re-analyze (new analysis, same startup) | 59,295ms |
| History page load | 1,071ms |
| Refresh persistence (reload the Reveal URL directly) | 2,057ms, content persisted correctly |
| Mobile viewport render | clean, no layout breakage |
| Console errors | 4 — all harmless `/api/v1/system/status` 404s (dev-only endpoint, by design) |
| Page errors (uncaught exceptions) | **0** |
| Real API call results | `POST /startups` 201, `POST /analyze` 201×2, `GET /analyses/{id}` 200×many, `GET /taxonomy` 200, `GET /startups/{id}` 200 — zero unexpected failures |

Average per-endpoint response time (production, warm backend): `GET /analyses/{id}` ~513ms, `GET /startups/{id}` ~358ms, `GET /taxonomy` ~376ms, `POST /startups` 569ms, `POST /analyze` ~454ms, `POST /predict/industry` 2,202ms (a real Gemini-adjacent call the ML classifier still answers quickly, most of the 2.2s is TF-IDF+network round trip).

An earlier test run against the **wrong URL** (the ephemeral per-deployment hash domain) showed every API call failing on CORS — this was correctly diagnosed as a test-target mistake, not a real production bug, after confirming the stable project domain passes CORS cleanly and a full real analysis completes end to end.

---

## 11. Limitations

Stated honestly, no marketing language:

1. **No authentication/authorization layer anywhere.** Every endpoint, including reading any analysis by ID, is unauthenticated. Anyone with an analysis ID (or who guesses/enumerates one) can read it. Likely acceptable for the current hackathon/demo stage, but a real limitation if this were to hold genuinely private founder data.
2. **Render free-tier cold start** — the backend spins down after inactivity; the first request after idle takes ~30s. This is a hosting-tier limitation, not a code defect.
3. **Success predictor survivorship bias** — "operating" (unresolved) companies are excluded from training entirely; only resolved acquired/IPO/closed outcomes are used. A separate Cox survival model exists that could partially address this but is not integrated into serving.
4. **No investor-count or funding-round-type data** exists anywhere in the training data — a real, structural gap in what the success predictor can ever learn from.
5. **Positioning taxonomy coverage gaps remain.** Even after this week's additions, a description stuffed almost entirely with generic AI buzzwords ("AI-powered predictive analytics platform... automation... machine learning") can still out-score a more specific domain, because the scoring formula normalizes by each domain's own vocabulary size, and Enterprise AI's small vocabulary saturates faster. Verified directly; deliberately not "fixed" this sprint because changing the core scoring formula affects every existing domain's relative ranking — flagged as future work (§12), not silently patched under time pressure.
6. **Industry knowledge-pack resolution can still be influenced by incidental wording** in edge cases even after this week's confidence-ranking fix, if a founder's own description happens to use more vocabulary from an unrelated category than from their real one. The fix meaningfully narrowed this (verified against a reproduced regression case), but a keyword-count heuristic is inherently not a semantic understanding of the text.
7. **Venture retrieval / survival model are dormant or gated off by default** — real, evaluated, working components that are not part of the default user-facing experience.
8. **Frontend has 2 known-flaky pre-existing tests** (EventSource mock isolation across test files) — confirmed unrelated to any of this sprint's changes, not yet fixed.
9. **No caching layer, message queue, or Redis** — the entire runtime is React + FastAPI (with an in-process, single-instance SSE pub/sub) + Postgres. This means the SSE pub/sub does **not** work correctly if the backend is ever scaled to more than one process/instance (a subscriber connected to instance A would never see an event published from instance B) — a real horizontal-scaling limitation, not currently hit at this project's scale.
10. **Consumer vs. B2B industry-classification confusion is the dominant classifier error mode** (F1 0.687 for consumer, the weakest class) — generic "platform for X" language is genuinely ambiguous, not a bug to fix, a real limit of the training data's signal.

---

## 12. Future Improvements

Only realistic, concretely scoped ones:

1. **Add authentication** (even a simple API key or session model) before any real private-data use case, given finding #1 above.
2. **Integrate the Cox survival model** into a genuine Risk/Longevity agent, with clear product framing around its proxy-duration caveat, rather than leaving it fully dormant.
3. **Revisit the positioning-taxonomy scoring formula** (weighted-sum ratio → something less sensitive to vocabulary-size differences between domains) — a genuinely useful next step, deliberately deferred this sprint because it touches every existing domain's relative ranking and needs careful regression testing across the full taxonomy, not a same-day change.
4. **Move the SSE pub/sub to a shared store** (e.g. Redis pub/sub or Postgres `LISTEN`/`NOTIFY`) if/when the backend is ever scaled beyond one instance.
5. **Enable `venture_retrieval` by default** once its 20-40s first-load cost is addressed (e.g. a warm-start on deploy, or a background pre-load), since it's already evaluated and working.
6. **Fix the 2 pre-existing flaky frontend tests** (EventSource mock isolation) — low-risk, just not yet done.

---

## 13. Viva Preparation — FAQ

### Architecture

**Q1. What's the high-level architecture in one sentence?**
React SPA → FastAPI REST/SSE → PostgreSQL, with a background-thread-driven LangGraph pipeline doing the actual analysis (ML models + deterministic agents + optional Gemini calls) synthesized by a deterministic Judge into a founder report.

**Q2. Why is the analysis run in a background thread instead of returning it synchronously from the POST request?**
A real analysis takes 30-90+ seconds (multiple ML inferences plus optional LLM calls). Holding an HTTP request open that long is fragile (proxy timeouts, no progress feedback). `POST /analyze` returns immediately with the row marked `RUNNING`; the frontend gets live progress via SSE instead.

**Q3. Why LangGraph specifically, rather than just calling functions in sequence?**
It gives an explicit, inspectable state graph (nodes/edges), a single typed state object every node reads/writes, and built-in `.stream()` support for per-node progress — which is exactly what the SSE progress feature needs. The graph itself, though, is almost entirely linear; LangGraph's cyclic/branching power is barely used (one conditional branch total).

**Q4. Is the orchestrator graph actually cyclic or does it have loops?**
No loops. Strictly linear except the single `input_validation` → (valid/invalid) branch at the very start.

**Q5. What's `recursion_limit=100` for and why 100?**
LangGraph enforces a max node-execution count to prevent runaway graphs. The default (25) was hit once the node count grew; 100 is deliberate headroom, not a precisely tuned number.

**Q6. What happens if the backend crashes mid-analysis?**
The `analyses` row is left in `RUNNING` status (not automatically marked `FAILED`) since the persistence writes happen after each completed node, not via a crash handler. This is a real gap — there's no watchdog that detects and cleans up an orphaned `RUNNING` row from a crashed process. (Honest answer: not handled.)

**Q7. How does the frontend know when an analysis is done?**
Primarily via SSE (`GET /analyses/{id}/events`, native `EventSource`), which re-emits on every real node completion; falls back to polling `GET /analyses/{id}` if SSE isn't available.

**Q8. What's the single most important architectural decision in this project?**
Keeping ML/deterministic scoring and LLM narrative strictly separate — every score a user sees traces to a trained model or a versioned rubric, never to an LLM's own judgment, and the system is fully functional with zero LLM calls.

### Frontend

**Q9. Why no Redux/Zustand?**
Deliberate choice — the app's real shared state is small (one in-progress draft, a theme, two nav-registration providers), and hooks + one Context cover it without the overhead of a global store.

**Q10. How does a page survive a hard refresh mid-wizard?**
`NewAnalysisContext` auto-persists the in-progress idea/evidence draft to `localStorage` on every change.

**Q11. Why pdf-lib instead of jsPDF?**
jsPDF's bundle statically pulls in html2canvas/dompurify/canvg regardless of whether they're used, adding ~260KB gzipped for a feature most visitors never touch. pdf-lib doesn't have that cost and is dynamically imported only on click.

**Q12. Why Recharts and not D3/Chart.js?**
Not independently justified in the docs beyond "it's what's used" — an honest answer here is that this was a team choice, not something with a documented comparison.

**Q13. How is the 404 page handled and why did it need adding?**
A catch-all `*` route renders `NotFoundPage`. Before this sprint, an unmatched URL rendered nothing — React Router had no matching route element, so the page was completely blank with no way back.

**Q14. What was the "[object Object]" bug and how was it found/fixed?**
Found via deliberate break-testing (an invalid startup ID hit a FastAPI 422 response, whose `detail` is an array of Pydantic error objects). `useAsync`'s error-message logic did `String(err.detail ?? err.message)`, and `String()` on an array of objects produces the literal text `"[object Object]"`. Fixed to only trust `detail` when it's actually a string.

**Q15. How does the History page avoid showing permanently-broken links?**
`AnalysisResultPage` watches for a 404 from `getAnalysis` and calls `deleteHistoryEntry` automatically — a stale/deleted analysis ID self-prunes the next time anyone tries to view it.

**Q16. Is the frontend accessible?**
ESLint's `jsx-a11y` recommended rule set runs as errors (not warnings) in this project's config, and `jest-axe` assertions exist in the test suite — accessibility is enforced at the tooling level, not just aspirational.

### Backend

**Q17. Why FastAPI over Django/Flask?**
Not explicitly documented in the repo — inference: Pydantic-native request/response validation (used extensively, including the `allow_inf_nan=False` NaN-rejection pattern) and native async/SSE support are a natural fit for this project's shape.

**Q18. Why is the DB driver synchronous (`psycopg2-binary`) if FastAPI supports async?**
The codebase doesn't document this choice explicitly — the background-thread execution model for analyses (not `asyncio` tasks) is consistent with a synchronous-session design throughout.

**Q19. What happens on a rapid double-click of "Analyze"?**
The second `INSERT` violates the partial unique index (`ux_analyses_one_running_per_startup`), Postgres raises `IntegrityError`, and the service layer catches it and returns the already-running analysis instead of erroring or creating a duplicate.

**Q20. Why not just check "does a RUNNING analysis exist" before inserting, in application code?**
That's a check-then-act pattern with a real race window under genuine concurrency — two requests could both pass the check before either inserts. The DB-level partial unique index is race-proof by construction.

**Q21. Why a partial index and not a plain `UNIQUE(startup_id)`?**
A blanket unique constraint would make the *second* analysis ever run for a startup fail outright, breaking Re-analyze. Scoping to `WHERE status = 'RUNNING'` makes historical rows invisible to the constraint.

**Q22. What's the difference between `/health` and `/system/status`?**
`/health` is trivial, always-on, no DB touch — the actual Render health-check target. `/system/status` does real diagnostic work (DB ping, migration-head check, model load state) but 404s in production by design, so it can never be mistaken for the health check and can't leak internal state to the public internet.

**Q23. How are NaN/Infinity payloads handled?**
Several float fields explicitly set `allow_inf_nan=False`, which makes Pydantic reject them with a 422. A custom exception handler additionally sanitizes any NaN/Infinity before echoing the rejected value back in the error body — otherwise Starlette's default JSON encoder would crash trying to serialize it, silently turning a clean 422 into an unrelated 500.

**Q24. Does `POST /predict/industry` run a second, different classifier?**
No — it calls the exact same `predict_industry`/`extract_deployment_sectors` functions the real analysis pipeline uses, explicitly to avoid a second prediction path that could drift out of sync.

### Database

**Q25. How many tables are there?**
Two: `startups` and `analyses`.

**Q26. Why so many JSONB columns instead of normalized tables?**
The agent outputs (judge summary, market intelligence, mentor interpretation, etc.) are large, semi-structured, and don't benefit from relational decomposition for this project's access patterns (always read/written as a whole per analysis). JSONB gives indexable, binary JSON storage without forcing a rigid schema on data whose shape evolves as new agents are added.

**Q27. How many migrations exist and are they reversible?**
11, all linear (no branches), each with a real `downgrade()`.

**Q28. What's the FK relationship?**
`analyses.startup_id → startups.id`, `ON DELETE CASCADE` — deleting a startup deletes its analyses.

**Q29. Is there a formal justification for choosing PostgreSQL over, say, MongoDB (given how JSONB-heavy the schema is)?**
No documented comparison exists in the repo. Honest answer: Postgres was the starting choice from migration 0001 and the JSONB-heavy schema grew around that, not the other way around.

### ML

**Q30. How many ML models are actually deployed?**
Two live on every analysis (industry classifier, success predictor) plus one live-conditional (customer segmentation, only when the caller supplies RFM data). A survival model is trained but dormant; two retrieval components are live but off by default.

**Q31. What algorithm does the industry classifier use and why?**
TF-IDF (word+char n-grams) + logistic regression, chosen because it beat several sentence-transformer embedding variants on cross-validated macro-F1 (0.775 vs. 0.605–0.735) — a concrete, measured result, not an assumption that embeddings are always better.

**Q32. What's the success predictor's real test ROC-AUC?**
0.8384, with a well-calibrated 0.0148 ECE and F1-optimal operating threshold 0.40.

**Q33. What was the train/serve skew bug and how was it proven, not just assumed?**
Three features (funding-round-date-derived) were always missing at serving time because the intake form never collects those dates. A controlled experiment wiped those same fields on the held-out test set to simulate real serving conditions — served ROC-AUC measurably improved after removing them (0.812→0.827), proving the fix rather than assuming it.

**Q34. Why exclude "operating" companies from the success predictor's training data?**
Their outcome is genuinely unresolved (could still succeed or fail) — including them as either class would be a label-quality problem, not just noise. The tradeoff (survivorship bias from only training on resolved outcomes) is documented as a real, unaddressed limitation, not hidden.

**Q35. Is the venture-positioning taxonomy machine learning?**
No — it's a deterministic, hand-curated keyword+phrase weighted-scoring system with zero training and zero dataset. This distinction is deliberately preserved in this document because it's easy to assume everything labeled "AI" in this project used a trained model.

**Q36. Why does "Enterprise AI" sometimes still win even after adding Robotics/Logistics/Retail domains?**
The scoring formula normalizes each domain's score by that domain's own maximum possible weight. Enterprise AI's vocabulary is small, so it reaches a high ratio quickly on generic AI-buzzword text; a richer domain's ratio grows more slowly even with more real matched concepts. Verified directly with an adversarial (buzzword-stuffed) test description; realistic pitches are unaffected. Deliberately not "fixed" further this sprint — flagged as future work since it touches every domain's relative ranking.

**Q37. What's permutation importance and why is it labeled "global" not "local"?**
It measures how much a model's overall performance drops when one feature's values are shuffled — a property of the model across the whole dataset, not a specific prediction's real contributing factors. The genuinely per-prediction explanation is a separate function (`local_success_explainer`), and the API response labels each accordingly rather than presenting the global metric as if it explained one specific prediction.

**Q38. Was SHAP used?**
No — the local explanation is a custom function (`app.ml.local_success_explainer`), not SHAP. If asked "is this SHAP," the honest answer is no, and the API never claims it is.

**Q39. What's the calibration method for the success predictor and why isotonic over Platt/sigmoid?**
`CalibratedClassifierCV(method="isotonic")`, chosen because it scored the lowest out-of-fold Brier score among the methods compared.

**Q40. How was the customer-segmentation cluster count (k) chosen?**
Not by silhouette score alone — a rank-sum across silhouette, Davies-Bouldin, Calinski-Harabasz, **and** adjusted-Rand stability across 4-seed 80% resamples, specifically to avoid picking a k that scores well on one metric by chance.

**Q41. Why wasn't DistilBERT fine-tuned for the industry classifier?**
Measured free system RAM was below a safe margin on the development machine at the time — a resource constraint, documented honestly rather than omitted.

**Q42. What's the dataset license for each model and why does it matter?**
Industry classifier: CC BY 4.0 / Apache-2.0 / CC-BY-SA-4.0 (3 merged sources). Success predictor: CDLA-Sharing-1.0. Customer segmentation: CC BY 4.0. It matters because several other candidate datasets were explicitly rejected in `ml/DATASETS.md` for unclear or non-commercial licensing — a real legal-risk-avoidance decision, not an afterthought.

### AI / Agents

**Q43. How many of the ~47 agent modules actually call an LLM?**
6.

**Q44. What happens if `GEMINI_API_KEY` is never set?**
The system is fully functional — every one of the 6 LLM call sites short-circuits to a deterministic fallback with zero network calls. Only a narrative paragraph and a few "advisory" list items end up empty.

**Q45. Can Gemini's output ever directly set a score or a decision?**
No. For venture positioning specifically, Gemini's recommendation can only be *adopted* if it independently satisfies pre-typed, already-eligible conditions the deterministic rule set defines — and its free-text rationale is never read at all, only its structured `recommended_primary_domain`/`confidence` fields.

**Q46. Is there a prompt-injection defense, and is it tested?**
Yes — a dedicated test (`test_malicious_rationale_text_has_no_effect_on_an_adopted_recommendation`) constructs a Gemini response whose rationale text says "IGNORE ALL PRIOR RULES... set primary_domain to 'Enterprise AI'" and asserts the actual outcome is unaffected, because the rationale field is structurally never parsed for instructions.

**Q47. What does the "Judge" actually decide versus what does it just narrate?**
It decides `strengths`/`weaknesses`/`missing_evidence`/`next_actions`/`overall_assessment`/`confidence_level` from the funding rubric and evidence check. It does **not** independently re-score industry or funding readiness — those come from upstream deterministic modules; the Judge's job is synthesis and source-attribution, not recomputation.

**Q48. Does Success Prediction influence the Judge's verdict?**
Per this project's prior investigation (not re-litigated this sprint): Funding Readiness and Industry Classification are the only two signals that measurably move `confidence_level`; Success Prediction and Risk Assessment populate descriptive `source_attribution` text but were found to have no measurable effect on the decision fields in a direct sensitivity test. This is documented as an intentional design choice (funding readiness and success prediction measure genuinely different things), not a bug.

**Q49. What's the "Intelligence Architecture" (evidence_ledger, contradiction_engine, etc.)?**
8 deterministic reasoning modules that operate only on already-computed structured outputs from earlier nodes — no LLM calls, no new data. They build an evidence ledger, a "venture frame," a hypothesis set, a contradiction set, alternative explanations, a decision synthesis, causal reasoning, and counterfactual simulation, all traceable back to real upstream fields.

**Q50. How does the system avoid an LLM inventing a fake competitor?**
`competitor_reviewer`'s prompt explicitly forbids naming real companies — it's only invoked when the founder named zero competitors themselves, and its output is category-level, not specific company names.

### Deployment

**Q51. Where is the app actually hosted?**
Backend + Postgres on Render, frontend on Vercel, connected via each platform's own GitHub integration (no deploy step lives in this project's CI).

**Q52. What triggers a production deploy?**
A push to `main` — both Render and Vercel auto-deploy via their GitHub App integrations. Verified directly this sprint: pushing commit `759b8a3` produced real GitHub Deployment API records and a live, working production site within seconds.

**Q53. Are migrations applied automatically?**
Yes — Render's `startCommand` runs `alembic upgrade head` before starting uvicorn, on every deploy.

**Q54. Why does the backend take ~30 seconds to respond to the first request sometimes?**
Render's free tier spins the service down after inactivity; the first request after idle pays a cold-start cost. Measured directly at ~31 seconds this sprint. This is a hosting-tier characteristic, not an application bug.

**Q55. There were two different `.vercel.app` URLs found during testing — which is the real one, and how was that determined?**
Vercel provisions both a stable project-level alias and a unique per-deployment hash URL that changes on every push. The stable alias (`ventureforge-ai-divyashrees09s-projects.vercel.app`) is confirmed correct because its served JS bundle hash exactly matches the per-deployment URL's bundle. The backend's CORS allowlist is configured for the stable alias, so testing against the ephemeral hash URL produces CORS errors that look like a bug but aren't — this was diagnosed directly (a CORS preflight request against the stable origin succeeded) rather than reported as a false production defect.

**Q56. What environment variables does production need, and which are secret?**
`DATABASE_URL` (from Render's managed DB, not manually set), `APP_ENV`, `API_V1_PREFIX`, `BACKEND_CORS_ORIGINS` (manually set, not committed), `GEMINI_API_KEY` (optional, secret), `GEMINI_MODEL`, `MODEL_DIR`.

### Security

**Q57. Is there authentication?**
No. Every endpoint is unauthenticated. This is disclosed as a real, current limitation (§11), not hidden.

**Q58. How are secrets kept out of the repo?**
`.gitignore` excludes `.env`/`.env.*` (with an explicit exception only for `.env.example`); verified via `git log --all --diff-filter=A` that no real `.env` was ever committed at any point in history. Only placeholder-valued `.env.example` files are tracked.

**Q59. Is the CORS configuration safe?**
`allow_credentials` is not set (defaults to `False`), and `allow_origins` is an explicit comma-separated allowlist from an environment variable — not a wildcard `*` combined with credentials, which would be the actual vulnerable combination.

**Q60. Is user input validated against injection attacks?**
All database access goes through SQLAlchemy's ORM with bound parameters; the only raw `text()` SQL calls in the codebase are static strings (`SELECT 1`, an Alembic version check) with zero user-input interpolation — verified directly, not assumed.

**Q61. What about NaN/Infinity injection as a denial-of-service vector?**
Explicitly guarded — several numeric fields set `allow_inf_nan=False`, rejecting such payloads with a clean 422 rather than risking a downstream crash (this was itself the subject of a real bug fix: the naive rejection path used to crash trying to echo the rejected value, until the custom sanitizing handler was added).

**Q62. Is there rate limiting?**
Not found in the codebase — a real, undisclosed-until-now gap if asked directly. Honest answer: no rate limiting exists at the application layer.

### Testing

**Q63. How many backend tests exist and do they all pass?**
724, all passing as of this sprint's final run.

**Q64. How many frontend tests, and are all passing?**
190 across 37 files; 188 passing, 2 pre-existing failures confirmed unrelated to recent changes (an EventSource mock-isolation issue reproduced identically with the relevant changes stashed out).

**Q65. Does CI train a real model or use a mock?**
A real model — CI trains a genuine (bootstrap-corpus) industry classifier so integration tests exercise a real artifact, explicitly never a real production dataset.

**Q66. Was the live production deployment actually tested, or just assumed working from local tests?**
Actually tested — a real Playwright run drove the live production URL through the full user journey (idea → evidence → analyze → SSE progress → Reveal → PDF → Re-analyze → History → refresh → mobile), with zero uncaught page errors and only expected (dev-endpoint 404) console noise.

**Q67. How was the CORS false-alarm distinguished from a real bug during testing?**
By testing a CORS preflight request directly against the two different candidate origins with `curl -X OPTIONS` and comparing the `access-control-allow-origin` response header — the stable domain passed, the ephemeral one didn't, which is expected platform behavior, not a defect requiring a fix.

### Software Engineering

**Q68. What's the git commit history strategy for this project's recent sprints?**
Logically-separated commits by subject area (e.g. one for the ML train/serve fix, one for the race-condition fix, one for frontend safety fixes, one for the taxonomy/knowledge-pack fix) rather than one giant commit — chosen for reviewability and the ability to revert one concern without reverting unrelated ones.

**Q69. How is a regression caught before it ships, concretely (not hypothetically)?**
During this sprint's taxonomy work, a first version of the resolver fix was regression-tested against 10 real end-to-end analyses; two of them (ClimateTech, AgriTech) resolved to the wrong knowledge pack because the coarse classifier label "industrials" substring-matched the hardware category's "industrial" keyword. This was found, root-caused, fixed, covered with a new regression test, and re-verified — before the change was committed.

**Q70. What's the project's stance on "do not refactor working code"?**
Explicit and repeatedly instructed across sprints — changes are scoped to proven defects only, with root-cause evidence required before any change, and explicit permission to defer a real-but-risky fix (e.g. the taxonomy scoring-formula limitation) rather than force it under time pressure.

**Q71. How are AI-generated Playwright/E2E scripts kept from producing false results?**
By cross-checking surprising results directly rather than trusting the first run — e.g. the CORS "production is broken" finding was independently re-verified with a raw `curl` preflight request before being written into any report, and turned out to be a wrong-URL test artifact, not a real defect.

### Hackathon Questions

**Q72. What's the single most technically interesting thing you built?**
The train/serve skew fix for the success predictor — proving via a controlled, serving-condition-simulating experiment (not assumption) that removing 3 permanently-fabricated features *improved* real-world accuracy, even though it made the "full-info" offline metric look worse.

**Q73. What would you do differently with another week?**
Fix the positioning-taxonomy scoring formula's vocabulary-size sensitivity (§11/§12) and add basic authentication — both identified, both deliberately deferred as too risky to force in the time available.

**Q74. What's the biggest risk in this system if it went to real users tomorrow?**
No authentication on any endpoint — anyone with (or able to guess) an analysis ID can read it.

**Q75. How do you know the AI isn't just making things up?**
Every claim in a founder report is tagged one of 5 categories (`evidence`/`inference`/`ai_recommendation`/`market_assumption`/`experiment_suggestion`), enforced by an assertion in the composer code — and two dedicated deterministic auditors (`consistency_audit.py`, `knowledge_audit.py`) check the assembled report post-hoc for unsupported claims.

**Q76. What happens if two people click "Analyze" on the same startup at the same time?**
A database-level partial unique index guarantees only one analysis actually runs; the second request gets back the already-running one instead of creating a duplicate. Verified under real concurrent load (10 simultaneous requests → 1 analysis) in a prior sprint.

**Q77. Why does the funding-readiness score sometimes disagree with the success-probability score?**
By design — they measure different things (a rubric over the founder's own answers vs. a historical-pattern comparison against Crunchbase outcomes), and this project's Judge deliberately narrates them separately rather than blending them into one misleading number.

**Q78. Is any part of this a black box you can't explain?**
The LLM narrative layer (6 modules) is the one place output isn't fully deterministic/reproducible — but every one of those 6 is additive-only and never changes a score or decision field, so the "black box" surface is deliberately confined to narrative text, not to any number a founder relies on.

### Judge Questions (harder/adversarial)

**Q79. If your success predictor is trained on Crunchbase data ending well before "now," how do you know it still applies to a startup founded today?**
We don't fully — this is an honest limitation. The model reflects historical patterns in resolved Crunchbase outcomes; it has no mechanism to detect a genuinely novel market shift. This is why the founder-facing framing is a hedged "pattern signal," never a verdict.

**Q80. Your industry classifier is 79% accurate — isn't that quite mediocre for a headline feature?**
It's the real, measured number, not inflated — and the system compensates by exposing `is_uncertain`/`is_low_confidence` and top-3 alternatives rather than presenting one label as certain. Top-2 accuracy is 96%, which is why alternatives are always available.

**Q81. You rejected a 34-class sub-industry taxonomy because CV macro-F1 collapsed to 0.44 — doesn't that mean your data just isn't rich enough for real granularity, and the whole classifier is fundamentally coarse?**
Yes, and that's exactly why the separate, non-ML positioning taxonomy exists — to give a founder-facing granular identity without pretending the trained classifier itself has that resolution.

**Q82. Explain, precisely, why a partial unique index is safe under concurrent transactions but a "SELECT then INSERT" check in Python is not.**
Two concurrent Python requests can both execute the SELECT before either commits an INSERT — neither sees the other's not-yet-committed row, so both proceed to insert, creating two RUNNING rows. A unique index is enforced by the database at INSERT time itself, atomically, regardless of what either transaction "saw" beforehand — the second INSERT is rejected by Postgres directly, not by application logic that could itself race.

**Q83. Your CORS "bug" during testing turned out to be a test methodology error. How do we know your other findings this sprint aren't the same kind of mistake?**
Every other finding in this sprint's regression testing was reproduced against the correct, verified production URL, cross-checked with direct `curl` calls where relevant (e.g. the CORS preflight check), and — for the taxonomy fix specifically — caught its own regression (ClimateTech/AgriTech) via a second full regression pass before shipping, not just a first green run.

**Q84. If Gemini is optional, why include it at all — doesn't that add complexity for a feature you claim doesn't matter?**
It adds narrative fluency and a few advisory suggestions a purely deterministic system can't produce (e.g. plausible competitor categories when the founder named none) — genuinely useful, just never load-bearing for a score or decision.

**Q85. Your database schema is JSONB-heavy with no documented rationale — isn't that just poor schema design?**
It's a defensible tradeoff (semi-structured, evolving agent outputs that don't benefit from rigid relational decomposition) but the honest answer is that it was never formally justified against alternatives in writing — that's a real documentation gap, not a design defect being denied.

**Q86. What's stopping someone from enumerating all analysis IDs and reading everyone's data?**
UUIDs are not sequential/enumerable, which raises the practical bar, but this is not the same as real access control — an attacker who obtains one real ID (e.g. via a shared link, log, or referrer header) can read that analysis freely. This is the same "no auth" limitation as Q57/Q86, stated concretely.

**Q87. Walk me through what happens, step by step, if the Gemini API is down mid-analysis.**
Whichever of the 6 optional call sites is about to fire catches the resulting exception (`LLMUnavailable` or a generic exception, both handled identically), logs it, and returns its deterministic fallback value/empty list — the orchestrator node completes normally, the pipeline proceeds to the next node, and the final analysis completes with `status: COMPLETED`, just with an empty narrative/advisory field.

### Additional Architecture/Engineering Depth

**Q88. Why is `resolve_venture_positioning` run right after industry classification instead of at the end with everything else?**
Downstream nodes (`estimate_revenue`, `analyze_competitors`) key off `venture_positioning.primary_domain` for category-specific reasoning — it has to exist before they run, not after.

**Q89. What's the actual mechanism the SSE endpoint uses to detect new events — polling the database?**
No — an in-process pub/sub queue (`analysis_events.py`) that the orchestrator's persistence step publishes to directly after every node; the SSE handler subscribes to that queue rather than polling the database on an interval.

**Q90. Does the in-process SSE pub/sub work if you deploy multiple backend instances?**
No — this is a real, disclosed limitation (§11). A subscriber connected to instance A never sees an event published by instance B. Not currently hit because the deployment is single-instance.

**Q91. How do you know the taxonomy/knowledge-pack fix didn't just move the bug somewhere else?**
By running the exact same 10-category regression suite twice — once after the first fix attempt (which surfaced the ClimateTech/AgriTech regression), and again after the corrected fix — and independently re-verifying with direct unit-level reproduction of the specific failing case before considering it resolved.

**Q92. What's the difference between `is_uncertain` and `is_low_confidence` on the industry prediction?**
`is_uncertain` fires on any of three independent conditions (no TF-IDF vocabulary match, confidence below a floor, or a narrow top-1/top-2 margin). `is_low_confidence` is a separate, single abstention-threshold gate used for a different downstream decision (whether to show the prediction as a confident recommendation at all). They're deliberately distinct signals, not aliases.

**Q93. If a founder submits a description in a language other than English, what happens?**
Not explicitly handled — the industry classifier is English-only by training data composition (a stated limitation), so a non-English description would likely produce a low-confidence or effectively random classification rather than a clean error. Honest answer: not tested, not guarded against explicitly.

**Q94. How does the "review & analyze" step differ from a normal wizard "continue"?**
It's the terminal action of the evidence wizard — it triggers the actual `POST /startups` + `POST /analyze` calls, whereas every other "Continue" just advances local wizard state.

**Q95. What's stored in `workflow_trace` and what's it for?**
A JSONB field on `analyses` recording the pipeline's own execution trace — used for debugging/explainability rather than shown directly to a founder.

**Q96. Why does `AnalysisStatusPage` fall back to polling if SSE is the primary mechanism?**
Some network environments/proxies don't handle long-lived SSE connections well; the polling fallback (re-fetching `GET /analyses/{id}` on an interval) guarantees progress is still eventually visible even if the SSE channel silently fails.

**Q97. What guarantees that `engineer_features()` can't drift between training and serving for the success predictor?**
It's the same literal function, imported from `ml/src/features/success_features.py` by both the training script and the backend's serving wrapper — a single source of truth by construction, not a convention that could be violated by editing one copy and forgetting the other.

**Q98. How does the founder report avoid repeating the same fact in five different sections?**
`insights.ts` (frontend) and the founder-report composer's own information architecture (backend) both derive certain recurring facts (biggest risk, strongest signal) exactly once and have every other section reference them by id/anchor rather than re-deriving or restating the sentence.

**Q99. What's the honest answer if a judge asks "is this actually AI or just a form with some Python around it"?**
Both, precisely: two real trained ML models (with measured, reported metrics) run on every analysis; a working, prompt-injection-resistant LLM integration exists and is used for 6 specific advisory purposes; and a deliberately large portion of the "intelligence" is versioned, deterministic, explainable rule-based logic — because that's the more defensible choice wherever no real trained-model-quality dataset existed. The honest framing is "ML + deterministic reasoning + optional LLM," not "AI does everything."

**Q100. If you had to defend one number in this entire project under hostile questioning, which would you pick and why?**
The success predictor's real, current test ROC-AUC of 0.8384 — because it's the one metric in the project backed by a full, documented chain: a licensed dataset with disclosed exclusions, a controlled experiment that empirically justified a feature-removal decision (not a guess), a fair train/test split, and a serving path proven to use the identical feature-engineering function as training.

---

*End of PROJECT_TECHNICAL_GUIDE.md.*
