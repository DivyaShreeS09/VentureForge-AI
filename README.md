# VentureForge AI

VentureForge AI is a full-stack AI/ML platform that analyzes startup ideas using real-data
industry classification, explainable funding-readiness assessment, LangGraph orchestration, a
deterministic Judge Agent, and optional Gemini narrative enhancement, built on PostgreSQL,
FastAPI, and React.

## Current Foundation

- Real-data industry classification (TF-IDF + Logistic Regression, trained on Y Combinator
  company descriptions)
- Confidence score and top alternative categories
- Explainable term-level contributions behind each prediction
- Deterministic, versioned funding-readiness assessment across 8 dimensions
- Judge Agent — deterministic synthesis of the above into strengths, weaknesses, and next actions
- LangGraph workflow orchestration (7-node pipeline, deterministic routing)
- PostgreSQL persistence via Alembic-managed migrations
- Cinematic React interface built on the official VentureForge AI brand identity
- Optional Gemini narrative enhancement (additive only; never overrides deterministic output)
- Automated backend, ML, integration, and frontend test suites
- Real-data startup success prediction (HistGradientBoosting, trained on resolved Crunchbase
  acquisition/IPO/shutdown outcomes) with historical-pattern framing, never a guarantee
- Deterministic revenue scenario calculator (conservative/base/optimistic 12-month projections
  from user-supplied pricing/growth assumptions — not a trained model)
- Deterministic market intelligence, competitor analysis, customer persona, and business model
  agents — evidence-bound, never fabricating market size, competitor facts, or demographics

This repository implements the Student 1 and Student 2 vertical slices. Student 3
(segmentation/innovation/risk/growth/pitch/dashboard) is not yet implemented — see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how it extends this codebase.

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **ML**: scikit-learn (TF-IDF + Logistic Regression), pandas
- **Orchestration**: LangGraph
- **Frontend**: React, TypeScript, Vite, TailwindCSS
- **Optional AI layer**: Google Gemini (additive narrative only)

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 17 (or compatible)
- Git
- Kaggle CLI + credentials — only required if retraining from the raw dataset
- Gemini API key — optional

## Local Setup — Five Steps

### Step 1 — Create environment files

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Open `backend/.env` and set `DATABASE_URL` to your local PostgreSQL password. The Gemini API key,
if used, also belongs only in `backend/.env` — never in `frontend/.env`.

### Step 2 — Install dependencies

From the repository root:

```powershell
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt -r ml/requirements.txt
cd frontend
npm install
cd ..
```

### Step 3 — Prepare PostgreSQL

```powershell
psql -U postgres -c "CREATE DATABASE ventureforge_ai;"
```

If the database already exists, the creation error can be ignored.

```powershell
cd backend
alembic upgrade head
cd ..
```

`DATABASE_URL` format:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ventureforge_ai
```

An optional `docker-compose.yml` is provided as an alternative to a native PostgreSQL install
(`docker compose up -d`, then run the `alembic upgrade head` step above).

### Step 4 — Train or verify the ML models

Only required if `ml/models/industry_classifier/v2/model.joblib` and/or
`ml/models/success_predictor/v1/model.joblib` do not already exist. Kaggle credentials, if used to
re-source the raw datasets, must stay outside the repository (see `scripts/download_datasets.py`).

```powershell
python -m ml.src.training.train_industry_classifier
python -m ml.src.training.train_success_classifier
```

Both fall back to a small generated bootstrap corpus (never presented as real accuracy) if the
real dataset CSV hasn't been downloaded — see [ml/DATASETS.md](ml/DATASETS.md).

### Step 5 — Start the application

Terminal 1:

```powershell
backend\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload
```

Terminal 2:

```powershell
cd frontend
npm run dev
```

- Application: http://localhost:5173
- API docs: http://127.0.0.1:8000/docs
- Health endpoint: http://127.0.0.1:8000/api/v1/health

## Optional Gemini Setup

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash
```

- The key belongs only in `backend/.env` and is never sent to the frontend.
- The project works fully without Gemini configured.
- The deterministic Judge Agent output is always produced; Gemini only adds a supplementary
  narrative field on top of it and is never a fallback dependency.

## Tests

```powershell
cd backend
pytest
cd ../ml
pytest tests
cd ../frontend
npm run test
npm run build
cd ..
pytest tests/integration
```

## Known Limitations

- Industry classification covers a 7-class YC-based taxonomy, English-only.
- Funding readiness is a deterministic rubric, not a trained funding probability.
- Success prediction is a historical-pattern estimate from resolved Crunchbase outcomes — cumulative
  funding-history features carry some inherent timing bias (see ml/DATASETS.md); never a guarantee.
- Revenue estimation is a deterministic scenario calculator driven entirely by user-supplied
  assumptions, not a trained model — no defensible real revenue dataset was found (see
  ml/DATASETS.md).
- Market intelligence / competitor analysis / customer persona / business model agents have no
  live market-data, company-database, or web-search integration — every field not derivable from
  submitted evidence is reported as a gap, never invented.
- Gemini's live behavior depends on API availability; only mocked calls are tested in this
  environment.
- Student 3 business modules are not yet implemented in this repository.

## Before Pushing to Main

1. `git pull --rebase origin main`
2. Run the tests (see [Tests](#tests) above)
3. Stage only your own changed files — never `git add .` blindly
4. Do not replace this README or introduce another framework/stack alongside FastAPI/React
