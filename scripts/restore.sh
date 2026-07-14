#!/usr/bin/env bash
# ─── scripts/restore.sh ───────────────────────────────────────────────────────
#
# Restores persistent data volumes from a backup created by backup.sh.
#
# Usage:
#   ./scripts/restore.sh --backup .backups/backup_20240715_120000
#   ./scripts/restore.sh --latest
#   ./scripts/restore.sh --latest --volume db   # restore specific volume only
#
# WARNING: This overwrites existing volume data. Stop containers first.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.yml"
BACKUP_DIR="${REPO_ROOT}/.backups"
BACKUP_PATH=""
RESTORE_VOLUME=""
USE_LATEST=false

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --backup)   BACKUP_PATH="$2"; shift 2 ;;
    --latest)   USE_LATEST=true; shift ;;
    --volume)   RESTORE_VOLUME="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if $USE_LATEST; then
  BACKUP_PATH=$(ls -td "${BACKUP_DIR}"/backup_* 2>/dev/null | head -1 || true)
  [[ -n "$BACKUP_PATH" ]] || { echo "[RESTORE] No backups found in ${BACKUP_DIR}"; exit 1; }
fi

[[ -n "$BACKUP_PATH" ]] || { echo "[RESTORE] Specify --backup <path> or --latest"; exit 1; }
[[ -d "$BACKUP_PATH" ]] || { echo "[RESTORE] Backup path does not exist: ${BACKUP_PATH}"; exit 1; }

echo ""
echo "[RESTORE] ============================================================"
echo "[RESTORE] Brain Tumour Detection — Restore"
echo "[RESTORE] Backup: ${BACKUP_PATH}"
echo "[RESTORE] ============================================================"
echo ""

# ── Safety prompt ─────────────────────────────────────────────────────────────
read -r -p "[RESTORE] WARNING: This will OVERWRITE existing volume data. Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "[RESTORE] Aborted."; exit 0; }

# ── Stop running containers ───────────────────────────────────────────────────
echo "[RESTORE] Stopping containers..."
docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true

# ── Determine project name ────────────────────────────────────────────────────
PROJECT_NAME=$(docker compose -f "$COMPOSE_FILE" config --format json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name','brain-tumor'))" \
  2>/dev/null || echo "brain-tumor")

# ── Volume restore helper ──────────────────────────────────────────────────────
restore_volume() {
  local archive_name="$1"
  local volume_name="$2"
  local dest_path="${3:-/data}"

  # Find the archive (compressed or uncompressed)
  local archive
  archive=$(ls "${BACKUP_PATH}/${archive_name}.tar.gz" 2>/dev/null || \
            ls "${BACKUP_PATH}/${archive_name}.tar" 2>/dev/null || echo "")

  if [[ -z "$archive" ]]; then
    echo "[RESTORE] ⚠ No archive found for '${archive_name}' — skipping"
    return
  fi

  echo "[RESTORE] Restoring ${archive_name} → ${volume_name}..."

  # Ensure volume exists
  docker volume create "$volume_name" >/dev/null 2>&1 || true

  local tar_flags="xf"
  [[ "$archive" == *.gz ]] && tar_flags="xzf"

  docker run --rm \
    -v "${volume_name}:${dest_path}" \
    -v "${archive}:/archive/data.tar${archive##*.tar}" \
    alpine \
    sh -c "cd ${dest_path} && tar ${tar_flags} /archive/data.tar${archive##*.tar}"

  echo "[RESTORE]   ✓ ${archive_name} restored"
}

# ── Restore volumes ───────────────────────────────────────────────────────────
declare -A VOLUME_MAP=(
  ["db"]="${PROJECT_NAME}_db_volume"
  ["models"]="${PROJECT_NAME}_models_volume"
  ["uploads"]="${PROJECT_NAME}_uploads_volume"
  ["ai_logs"]="${PROJECT_NAME}_ai_logs_volume"
  ["backend_logs"]="${PROJECT_NAME}_backend_logs_volume"
)

if [[ -n "$RESTORE_VOLUME" ]]; then
  # Restore specific volume only
  if [[ -v VOLUME_MAP[$RESTORE_VOLUME] ]]; then
    restore_volume "$RESTORE_VOLUME" "${VOLUME_MAP[$RESTORE_VOLUME]}"
  else
    echo "[RESTORE] Unknown volume: ${RESTORE_VOLUME}. Valid options: ${!VOLUME_MAP[*]}"
    exit 1
  fi
else
  # Restore all volumes
  for archive_name in "${!VOLUME_MAP[@]}"; do
    restore_volume "$archive_name" "${VOLUME_MAP[$archive_name]}"
  done
fi

echo ""
echo "[RESTORE] ✓ Restore complete from: ${BACKUP_PATH}"
echo "[RESTORE] Restart containers with: make docker-up-prod"
echo ""
