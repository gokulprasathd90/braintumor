#!/usr/bin/env bash
# =============================================================================
# package_release.sh — Brain Tumour Detection Release Packager
#
# Builds a distributable release archive containing all source code,
# documentation, scripts, and metadata. Generates a release_manifest.json
# describing the contents and checksums.
#
# Usage:
#   ./scripts/package_release.sh [OPTIONS]
#
# Options:
#   -v, --version VERSION    Override the version (default: read from VERSION file)
#   -o, --output DIR         Output directory for the archive (default: ./dist)
#   -f, --format FORMAT      Archive format: tar.gz | zip (default: tar.gz)
#   --skip-tests             Skip test verification before packaging
#   --skip-build             Skip frontend production build
#   --dry-run                Print what would be done without doing it
#   -h, --help               Show this help message
#
# Examples:
#   ./scripts/package_release.sh
#   ./scripts/package_release.sh --version 1.2.0 --output ./releases
#   ./scripts/package_release.sh --format zip --skip-tests
# =============================================================================

set -euo pipefail

# ── Colour codes ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Defaults ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION_FILE="${ROOT_DIR}/VERSION"
OUTPUT_DIR="${ROOT_DIR}/dist"
ARCHIVE_FORMAT="tar.gz"
SKIP_TESTS=false
SKIP_BUILD=false
DRY_RUN=false
VERSION=""

# ── Logging helpers ───────────────────────────────────────────────────────────
log_info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()    { echo -e "\n${BOLD}${CYAN}▶ $*${NC}"; }
dry_run()     { echo -e "${YELLOW}[DRY-RUN]${NC} Would run: $*"; }

# ── Usage ─────────────────────────────────────────────────────────────────────
usage() {
    sed -n '/^# Usage:/,/^# ====/p' "$0" | grep '^#' | sed 's/^# \{0,2\}//'
    exit 0
}

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--version)   VERSION="$2"; shift 2 ;;
        -o|--output)    OUTPUT_DIR="$2"; shift 2 ;;
        -f|--format)    ARCHIVE_FORMAT="$2"; shift 2 ;;
        --skip-tests)   SKIP_TESTS=true; shift ;;
        --skip-build)   SKIP_BUILD=true; shift ;;
        --dry-run)      DRY_RUN=true; shift ;;
        -h|--help)      usage ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

# ── Validate format ───────────────────────────────────────────────────────────
if [[ "$ARCHIVE_FORMAT" != "tar.gz" && "$ARCHIVE_FORMAT" != "zip" ]]; then
    log_error "Unsupported format: $ARCHIVE_FORMAT. Use 'tar.gz' or 'zip'."
    exit 1
fi

# ── Resolve version ───────────────────────────────────────────────────────────
if [[ -z "$VERSION" ]]; then
    if [[ -f "$VERSION_FILE" ]]; then
        VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
    else
        log_error "VERSION file not found at ${VERSION_FILE}. Use --version to specify."
        exit 1
    fi
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    log_error "Invalid version format: '$VERSION'. Expected semver (e.g., 1.0.0)."
    exit 1
fi

# ── Derived names ─────────────────────────────────────────────────────────────
PACKAGE_NAME="brain-tumor-detection-v${VERSION}"
STAGING_DIR="${OUTPUT_DIR}/${PACKAGE_NAME}"
BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
GIT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
GIT_BRANCH="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"

# ── Header ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        Brain Tumour Detection — Release Packager         ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Version    : ${VERSION}"
log_info "Package    : ${PACKAGE_NAME}"
log_info "Format     : ${ARCHIVE_FORMAT}"
log_info "Output dir : ${OUTPUT_DIR}"
log_info "Git commit : ${GIT_COMMIT} (${GIT_BRANCH})"
log_info "Build date : ${BUILD_DATE}"
$DRY_RUN && log_warn "DRY-RUN mode — no files will be modified"
echo ""

# ── Step 1: Run tests ─────────────────────────────────────────────────────────
log_step "Step 1/7 — Test verification"

if $SKIP_TESTS; then
    log_warn "Tests skipped (--skip-tests)"
else
    log_info "Running AI service tests..."
    if $DRY_RUN; then
        dry_run "cd ai-service && source .venv/bin/activate && pytest -v --tb=short -q"
    else
        if [[ -f "${ROOT_DIR}/ai-service/.venv/bin/activate" ]]; then
            cd "${ROOT_DIR}/ai-service"
            source .venv/bin/activate
            pytest -v --tb=short -q || {
                log_error "AI service tests failed. Fix failures before packaging."
                exit 1
            }
            cd "${ROOT_DIR}"
            log_success "AI service tests passed"
        else
            log_warn "AI service venv not found — skipping Python tests"
        fi
    fi

    log_info "Running backend tests..."
    if $DRY_RUN; then
        dry_run "cd backend && npm test -- --runInBand"
    else
        if [[ -d "${ROOT_DIR}/backend/node_modules" ]]; then
            cd "${ROOT_DIR}/backend"
            npm test -- --runInBand --passWithNoTests || {
                log_error "Backend tests failed. Fix failures before packaging."
                exit 1
            }
            cd "${ROOT_DIR}"
            log_success "Backend tests passed"
        else
            log_warn "backend/node_modules not found — skipping backend tests"
        fi
    fi
fi

# ── Step 2: Build frontend ────────────────────────────────────────────────────
log_step "Step 2/7 — Frontend production build"

if $SKIP_BUILD; then
    log_warn "Frontend build skipped (--skip-build)"
else
    if $DRY_RUN; then
        dry_run "cd frontend && npm run build"
    else
        if [[ -d "${ROOT_DIR}/frontend/node_modules" ]]; then
            log_info "Building React application..."
            cd "${ROOT_DIR}/frontend"
            npm run build || {
                log_error "Frontend build failed."
                exit 1
            }
            cd "${ROOT_DIR}"
            log_success "Frontend built → frontend/dist/"
        else
            log_warn "frontend/node_modules not found — skipping frontend build"
        fi
    fi
fi

# ── Step 3: Prepare staging directory ────────────────────────────────────────
log_step "Step 3/7 — Staging release files"

if $DRY_RUN; then
    dry_run "mkdir -p ${STAGING_DIR}"
    dry_run "rsync source → ${STAGING_DIR}"
else
    rm -rf "${STAGING_DIR}"
    mkdir -p "${STAGING_DIR}"

    # Files and directories to include
    INCLUDE=(
        "ai-service/app"
        "ai-service/tests"
        "ai-service/requirements.txt"
        "ai-service/Dockerfile"
        "ai-service/.env.example"
        "ai-service/.env.production"
        "ai-service/.python-version"
        "backend/api"
        "backend/database"
        "backend/middleware"
        "backend/pipeline"
        "backend/server.js"
        "backend/package.json"
        "backend/package-lock.json"
        "backend/.env.example"
        "backend/Dockerfile"
        "frontend/src"
        "frontend/public"
        "frontend/package.json"
        "frontend/package-lock.json"
        "frontend/vite.config.ts"
        "frontend/tsconfig.json"
        "frontend/tailwind.config.ts"
        "frontend/.env.example"
        "frontend/Dockerfile"
        "docker"
        "docs"
        "scripts"
        ".github"
        "Makefile"
        "README.md"
        "CHANGELOG.md"
        "CONTRIBUTING.md"
        "CODE_OF_CONDUCT.md"
        "SECURITY.md"
        "RELEASE_CHECKLIST.md"
        "LICENSE"
        "VERSION"
        ".pre-commit-config.yaml"
        ".gitignore"
    )

    # Also include frontend/dist if it exists
    [[ -d "${ROOT_DIR}/frontend/dist" ]] && INCLUDE+=("frontend/dist")

    for item in "${INCLUDE[@]}"; do
        src="${ROOT_DIR}/${item}"
        dst="${STAGING_DIR}/${item}"
        if [[ -e "$src" ]]; then
            mkdir -p "$(dirname "$dst")"
            cp -r "$src" "$dst"
        else
            log_warn "Skipping missing item: ${item}"
        fi
    done

    log_success "Staged $(find "${STAGING_DIR}" | wc -l) entries to ${STAGING_DIR}"
fi

# ── Step 4: Generate release manifest ────────────────────────────────────────
log_step "Step 4/7 — Generating release manifest"

MANIFEST_FILE="${ROOT_DIR}/release_manifest.json"

if $DRY_RUN; then
    dry_run "Generate ${MANIFEST_FILE}"
else
    # Count files per component
    ai_files=$(find "${STAGING_DIR}/ai-service" -type f 2>/dev/null | wc -l || echo 0)
    be_files=$(find "${STAGING_DIR}/backend"    -type f 2>/dev/null | wc -l || echo 0)
    fe_files=$(find "${STAGING_DIR}/frontend"   -type f 2>/dev/null | wc -l || echo 0)
    doc_files=$(find "${STAGING_DIR}/docs"      -type f 2>/dev/null | wc -l || echo 0)
    total_files=$(find "${STAGING_DIR}"         -type f 2>/dev/null | wc -l || echo 0)

    cat > "${MANIFEST_FILE}" <<EOF
{
  "project": "Brain Tumour Detection",
  "version": "${VERSION}",
  "release_date": "${BUILD_DATE%T*}",
  "build_timestamp": "${BUILD_DATE}",
  "git_commit": "${GIT_COMMIT}",
  "git_branch": "${GIT_BRANCH}",
  "package_name": "${PACKAGE_NAME}",
  "archive_format": "${ARCHIVE_FORMAT}",
  "components": {
    "ai_service": {
      "language": "Python",
      "framework": "FastAPI + TensorFlow",
      "python_version": "3.12",
      "files": ${ai_files}
    },
    "backend": {
      "language": "JavaScript",
      "framework": "Node.js + Express",
      "node_version": "20 LTS",
      "files": ${be_files}
    },
    "frontend": {
      "language": "TypeScript",
      "framework": "React 18 + Vite 5",
      "files": ${fe_files}
    },
    "documentation": {
      "files": ${doc_files}
    }
  },
  "total_files": ${total_files},
  "checksums": {},
  "release_type": "stable",
  "license": "MIT",
  "repository": "https://github.com/your-org/brain-tumor-detection",
  "docker_images": [
    "ghcr.io/your-org/brain-tumor-detection/ai-service:${VERSION}",
    "ghcr.io/your-org/brain-tumor-detection/backend:${VERSION}",
    "ghcr.io/your-org/brain-tumor-detection/frontend:${VERSION}"
  ]
}
EOF

    # Copy manifest into staging dir as well
    cp "${MANIFEST_FILE}" "${STAGING_DIR}/release_manifest.json"
    log_success "Manifest written to ${MANIFEST_FILE}"
fi

# ── Step 5: Create archive ────────────────────────────────────────────────────
log_step "Step 5/7 — Creating release archive"

ARCHIVE_BASE="${OUTPUT_DIR}/${PACKAGE_NAME}"

if $DRY_RUN; then
    dry_run "Create ${ARCHIVE_BASE}.${ARCHIVE_FORMAT}"
else
    cd "${OUTPUT_DIR}"
    if [[ "$ARCHIVE_FORMAT" == "tar.gz" ]]; then
        ARCHIVE_FILE="${ARCHIVE_BASE}.tar.gz"
        tar -czf "${ARCHIVE_FILE}" "${PACKAGE_NAME}/"
    else
        ARCHIVE_FILE="${ARCHIVE_BASE}.zip"
        zip -r -q "${ARCHIVE_FILE}" "${PACKAGE_NAME}/"
    fi

    ARCHIVE_SIZE=$(du -sh "${ARCHIVE_FILE}" | cut -f1)
    log_success "Archive created: $(basename "${ARCHIVE_FILE}") (${ARCHIVE_SIZE})"
    cd "${ROOT_DIR}"
fi

# ── Step 6: Compute checksums ─────────────────────────────────────────────────
log_step "Step 6/7 — Computing checksums"

CHECKSUM_FILE="${OUTPUT_DIR}/${PACKAGE_NAME}.sha256"

if $DRY_RUN; then
    dry_run "sha256sum ${ARCHIVE_FILE} > ${CHECKSUM_FILE}"
else
    if command -v sha256sum &>/dev/null; then
        sha256sum "${ARCHIVE_FILE}" > "${CHECKSUM_FILE}"
    elif command -v shasum &>/dev/null; then
        shasum -a 256 "${ARCHIVE_FILE}" > "${CHECKSUM_FILE}"
    else
        log_warn "sha256sum / shasum not found — skipping checksum"
    fi

    if [[ -f "${CHECKSUM_FILE}" ]]; then
        CHECKSUM=$(awk '{print $1}' "${CHECKSUM_FILE}")
        log_success "SHA-256: ${CHECKSUM}"

        # Embed checksum back into manifest
        if command -v python3 &>/dev/null; then
            python3 - "${MANIFEST_FILE}" "${CHECKSUM}" <<'PYEOF'
import sys, json
path, checksum = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
data["checksums"]["sha256"] = checksum
with open(path, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
        fi
    fi
fi

# ── Step 7: Cleanup staging directory ────────────────────────────────────────
log_step "Step 7/7 — Cleanup"

if $DRY_RUN; then
    dry_run "rm -rf ${STAGING_DIR}"
else
    rm -rf "${STAGING_DIR}"
    log_success "Staging directory removed"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║                Release Package Complete                 ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if ! $DRY_RUN; then
    log_info "Archive  : ${ARCHIVE_FILE}"
    [[ -f "${CHECKSUM_FILE}" ]] && log_info "Checksum : ${CHECKSUM_FILE}"
    log_info "Manifest : ${MANIFEST_FILE}"
fi

echo ""
log_info "Next steps:"
echo "  1. Verify the archive: tar -tzf ${ARCHIVE_BASE}.${ARCHIVE_FORMAT} | head -20"
echo "  2. Create a GitHub release and attach the archive and manifest"
echo "  3. Push the version tag: git tag -a v${VERSION} -m \"Release v${VERSION}\" && git push origin v${VERSION}"
echo ""
