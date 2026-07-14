#!/usr/bin/env bash
# ─── scripts/bump-version.sh ──────────────────────────────────────────────────
#
# Bumps the semantic version across all manifests and creates a git tag.
#
# Usage:
#   ./scripts/bump-version.sh patch    # 1.0.0 → 1.0.1
#   ./scripts/bump-version.sh minor    # 1.0.0 → 1.1.0
#   ./scripts/bump-version.sh major    # 1.0.0 → 2.0.0
#   ./scripts/bump-version.sh 1.2.3   # explicit version
#   ./scripts/bump-version.sh --dry-run patch  # preview only

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=false
BUMP_TYPE=""
NEW_VERSION=""

# ── Parse arguments ───────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    major|minor|patch) BUMP_TYPE="$arg" ;;
    [0-9]*.[0-9]*.[0-9]*) NEW_VERSION="$arg" ;;
    *) echo "Usage: $0 [--dry-run] (major|minor|patch|X.Y.Z)"; exit 1 ;;
  esac
done

[[ -n "$BUMP_TYPE" || -n "$NEW_VERSION" ]] || { echo "Specify bump type: major, minor, patch, or X.Y.Z"; exit 1; }

# ── Get current version from pyproject.toml ────────────────────────────────────
CURRENT=$(grep -oP '(?<=^version = ")[^"]+' "${REPO_ROOT}/ai-service/pyproject.toml")
echo "Current version: ${CURRENT}"

# ── Calculate new version ─────────────────────────────────────────────────────
if [[ -n "$NEW_VERSION" ]]; then
  NEXT="$NEW_VERSION"
else
  IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
  case "$BUMP_TYPE" in
    major) NEXT="$((MAJOR + 1)).0.0" ;;
    minor) NEXT="${MAJOR}.$((MINOR + 1)).0" ;;
    patch) NEXT="${MAJOR}.${MINOR}.$((PATCH + 1))" ;;
  esac
fi

echo "New version:     ${NEXT}"
$DRY_RUN && echo "[DRY RUN] No files modified" && exit 0

# ── Update version in all manifests ──────────────────────────────────────────

# ai-service/pyproject.toml
sed -i "s/^version = \"${CURRENT}\"/version = \"${NEXT}\"/" \
  "${REPO_ROOT}/ai-service/pyproject.toml"
echo "  ✓ ai-service/pyproject.toml"

# frontend/package.json
sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"${NEXT}\"/" \
  "${REPO_ROOT}/frontend/package.json"
echo "  ✓ frontend/package.json"

# backend/package.json (if it exists)
if [[ -f "${REPO_ROOT}/backend/package.json" ]]; then
  sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"${NEXT}\"/" \
    "${REPO_ROOT}/backend/package.json"
  echo "  ✓ backend/package.json"
fi

# Update OCI label in Dockerfiles
for dockerfile in \
  "${REPO_ROOT}/ai-service/Dockerfile" \
  "${REPO_ROOT}/docker/Dockerfile.backend" \
  "${REPO_ROOT}/docker/Dockerfile.frontend"; do
  if [[ -f "$dockerfile" ]]; then
    sed -i "s/org.opencontainers.image.version=\"[^\"]*\"/org.opencontainers.image.version=\"${NEXT}\"/" \
      "$dockerfile" 2>/dev/null || true
  fi
done

# ── Generate CHANGELOG entry ──────────────────────────────────────────────────
CHANGELOG="${REPO_ROOT}/CHANGELOG.md"
TODAY=$(date +%Y-%m-%d)
PREV_TAG=$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || echo "")
RANGE="${PREV_TAG:+${PREV_TAG}..HEAD}"

{
  echo "# Changelog"
  echo ""
  echo "## [${NEXT}] - ${TODAY}"
  echo ""

  if [[ -n "$RANGE" ]]; then
    FEATS=$(git -C "$REPO_ROOT" log "$RANGE" --pretty=format:"%s" | grep -E "^feat" | sed 's/^feat[^:]*: /- /' || true)
    FIXES=$(git -C "$REPO_ROOT" log "$RANGE" --pretty=format:"%s" | grep -E "^fix"  | sed 's/^fix[^:]*: /- /'  || true)
    DOCS=$(git  -C "$REPO_ROOT" log "$RANGE" --pretty=format:"%s" | grep -E "^docs" | sed 's/^docs[^:]*: /- /' || true)

    [[ -n "$FEATS" ]] && echo "### Added" && echo "$FEATS" && echo ""
    [[ -n "$FIXES" ]] && echo "### Fixed" && echo "$FIXES" && echo ""
    [[ -n "$DOCS"  ]] && echo "### Documentation" && echo "$DOCS" && echo ""
  fi

  # Append existing changelog
  if [[ -f "$CHANGELOG" ]]; then
    tail -n +3 "$CHANGELOG"
  fi
} > "${CHANGELOG}.tmp" && mv "${CHANGELOG}.tmp" "$CHANGELOG"
echo "  ✓ CHANGELOG.md"

# ── Git commit and tag ────────────────────────────────────────────────────────
git -C "$REPO_ROOT" add \
  ai-service/pyproject.toml \
  frontend/package.json \
  CHANGELOG.md \
  2>/dev/null

[[ -f "${REPO_ROOT}/backend/package.json" ]] && \
  git -C "$REPO_ROOT" add backend/package.json 2>/dev/null || true

git -C "$REPO_ROOT" commit -m "chore(release): bump version to v${NEXT}" \
  --no-verify 2>/dev/null || echo "  (nothing to commit)"

git -C "$REPO_ROOT" tag -a "v${NEXT}" -m "Release v${NEXT}"

echo ""
echo "✓ Version bumped: ${CURRENT} → ${NEXT}"
echo "✓ Tag created:    v${NEXT}"
echo ""
echo "Push with:"
echo "  git push origin main && git push origin v${NEXT}"
