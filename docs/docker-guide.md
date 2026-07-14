# Docker Guide

Reference for all Docker and Docker Compose operations.

---

## Image Overview

| Image | Base | Size (approx) | Purpose |
|---|---|---|---|
| `brain-tumor-ai-service` | python:3.12-slim | ~1.8 GB | FastAPI + TensorFlow |
| `brain-tumor-backend` | node:20-slim | ~250 MB | Express REST API |
| `brain-tumor-frontend` | nginx:1.27-alpine | ~40 MB | React SPA |

### Multi-stage build summary

**AI Service** (`ai-service/Dockerfile`):
- `builder` — installs Python wheels into `/install` prefix
- `runtime` — python:3.12-slim + copied wheels + app source

**Backend** (`docker/Dockerfile.backend`):
- `deps` — `npm ci --omit=dev` (production deps only)
- `builder` — full install + native module compilation (better-sqlite3)
- `runtime` — node:20-slim + compiled node_modules

**Frontend** (`docker/Dockerfile.frontend`):
- `builder` — node:20-slim + `npm ci` + `npm run build` (Vite)
- `runtime` — nginx:1.27-alpine + compiled `/dist`

---

## Compose Files

| File | Purpose |
|---|---|
| `docker/docker-compose.yml` | Base — shared service definitions, volumes, networks |
| `docker/docker-compose.dev.yml` | Dev overlay — bind mounts, hot reload, Vite dev server |
| `docker/docker-compose.prod.yml` | Prod overlay — resource limits, secrets, security options |
| `docker/docker-compose.override.yml` | Local override — loaded automatically, developer tweaks |

### Combining files

```bash
# Development
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.dev.yml \
  up --build

# Production
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  up -d
```

---

## Named Volumes

| Volume | Contents | Shared by |
|---|---|---|
| `models_volume` | Keras `.keras` weights | ai-service (rw) |
| `dataset_volume` | Raw + processed MRI images | ai-service (rw), backend (ro) |
| `uploads_volume` | User-uploaded scans (Multer) | backend (rw) |
| `db_volume` | SQLite database file | backend (rw) |
| `gradcam_volume` | Grad-CAM heatmap PNGs | ai-service (rw), backend (ro) |
| `ai_logs_volume` | AI service rotating logs | ai-service (rw) |
| `backend_logs_volume` | Winston logs | backend (rw) |

---

## Building Images Manually

```bash
# AI service (from repo root)
docker build \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.0.0 \
  -t brain-tumor-ai-service:1.0.0 \
  ./ai-service

# Backend
docker build \
  -f docker/Dockerfile.backend \
  --build-arg VERSION=1.0.0 \
  -t brain-tumor-backend:1.0.0 \
  .

# Frontend (with production API URLs)
docker build \
  -f docker/Dockerfile.frontend \
  --build-arg VITE_API_BASE_URL=https://api.your-domain.com \
  --build-arg VITE_AI_SERVICE_URL=https://ai.your-domain.com \
  --build-arg VERSION=1.0.0 \
  -t brain-tumor-frontend:1.0.0 \
  .
```

---

## Nginx Configuration

Two nginx configuration files:

**`docker/nginx.conf`** — SPA-only config (used by the frontend image standalone)
- Serves React from `/usr/share/nginx/html`
- SPA fallback routing (`try_files $uri /index.html`)
- Gzip compression
- Security headers

**`docker/nginx/default.conf`** — Full reverse proxy config
- Proxies `/api/*` → `backend:5000`
- Proxies `/ai/*` → `ai-service:8000`
- Rate limiting zones per endpoint type
- HTTPS-ready (TLS block commented out)

### Enabling HTTPS

1. Mount TLS certificates into the container:
```yaml
# docker-compose.prod.yml addition
frontend:
  volumes:
    - /etc/letsencrypt/live/your-domain.com:/etc/nginx/certs:ro
```

2. Uncomment the HTTPS server block in `docker/nginx/default.conf`.

3. Update `ALLOWED_ORIGINS` in `ai-service/.env` to the HTTPS URL.

---

## Health Checks

All three services have Docker health checks configured:

| Service | Probe | Interval | Start period |
|---|---|---|---|
| ai-service | `curl -f http://localhost:8000/api/v1/health` | 30s | 90s |
| backend | `curl -f http://localhost:5000/health` | 30s | 20s |
| frontend | `curl -f http://localhost:8080/nginx-health` | 30s | 10s |

The AI service has a 90-second start period because TensorFlow model loading is slow.

---

## Common Commands

```bash
# View container status
docker compose -f docker/docker-compose.yml ps

# Tail all logs
docker compose -f docker/docker-compose.yml logs -f

# Tail AI service only
docker compose -f docker/docker-compose.yml logs -f ai-service

# Open a shell in the AI service
docker compose -f docker/docker-compose.yml exec ai-service bash

# Restart a single service
docker compose -f docker/docker-compose.yml restart ai-service

# Force rebuild one service
docker compose -f docker/docker-compose.yml \
  up --build --force-recreate ai-service -d

# Remove containers (keep volumes)
docker compose -f docker/docker-compose.yml down

# Remove containers AND volumes (destroys data!)
docker compose -f docker/docker-compose.yml down -v

# Prune unused Docker resources
docker system prune -f && docker volume prune -f
```
