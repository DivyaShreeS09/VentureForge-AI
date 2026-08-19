#!/usr/bin/env bash
# One-time local dev setup: backend venv + deps, frontend deps, env files.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Setting up backend..."
python -m venv backend/.venv
source backend/.venv/Scripts/activate 2>/dev/null || source backend/.venv/bin/activate
pip install -r backend/requirements.txt
pip install -r ml/requirements.txt
deactivate

echo "Setting up frontend..."
(cd frontend && npm install)

echo "Copying .env files (edit them with real values)..."
[ -f .env ] || cp .env.example .env
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env

echo "Done. Set up PostgreSQL (native install, or 'docker compose up -d'), then:"
echo "  cd backend && alembic upgrade head"
echo "  backend:  cd backend && source .venv/Scripts/activate && uvicorn app.main:app --reload"
echo "  frontend: cd frontend && npm run dev"
