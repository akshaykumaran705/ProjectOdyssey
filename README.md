# 🩺 Project Odyssey

> An AI-powered medical case analysis platform that leverages MedGemma (a medical-specialized LLM) to extract, analyze, and generate clinical insights from patient case documents.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Running the Application](#running-the-application)
  - [Local Development](#local-development)
- [Service URLs](#service-urls)
- [Database Migrations](#database-migrations)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)

---

## Overview

Project Odyssey is a full-stack medical AI platform designed to assist clinicians in analyzing patient cases. It ingests PDF case files, extracts structured clinical data, runs hallucination checks, generates cost estimates, and produces trust reports — all powered by a locally hosted MedGemma language model.

Key capabilities include:
- **PDF Case Ingestion** — Upload and parse medical case documents
- **AI-Powered Analysis** — Structured extraction using MedGemma (4B, 4-bit quantized)
- **Safety & Validation** — Built-in safety rules, hallucination detection, and evidence verification
- **Cost Estimation** — Automated cost analysis using a medical cost catalog
- **Rare Disease Spotlight** — Flags potential rare conditions for further review
- **Audio Transcription** — Medical ASR via OpenAI Whisper

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Next.js 16    │────▶│  FastAPI Backend │────▶│  PostgreSQL 15   │
│   Frontend      │     │  (Python 3.11)  │     │  (Database)      │
│   Port: 3000    │     │  Port: 8000     │     │  Port: 5432      │
└─────────────────┘     └────────┬────────┘     └──────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
             ┌──────▼──────┐          ┌───────▼──────┐
             │    MinIO    │          │   MedGemma   │
             │ (S3 Storage)│          │  LLM Server  │
             │ Port: 9000  │          │  Port: 8080  │
             └─────────────┘          └──────────────┘
```

---

## Tech Stack

| Layer        | Technology                                      |
|--------------|-------------------------------------------------|
| Frontend     | Next.js 16, React 19, TypeScript, Tailwind CSS  |
| Backend      | FastAPI, Python 3.11, SQLAlchemy, Uvicorn       |
| Database     | PostgreSQL 15                                   |
| Object Store | MinIO (S3-compatible)                           |
| LLM          | MedGemma 4B (mlx-community/medgemma-4b-it-4bit) via mlx-vlm |
| Auth         | JWT (python-jose)                               |
| Migrations   | Alembic                                         |
| Deployment   | Railway (backend) / Vercel (frontend) |

---

## Prerequisites

Ensure the following tools are installed:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+)
- [Node.js](https://nodejs.org/) (v20+) and npm — for local frontend dev
- [Python](https://www.python.org/downloads/) (3.11+) — for local backend dev
- [MLX-VLM](https://github.com/Blaizzy/mlx-vlm) — for local MedGemma server (Apple Silicon Mac only)

---

## Environment Setup

1. **Copy the environment file** (already provided as `.env` in the repo root):

```bash
cp .env .env.local   # Optional: keep a local override
```

2. **Review and update `.env`** as needed:

```env
# Database
DATABASE_URL=postgresql://odyssey:odyssey_secret@localhost:5432/odyssey
POSTGRES_DB=odyssey
POSTGRES_USER=odyssey
POSTGRES_PASSWORD=odyssey_secret

# Object Storage (MinIO)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=odyssey-files
S3_REGION=us-east-1

# JWT
SECRET_KEY=your-secret-key-change-me    # ⚠️ Change this in production!
ALGORITHM=HS256

# LLM Server (MedGemma via mlx-vlm)
LLM_BASE_URL=http://localhost:8080
LLM_MODEL=mlx-community/medgemma-4b-it-4bit
```

---

## Running the Application

### Local Development

PostgreSQL and MinIO are hosted on cloud — only the LLM, backend, and frontend run locally.

#### Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
npm run build
```

#### Start Services

Open **three separate terminals**:

**Terminal 1 — MedGemma LLM Server** *(Apple Silicon, downloads ~2.5 GB on first run)*
```bash
python -m mlx_vlm.server --host 0.0.0.0 --port 8080 --model mlx-community/medgemma-4b-it-4bit
```

**Terminal 2 — Backend**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 3 — Frontend**
```bash
cd frontend
npm run dev
```

---

## Service URLs

| Service             | URL                                       |
|---------------------|-------------------------------------------|
| Frontend            | http://localhost:3000                     |
| Backend API         | http://localhost:8000                     |
| Backend API Docs    | http://localhost:8000/docs                |
| Backend Health      | http://localhost:8000/health              |
| MedGemma LLM Server | http://localhost:8080                     |
| MinIO Console       | http://localhost:9003 (Docker) / http://localhost:9001 (local) |
| MinIO API           | http://localhost:9002 (Docker) / http://localhost:9000 (local) |
| PostgreSQL          | localhost:5435 (Docker) / localhost:5432 (local) |

---

## Database Migrations

Migrations are managed with [Alembic](https://alembic.sqlalchemy.org/).

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback the last migration
alembic downgrade -1

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# View migration history
alembic history
```

---

## Running Tests

All test files are located in the `backend/` directory.

```bash
cd backend
source .venv/bin/activate

# Run a specific test
python test_full_flow.py
python test_grounding.py
python test_multi_cases.py

# Run phase-specific tests
python test_phase5a.py
python test_phase6.py
python test_phase7.py
python test_phase8.py

# Generate test PDF case files
python create_test_pdfs.py

# Seed demo cases into the database
python demo_cases.py
```

---

## Project Structure

```
ProjectOdyssey/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/                # API route handlers (auth, cases, health)
│   │   ├── core/               # Core configuration
│   │   ├── db/                 # Database connection & session
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic & AI pipeline
│   │   │   ├── pipeline_runner.py      # Main analysis pipeline
│   │   │   ├── llm_model.py            # MedGemma LLM client
│   │   │   ├── pdf_extractor.py        # PDF parsing
│   │   │   ├── safety.py               # Safety checks
│   │   │   ├── hallucination_check.py  # Hallucination detection
│   │   │   ├── cost_engine.py          # Cost estimation
│   │   │   ├── evidence_index.py       # Evidence indexing
│   │   │   └── rare_spotlight.py       # Rare disease detection
│   │   └── utils/              # Helpers (object store, etc.)
│   ├── requirements.txt        # Python dependencies
│   └── railway.toml            # Railway deployment config
├── frontend/                   # Next.js 16 frontend
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   ├── components/         # React UI components
│   │   └── lib/                # Utilities, API client, auth context
│   └── package.json
├── alembic/                    # Database migration scripts
├── medgemma/                   # MedGemma server Dockerfile

└── .env                        # Environment variables
```

---

## Deployment

- **Backend** is configured for [Railway](https://railway.app/) via `backend/railway.toml`
- **Frontend** is configured for [Vercel](https://vercel.com/) via `frontend/.vercel/`
- Set `NEXT_PUBLIC_API_URL` in Vercel to point to your deployed backend URL

---

*Built with ❤️ for advancing AI-assisted clinical decision support.*
