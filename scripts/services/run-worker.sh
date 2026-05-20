#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
POLL_INTERVAL="${LSMS_WORKER_POLL_INTERVAL:-2.0}"
LIMIT="${LSMS_WORKER_LIMIT:-10}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

cd "${REPO_ROOT}"
exec "${PYTHON_BIN}" scripts/run_worker_service.py --mode loop --poll-interval "${POLL_INTERVAL}" --limit "${LIMIT}"
