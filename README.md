# 🔬 Scientific Pathfinder

> AI-powered research gap discovery system using Knowledge Graphs and LLMs.

[![CI](https://github.com/Pruthviraj-333/scientific-pathfinder/actions/workflows/ci.yml/badge.svg)](https://github.com/Pruthviraj-333/scientific-pathfinder/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)

---

## Overview

Scientific Pathfinder is an autonomous multi-agent research system that:

1. **🔍 Searches** scientific papers via Semantic Scholar API
2. **🗺️ Maps** research into a Neo4j Knowledge Graph
3. **💡 Discovers** structural holes and underexplored combinations
4. **🧪 Proposes** novel, testable hypotheses with validation scripts

```
┌─────────────┐      ┌──────────────┐      ┌──────────┐
│  Librarian  │ ───▶ │ Cartographer │ ───▶ │ Scientist│
└─────────────┘      └──────────────┘      └──────────┘
  Search Papers        Build Graph         Find Gaps
  Extract Entities     Structure Data      Generate Hypothesis
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS, D3.js |
| **Backend** | Python 3.11, FastAPI, LangGraph, WebSockets |
| **AI/LLM** | Groq API (Llama 3.3 70B) |
| **Database** | Neo4j (Aura or Docker) |
| **Data Source** | Semantic Scholar API |
| **Infrastructure** | Docker, Nginx, GitHub Actions |

---

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Pruthviraj-333/scientific-pathfinder.git
cd scientific-pathfinder

# Set your Groq API key
# Bash (Linux/macOS):
export GROQ_API_KEY=gsk_your_key_here
# PowerShell (Windows):
$env:GROQ_API_KEY="gsk_your_key_here"
# CMD (Windows):
set GROQ_API_KEY=gsk_your_key_here

# Start all services (backend + frontend + Neo4j)
docker-compose up -d

# Open the app
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Neo4j Browser: http://localhost:7474
```

### Option 2: Manual Setup

#### Backend

```bash
cd scientific_pathfinder
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # Edit with your API keys
python -m uvicorn api:app --reload
```

#### Frontend

```bash
cd scientific_pathfinder_frontend
npm install
cp .env.example .env          # Edit VITE_API_URL if needed
npm run dev
```

---

## Environment Variables

### Backend (`scientific_pathfinder/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Groq API key for LLM |
| `NEO4J_URI` | ✅ | — | Neo4j connection URI |
| `NEO4J_PASSWORD` | ✅ | — | Neo4j password |
| `NEO4J_USERNAME` | ❌ | `neo4j` | Neo4j username |
| `ENVIRONMENT` | ❌ | `development` | `development` / `production` |
| `CORS_ORIGINS` | ❌ | `localhost:3000,5173` | Comma-separated origins |
| `API_KEY` | ❌ | — | Optional API key auth |
| `SEMANTIC_SCHOLAR_API_KEY` | ❌ | — | Higher rate limits |
| `RATE_LIMIT_REQUESTS` | ❌ | `60` | Requests per minute |
| `LOG_FORMAT` | ❌ | `text` | `text` (dev) / `json` (prod) |

### Frontend (`scientific_pathfinder_frontend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | ❌ | `http://localhost:8000` | Backend API URL |

---

## Project Structure

```
scientific-pathfinder/
├── docker-compose.yml              # Development compose
├── docker-compose.prod.yml         # Production compose
├── nginx/nginx.conf                # Reverse proxy config
├── .github/workflows/
│   ├── ci.yml                      # CI pipeline
│   └── deploy.yml                  # Deployment pipeline
│
├── scientific_pathfinder/          # Backend (Python/FastAPI)
│   ├── api.py                      # FastAPI application
│   ├── config.py                   # Pydantic settings
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   ├── agents.py               # Librarian, Cartographer, Scientist
│   │   ├── graph_db.py             # Neo4j interface
│   │   ├── state.py                # LangGraph state
│   │   ├── tools.py                # Semantic Scholar client
│   │   ├── database.py             # DB lifecycle management
│   │   ├── schemas.py              # API request/response models
│   │   ├── middleware.py           # Security, rate limiting, logging
│   │   ├── exceptions.py          # Custom exception hierarchy
│   │   ├── logging_config.py      # Structured logging
│   │   └── metrics.py             # API metrics
│   ├── prompts/
│   │   └── system_prompts.py       # LLM prompts
│   └── tests/
│       ├── conftest.py
│       ├── test_api.py
│       ├── test_config.py
│       └── test_schemas.py
│
└── scientific_pathfinder_frontend/ # Frontend (React/Vite)
    ├── Dockerfile
    ├── nginx.conf
    ├── src/
    │   ├── App.tsx
    │   ├── config/index.ts          # Environment config
    │   ├── services/api.ts          # Centralized API client
    │   ├── components/
    │   ├── types/
    │   └── utils/
    └── vite.config.ts
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Full health check |
| `GET` | `/api/v1/health/live` | Liveness probe |
| `GET` | `/api/v1/health/ready` | Readiness probe |
| `GET` | `/api/v1/metrics` | API metrics |
| `POST` | `/api/v1/research/start` | Start research session |
| `GET` | `/api/v1/research/{id}` | Get session status |
| `GET` | `/api/v1/graph/{id}` | Get graph visualization data |
| `POST` | `/api/v1/graph/clear` | Clear Neo4j database |
| `WS` | `/ws/{session_id}` | Real-time progress updates |

---

## Docker Commands

```bash
# Development
docker-compose up -d                    # Start all
docker-compose logs -f backend          # View backend logs
docker-compose down                     # Stop all
docker-compose down -v                  # Stop + remove volumes

# Production
docker-compose -f docker-compose.prod.yml up -d --build

# Individual builds
docker build -t sp-backend ./scientific_pathfinder
docker build -t sp-frontend ./scientific_pathfinder_frontend \
  --build-arg VITE_API_URL=https://your-api.com
```

---

## Testing

```bash
cd scientific_pathfinder
pip install -r requirements.txt
pytest tests/ -v
```

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guides on:
- Local Docker deployment
- Render deployment
- Railway deployment
- Custom VPS with Docker Compose

---

## License

MIT

---

**Built with ❤️ for researchers exploring the frontiers of science**
