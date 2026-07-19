# Architecture

Reflects the Student 1 foundation plus the additive Student 3 vertical slice: industry
classification, funding readiness, segmentation fallback, deterministic innovation/risk/growth/
pitch planning, action ranking, and Judge Agent synthesis. Student 2 modules remain optional
extension points and are not required by this flow.

## System Overview

```
React (frontend) --HTTP/JSON--> FastAPI (backend)
                                     │
                                     ▼
                    LangGraph Orchestrator (backend/app/agents/orchestrator.py)
                                     │
        ┌────────────────┬──────────┴──────────┬─────────────────┐
        ▼                ▼                     ▼                 ▼
  Input Validation  Industry Classifier   Funding Readiness   PostgreSQL
  (deterministic)   (backend/app/ml,      Rubric (deterministic, (startups, analyses)
                     trained sklearn       backend/app/ml/
                     pipeline)             funding_readiness.py)
        │                │                     │
        └────────────────┴─────────┬───────────┘
                                    ▼
                        Evidence/Confidence Check
                                    ▼
                              Judge Agent (deterministic)
                                    ▼
                              Persistence -> Final Response
```

No external LLM API is *required* anywhere in this path — see "Optional LLM Layer" below for the
one place a call can happen, and only if explicitly configured.

## Request Flow

1. `POST /api/v1/startups` — frontend submits name, description, and optional funding-readiness
   answers. `analysis_service.create_startup` persists a `Startup` row.
2. `POST /api/v1/startups/{id}/analyze` — `analysis_service.run_analysis_for_startup` creates a
   `PENDING` `Analysis` row, then calls `agents/orchestrator.run_pipeline`.
3. The orchestrator runs synchronously (see "Multi-Agent Flow") and its `persist_fn` closure
   writes the final industry prediction, funding assessment, Judge summary, and trace back onto
   the same `Analysis` row before the HTTP response is returned.
4. `GET /api/v1/analyses/{id}` — used both by the immediate response and by a page reload; both
   read the same persisted Postgres row, so a reload shows identical results.

## Multi-Agent Flow

Student 3 extends the deterministic flow with additive planning nodes. No external API call is
required for either the Student 1 foundation or Student 3 outputs:

```
input_validation ──(invalid)──► invalid_input ──┐
       │ (valid)                                │
       ▼                                        │
industry_classification                         │
       ▼                                        │
funding_readiness                                │
       ▼                                        │
evidence_confidence_check                        │
       ▼                                        │
     judge                                        │
       ▼                                        │
   persistence ◄─────────────────────────────────┘
       ▼
 final_response
```

- **input_validation**: rejects a missing name or a description under 10 characters; routes
  straight to `invalid_input` (which marks the run `FAILED`) rather than running any ML node.
- **industry_classification**: calls the trained TF-IDF + Logistic Regression pipeline
  (`backend/app/ml/predictor.py`). If no artifact is trained yet, this degrades to
  `industry_prediction: null` rather than raising — a missing model is not the same failure class
  as invalid input.
- **funding_readiness**: calls the deterministic rubric (`backend/app/ml/funding_readiness.py`).
- **customer_segmentation**: returns an explicitly labelled deterministic startup-buyer segment
  fallback from model/rubric evidence. It is not presented as a live transaction-data cluster.
- **recommendation_ranking**, **innovation**, **risk_assessment**, **growth_strategy**, and
  **pitch_deck**: versioned deterministic planning outputs grounded in submitted evidence; they
  label missing revenue, customer, funding, legal, and market claims as unknown/evidence required.
- **evidence_confidence_check**: flags low industry-confidence (<0.35) and surfaces how many
  funding dimensions were left unanswered.
- **judge**: deterministic synthesis (`backend/app/agents/judge.py`) — reformats the two upstream
  outputs into strengths/weaknesses/next actions/confidence, and never invents a fact not present
  in either upstream output.
- **persistence**: the single place that finalizes run status (`COMPLETED` unless something
  upstream set `FAILED`) and writes the `Analysis` row.
- **final_response**: formats the trace; does not change status.

State is a `TypedDict` (`backend/app/agents/state.py`); nodes never import each other directly —
only `orchestrator.py` wires them.

## Optional LLM Layer

Every node in the Multi-Agent Flow above is deterministic Python/scikit-learn — no network
dependency, no API key required to run the app or its test suite. `backend/app/ai/` adds one
optional, additive step: after `judge.synthesize()` produces its fully deterministic
`judge_summary`, the orchestrator's `_try_llm_narrative` (in `orchestrator.py`) calls
`app.ai.factory.get_llm_provider()`. That returns `None` unless `GEMINI_API_KEY` is set, in which
case the deterministic summary is returned completely unmodified.

```
backend/app/ai/
├── base.py             — LLMProvider Protocol + LLMUnavailable exception (the only two things
│                          the rest of the app imports from this package)
├── schemas.py             — NarrativeContext (input, facts-only) / NarrativeEnhancement (output,
│                             no field for industry/confidence/score — nothing to override)
├── guardrails.py             — prompt construction; delimits user text, instructs the model to
│                                treat it as data not instructions
├── gemini_provider.py           — the only concrete implementation; every failure mode (timeout,
│                                  HTTP error, malformed JSON, schema violation) raises
│                                  LLMUnavailable, never propagates a raw exception
└── factory.py                     — returns a provider or None based on Settings; nothing else in
                                      the codebase imports gemini_provider.py directly
```

If a provider is configured, its output is merged into `judge_summary["llm_narrative"]` as a
*separate, additional* field — `strengths`, `weaknesses`, `confidence_level`, and everything else
the deterministic Judge Agent already produced are untouched. Any exception from the provider
(including one this codebase didn't anticipate) is caught in `_try_llm_narrative` and logged, and
the pipeline proceeds exactly as if no provider were configured.

## ML Flow

```
ml/data/raw (real YC dataset, or generated bootstrap corpus as a fallback) → ml/src/preprocessing
    → ml/src/features → ml/src/training → ml/models/industry_classifier/v2/ (joblib + metadata.json)
         │
         ▼
backend/app/ml/predictor.py (loads once, cached; serves predict_industry())
```

Training/evaluation never runs inside the FastAPI request path. See
[ml/README.md](../ml/README.md) and [ml/DATASETS.md](../ml/DATASETS.md) for the dataset honesty
caveat this pipeline currently operates under (no verified real dataset was available in the
development environment — see that document before trusting any accuracy figure).

## Module Layout

```
backend/app/
├── main.py             — FastAPI app + CORS + database-unavailable exception handler
├── core/config.py        — settings (env vars)
├── api/v1/                 — routers: health, startups, analyses, models_status
├── database/                 — engine/session + cross-backend JSON/UUID column types
├── models/                     — SQLAlchemy ORM: Startup, Analysis
├── schemas/                      — Pydantic request/response models
├── services/                       — analysis_service.py (business logic; routers call this)
├── agents/                           — state.py, nodes.py, judge.py, student3.py, orchestrator.py
├── ml/                                 — funding_readiness.py, predictor.py
└── ai/                                   — optional LLM layer (see "Optional LLM Layer" above)
```

Import direction: `api → services → {agents, database, ml}`. The one exception is
`backend/app/ml/predictor.py` importing `ml.src.explainability` directly (the `ml/` package lives
alongside `backend/`, not inside it — see that file's module docstring for why).

## Extension Points (Student 2 / Student 3)

These are additive extension points, not places to modify Student 1's existing nodes, schemas, or
tables. Everything below has been verified to accept new keys/nodes without touching existing
code paths.

**Adding a new orchestrator node** (Student 2: success prediction, revenue estimation, market
intelligence, competitor analysis, customer persona, business model — Student 3: customer
segmentation, innovation, risk, growth, pitch):
1. Write a pure node function in a new file (mirror `backend/app/agents/nodes.py`'s shape: takes
   `OrchestratorState`, returns only the keys it sets, e.g. `{"my_result": ..., "trace": [...]}`).
   `OrchestratorState` (`state.py`) is `total=False`, so adding a new key never breaks existing
   nodes that don't reference it.
2. Register it in `build_graph()` (`orchestrator.py`) between `funding_readiness` and `judge` (or
   wherever it logically belongs) via `graph.add_node(...)` and `graph.add_edge(...)` — do not
   edit `input_validation`, `industry_classification`, `funding_readiness`, or `judge` themselves.
3. If the Judge Agent should reference the new output, extend `judge.synthesize`'s parameters
   *additively* (new optional argument with a default), not by changing its existing return keys.
   It must keep never inventing a fact not present in an upstream output — the same rule your new
   node's output must follow.
4. If the result needs its own database column, add a new nullable column via a new Alembic
   migration (`alembic revision`) — never edit `0001_initial.py` in place.
5. Add a frontend results section using `frontend/src/components/results/Section.tsx` — a plain,
   reusable wrapper (title + data-source badge) that every section in
   `frontend/src/components/results/AnalysisResult.tsx` already uses, not tied to Student 1's
   specific sections. Component groups under `frontend/src/components/` are organized by concern
   (`brand/`, `layout/`, `venture/`, `forge/`, `results/`, `visualizations/`, `status/`) — a new
   results component belongs in `results/` or `visualizations/`, not a new top-level folder.
6. Add tests mirroring `backend/tests/test_orchestrator.py` and `test_judge.py`'s shape (success
   path, failure path, no-fabrication check).

**Adding a new ML model** (e.g. Student 2's success/revenue models): follow the same shape as
`ml/src/training/train_industry_classifier.py` — dataset schema-inspected and approved in
`ml/DATASETS.md` first (see the real/rejected dataset table there for the bar to clear), a dummy
baseline always included in the comparison, trained offline (never inside a request), evaluated
with leakage checks before selection, and served via a new `backend/app/ml/*.py` module loaded
once at import time (mirror `predictor.py`'s `@lru_cache`-backed loader).

**Adding a second LLM provider**: implement `LLMProvider` (`backend/app/ai/base.py`) in a new
`backend/app/ai/<name>_provider.py`, raising `LLMUnavailable` for every failure mode exactly like
`gemini_provider.py` does. Wire it into `factory.py`'s `get_llm_provider()` behind its own env var
— never change `NarrativeContext`/`NarrativeEnhancement` to add provider-specific fields, since
those schemas are what guarantee no provider can override a deterministic value.

## Brand Assets

The official logo (`VentureForgeAI logo.jpg`, repo root) is a single square poster containing the
emblem, wordmark, tagline, and an icon row. `frontend/src/assets/ventureforge-emblem.webp` and
`ventureforge-lockup.webp` are cropped, alpha-matted (near-black background keyed to transparent),
resized, and compressed derivatives — not a redrawn logo. To regenerate them (e.g. a different
crop), reprocess the source JPG with Pillow: crop the desired region, key out the near-black
background by mapping pixel luminance to alpha, resize to a sane max width (600-900px is enough
for how large these render in the UI), and export as WebP (`quality=90`) to keep file size small —
the first unoptimized export of these assets was over 1MB each and had to be redone.

## Data Model

See [ml/DATASETS.md](../ml/DATASETS.md) for dataset details and
`backend/alembic/versions/0001_initial.py` for the `startups`/`analyses` schema — two tables, no
speculative tables for unimplemented agents. Alembic (not a hand-maintained `schema.sql`) is the
single source of truth for the schema.
