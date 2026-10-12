#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
HOST="${VELINGO_CHECK_HOST:-127.0.0.1}"
PORT="${VELINGO_CHECK_PORT:-18082}"
LOG_FILE="/tmp/velingo-phase0-local-server.log"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing ${PYTHON_BIN}; create the Python 3.11 venv first." >&2
  exit 1
fi

cd "${ROOT_DIR}"

echo "[1/6] pytest"
"${PYTHON_BIN}" -m pytest -q

echo "[2/6] compileall"
"${PYTHON_BIN}" -m compileall -q backend server tests

echo "[3/6] diff check"
git diff --check

echo "[4/6] graft freshness"
if command -v graft >/dev/null 2>&1; then
  graft check
else
  echo "graft not installed; skipped"
fi

echo "[5/6] local server"
VELINGO_HOST="${HOST}" PORT="${PORT}" "${ROOT_DIR}/scripts/run_local_server.sh" >"${LOG_FILE}" 2>&1 &
server_pid=$!
cleanup() {
  kill "${server_pid}" 2>/dev/null || true
  wait "${server_pid}" 2>/dev/null || true
}
trap cleanup EXIT

ready=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null; then
    ready=1
    break
  fi
  sleep 0.5
done
if [[ "${ready}" -ne 1 ]]; then
  echo "Local server did not become ready; log: ${LOG_FILE}" >&2
  cat "${LOG_FILE}" >&2
  exit 1
fi

echo "[6/6] health and OpenAPI"
health="$(curl -fsS "http://${HOST}:${PORT}/health")"
printf 'health: %s\n' "${health}"
route_count="$(${PYTHON_BIN} -c 'import json,sys; print(len(json.load(sys.stdin)["paths"]))' < <(curl -fsS "http://${HOST}:${PORT}/openapi.json"))"
if [[ "${route_count}" -lt 6 ]]; then
  echo "Expected at least 6 OpenAPI routes, got ${route_count}." >&2
  exit 1
fi
printf 'openapi routes: %s\n' "${route_count}"
echo "Phase 0 local verification: PASS"
