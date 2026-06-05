# Deployment Guide

This guide covers deploying Scientific Pathfinder to various platforms.

---

## Prerequisites

- Docker & Docker Compose installed
- A [Groq API key](https://console.groq.com/keys)
- A Neo4j database (local Docker or [Neo4j Aura](https://neo4j.com/cloud/aura/) free tier)

---

## 1. Local Docker Deployment

The simplest way to run everything locally.

```bash
# Clone and enter the project
git clone https://github.com/Pruthviraj-333/scientific-pathfinder.git
cd scientific-pathfinder

# Set your API key
export GROQ_API_KEY=gsk_your_key_here

# Start all services
docker-compose up -d --build

# Verify
curl http://localhost:8000/api/v1/health
```

**Services:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Neo4j Browser: http://localhost:7474 (user: `neo4j`, pass: `devpassword123`)

---

## 2. Production Docker Deployment

For a VPS or cloud VM with Docker installed.

```bash
# Create a .env file with production values
cat > .env << EOF
GROQ_API_KEY=gsk_your_key
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
CORS_ORIGINS=https://yourdomain.com
VITE_API_URL=https://yourdomain.com
EOF

# Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# The app is now available on port 80
```

---

## 3. Render Deployment

Deploy backend and frontend as separate services.

### Backend (Web Service)
1. Create a **Web Service** on Render
2. **Root Directory**: `scientific_pathfinder`
3. **Runtime**: Docker
4. **Environment Variables**:
   - `GROQ_API_KEY`
   - `NEO4J_URI`
   - `NEO4J_PASSWORD`
   - `ENVIRONMENT=production`
   - `LOG_FORMAT=json`
   - `CORS_ORIGINS=https://your-frontend.onrender.com`
5. **Health Check Path**: `/api/v1/health/live`

### Frontend (Static Site)
1. Create a **Static Site** on Render
2. **Root Directory**: `scientific_pathfinder_frontend`
3. **Build Command**: `npm ci && npm run build`
4. **Publish Directory**: `dist`
5. **Environment Variables**:
   - `VITE_API_URL=https://your-backend.onrender.com`

---

## 4. Railway Deployment

1. Connect your GitHub repository
2. Railway will auto-detect the Docker setup
3. Add environment variables in the Railway dashboard
4. Deploy each service separately or use the monorepo setup

---

## 5. Environment Configuration Reference

### Required for All Deployments

| Variable | Example |
|----------|---------|
| `GROQ_API_KEY` | `gsk_abc123...` |
| `NEO4J_URI` | `neo4j+s://xxx.databases.neo4j.io` |
| `NEO4J_PASSWORD` | `your_password` |

### Production-Specific

| Variable | Value |
|----------|-------|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `LOG_FORMAT` | `json` |
| `CORS_ORIGINS` | `https://yourdomain.com` |
| `VITE_API_URL` | `https://api.yourdomain.com` |

### Optional Security

| Variable | Description |
|----------|-------------|
| `API_KEY` | Enable API key auth (set to any secret string) |
| `RATE_LIMIT_REQUESTS` | Max requests/minute (default: 60) |

---

## Rollback

```bash
# View recent images
docker images | grep sp-

# Roll back to a previous image tag
docker-compose -f docker-compose.prod.yml down
# Edit image tags in compose file or set env vars
docker-compose -f docker-compose.prod.yml up -d
```

---

## Monitoring

- **Health**: `GET /api/v1/health` — full dependency check
- **Liveness**: `GET /api/v1/health/live` — process alive
- **Readiness**: `GET /api/v1/health/ready` — ready to serve
- **Metrics**: `GET /api/v1/metrics` — request counts, latency, errors
