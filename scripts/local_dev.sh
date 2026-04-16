#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

echo "=== K8s Agent Tools Server — Phase 1 ==="
echo ""

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/3] Creating virtualenv ..."
    python3 -m venv "$VENV_DIR"
fi

echo "[2/3] Installing dependencies ..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

echo "[3/3] Starting server on http://0.0.0.0:5005 ..."
echo ""
echo "  Splash:     http://localhost:5005/"
echo "  Dashboard:  http://localhost:5005/dashboard"
echo "  Skills:     http://localhost:5005/skills"
echo "  Register:   http://localhost:5005/register"
echo "  API health: http://localhost:5005/api/health"
echo ""

export K8S_AGENT_TOOLS_DATA_ROOT="$SCRIPT_DIR/data"
export K8S_AGENT_TOOLS_PORT=5005

cd "$SCRIPT_DIR"
exec "$VENV_DIR/bin/python" -m flask --app web_app.app run \
    --host 0.0.0.0 --port 5005 --debug
