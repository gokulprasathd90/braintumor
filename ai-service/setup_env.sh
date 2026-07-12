#!/usr/bin/env bash
# Bash — create and activate the Python virtual environment
# Run from the ai-service/ directory:
#   chmod +x setup_env.sh && ./setup_env.sh

set -euo pipefail

VENV_DIR=".venv"

echo "Brain Tumour Detection — AI Service environment setup"
echo ""

PYTHON_CMD=""
if command -v py &>/dev/null && py -3.12 -c "import sys" &>/dev/null; then
    PYTHON_CMD="py -3.12"
elif command -v python3.12 &>/dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &>/dev/null; then
    echo "WARNING: Python 3.12 not found. Using default python3 (requires TensorFlow >= 2.20 for 3.13)."
    PYTHON_CMD="python3"
else
    echo "ERROR: Python not found. Install Python 3.12+ from https://www.python.org/downloads/"
    exit 1
fi

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists — skipping creation."
else
    echo "Creating virtual environment in '$VENV_DIR' using $PYTHON_CMD ..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "Virtual environment created."
fi

echo ""
echo "Activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Then install dependencies:"
echo "  pip install --upgrade pip"
echo "  pip install -r requirements.txt"
echo ""
echo "Start the server:"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
