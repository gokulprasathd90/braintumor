# Troubleshooting Guide

Common issues and solutions for Brain Tumour Detection deployment.

---

## Container Issues

### AI service container keeps restarting

**Symptoms:** `docker compose ps` shows ai-service as `Restarting`

**Causes and fixes:**

1. **JWT_SECRET_KEY is default value** — The entrypoint script aborts with:
   ```
   [AI-SERVICE] ERROR: JWT_SECRET_KEY is still the default placeholder!
   ```
   Fix: Set a strong JWT secret in `ai-service/.env`.

2. **TensorFlow import fails** — Usually a dependency mismatch:
   ```bash
   docker compose logs ai-service | grep "ImportError"
   docker compose exec ai-service python -c "import tensorflow"
   ```
   Fix: Rebuild the image to reinstall dependencies: `docker compose build --no-cache ai-service`

3. **Port 8000 already in use:**
   ```bash
   lsof -i :8000   # Linux/macOS
   netstat -ano | findstr :8000  # Windows
   ```
   Fix: Stop the conflicting process or change `AI_SERVICE_PORT` in `.env`.

---

### Container is unhealthy

**Check the health check output:**
```bash
docker inspect bt_ai_service | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d[0]['State']['Health'], indent=2))"
```

**AI service start_period** is 90 seconds — wait before declaring it broken.
TensorFlow model loading takes 30–60 seconds on first startup.

---

### "No space left on device" error

```bash
docker system df        # show space usage
docker system prune -f  # remove stopped containers, dangling images
docker volume prune -f  # WARNING: removes unused volumes (data loss risk)
```

For production, never prune named volumes. Only prune anonymous volumes.

---

## Build Issues

### `pip install` fails during Docker build

Usually a network timeout or package version conflict:

```bash
# Try with --no-cache
docker compose build --no-cache ai-service

# Check for incompatible pinned versions
docker compose exec ai-service pip check
```

### `npm ci` fails: `package-lock.json` mismatch

```bash
# Regenerate lockfile locally and commit
cd frontend && npm install && git add package-lock.json
```

---

## Nginx Issues

### Frontend returns 502 Bad Gateway for `/api/` requests

Nginx is running but cannot reach the backend. Check:

```bash
# Is backend healthy?
docker compose ps backend

# Can nginx reach backend? (test from within frontend container)
docker compose exec frontend curl -f http://backend:5000/health
```

Common fix: Backend container not yet healthy when nginx starts. Add `depends_on` with health condition, or increase nginx `proxy_connect_timeout`.

### Static assets return 404

The Vite build output is not in `/usr/share/nginx/html`. Check the build stage:

```bash
docker compose exec frontend ls /usr/share/nginx/html
```

If empty, the frontend `npm run build` failed silently. Rebuild with:
```bash
docker compose build --no-cache --progress=plain frontend 2>&1 | tail -50
```

### nginx: bind() to 0.0.0.0:80 failed: Permission denied

The frontend container runs as non-root (uid 1001) and cannot bind port 80. The image correctly uses port **8080** internally. The external port mapping is `3000:8080` in `docker-compose.yml`. If you see this error, your nginx.conf still uses `listen 80` — update to `listen 8080`.

---

## Security Issues

### Login endpoint always returns 401

1. Check that the user exists: POST `/api/v1/auth/register` first.
2. In tests, ensure `BCRYPT_ROUNDS=4` is set (the default of 12 is too slow for tests).
3. Check rate limiting is not blocking: `docker compose logs ai-service | grep "429"`.

### JWT token rejected after deployment

If you changed `JWT_SECRET_KEY`, all existing tokens are invalidated. Users must log in again. This is expected behaviour.

---

## CI/CD Issues

### GitHub Actions: Docker push fails (unauthorized)

Ensure the workflow has `packages: write` permission:

```yaml
permissions:
  contents: read
  packages: write
```

### pytest coverage below threshold

```bash
# Run with coverage locally to see which modules are uncovered
cd ai-service
pytest --cov=app --cov-report=term-missing tests/
```

### Trivy scan blocks CI

Trivy found a HIGH/CRITICAL CVE. Options:
1. Update the affected dependency in `requirements.txt` or `package.json`.
2. Add a `.trivyignore` file with the CVE ID if it's a false positive.
3. Set `ignore-unfixed: true` in the trivy-action config.

---

## Performance Issues

### AI service is slow (>5 seconds per prediction)

1. **Model not cached:** First request loads from disk. Subsequent requests use LRU cache.
2. **Too few uvicorn workers:** Increase `UVICORN_WORKERS` in `.env` (default: 2).
3. **CPU throttling:** Check resource limits in `docker-compose.prod.yml`. The AI service needs at least 1 full CPU core for TF inference.
4. **Image is too large:** Ensure `IMAGE_SIZE=224` not accidentally set to 512+.

### High memory usage

TensorFlow loads model weights into RAM. Expected usage per model:
- EfficientNetB0: ~150 MB
- ResNet50: ~200 MB
- VGG16: ~550 MB

If usage grows unboundedly, check for memory leaks in the inference pipeline. The LRU cache capacity is 4 models max.

---

## Getting Help

1. Check container logs: `docker compose logs --tail=100 <service>`
2. Open a shell: `docker compose exec <service> bash`
3. Check the [Deployment Guide](./deployment-guide.md)
4. Check the [CI/CD Guide](./cicd-guide.md)
5. Open an issue on GitHub with the output of:
   ```bash
   docker compose ps
   docker compose logs --tail=50
   ./scripts/validate-env.sh
   ```
