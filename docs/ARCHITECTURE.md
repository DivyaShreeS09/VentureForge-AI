# Architecture

Reflects the Student 1 (industry classification, funding readiness, Judge Agent), Student 2
(startup success prediction, revenue estimation, market intelligence, competitor analysis,
customer persona, business model), and Student 3 (customer segmentation, ranked actions,
innovation opportunities, planning risks, growth strategy, pitch-deck outline — see "Phase 5:
Student 3 Integration" below) vertical slices, plus the Founder Guidance / Idea Expansion /
Strategic Opportunity Discovery / Founder Decision Studio layers built on top of them (Phases 1-4).
See "Extension Points" below for how a further vertical slice would plug in.

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

21 nodes (see `backend/tests/test_orchestrator.py::test_valid_input_completes_successfully` for
the exact, tested order), deterministic routing, no loops, no external API call required for the
deterministic pipeline itself:

```
input_validation ──(invalid)──► invalid_input ──┐
       │ (valid)                                │
       ▼                                        │
industry_classification                         │
       ▼                                        │
resolve_venture_positioning                     │
       ▼                                        │
funding_readiness                                │
       ▼                                        │
predict_success  ─▶ estimate_revenue ─▶ analyze_market ─▶ analyze_competitors
       ▼                                        │              (Student 2 chain)
build_customer_persona ─▶ evaluate_business_model
       ▼
segment_customers ─▶ rank_actions ─▶ surface_innovation ─▶ assess_risks
       ▼                                                    (Phase 5 / Student 3 chain)
plan_growth_strategy ─▶ build_pitch_deck
       ▼                                        │
evidence_confidence_check                        │
       ▼                                        │
     judge                                        │
       ▼                                        │
mentor_synthesis                                 │
       ▼                                        │
expand_ideas ─▶ discover_strategic_opportunities │
       ▼                                        │
   persistence ◄─────────────────────────────────┘
       ▼
 final_response
```

(Node ids like `predict_success`, `expand_ideas`, `segment_customers`, etc. are deliberately
distinct from the `OrchestratorState` output keys they populate — LangGraph rejects a node id that
collides with an existing state key.)

- **input_validation**: rejects a missing name or a description under 10 characters; routes
  straight to `invalid_input` (which marks the run `FAILED`) rather than running any ML node.
- **industry_classification**: calls the trained TF-IDF + Logistic Regression pipeline
  (`backend/app/ml/predictor.py`). Degrades to `industry_prediction: null` if no artifact is
  trained yet — a missing model is not the same failure class as invalid input.
- **resolve_venture_positioning**: resolves the founder-facing `venture_positioning` from a
  controlled taxonomy (`backend/app/agents/venture_positioning.py`,
  `backend/app/ml/positioning_taxonomy.py`) — distinct from, and more specific than, the raw
  industry classification. Only calls Gemini when the deterministic taxonomy signal is ambiguous.
- **funding_readiness**: the deterministic rubric (`backend/app/ml/funding_readiness.py`).
- **predict_success / estimate_revenue / analyze_market / analyze_competitors /
  build_customer_persona / evaluate_business_model** (Student 2): trained success-prediction
  model, a deterministic revenue-scenario calculator, and three deterministic business-intelligence
  agents — see each module's docstring for its specific no-fabrication guarantee.
- **segment_customers / rank_actions / surface_innovation / assess_risks /
  plan_growth_strategy / build_pitch_deck** (Phase 5 / Student 3, `backend/app/agents/student3.py`):
  deterministic growth/strategy planning grounded only in the funding-readiness breakdown and
  industry prediction — labels missing revenue/customer/legal claims as "unknown"/"evidence
  required" rather than inventing them. Customer segmentation attaches a real clustering result
  only when a trained artifact *and* caller-supplied RFM input are both present
  (`backend/app/ml/segmentation.py`); otherwise reports itself unavailable.
- **evidence_confidence_check**: flags low industry-confidence (<0.35) and surfaces how many
  funding dimensions were left unanswered.
- **judge**: deterministic synthesis (`backend/app/agents/judge.py`) — reformats all upstream
  outputs into strengths/weaknesses/next actions/confidence/source_attribution, and never invents
  a fact not present in an upstream output, nor blends incompatible values (e.g. a success
  probability is never averaged with a funding-readiness score).
- **mentor_synthesis** (Phases 1/1.5): reconciles the Judge Agent's output and every
  business-intelligence agent's output into one coherent, founder-facing `mentor_interpretation`
  (`backend/app/agents/mentor_synthesis.py`) — Founder Guidance items, verdict, validation plan,
  30/60/90 roadmap. Always runs its deterministic baseline first; Gemini may only rephrase a
  narrow, safety-checked subset on top.
- **expand_ideas** (Phase 2): Idea Expansion — `backend/app/agents/idea_expansion.py`.
- **discover_strategic_opportunities** (Phase 3): Strategic Opportunity Discovery —
  `backend/app/agents/strategic_opportunity.py`.
- **persistence**: the single place that finalizes run status (`COMPLETED` unless something
  upstream set `FAILED`) and writes the `Analysis` row.
- **final_response**: formats the trace; does not change status.

State is a `TypedDict` (`backend/app/agents/state.py`); nodes never import each other directly —
only `orchestrator.py` wires them. The Founder Decision Studio (Phase 4,
`frontend/src/components/results/AnalysisResult.tsx` + `studio/*.tsx`) is a pure client-side
presentation layer over this state — it derives its 9-section guided journey from data the
pipeline above already computed, and never recomputes a score or prediction itself
(`frontend/src/utils/founderDecision.ts`).

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
ml/data/raw (real dataset, or generated bootstrap corpus as a fallback) → ml/src/preprocessing
    → ml/src/features → ml/src/training → ml/models/<model_name>/<version>/ (joblib + metadata.json)
         │
         ▼
backend/app/ml/{predictor,success_predictor}.py (each loads once, cached)
```

Two independently trained models follow this same shape:
- `industry_classifier` (`ml/src/training/train_industry_classifier.py` →
  `backend/app/ml/predictor.py`) — text classification.
- `success_predictor` (`ml/src/training/train_success_classifier.py` →
  `backend/app/ml/success_predictor.py`) — binary classification on structured company/funding
  features (`ml/src/features/success_features.py`).

Training/evaluation never runs inside the FastAPI request path. See
[ml/README.md](../ml/README.md) and [ml/DATASETS.md](../ml/DATASETS.md) for the dataset honesty
caveat both pipelines operate under, and the real/rejected dataset audit trail for each task.

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
├── agents/                           — state.py, nodes.py, judge.py, orchestrator.py,
│                                        market_agent.py, competitor_agent.py,
│                                        customer_persona_agent.py, business_model_agent.py
├── ml/                                 — funding_readiness.py, predictor.py, success_predictor.py,
│                                          revenue_scenario.py
└── ai/                                   — optional LLM layer (see "Optional LLM Layer" above)
```

Import direction: `api → services → {agents, database, ml}`. The one exception is
`backend/app/ml/predictor.py` importing `ml.src.explainability` directly (the `ml/` package lives
alongside `backend/`, not inside it — see that file's module docstring for why).

## Extension Points (Student 3)

These are additive extension points (already exercised once by the Student 2 nodes described
above), not places to modify Student 1 or Student 2's existing nodes, schemas, or tables.
Everything below has been verified to accept new keys/nodes without touching existing code paths.

**Adding a new orchestrator node** (Student 3: customer segmentation, innovation, risk, growth,
pitch):
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

**Adding a new ML model**: follow the same shape as `ml/src/training/train_industry_classifier.py`
and `ml/src/training/train_success_classifier.py` — dataset schema-inspected and approved in
`ml/DATASETS.md` first (see the real/rejected dataset table there for the bar to clear), a dummy
baseline always included in the comparison, trained offline (never inside a request), evaluated
with leakage checks before selection, and served via a new `backend/app/ml/*.py` module loaded
once at import time (mirror `predictor.py`'s `@lru_cache`-backed loader).

**Adding a second LLM provider**: implement `LLMProvider` (`backend/app/ai/base.py`) in a new
`backend/app/ai/<name>_provider.py`, raising `LLMUnavailable` for every failure mode exactly like
`gemini_provider.py` does. Wire it into `factory.py`'s `get_llm_provider()` behind its own env var
— never change `NarrativeContext`/`NarrativeEnhancement` to add provider-specific fields, since
those schemas are what guarantee no provider can override a deterministic value.

## Phase 5: Student 3 Integration (implemented, 2026-07-20)

The "Extension Points (Student 3)" plan above was followed to integrate Student 3's actual
contribution (originally `2058d0357de81e283f57ff6f638faf0912ce9607` on `origin/main`, one commit
ahead of the branch this repo continued from). That commit could not be merged directly — it was
authored against a base that predated Student 2 and Phases 1-4, and its diff deleted the Student 2
agents, judge.py's Student 2 kwargs, `company_metrics`/`revenue_assumptions`/`market_evidence`,
and collided its own Alembic revision ids (`0002`/`0003`) with ones already used differently here.
Every module was instead re-implemented additively, exactly per the extension-point rules above:

- **New nodes** (`backend/app/agents/nodes.py`): `segment_customers_node`, `rank_actions_node`,
  `surface_innovation_node`, `assess_risks_node`, `plan_growth_strategy_node`,
  `build_pitch_deck_node` — pure functions calling `backend/app/agents/student3.py`. Spliced into
  `build_graph()` between `evaluate_business_model` and `evidence_confidence_check`; none of the
  existing node ids, edges, or the Student 2 chain were touched or renamed.
- **New state keys** (`state.py`): `customer_rfm` (input), `customer_segment`, `ranked_actions`,
  `innovation_opportunities`, `risk_assessment`, `growth_strategy`, `pitch_deck` (outputs) — added
  alongside the existing keys, not replacing them.
- **Judge Agent** (`judge.py`): `synthesize()` gained three new optional keyword arguments
  (`customer_segment`, `ranked_actions`, `risks`), each contributing its own `source_attribution`
  entry and passed through in the return dict — the existing Student 2/venture-positioning
  parameters and return keys are unchanged.
- **Segmentation** (`backend/app/ml/segmentation.py`): a version-checked joblib artifact loader —
  assigns a segment only when both a trained artifact and caller-supplied customer RFM input
  (`recency_days`/`frequency`/`monetary`) are present; otherwise reports segmentation as
  unavailable rather than fabricating a fallback. The offline research pipeline that produces that
  artifact (RFM feature engineering, a 4-way clustering comparison, and its own tests) lives in
  `ml/src/preprocessing/customer_segmentation.py`, `ml/src/training/train_customer_segmentation*.py`,
  and `ml/src/evaluation/clustering_metrics.py` — see `ml/DATASETS.md`'s "Customer Segmentation
  Research Dataset" section for the UCI Online Retail dataset it was validated against.
- **Persistence**: `analyses.student3_outputs` (new nullable JSONB column, migration `0008`) and
  `startups.customer_rfm` (new nullable JSON column, migration `0009`) — both purely additive,
  chained after the existing `0007_strategic_opportunity` head.
- **Frontend**: no new standalone "Student 3" card was added (the original commit's
  `Student3Results.tsx` bolted one on, which would have broken Phase 4's guided-journey design).
  Instead its content was folded into the existing Founder Decision Studio sections: planning risks
  merge into the Risk Dashboard (Section 7) alongside `strategic_risks`; the single highest-priority
  "now"-urgency ranked action folds into the Roadmap's First Week bucket (Section 4), deduped by
  title; growth-strategy recommendations add a "Growth Strategy" subsection to Market Expansion
  (Section 6); innovation opportunities and the pitch-deck outline are Advanced-only detail, since
  they're exploratory rather than this week's action.

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

See [ml/DATASETS.md](../ml/DATASETS.md) for dataset details. Two tables (`startups`, `analyses`),
no speculative tables for unimplemented (Student 3) agents:
`backend/alembic/versions/0001_initial.py` — original Student 1 schema;
`backend/alembic/versions/0002_student2_extension.py` — additive Student 2 columns
(`company_metrics`/`revenue_assumptions`/`market_evidence` on `startups`;
`success_prediction`/`revenue_estimate`/`market_intelligence`/`competitor_analysis`/
`customer_personas`/`business_model` plus their version columns on `analyses`). Alembic (not a
hand-maintained `schema.sql`) is the single source of truth for the schema; never edit `0001_*` in
place — extend with a new revision instead.
