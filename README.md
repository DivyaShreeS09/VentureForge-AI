<div align="center">

<img src="frontend/src/assets/ventureforge-lockup.webp" alt="VentureForge AI" width="360" />

### From Idea to Investor-Ready Startup in Minutes

Turn one startup idea into a full investor blueprint — industry fit, funding readiness, success signal, revenue outlook, market position, and a final verdict.

[![CI](https://github.com/DivyaShreeS09/VentureForge-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/DivyaShreeS09/VentureForge-AI/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Node](https://img.shields.io/badge/node-20-blue)
![PostgreSQL](https://img.shields.io/badge/postgresql-17-blue)

<!-- Add hero banner at docs/assets/hero-banner.png (recommended 1600x700) -->

**[Preview](#screenshots)** · **[Product Journey](#product-journey)** · **[AI Workflow](#the-ai-workflow)** · **[Machine Learning](#machine-learning)** · **[Architecture](#architecture)** · **[Quick Start](#quick-start)**

</div>

<br/>

## The Problem

Validating a startup idea usually means a dozen scattered tools and a friend's opinion. Nothing tells you what it actually doesn't know.

**Most startup tools answer questions. VentureForge AI builds a decision path.**

## The Vision

VentureForge AI is designed as an AI-powered startup-building ecosystem, not merely an idea evaluator. It combines machine learning, business-intelligence agents, explainable decision support, and startup planning into one coordinated workflow — from concept validation to an investor-ready blueprint.

## Product Journey

```mermaid
journey
    title From Idea to Investor Blueprint
    section Submit
      Enter a startup idea: 5: Founder
    section Analyze
      Machine Learning + Business Agents run in parallel: 5: System
    section Decide
      Judge Agent synthesizes the evidence: 5: System
    section Receive
      Full investor blueprint: 5: Founder
```

### A Walkthrough

> *"An AI platform for early diabetic-foot risk detection."*

| Stage | What Comes Back |
|---|---|
| Industry | HealthTech, with a confidence score |
| Funding Readiness | A structured score built from your evidence |
| Success Signal | A calibrated estimate against historical outcomes |
| Revenue | Conservative / base / optimistic scenarios |
| Market & Persona | Opportunity signals and likely early adopters |
| Judge Agent | Strengths, weaknesses, missing evidence, next actions |

*Illustrative — actual output depends entirely on the idea and evidence you submit.*

## Product Capabilities

| Machine Learning | Business Intelligence |
|---|---|
| **Industry Classification** — identifies the startup's primary sector | **Market Intelligence** — frames the opportunity and its constraints |
| **Success Prediction** — compares the idea against historical outcomes | **Competitor Analysis** — maps known alternatives and gaps |
| **Funding Readiness** — evaluates investor preparedness across key dimensions | **Customer Persona** — defines the strongest early-adopter profile |
| **Revenue Scenarios** — models conservative, base, and optimistic outlooks | **Business Model** — assembles value proposition, channels, and revenue streams |

| Decision Layer | Product |
|---|---|
| **Explainability** — shows the reasoning behind every prediction | **Live Workflow Progress** — watch the pipeline run in real time |
| **Confidence Scoring** — flags low-confidence results instead of guessing | **Unified Results View** — one screen for every signal |
| **Evidence Checks** — surfaces what's missing before the verdict | **Analysis History** — every past run, saved |
| **Judge Agent** — combines all outputs into one final evaluation | **Report-Ready Output** — a blueprint you can act on |

## Why Not Just a Chatbot?

| | Chatbot | VentureForge AI |
|---|---|---|
| Response | One opinion | A structured pipeline |
| Prediction | Generated on the spot | Trained models, tested on unseen data |
| Funding view | A narrative | A versioned scoring rubric |
| Success signal | Rarely offered | A calibrated historical estimate |
| Missing info | A confident guess | Reported as a gap |
| Output | Advice | A reusable blueprint |

## The AI Workflow

```mermaid
flowchart TD
    IDEA([Startup Idea]) --> DATA[Evidence Collection]

    DATA --> MLL[["Machine Learning"]]
    DATA --> BIL[["Business Intelligence"]]

    subgraph ML[" "]
        direction LR
        ML1[Industry] --> ML2[Funding] --> ML3[Success] --> ML4[Revenue]
    end

    subgraph BI[" "]
        direction LR
        BI1[Market] --> BI2[Competitor] --> BI3[Persona] --> BI4[Business Model]
    end

    MLL --> ML --> JUDGE
    BIL --> BI --> JUDGE

    JUDGE{{Judge Agent}} --> BLUEPRINT([Investor Blueprint])
    BLUEPRINT --> DASH[Dashboard]

    style JUDGE fill:#1a1a2e,stroke:#ec4899,color:#fff
    style BLUEPRINT fill:#1a1a2e,stroke:#22c55e,color:#fff
```

**Industry Classification** — determines the startup's domain before every other module runs.
**Funding Readiness** — surfaces what investors expect before a pitch.
**Success Prediction** — measures how closely the idea patterns after historical outcomes.
**Revenue Estimation** — grounds ambition in a realistic range.
**Judge Agent** — the single point where every signal above converges into one verdict, with an optional Gemini narrative layered on top, never replacing it.

## Machine Learning

| Model | What It Does | Performance |
|---|---|---|
| Industry Classifier | Selects the most relevant startup industry from seven categories | Macro F1: 0.776 — consistent performance across all categories |
| Success Predictor | Compares the startup with historical company outcomes | ROC-AUC: 0.855 — strong separation between outcome patterns |

Full methodology and dataset detail: [`ml/DATASETS.md`](ml/DATASETS.md).

## Architecture

```mermaid
flowchart TD
    subgraph Client
        FE[React Frontend]
    end
    subgraph Server
        API[FastAPI] --> LG[LangGraph Orchestrator]
        LG --> ML[ML Models]
        LG --> AGT[Business Agents]
        LG --> JDG{{Judge Agent}}
    end
    subgraph Storage
        DB[(PostgreSQL)]
    end

    FE --> API
    JDG --> DB --> API --> FE
    JDG -. optional .-> GEM[Gemini]

    style JDG fill:#1a1a2e,stroke:#ec4899,color:#fff
    style GEM fill:#1a1a2e,stroke:#94a3b8,color:#fff,stroke-dasharray: 5 5
```

## Tech Stack

| | |
|---|---|
| **Frontend** | React · TypeScript · TailwindCSS · Vite |
| **Backend** | FastAPI · SQLAlchemy · Alembic |
| **Database** | PostgreSQL |
| **Artificial Intelligence** | LangGraph · Google Gemini |
| **Machine Learning** | TF-IDF · Logistic Regression · HistGradientBoosting · Sentence Transformers |
| **Explainable AI** | Feature Importance · Term Contributions · Confidence Calibration |
| **Data Processing** | pandas · NumPy · scikit-learn |
| **Testing** | pytest · Vitest · React Testing Library |

## Repository

| | |
|---|---|
| `backend/` | AI orchestration, FastAPI, Judge Agent, persistence |
| `frontend/` | React UI, workflow view, results, reports |
| `ml/` | Training, evaluation, feature engineering, explainability |

## Screenshots

<!--
  docs/assets/hero-banner.png · docs/assets/demo.gif
  docs/assets/screenshots/{idea-input,workflow,results,explainability,report}.png
-->

| | |
|---|---|
| **Hero** — where the idea begins | **Idea Intake** — the input form |
| **Workflow** — the pipeline in motion | **Results** — the unified view |
| **Explainability** — the reasoning behind it | **Judge Verdict** — the final decision |

## Quick Start

```bash
git clone <repository-url> && cd VentureForge-AI
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

docker compose up -d                 # PostgreSQL — or use a native install

python -m venv backend/.venv
source backend/.venv/bin/activate    # Windows: backend\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt -r ml/requirements.txt
cd frontend && npm install && cd ..

cd backend && alembic upgrade head && cd ..

python -m ml.src.training.train_industry_classifier
python -m ml.src.training.train_success_classifier

cd backend && uvicorn app.main:app --reload   # terminal 1
cd frontend && npm run dev                    # terminal 2
```

| | |
|---|---|
| App | http://localhost:5173 |
| API docs | http://127.0.0.1:8000/docs |
| Health | http://127.0.0.1:8000/api/v1/health |

Model training falls back to a small bootstrap dataset without a downloaded real dataset — logged clearly, never treated as the metrics above.

Stuck on setup? See [`docs/SETUP.md`](docs/SETUP.md).

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `GEMINI_API_KEY` | Optional narrative layer |
| `VITE_API_BASE_URL` | Frontend → backend API URL |

## The Future of VentureForge

```mermaid
timeline
    title Where VentureForge AI Is Headed
    Now : Industry · Funding · Success · Revenue : Market · Competitor · Persona · Business Model : Judge Agent
    Next : Customer Segmentation : Innovation Scoring : Risk & Growth Agents : Pitch Deck Generator : Founder Dashboard
    Beyond : Investor Matching : Grant Discovery : Patent Search : AI Co-Founder : Incubator Integration
```

## Acknowledgements

Built with [FastAPI](https://fastapi.tiangolo.com/), [React](https://react.dev/), [LangGraph](https://langchain-ai.github.io/langgraph/), [scikit-learn](https://scikit-learn.org/), [PostgreSQL](https://www.postgresql.org/), [SQLAlchemy](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/), and [TailwindCSS](https://tailwindcss.com/).
