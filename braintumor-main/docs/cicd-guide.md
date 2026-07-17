# CI/CD Guide

Brain Tumour Detection — Continuous Integration and Deployment reference.

---

## Overview

The project uses GitHub Actions for CI/CD with three workflows:

| Workflow | File | Trigger |
|---|---|---|
| CI | `.github/workflows/ci.yml` | Push to main/develop, PRs |
| CD | `.github/workflows/cd.yml` | Push to main (staging), GitHub Release (production) |
| Release | `.github/workflows/release.yml` | Version tags (`v*.*.*`) |

---

## CI Pipeline

### Jobs (parallel where independent)

```
lint-ai          lint-frontend    lint-backend
     │                 │               │
     ▼                 ▼               ▼
test-ai          test-frontend    test-backend
          └──────────┴───────────────┘
                        │
                        ▼
                  docker-build  (all 3 images in matrix)
                        │
                        ▼
                 security-scan
                        │
                        ▼
                   ci-summary  ← gate job (all must pass)
```

### Python linting

```bash
# ruff — linter + import sorter
ruff check app/ tests/ --output-format=github

# black — formatter check
black --check --diff app/ tests/

# isort — import order check
isort --check-only --diff app/ tests/
```

### Frontend linting

```bash
npx tsc --noEmit              # TypeScript type-check
npm run lint -- --max-warnings=0  # ESLint
npx prettier --check "src/**/*.{ts,tsx,css,json}"  # Prettier
```

### Test coverage thresholds

| Suite | Tool | Minimum coverage |
|---|---|---|
| AI Service (Python) | pytest-cov | 70% |
| Frontend | vitest --coverage | (reported) |
| Backend | jest | (reported) |

### Docker image matrix

Three images are built in parallel:
- `ghcr.io/<owner>/brain-tumor-ai-service`
- `ghcr.io/<owner>/brain-tumor-backend`
- `ghcr.io/<owner>/brain-tumor-frontend`

Images are **only pushed** on non-PR runs (push to main/develop/release/*).

Layer caching uses GitHub Actions cache (`type=gha`) per image scope.

---

## CD Pipeline

### Staging (automatic on push to main)

Every merge to `main` triggers a staging deployment:
1. Resolve image version (short SHA)
2. Copy compose files to staging server via SCP
3. SSH: pull images + `docker compose up -d`
4. Smoke-test the AI health endpoint

### Production (on GitHub Release)

When a GitHub Release is published, the CD workflow deploys to production using
the release tag as the image version.

### Manual deployment

```
GitHub → Actions → CD → Run workflow
  Environment: production
  Version: v1.2.3
```

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `DEPLOY_HOST_STAGING` | Staging server hostname/IP |
| `DEPLOY_HOST_PRODUCTION` | Production server hostname/IP |
| `DEPLOY_USER` | SSH username |
| `DEPLOY_SSH_KEY` | SSH private key (PEM) |
| `DEPLOY_PATH` | Remote deployment path (e.g. `/opt/brain-tumor`) |
| `JWT_SECRET_KEY` | AI service JWT secret |
| `SLACK_WEBHOOK` | Slack notifications (optional) |

---

## Release Workflow

### Creating a release

```bash
# Using the bump-version script (recommended)
./scripts/bump-version.sh patch      # 1.0.0 → 1.0.1
./scripts/bump-version.sh minor      # 1.0.0 → 1.1.0
./scripts/bump-version.sh major      # 1.0.0 → 2.0.0
./scripts/bump-version.sh 1.2.3      # explicit version

# Then push to trigger the release workflow
git push origin main && git push origin v1.0.1
```

### What the release workflow does

1. Parses the version tag (detects pre-releases like `v1.0.0-rc.1`)
2. Builds and pushes versioned Docker images to GHCR with tags:
   - `1.2.3` — exact version
   - `1.2` — major.minor
   - `1` — major
   - `latest` — only for stable releases (not pre-releases)
3. Generates a changelog from conventional commits
4. Creates a GitHub Release with release notes and compose files attached

### Conventional commit format

Used by the changelog generator:

```
feat(inference): add ZIP batch prediction endpoint
fix(auth): prevent token refresh after account lockout
docs(api): update /predict endpoint documentation
chore(deps): bump tensorflow to 2.20.0
```

---

## Running CI Locally

Install [act](https://github.com/nektos/act) to run GitHub Actions locally:

```bash
# Install act
brew install act   # macOS
# or download from https://github.com/nektos/act

# Run the CI workflow
act push --job lint-ai
act push --job test-ai
act push --job docker-build
```

Or run the checks directly:

```bash
# Python
cd ai-service
pip install -r requirements-dev.txt
ruff check app/ tests/
black --check app/ tests/
pytest -v tests/

# Frontend
cd frontend
npm ci
npm run type-check
npm run lint
npm run test
```
