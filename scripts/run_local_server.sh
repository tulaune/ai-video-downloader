#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
HOST="${VELINGO_HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing ${PYTHON_BIN}; create the Python 3.11 venv first." >&2
  exit 1
fi

cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" -m uvicorn server.app.main:app --host "${HOST}" --port "${PORT}"
