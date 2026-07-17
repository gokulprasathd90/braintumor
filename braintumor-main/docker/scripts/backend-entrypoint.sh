#!/bin/sh
# ─── docker/scripts/backend-entrypoint.sh ─────────────────────────────────────
#
# Entrypoint for the Node.js backend container.
# Runs migrations then exec's the CMD (node server.js).
#
set -e

log_info()  { echo "[BACKEND] INFO:  $1"; }
log_warn()  { echo "[BACKEND] WARN:  $1" >&2; }
log_error() { echo "[BACKEND] ERROR: $1" >&2; }

log_info "=== Brain Tumour Backend — startup ==="
log_info "Environment : ${NODE_ENV:-production}"
log_info "Port        : ${PORT:-5000}"

# ── Ensure upload and log directories exist ────────────────────────────────────
for dir in \
    "${UPLOAD_DIR:-/app/uploads}" \
    "/app/logs" \
    "/app/database"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir" 2>/dev/null || log_warn "Could not create $dir"
    fi
done

# ── Run database migrations ────────────────────────────────────────────────────
if [ -f "./database/migrate.js" ]; then
    log_info "Running database migrations..."
    node database/migrate.js \
        && log_info "Migrations complete." \
        || { log_error "Migration failed — aborting startup"; exit 1; }
else
    log_warn "No migration script found at ./database/migrate.js — skipping"
fi

log_info "Pre-flight checks passed — starting application..."

exec "$@"
