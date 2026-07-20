# Setup Guide

Detailed installation paths and fixes for common problems. See [`README.md`](../README.md) for the fast path.

## Path A — Docker for PostgreSQL

```bash
git clone <repository-url> && cd VentureForge-AI
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env      # Windows: Copy-Item

docker compose up -d
```

## Path B — Native PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE ventureforge_ai;"
```

*If `database already exists`: safe to ignore, continue.*

## Both Paths

```bash
python -m venv backend/.venv
source backend/.venv/bin/activate           # Windows: backend\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt -r ml/requirements.txt
cd frontend && npm install && cd ..

cd backend && alembic upgrade head && cd ..

python -m ml.src.training.train_industry_classifier
python -m ml.src.training.train_success_classifier

cd backend && uvicorn app.main:app --reload   # terminal 1
cd frontend && npm run dev                    # terminal 2
```

## 60-Second Verification

- [ ] `/docs` opens and lists live endpoints
- [ ] `/api/v1/health` returns a success response
- [ ] `/api/v1/models/status` reports loaded model versions
- [ ] The frontend loads at `localhost:5173`
- [ ] `alembic current` shows the latest migration head
- [ ] A sample startup idea can be submitted and returns a full analysis

## Common Fixes

| Problem | Fix |
|---|---|
| PowerShell blocks the venv activation script | `Set-ExecutionPolicy -Scope Process RemoteSigned` |
| `python` not found | Use `python3`, or confirm Python 3.12 is on PATH |
| `npm` not found | Install Node.js 20 and reopen your terminal |
| PostgreSQL connection refused | Confirm the container/service is running and the port matches `DATABASE_URL` |
| Password authentication failed | Match `DATABASE_URL` to the password you set during install |
| `database already exists` | Safe to ignore — continue to the next step |
| Alembic import/path error | Run `alembic` commands from inside `backend/`, not the repo root |
| Missing model artifact | Run the training commands above |
| Port 8000 already in use | Stop the conflicting process, or run `uvicorn` with `--port` |
| Port 5173 already in use | Stop the conflicting process, or set a different Vite port |
| Frontend can't reach the backend | Check `VITE_API_BASE_URL` in `frontend/.env` |
| No Kaggle credentials | Only required to re-download raw datasets — training still runs on the bootstrap corpus without them |
| No Gemini key | Optional by design — the full deterministic pipeline works without it |

## Full Environment Reference

| Variable | Location | Purpose |
|---|---|---|
| `DATABASE_URL` | `backend/.env` | PostgreSQL connection string |
| `GEMINI_API_KEY` | `backend/.env` | Optional narrative layer |
| `GEMINI_MODEL` | `backend/.env` | e.g. `gemini-2.0-flash` |
| `VITE_API_BASE_URL` | `frontend/.env` | Backend API base URL |
| Kaggle credentials | `~/.kaggle/kaggle.json` | Only needed to re-download raw ML training data |

## Test & Build Commands

| | |
|---|---|
| Backend tests | `pytest` — from `backend/` |
| ML tests | `pytest tests` — from `ml/` |
| Frontend tests | `npm run test` — from `frontend/` |
| Integration tests | `pytest tests/integration` |
| Frontend production build | `npm run build` — from `frontend/` |

`backend/tests/` and `ml/tests/` are two separate suites, not duplicates of each other:
`backend/tests/` exercises the served FastAPI application (API routes, agents, the orchestrated
pipeline) end-to-end; `ml/tests/` exercises the offline training/preprocessing pipeline (feature
engineering, dataset splitting, evaluation metrics) that produces the model artifacts
`backend/app/ml/` loads. Neither imports from the other.

## Runtime Dependencies

PostgreSQL is the only datastore this application uses. There is no Redis (or any other cache/
queue) client anywhere in the codebase — `docker-compose.yml` provisions PostgreSQL alone, for
anyone who doesn't already have it installed natively.
