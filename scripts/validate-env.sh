#!/usr/bin/env bash
# ─── scripts/validate-env.sh ──────────────────────────────────────────────────
#
# Validates all environment files for completeness and security.
# Run before deploying to catch missing or insecure config early.
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more errors found
#
# Usage:
#   ./scripts/validate-env.sh [--env production]

set -euo pipefail

ENVIRONMENT="${1:-development}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0
WARNINGS=0

# ── Helpers ───────────────────────────────────────────────────────────────────
ok()   { echo "  ✓ $*"; }
fail() { echo "  ✗ $*" >&2; ERRORS=$((ERRORS + 1)); }
warn() { echo "  ⚠ $*"; WARNINGS=$((WARNINGS + 1)); }

check_file_exists() {
  local path="$1" example="$2"
  if [[ -f "$path" ]]; then
    ok "File exists: $path"
  else
    fail "Missing: $path (copy from ${example})"
  fi
}

check_var_set() {
  local file="$1" var="$2" required="${3:-true}"
  if grep -qE "^${var}=.+" "$file" 2>/dev/null; then
    ok "${var} is set"
  elif [[ "$required" == "true" ]]; then
    fail "${var} is not set in $file"
  else
    warn "${var} is not set (optional) in $file"
  fi
}

check_var_not_default() {
  local file="$1" var="$2" default_val="$3"
  local actual
  actual=$(grep -oP "(?<=${var}=).*" "$file" 2>/dev/null | head -1 || echo "")
  if [[ "$actual" == "$default_val" ]]; then
    fail "${var} is still the default value in $file — must be changed for ${ENVIRONMENT}"
  else
    ok "${var} is not the default value"
  fi
}

check_var_min_length() {
  local file="$1" var="$2" min_len="$3"
  local actual
  actual=$(grep -oP "(?<=${var}=).*" "$file" 2>/dev/null | head -1 || echo "")
  if [[ ${#actual} -ge $min_len ]]; then
    ok "${var} length OK (${#actual} chars)"
  else
    fail "${var} is too short (${#actual} chars, minimum ${min_len})"
  fi
}

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Environment Validation — Brain Tumour Detection"
echo "  Target: ${ENVIRONMENT}"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── AI Service ────────────────────────────────────────────────────────────────
echo "── AI Service (.env) ────────────────────────────────────"
AI_ENV="${REPO_ROOT}/ai-service/.env"
check_file_exists "$AI_ENV" "ai-service/.env.example"

if [[ -f "$AI_ENV" ]]; then
  check_var_set "$AI_ENV" "AI_SERVICE_HOST"
  check_var_set "$AI_ENV" "AI_SERVICE_PORT"
  check_var_set "$AI_ENV" "ACTIVE_MODEL"
  check_var_set "$AI_ENV" "JWT_SECRET_KEY"
  check_var_set "$AI_ENV" "CLASS_NAMES"
  check_var_set "$AI_ENV" "LOG_LEVEL"

  if [[ "$ENVIRONMENT" == "production" ]]; then
    check_var_not_default "$AI_ENV" "JWT_SECRET_KEY" \
      "change-me-in-production-use-a-long-random-secret"
    check_var_min_length "$AI_ENV" "JWT_SECRET_KEY" 32

    # Check AI_SERVICE_DEBUG is false
    if grep -qE "^AI_SERVICE_DEBUG=true" "$AI_ENV"; then
      fail "AI_SERVICE_DEBUG=true in production — must be false"
    else
      ok "AI_SERVICE_DEBUG is not true"
    fi

    # Check ALLOWED_ORIGINS is not wildcard
    if grep -qE "^ALLOWED_ORIGINS=\*" "$AI_ENV"; then
      fail "ALLOWED_ORIGINS=* in production — specify exact origins"
    else
      ok "ALLOWED_ORIGINS is not a wildcard"
    fi
  fi
fi

echo ""

# ── Backend ───────────────────────────────────────────────────────────────────
echo "── Backend (.env) ────────────────────────────────────────"
BE_ENV="${REPO_ROOT}/backend/.env"
check_file_exists "$BE_ENV" "backend/.env.example"

if [[ -f "$BE_ENV" ]]; then
  check_var_set "$BE_ENV" "PORT"
  check_var_set "$BE_ENV" "NODE_ENV"
  check_var_set "$BE_ENV" "AI_SERVICE_URL"
  check_var_set "$BE_ENV" "FRONTEND_URL"

  if [[ "$ENVIRONMENT" == "production" ]]; then
    if grep -qE "^NODE_ENV=development" "$BE_ENV"; then
      fail "NODE_ENV=development in production — must be production"
    else
      ok "NODE_ENV is not development"
    fi
  fi
fi

echo ""

# ── Frontend ──────────────────────────────────────────────────────────────────
echo "── Frontend (.env.local) ─────────────────────────────────"
FE_ENV="${REPO_ROOT}/frontend/.env.local"
FE_ENV_EXAMPLE="${REPO_ROOT}/frontend/.env.example"
if [[ -f "$FE_ENV" ]]; then
  check_var_set "$FE_ENV" "VITE_AI_SERVICE_URL" "false"
  check_var_set "$FE_ENV" "VITE_APP_NAME" "false"
  ok "Frontend .env.local present"
elif [[ -f "$FE_ENV_EXAMPLE" ]]; then
  warn "Frontend .env.local missing — using .env.example defaults (OK for Docker builds)"
else
  warn "No frontend env file found (OK if using docker build-args only)"
fi

echo ""

# ── Docker secrets directory ─────────────────────────────────────────────────
if [[ "$ENVIRONMENT" == "production" ]]; then
  echo "── Docker Secrets (docker/secrets/) ──────────────────────"
  SECRETS_DIR="${REPO_ROOT}/docker/secrets"
  if [[ -d "$SECRETS_DIR" ]]; then
    check_file_exists "${SECRETS_DIR}/jwt_secret_key.txt"     "docker/secrets/"
    check_file_exists "${SECRETS_DIR}/db_encryption_key.txt"  "docker/secrets/"
    # Ensure secrets are not tracked by git
    if git -C "$REPO_ROOT" ls-files "${SECRETS_DIR}" 2>/dev/null | grep -q .; then
      fail "docker/secrets/ is tracked by git — add to .gitignore immediately!"
    else
      ok "docker/secrets/ is not tracked by git"
    fi
  else
    warn "docker/secrets/ not found — required for production Docker Compose secrets"
  fi
  echo ""
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════"
if [[ $ERRORS -eq 0 ]]; then
  echo "  ✓ Validation passed (${WARNINGS} warning(s))"
  echo "═══════════════════════════════════════════════════════"
  exit 0
else
  echo "  ✗ Validation FAILED: ${ERRORS} error(s), ${WARNINGS} warning(s)"
  echo "═══════════════════════════════════════════════════════"
  exit 1
fi
