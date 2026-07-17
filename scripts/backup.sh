#!/usr/bin/env bash
# ─── scripts/backup.sh ────────────────────────────────────────────────────────
#
# Creates a timestamped backup of all persistent data volumes:
#   - SQLite database (db_volume)
#   - Trained model weights (models_volume)
#   - Uploaded MRI images (uploads_volume)
#   - AI service logs (ai_logs_volume)
#
# Usage:
#   ./scripts/backup.sh [--output /path/to/backup/dir] [--no-compress]
#
# Output:
#   .backups/backup_YYYYMMDD_HHMMSS/
#     db.tar.gz
#     models.tar.gz
#     uploads.tar.gz
#     logs.tar.gz
#     manifest.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.yml"
OUTPUT_DIR="${REPO_ROOT}/.backups"
COMPRESS=true
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --output)     OUTPUT_DIR="$2"; shift 2 ;;
    --no-compress) COMPRESS=false; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

BACKUP_PATH="${OUTPUT_DIR}/backup_${TIMESTAMP}"
mkdir -p "$BACKUP_PATH"

echo "[BACKUP] Starting backup → ${BACKUP_PATH}"

# ── Volume backup helper ───────────────────────────────────────────────────────
backup_volume() {
  local volume_name="$1"
  local archive_name="$2"
  local src_path="${3:-/data}"

  echo "[BACKUP] Backing up volume: ${volume_name}..."

  if $COMPRESS; then
    docker run --rm \
      -v "${volume_name}:${src_path}:ro" \
      -v "${BACKUP_PATH}:/backup" \
      alpine \
      tar czf "/backup/${archive_name}.tar.gz" -C "$src_path" . 2>/dev/null \
      && echo "[BACKUP]   → ${archive_name}.tar.gz" \
      || echo "[BACKUP]   ⚠ Volume ${volume_name} is empty or missing — skipped"
  else
    docker run --rm \
      -v "${volume_name}:${src_path}:ro" \
      -v "${BACKUP_PATH}:/backup" \
      alpine \
      tar cf "/backup/${archive_name}.tar" -C "$src_path" . 2>/dev/null \
      && echo "[BACKUP]   → ${archive_name}.tar" \
      || echo "[BACKUP]   ⚠ Volume ${volume_name} is empty or missing — skipped"
  fi
}

# ── Determine docker-compose project name ─────────────────────────────────────
PROJECT_NAME=$(docker compose -f "$COMPOSE_FILE" config --format json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name','brain-tumor'))" \
  2>/dev/null || echo "brain-tumor")

# ── Backup each volume ────────────────────────────────────────────────────────
backup_volume "${PROJECT_NAME}_db_volume"           "db"      "/data"
backup_volume "${PROJECT_NAME}_models_volume"        "models"  "/data"
backup_volume "${PROJECT_NAME}_uploads_volume"       "uploads" "/data"
backup_volume "${PROJECT_NAME}_ai_logs_volume"       "ai_logs" "/data"
backup_volume "${PROJECT_NAME}_backend_logs_volume"  "backend_logs" "/data"

# ── Write manifest ────────────────────────────────────────────────────────────
MANIFEST="${BACKUP_PATH}/manifest.json"
{
  echo "{"
  echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"project\": \"${PROJECT_NAME}\","
  echo "  \"compressed\": ${COMPRESS},"
  echo "  \"host\": \"$(hostname)\","
  echo "  \"git_commit\": \"$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')\","
  echo "  \"files\": ["
  ls "${BACKUP_PATH}"/*.tar* 2>/dev/null | \
    awk '{printf "    \"%s\"", $0}' | \
    sed 's|  *"[^"]*"$|\n  ]|' | \
    sed 's/\"\"/\",\n    \"/g' || echo "  ]"
  echo "}"
} > "$MANIFEST" 2>/dev/null || true

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL_SIZE=$(du -sh "$BACKUP_PATH" 2>/dev/null | cut -f1 || echo "unknown")
echo ""
echo "[BACKUP] ✓ Backup complete"
echo "[BACKUP]   Path : ${BACKUP_PATH}"
echo "[BACKUP]   Size : ${TOTAL_SIZE}"
echo "[BACKUP]   Files: $(ls "$BACKUP_PATH" | wc -l)"

# ── Retention: keep last 5 backups ───────────────────────────────────────────
echo "[BACKUP] Pruning old backups (keeping last 5)..."
ls -td "${OUTPUT_DIR}"/backup_* 2>/dev/null | tail -n +6 | xargs rm -rf 2>/dev/null || true

echo "[BACKUP] Done."
