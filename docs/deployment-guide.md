# Deployment Guide

Brain Tumour Detection — Production deployment reference.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Docker Deployment](#docker-deployment)
5. [Development Stack](#development-stack)
6. [Production Stack](#production-stack)
7. [Smoke Testing](#smoke-testing)
8. [Rollback Procedure](#rollback-procedure)
9. [Backup & Restore](#backup--restore)

---

## Architecture Overview

```
Browser
  │
  ▼
nginx (port 3000 → 8080 inside container)
  ├── /api/*    → backend:5000   (Node.js / Express)
  └── /ai/*     → ai-service:8000 (FastAPI / TensorFlow)

Shared volumes:
  models_volume   — Keras model weights
  dataset_volume  — Raw + processed MRI images
  uploads_volume  — User-uploaded scans
  db_volume       — SQLite database
  gradcam_volume  — Grad-CAM heatmaps
```

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Docker | 24.x |
| Docker Compose | v2.20 |
| Python | 3.12 (for local dev) |
| Node.js | 20 LTS (for local dev) |
| Git | 2.40 |

---

## Environment Setup

### 1. Copy environment templates

```bash
cp ai-service/.env.example  ai-service/.env
cp backend/.env.example     backend/.env
cp frontend/.env.example    frontend/.env.local
```

### 2. Configure secrets

Edit `ai-service/.env` and set a strong JWT secret:

```bash
# Generate a 64-char secret
python -c "import secrets; print(secrets.token_hex(32))"
```

```ini
# ai-service/.env
JWT_SECRET_KEY=<your-64-char-hex-string>
AI_SERVICE_ENV=production
AI_SERVICE_DEBUG=false
ALLOWED_ORIGINS=https://your-domain.com
```

### 3. Validate configuration

```bash
./scripts/validate-env.sh --env production
# Windows:
.\scripts\validate-env.ps1 -Environment production
```

---

## Docker Deployment

### Development (with hot-reload)

```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.dev.yml \
               up --build
```

Services:
- Frontend dev server: http://localhost:5173
- Backend:             http://localhost:5000
- AI Service:          http://localhost:8000
- API Docs:            http://localhost:8000/docs

### Production

```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.prod.yml \
               up -d --build
```

Or use the deployment script:

```bash
./scripts/deploy.sh --env production --version v1.2.3
# Windows:
.\scripts\deploy.ps1 -Environment production -Version v1.2.3
```

Services (production):
- App:       http://localhost:3000  (nginx → React SPA)
- Backend:   http://localhost:5000  (Express API)
- AI:        http://localhost:8000  (FastAPI)

---

## Development Stack

The dev compose file (`docker-compose.dev.yml`) uses bind-mounts so code changes inside the
`ai-service/app/` and `backend/` directories are reflected immediately without rebuilding.

The AI service runs with `--reload` (uvicorn), and the frontend uses the Vite dev server
with HMR on port 5173.

```bash
# Tail logs
docker compose -f docker/docker-compose.yml logs -f ai-service

# Open a shell in a running container
docker compose -f docker/docker-compose.yml exec ai-service bash
```

---

## Production Stack

### Docker Secrets

Create secret files (git-ignored):

```bash
mkdir -p docker/secrets
python -c "import secrets; print(secrets.token_hex(32))" > docker/secrets/jwt_secret_key.txt
python -c "import secrets; print(secrets.token_hex(16))" > docker/secrets/db_encryption_key.txt
```

The production compose file reads these as Docker secrets mounted at `/run/secrets/`.

### Resource limits

Defined in `docker/docker-compose.prod.yml`:

| Service | CPU limit | Memory limit |
|---|---|---|
| ai-service | 2.0 cores | 4 GB |
| backend | 1.0 core | 512 MB |
| frontend | 0.5 cores | 128 MB |

Adjust based on your server capacity.

---

## Smoke Testing

After deploying, verify all services are healthy:

```bash
# AI service health
curl http://localhost:8000/api/v1/health

# Backend health  
curl http://localhost:5000/health

# Frontend / nginx
curl http://localhost:3000/nginx-health
```

Expected AI response:
```json
{"success": true, "status": "ok", "service": "Brain Tumour Detection AI Service"}
```

---

## Rollback Procedure

The deploy script saves a backup of image digests before each deploy.

```bash
# Automatic rollback to previous version
./scripts/deploy.sh --rollback
# Windows:
.\scripts\deploy.ps1 -Rollback
```

To roll back to a specific version manually:

```bash
export APP_VERSION=v1.1.0
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.prod.yml \
               up -d --no-build
```

---

## Backup & Restore

### Create a backup

```bash
./scripts/backup.sh
# Saves compressed archives to .backups/backup_YYYYMMDD_HHMMSS/
```

### Restore from backup

```bash
# Restore all volumes from the latest backup
./scripts/restore.sh --latest

# Restore a specific backup
./scripts/restore.sh --backup .backups/backup_20240715_120000

# Restore only the database
./scripts/restore.sh --latest --volume db
```

Backups are retained for the last 5 runs automatically. Back up to off-site storage
(S3, Backblaze, etc.) for production disaster recovery.
