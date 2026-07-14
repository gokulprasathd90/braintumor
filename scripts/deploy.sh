#!/usr/bin/env bash
# ─── scripts/deploy.sh ────────────────────────────────────────────────────────
#
# Production deployment script for Brain Tumour Detection.
#
# Usage:
#   ./scripts/deploy.sh [OPTIONS]
#
# Options:
#   -e, --env        ENV    Target environment: staging | production (default: staging)
#   -v, --version    VER    Image version/tag to deploy (default: latest)
#   -n, --no-pull          Skip docker image pull (use locally built images)
#   -b, --build            Build images locally before deploying
#   -r, --rollback         Roll back to the previous version
#   -s, --status           Show current deployment status and exit
#   -h, --help             Show this help message
#
# Examples:
#   ./scripts/deploy.sh --env staging
#   ./scripts/deploy.sh --env production --version v1.2.3
#   ./scripts/deploy.sh --env staging --build
#   ./scripts/deploy.sh --rollback
#   ./scripts/deploy.sh --status

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'   GREEN='\033[0;32m'  YELLOW='\033[1;33m'
CYAN='\033[0;36m'  BOLD='\033[1m'      NC='\033[0m'

# ── Defaults ──────────────────────────────────────────────────────────────────
ENVIRONMENT="staging"
VERSION="latest"
NO_PULL=false
BUILD_IMAGES=false
ROLLBACK=false
STATUS_ONLY=false
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="${REPO_ROOT}/docker/docker-compose.yml"
COMPOSE_PROD="${REPO_ROOT}/docker/docker-compose.prod.yml"
BACKUP_DIR="${REPO_ROOT}/.backups"
LOG_FILE="${REPO_ROOT}/logs/deploy-$(date +%Y%m%d_%H%M%S).log"

# ── Logging helpers ───────────────────────────────────────────────────────────
info()    { echo -e "${CYAN}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
success() { echo -e "${GREEN}[OK]${NC}    $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2; }
die()     { error "$*"; exit 1; }

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--env)        ENVIRONMENT="$2"; shift 2 ;;
    -v|--version)    VERSION="$2"; shift 2 ;;
    -n|--no-pull)    NO_PULL=true; shift ;;
    -b|--build)      BUILD_IMAGES=true; shift ;;
    -r|--rollback)   ROLLBACK=true; shift ;;
    -s|--status)     STATUS_ONLY=true; shift ;;
    -h|--help)
      head -25 "$0" | tail -22
      exit 0
      ;;
    *) die "Unknown option: $1" ;;
  esac
done

# ── Validate environment ───────────────────────────────────────────────────────
[[ "$ENVIRONMENT" =~ ^(staging|production)$ ]] || \
  die "Invalid environment '$ENVIRONMENT'. Must be: staging | production"

mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Brain Tumour Detection — Deployment Script${NC}"
echo -e "${BOLD}  Environment : ${CYAN}${ENVIRONMENT}${NC}"
echo -e "${BOLD}  Version     : ${CYAN}${VERSION}${NC}"
echo -e "${BOLD}  Timestamp   : $(date -u '+%Y-%m-%d %H:%M:%S UTC')${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
echo ""

# ── Status-only mode ──────────────────────────────────────────────────────────
if $STATUS_ONLY; then
  info "Current container status:"
  docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" ps
  exit 0
fi

# ── Prerequisites ─────────────────────────────────────────────────────────────
check_prerequisites() {
  info "Checking prerequisites..."
  for cmd in docker docker-compose curl; do
    command -v "$cmd" >/dev/null 2>&1 || die "Required command not found: $cmd"
  done
  docker info >/dev/null 2>&1 || die "Docker daemon is not running"
  success "All prerequisites met"
}

# ── Environment file validation ───────────────────────────────────────────────
validate_env_files() {
  info "Validating environment files..."
  local missing=0

  for f in \
    "${REPO_ROOT}/ai-service/.env" \
    "${REPO_ROOT}/backend/.env"; do
    if [[ ! -f "$f" ]]; then
      error "Missing: $f — copy from .env.example and configure"
      missing=$((missing + 1))
    fi
  done

  [[ $missing -eq 0 ]] || die "$missing environment file(s) missing. Aborting."

  # Production secret strength checks
  if [[ "$ENVIRONMENT" == "production" ]]; then
    local jwt_key
    jwt_key=$(grep -oP '(?<=JWT_SECRET_KEY=).*' "${REPO_ROOT}/ai-service/.env" 2>/dev/null || true)
    if [[ "$jwt_key" == "change-me-in-production-use-a-long-random-secret" ]]; then
      die "JWT_SECRET_KEY is still the default value. Set a strong secret before production deployment."
    fi
    if [[ ${#jwt_key} -lt 32 ]]; then
      die "JWT_SECRET_KEY is too short (${#jwt_key} chars). Minimum 32 required."
    fi
  fi

  success "Environment files OK"
}

# ── Create backup ─────────────────────────────────────────────────────────────
create_backup() {
  info "Creating pre-deployment backup..."
  local backup_tag
  backup_tag=$(date +%Y%m%d_%H%M%S)
  local backup_path="${BACKUP_DIR}/${ENVIRONMENT}_${backup_tag}"
  mkdir -p "$backup_path"

  # Save current image digests for rollback
  docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" \
    images --format json > "${backup_path}/image_list.json" 2>/dev/null || true

  # Save current compose state
  docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" \
    ps --format json > "${backup_path}/container_state.json" 2>/dev/null || true

  echo "$VERSION" > "${backup_path}/version.txt"
  success "Backup saved to ${backup_path}"
}

# ── Build images ──────────────────────────────────────────────────────────────
build_images() {
  info "Building Docker images (version: ${VERSION})..."
  docker compose \
    -f "$COMPOSE_BASE" \
    -f "$COMPOSE_PROD" \
    build \
    --build-arg "VERSION=${VERSION}" \
    --build-arg "BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --build-arg "GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
    || die "Docker build failed"
  success "Images built"
}

# ── Pull images ───────────────────────────────────────────────────────────────
pull_images() {
  if $NO_PULL; then
    warn "Skipping image pull (--no-pull specified)"
    return
  fi
  info "Pulling images (version: ${VERSION})..."
  docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" pull || \
    warn "Pull failed — continuing with local images"
}

# ── Deploy ────────────────────────────────────────────────────────────────────
deploy() {
  info "Starting deployment..."

  # Export version for docker-compose interpolation
  export APP_VERSION="$VERSION"

  docker compose \
    -f "$COMPOSE_BASE" \
    -f "$COMPOSE_PROD" \
    up \
    --detach \
    --no-build \
    --remove-orphans \
    --wait \
    --wait-timeout 120 \
    || die "docker compose up failed"

  success "Containers started"
}

# ── Smoke tests ───────────────────────────────────────────────────────────────
smoke_tests() {
  info "Running smoke tests..."
  local ai_port=${AI_SERVICE_PORT:-8000}
  local backend_port=${BACKEND_PORT:-5000}
  local max_retries=12
  local wait_secs=5

  for i in $(seq 1 $max_retries); do
    if curl -sf "http://localhost:${ai_port}/api/v1/health" | grep -q '"status":"ok"'; then
      success "AI service health check passed"
      break
    fi
    if [[ $i -eq $max_retries ]]; then
      error "AI service health check failed after $((max_retries * wait_secs))s"
      docker compose -f "$COMPOSE_BASE" logs --tail=50 ai-service
      die "Deployment smoke test failed"
    fi
    info "  Waiting for AI service... (${i}/${max_retries})"
    sleep $wait_secs
  done

  if curl -sf "http://localhost:${backend_port}/health" >/dev/null 2>&1; then
    success "Backend health check passed"
  else
    warn "Backend health check skipped or failed (non-critical)"
  fi
}

# ── Rollback ──────────────────────────────────────────────────────────────────
rollback() {
  info "Rolling back deployment..."
  local latest_backup
  latest_backup=$(ls -td "${BACKUP_DIR}/${ENVIRONMENT}"_* 2>/dev/null | head -1 || true)

  if [[ -z "$latest_backup" ]]; then
    die "No backup found for environment '${ENVIRONMENT}'"
  fi

  local rollback_version
  rollback_version=$(cat "${latest_backup}/version.txt" 2>/dev/null || echo "previous")

  warn "Rolling back to version: ${rollback_version}"
  export APP_VERSION="$rollback_version"

  docker compose \
    -f "$COMPOSE_BASE" \
    -f "$COMPOSE_PROD" \
    up \
    --detach \
    --no-build \
    --remove-orphans \
    || die "Rollback failed"

  success "Rollback to ${rollback_version} complete"
}

# ── Cleanup ───────────────────────────────────────────────────────────────────
cleanup_old_images() {
  info "Pruning old images..."
  docker image prune -f --filter "until=72h" || true
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  if $ROLLBACK; then
    check_prerequisites
    rollback
    smoke_tests
    exit 0
  fi

  check_prerequisites
  validate_env_files
  create_backup

  if $BUILD_IMAGES; then
    build_images
  else
    pull_images
  fi

  deploy
  smoke_tests
  cleanup_old_images

  echo ""
  echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}${BOLD}  Deployment complete!${NC}"
  echo -e "${GREEN}${BOLD}  Version     : ${VERSION}${NC}"
  echo -e "${GREEN}${BOLD}  Environment : ${ENVIRONMENT}${NC}"
  echo -e "${GREEN}${BOLD}  Frontend    : http://localhost:${FRONTEND_PORT:-3000}${NC}"
  echo -e "${GREEN}${BOLD}  Backend     : http://localhost:${BACKEND_PORT:-5000}${NC}"
  echo -e "${GREEN}${BOLD}  AI Service  : http://localhost:${AI_SERVICE_PORT:-8000}${NC}"
  echo -e "${GREEN}${BOLD}  API Docs    : http://localhost:${AI_SERVICE_PORT:-8000}/docs${NC}"
  echo -e "${GREEN}${BOLD}  Log file    : ${LOG_FILE}${NC}"
  echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════${NC}"
}

main "$@"
