# Release Checklist

Use this checklist for every release of Brain Tumour Detection. Work through it in order — do not skip sections. Check off each item only after it is confirmed complete.

---

## 1. Pre-Release Preparation

### Code Quality

- [ ] All feature branches merged to `develop`
- [ ] No open pull requests targeting this release
- [ ] All CI checks passing on `develop` (lint, test, build, security scan)
- [ ] No `TODO`, `FIXME`, or `HACK` comments introduced in this release
- [ ] No debug logging left enabled in production code paths

### Tests

- [ ] AI service pytest suite passing: `cd ai-service && pytest -v --tb=short`
- [ ] Backend Jest suite passing: `cd backend && npm test`
- [ ] Frontend Vitest suite passing: `cd frontend && npm test -- --run`
- [ ] Test coverage not regressed from previous release
- [ ] All new features covered by tests
- [ ] All bug fixes covered by regression tests

### Security

- [ ] `pip-audit` clean: `cd ai-service && pip-audit -r requirements.txt`
- [ ] `npm audit` clean (backend): `cd backend && npm audit --audit-level=high`
- [ ] `npm audit` clean (frontend): `cd frontend && npm audit --audit-level=high`
- [ ] No secrets or credentials in new code (check with `git log --diff-filter=A -p`)
- [ ] JWT secret key is not a default value in any environment file
- [ ] `.env` files not staged or committed
- [ ] Hadolint passes on all Dockerfiles

### Dependencies

- [ ] All Python dependencies pinned to exact versions in `requirements.txt`
- [ ] All Node dependencies have exact versions in `package-lock.json`
- [ ] No new transitive dependency introduces a known vulnerability

---

## 2. Version Bump

- [ ] Decide the new version number following [Semantic Versioning](https://semver.org/):
  - `MAJOR` — breaking API or model format changes
  - `MINOR` — new features, backward-compatible
  - `PATCH` — bug fixes, security patches
- [ ] Run version bump script: `./scripts/bump-version.sh <major|minor|patch>`
- [ ] Verify `VERSION` file updated
- [ ] Verify `build_info.json` updated
- [ ] Verify `release_manifest.json` updated
- [ ] Verify `package.json` versions updated in `backend/` and `frontend/`
- [ ] Verify `pyproject.toml` or `setup.cfg` version updated in `ai-service/` (if present)

---

## 3. Changelog and Documentation

- [ ] `CHANGELOG.md` — `[Unreleased]` section renamed to `[x.y.z] - YYYY-MM-DD`
- [ ] New `[Unreleased]` section added at the top of `CHANGELOG.md`
- [ ] Comparison URL at the bottom of `CHANGELOG.md` updated for the new tag
- [ ] `docs/release_notes.md` updated with a summary of this release
- [ ] All new API endpoints documented in `docs/api_reference.md`
- [ ] All new environment variables documented in `README.md` and `docs/installation.md`
- [ ] Breaking changes documented in `docs/release_notes.md` with upgrade instructions
- [ ] `README.md` badges and version references up to date

---

## 4. Docker Build Verification

- [ ] Clean Docker build succeeds (no cache): `make docker-build`
- [ ] All three containers start and reach healthy state: `make docker-up`
- [ ] Health endpoints respond:
  - `curl http://localhost:8000/api/v1/health` → `{"status": "healthy"}`
  - `curl http://localhost:5000/health` → HTTP 200
  - `curl http://localhost:3000` → HTTP 200
- [ ] AI service Swagger UI loads: `http://localhost:8000/docs`
- [ ] No errors in container logs: `make docker-logs`
- [ ] Docker images tagged correctly with the new version
- [ ] Image sizes not unexpectedly large (AI < 3 GB, backend < 200 MB, frontend < 50 MB)

---

## 5. Environment Validation

- [ ] `./scripts/validate-env.sh` passes against `.env.production` template
- [ ] `./scripts/validate-env.ps1` passes on Windows (if applicable)
- [ ] All required environment variables documented and have sensible defaults
- [ ] No development-only values left in `.env.production`

---

## 6. Release Package

- [ ] Release package built: `./scripts/package_release.sh`
- [ ] `release_manifest.json` generated and accurate
- [ ] Package archive validated (contains all required files)
- [ ] Archive tested by extracting to a clean directory and running setup

---

## 7. Git Tagging and Merge

- [ ] All changes committed to `develop`
- [ ] `develop` merged to `main` via pull request
- [ ] PR approved by at least one maintainer
- [ ] Merge commit is clean (no conflicts, no stray files)
- [ ] Git tag created: `git tag -a v1.x.y -m "Release v1.x.y"`
- [ ] Tag pushed: `git push origin v1.x.y`

---

## 8. GitHub Release

- [ ] GitHub release created from the tag
- [ ] Release title: `v1.x.y — <short description>`
- [ ] Release body: copy from `CHANGELOG.md` for this version
- [ ] Release package archive attached as a release asset
- [ ] `release_manifest.json` attached as a release asset
- [ ] Release marked as latest (unless it is a pre-release)
- [ ] For pre-releases: marked as `pre-release` in GitHub UI

---

## 9. Container Registry

- [ ] Docker images pushed to GHCR (handled by CD pipeline on tag push)
- [ ] Images tagged with:
  - `ghcr.io/your-org/brain-tumor-detection/ai-service:1.x.y`
  - `ghcr.io/your-org/brain-tumor-detection/ai-service:latest`
  - Same pattern for `backend` and `frontend`
- [ ] Images are publicly pullable (if public registry)
- [ ] CD pipeline run succeeded in GitHub Actions

---

## 10. Post-Release Verification

- [ ] Pull fresh images and run smoke test against released containers
- [ ] `/api/v1/health` returns `healthy` with the correct version
- [ ] Single image prediction endpoint returns a valid response
- [ ] Frontend loads and displays the correct app version
- [ ] No regressions reported within 24 hours of release

---

## 11. Post-Release Housekeeping

- [ ] Announce release in project Discussions or relevant channels
- [ ] Close all GitHub issues and milestones associated with this release
- [ ] Open a new milestone for the next release
- [ ] Update project board / roadmap
- [ ] Archive any release-specific branches

---

## Rollback Plan

If a critical issue is found after release:

1. Identify the last known-good tag (e.g., `v1.0.0`)
2. Run `./scripts/deploy.sh --env production --version v1.0.0` to roll back containers
3. Open a GitHub issue with `[REGRESSION]` in the title, linked to the broken release
4. Prepare a `PATCH` release following this checklist

---

*This checklist was last updated for release v1.0.0 (2026-07-14).*
