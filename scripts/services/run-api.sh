#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
HOST="${LSMS_API_HOST:-0.0.0.0}"
PORT="${LSMS_API_PORT:-8000}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

cd "${REPO_ROOT}"
exec "${PYTHON_BIN}" -m uvicorn apps.api.main:app --host "${HOST}" --port "${PORT}"
