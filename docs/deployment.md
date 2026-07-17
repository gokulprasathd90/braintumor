# Deployment Guide

Brain Tumour Detection — production deployment reference for Docker, CI/CD, and cloud environments.

> For existing Docker and CI/CD specifics see also [docker-guide.md](docker-guide.md) and [cicd-guide.md](cicd-guide.md).

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Docker Deployment](#docker-deployment)
5. [Production Configuration](#production-configuration)
6. [Nginx Reverse Proxy](#nginx-reverse-proxy)
7. [SSL / HTTPS](#ssl--https)
8. [Health Checks](#health-checks)
9. [Deployment Script](#deployment-script)
10. [CI/CD Pipeline](#cicd-pipeline)
11. [Scaling Considerations](#scaling-considerations)
12. [Backup & Restore](#backup--restore)
13. [Rollback Procedure](#rollback-procedure)
14. [Monitoring in Production](#monitoring-in-production)
15. [Production Checklist](#production-checklist)

---

## Overview

The application ships as three Docker containers coordinated by Docker Compose:

```
nginx (port 80/443)
  ├── /          → frontend:8080   (nginx static + React SPA)
  ├── /api/*     → backend:5000    (Node.js / Express)
  └── /ai/*      → ai-service:8000 (FastAPI / TensorFlow)
```

Persistent state lives in five named Docker volumes:

| Volume | Contents |
|---|---|
| `models_volume` | Trained Keras model weights |
| `dataset_volume` | Raw and processed MRI images |
| `uploads_volume` | User-uploaded scan files |
| `db_volume` | SQLite database |
| `gradcam_volume` | Generated Grad-CAM heatmaps |
| `logs_volume` | Application and audit logs |

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Docker | 24.x |
| Docker Compose | v2.20 |
| Git | 2.40 |
| openssl | any (for secret generation) |

---

## Environment Setup

### 1. Clone the repository on your server

```bash
git clone https://github.com/your-org/brain-tumor-detection.git
cd brain-tumor-detection
```

### 2. Copy production environment templates

```bash
cp ai-service/.env.example  ai-service/.env
cp backend/.env.example     backend/.env
cp frontend/.env.example    frontend/.env.local
```

### 3. Generate secrets

```bash
# JWT secret (minimum 32 characters)
JWT_SECRET=$(openssl rand -hex 32)
echo "JWT_SECRET_KEY=$JWT_SECRET" >> ai-service/.env
```

### 4. Edit each .env file

**`ai-service/.env` — minimum production changes:**
```ini
AI_SERVICE_ENV=production
AI_SERVICE_DEBUG=false
JWT_SECRET_KEY=<generated-above>
ALLOWED_ORIGINS=https://yourdomain.com
BCRYPT_ROUNDS=12
LOG_LEVEL=INFO
```

**`backend/.env` — minimum production changes:**
```ini
NODE_ENV=production
PORT=5000
FRONTEND_URL=https://yourdomain.com
AI_SERVICE_URL=http://ai-service:8000
```

**`frontend/.env.local` — minimum production changes:**
```ini
VITE_API_BASE_URL=https://yourdomain.com/api
VITE_AI_SERVICE_URL=https://yourdomain.com/ai
VITE_APP_NAME=Brain Tumour Detection
```

---

## Docker Deployment

### Development stack

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

### Production stack

```bash
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  up --build -d
```

The production override enables:
- Restart policies (`always`)
- Production resource limits
- Reduced log verbosity
- nginx SSL configuration

### Using the deploy script

```bash
# Linux / macOS
bash scripts/deploy.sh production

# Windows PowerShell
.\scripts\deploy.ps1 -Environment production
```

The deploy script:
1. Validates all `.env` files
2. Pulls or builds updated images
3. Performs a rolling restart (zero-downtime where possible)
4. Runs post-deploy smoke tests
5. Rolls back automatically on failure

---

## Production Configuration

### AI Service production settings

```ini
AI_SERVICE_ENV=production
AI_SERVICE_DEBUG=false
AI_SERVICE_WORKERS=2          # uvicorn worker count
PREDICTION_AUTH_MODE=authenticated   # require JWT for inference
RATE_LIMIT_PREDICTION=30      # tighter in production
LOG_LEVEL=WARNING
```

### Uvicorn workers

In production the AI service runs with multiple workers:

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --proxy-headers \
  --forwarded-allow-ips='*'
```

Adjust `--workers` based on CPU cores: `workers = (2 × CPU_cores) + 1` is a common starting point, but memory-limited by TensorFlow model weights (~500 MB per worker for EfficientNet).

### Backend production settings

```ini
NODE_ENV=production
LOG_LEVEL=warn
```

Express disables stack traces in error responses when `NODE_ENV=production`.

---

## Nginx Reverse Proxy

The `docker/` directory includes an nginx configuration. Key directives:

```nginx
# Gzip compression
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# Security headers
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000" always;

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;

# Proxy to backend
location /api/ {
    proxy_pass         http://backend:5000;
    proxy_http_version 1.1;
    proxy_set_header   Host $host;
    proxy_set_header   X-Real-IP $remote_addr;
    proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;      # allow long training requests
    client_max_body_size 50M;     # allow large MRI file uploads
}

# Proxy to AI service
location /ai/ {
    proxy_pass         http://ai-service:8000/;
    proxy_http_version 1.1;
    proxy_set_header   Host $host;
    proxy_read_timeout 600s;      # training can take 10+ minutes
    client_max_body_size 50M;
}
```

---

## SSL / HTTPS

### Using Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (runs daily)
sudo systemctl enable certbot.timer
```

### Using existing certificates

Place your certificate files in `docker/ssl/`:
```
docker/ssl/
├── cert.pem
└── key.pem
```

Update the nginx configuration to reference these paths and expose port 443 in `docker-compose.prod.yml`.

---

## Health Checks

All three services expose health check endpoints used by Docker:

| Service | Health Check URL | Interval | Timeout | Retries |
|---|---|---|---|---|
| AI Service | `GET /api/v1/health` | 30s | 10s | 3 |
| Backend | `GET /api/health` | 30s | 5s | 3 |
| Frontend | `GET /` | 30s | 5s | 3 |

The AI service `start_period` is set to **90 seconds** — TensorFlow needs time to load on first startup.

Check container health:
```bash
docker compose ps
docker inspect bt_ai_service | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d[0]['State']['Health']['Status'])"
```

---

## Deployment Script

`scripts/deploy.sh` (and `scripts/deploy.ps1` for Windows) accepts an environment argument:

```bash
# Deploy to staging
bash scripts/deploy.sh staging

# Deploy to production
bash scripts/deploy.sh production

# Dry run (validate only)
bash scripts/deploy.sh production --dry-run
```

The script performs these steps:
1. Validate environment files (`scripts/validate-env.sh`)
2. Pull latest code (`git pull`)
3. Build updated images
4. Create a pre-deploy backup of volumes
5. Start new containers with a rolling update strategy
6. Wait for all health checks to pass (90-second timeout)
7. Run smoke tests against the live endpoints
8. If any check fails: automatic rollback to previous containers

---

## CI/CD Pipeline

Three GitHub Actions workflows automate the delivery pipeline:

### `ci.yml` — Continuous Integration

Triggers on every push and PR to `main` and `develop`.

| Job | What it does |
|---|---|
| `lint-ai` | ruff + black + isort on Python code |
| `lint-frontend` | ESLint + Prettier + TypeScript type check |
| `lint-backend` | ESLint on Node.js code |
| `test-ai` | pytest with coverage |
| `test-frontend` | Vitest run with coverage |
| `test-backend` | Jest with Supertest |
| `docker-build` | Builds all three images (multi-arch on main) |
| `security-scan` | Trivy vulnerability scan on built images |

### `cd.yml` — Continuous Deployment

| Trigger | Action |
|---|---|
| Push to `main` | Auto-deploy to staging environment |
| Release tag (`v*.*.*`) | Deploy to production |
| Manual dispatch | Deploy to any environment on demand |

### `release.yml` — Release Automation

Triggers on Git tags matching `v*.*.*`:
1. Builds versioned Docker images and pushes to GHCR
2. Creates a GitHub Release with changelog excerpt
3. Attaches the release bundle as a downloadable asset

---

## Scaling Considerations

### Horizontal scaling (multiple AI service instances)

The current architecture uses an in-process token revocation set. Before horizontally scaling the AI service:

1. Replace the in-process revocation set with a Redis store in `app/security/jwt.py`
2. Move the model cache to a shared filesystem or object store
3. Use a load balancer in front of multiple AI service instances

### Vertical scaling

For GPU-accelerated inference:
- Add NVIDIA Container Toolkit to the host
- Add GPU device reservation to `docker-compose.prod.yml`
- Set `CUDA_VISIBLE_DEVICES=0` in `ai-service/.env`

### Database scaling

SQLite is appropriate for single-server deployments. For higher write throughput:
1. Migrate to PostgreSQL by swapping `better-sqlite3` for `pg` in the backend
2. Update `database/schema.sql` for PostgreSQL dialect
3. Update the connection string in `backend/.env`

---

## Backup & Restore

### Create a backup

```bash
bash scripts/backup.sh

# Output: backups/brain-tumor-backup-YYYY-MM-DD-HHMMSS.tar.gz
# Includes: models_volume, dataset_volume, db_volume, uploads_volume
```

### Restore from backup

```bash
bash scripts/restore.sh backups/brain-tumor-backup-2026-07-14-120000.tar.gz
```

The restore script:
1. Stops running containers
2. Restores each named volume from the archive
3. Restarts containers
4. Runs health checks

### Backup schedule (cron)

```bash
# Daily backup at 2am
0 2 * * * /opt/brain-tumor-detection/scripts/backup.sh >> /var/log/bt-backup.log 2>&1

# Keep backups for 30 days
0 3 * * * find /opt/brain-tumor-detection/backups -mtime +30 -delete
```

---

## Rollback Procedure

### Automatic rollback

The deploy script rolls back automatically if health checks fail within 90 seconds of deployment.

### Manual rollback

```bash
# List available image tags
docker images | grep brain-tumor

# Rollback to a specific tag
docker compose down
docker tag brain-tumor-ai:previous brain-tumor-ai:latest
docker tag brain-tumor-backend:previous brain-tumor-backend:latest
docker compose up -d
```

### Rollback to a git revision

```bash
git log --oneline -10
git checkout <commit-sha>
docker compose up --build -d
```

---

## Monitoring in Production

### Application logs

```bash
# Tail all logs
docker compose logs -f

# AI service only
docker compose logs -f ai-service

# Last 100 lines
docker compose logs --tail=100 ai-service
```

Log files are also written to the `logs_volume` and accessible at `ai-service/logs/`.

### Performance dashboard

The `/api/v1/performance/summary` endpoint provides a live JSON snapshot of all system metrics. The `/api/v1/performance/report/html` endpoint returns a self-contained HTML dashboard.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/performance/summary | python3 -m json.tool
```

### Audit logs

Security events are written to JSONL files at `logs/audit/`. Each line is a JSON object:

```json
{
  "timestamp": "2026-07-14T12:00:00Z",
  "event":     "LOGIN",
  "username":  "admin",
  "ip":        "203.0.113.42",
  "outcome":   "success"
}
```

---

## Production Checklist

See [production-checklist.md](production-checklist.md) for the full pre-launch checklist.

Quick reference:

- [ ] `JWT_SECRET_KEY` set to a strong random value (≥32 chars)
- [ ] `AI_SERVICE_ENV=production`
- [ ] `AI_SERVICE_DEBUG=false`
- [ ] `NODE_ENV=production`
- [ ] HTTPS configured and certificates valid
- [ ] Firewall rules — only ports 80 and 443 exposed publicly
- [ ] `ALLOWED_ORIGINS` set to your actual domain
- [ ] Backup schedule configured
- [ ] Health check endpoints responding
- [ ] All CI tests passing on the release commit
- [ ] Docker image vulnerability scan clean
- [ ] `PREDICTION_AUTH_MODE=authenticated` (if inference should be protected)
