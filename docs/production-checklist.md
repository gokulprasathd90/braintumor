# Production Deployment Checklist

Work through this checklist before every production deployment.

---

## Pre-Deployment

### Security
- [ ] `JWT_SECRET_KEY` is a random 64+ character string (not the default placeholder)
- [ ] `AI_SERVICE_DEBUG=false` in `ai-service/.env`
- [ ] `NODE_ENV=production` in `backend/.env`
- [ ] `ALLOWED_ORIGINS` lists specific domains only (no wildcard `*`)
- [ ] `PREDICTION_AUTH_MODE=authenticated` (or `public` if intentional)
- [ ] Docker secrets files created in `docker/secrets/` (not committed to git)
- [ ] `docker/secrets/` is listed in `.gitignore` ✓
- [ ] TLS certificates mounted and HTTPS server block enabled in nginx

### Environment
- [ ] All `.env` files present on the deployment host
- [ ] Validation script passes: `./scripts/validate-env.sh --env production`
- [ ] `ai-service/.env` CORS origins match production domain
- [ ] Database path points to a persistent volume (not ephemeral container filesystem)

### Infrastructure
- [ ] Deployment host has Docker 24+ and Docker Compose v2.20+
- [ ] Named volumes exist (or will be created on first `up`)
- [ ] Sufficient disk space: ≥ 10 GB free (models ~2 GB, images variable)
- [ ] Sufficient RAM: ≥ 5 GB (AI service needs ~2–4 GB for TF model)
- [ ] Firewall allows ports 3000 (frontend), 5000 (backend), 8000 (AI) — or 443/80 for HTTPS

### Backup
- [ ] Most recent backup exists and is verified: `./scripts/backup.sh`
- [ ] Backup was copied to off-site storage (S3, NAS, etc.)

---

## Deployment

- [ ] Pull latest code: `git pull origin main`
- [ ] Check CI is green on the commit being deployed
- [ ] Run: `./scripts/deploy.sh --env production --version v<X.Y.Z>`
- [ ] Deployment script completes without errors
- [ ] Containers show `healthy` in `docker compose ps`

---

## Post-Deployment Smoke Tests

```bash
# AI service
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool

# Backend
curl -s http://localhost:5000/health

# Frontend
curl -s http://localhost:3000/nginx-health
```

- [ ] AI service returns `"status": "ok"`
- [ ] Backend returns 200
- [ ] Frontend nginx returns `ok`
- [ ] Can log in and submit a prediction via the UI
- [ ] Grad-CAM heatmap renders correctly

---

## Monitoring

- [ ] Log rotation is configured (`json-file` driver with `max-size: 20m`)
- [ ] Error rate is not elevated in logs: `docker compose logs --tail=100 ai-service`
- [ ] CPU and memory usage within expected bounds: `docker stats`
- [ ] Disk usage for volumes is within capacity: `docker system df`

---

## Rollback Criteria

Initiate rollback if any of the following occur within 15 minutes of deployment:

- [ ] AI service health check fails or returns error status
- [ ] Error rate > 5% on the `/predict` endpoint
- [ ] Container restarts more than 3 times
- [ ] Critical security alert

Rollback command:
```bash
./scripts/deploy.sh --rollback
```

---

## Troubleshooting Guide

See [troubleshooting.md](./troubleshooting.md) for common issues and solutions.
