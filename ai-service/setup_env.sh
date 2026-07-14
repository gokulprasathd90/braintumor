#!/usr/bin/env bash
# setup_env.sh — Bootstrap the Python virtual environment for the AI service.
#
# Run from the ai-service/ directory:
#   chmod +x setup_env.sh && ./setup_env.sh
#
# What this script does:
#   1. Locates Python 3.12 (falls back to 3.10+)
#   2. Creates a .venv virtual environment if one does not exist
#   3. Upgrades pip, setuptools, and wheel inside the venv
#   4. Installs all pinned dependencies from requirements.txt
#   5. Copies .env.example → .env if no .env exists yet
#   6. Prints the commands to activate and run the server

set -euo pipefail

VENV_DIR=".venv"
REQ_FILE="requirements.txt"
ENV_EXAMPLE=".env.example"
ENV_FILE=".env"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'

step()  { echo -e "  ${CYAN}→${NC} $*"; }
ok()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $*"; }
fatal() { echo -e "  ${RED}✗${NC} $*" >&2; exit 1; }

echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
echo -e "${MAGENTA}  Brain Tumour Detection — AI Service Setup${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
echo ""

# ── 1. Locate Python ──────────────────────────────────────────────────────────
step "Locating Python 3.12..."

PYTHON_CMD=""

for cmd in python3.12 python3.13 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')" 2>/dev/null || true)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "${major:-0}" -ge 3 ] && [ "${minor:-0}" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            ok "Found Python $ver at '$cmd'"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fatal "Python 3.10+ not found. Install from https://www.python.org/downloads/ and ensure it is on PATH."
fi

# ── 2. Create virtual environment ─────────────────────────────────────────────
step "Setting up virtual environment..."

if [ -d "$VENV_DIR" ]; then
    ok "Virtual environment '$VENV_DIR' already exists — skipping creation"
else
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    ok "Virtual environment created at '$VENV_DIR'"
fi

# Activate for this shell session so subsequent pip calls use the venv
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── 3. Upgrade pip, setuptools, wheel ─────────────────────────────────────────
step "Upgrading pip, setuptools, and wheel..."
pip install --quiet --upgrade pip setuptools wheel
ok "pip upgraded"

# ── 4. Install dependencies ────────────────────────────────────────────────────
[ -f "$REQ_FILE" ] || fatal "'$REQ_FILE' not found. Run this script from the ai-service/ directory."

step "Installing dependencies from '$REQ_FILE' (this may take a few minutes)..."
pip install --quiet -r "$REQ_FILE"
ok "All dependencies installed"

# ── 5. Copy .env.example → .env ───────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        ok "Created '$ENV_FILE' from '$ENV_EXAMPLE' — edit it before starting the server"
    else
        warn "'$ENV_EXAMPLE' not found — skipping .env creation"
    fi
else
    ok "'$ENV_FILE' already exists — keeping existing configuration"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Activate the environment:${NC}"
echo "    source .venv/bin/activate"
echo ""
echo -e "  ${CYAN}Run the development server:${NC}"
echo "    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo -e "  ${CYAN}Run tests:${NC}"
echo "    pytest"
echo ""
