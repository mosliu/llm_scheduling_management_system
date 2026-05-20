#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SERVICE_USER="${LSMS_SERVICE_USER:-root}"
SERVICE_GROUP="${LSMS_SERVICE_GROUP:-root}"
API_SERVICE_NAME="${LSMS_API_SERVICE_NAME:-llms-api.service}"
WORKER_SERVICE_NAME="${LSMS_WORKER_SERVICE_NAME:-llms-worker.service}"
API_HOST="${LSMS_API_HOST:-0.0.0.0}"
API_PORT="${LSMS_API_PORT:-8000}"
WORKER_POLL_INTERVAL="${LSMS_WORKER_POLL_INTERVAL:-2.0}"
WORKER_LIMIT="${LSMS_WORKER_LIMIT:-10}"
INSTALL_SYSTEM_USER="${LSMS_INSTALL_SYSTEM_USER:-0}"
CHOWN_REPO="${LSMS_CHOWN_REPO:-0}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This script must be run as root." >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is required for Linux service deployment." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but was not found in PATH." >&2
  exit 1
fi

mkdir -p "${REPO_ROOT}/logs"

if [[ "${INSTALL_SYSTEM_USER}" == "1" ]]; then
  if ! getent group "${SERVICE_GROUP}" >/dev/null 2>&1; then
    groupadd --system "${SERVICE_GROUP}"
  fi
  if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
    useradd --system --gid "${SERVICE_GROUP}" --home-dir "${REPO_ROOT}" --shell /usr/sbin/nologin "${SERVICE_USER}"
  fi
fi

if [[ "${CHOWN_REPO}" == "1" ]]; then
  chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${REPO_ROOT}"
fi

chmod +x "${REPO_ROOT}/scripts/services/run-api.sh"
chmod +x "${REPO_ROOT}/scripts/services/run-worker.sh"

pushd "${REPO_ROOT}" >/dev/null
uv sync
uv run alembic upgrade head
popd >/dev/null

cat >"/etc/systemd/system/${API_SERVICE_NAME}" <<EOF
[Unit]
Description=LLM Scheduling Management System API
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=${REPO_ROOT}/.env
Environment=LSMS_API_HOST=${API_HOST}
Environment=LSMS_API_PORT=${API_PORT}
ExecStart=${REPO_ROOT}/scripts/services/run-api.sh
Restart=always
RestartSec=5
StandardOutput=append:${REPO_ROOT}/logs/api.service.log
StandardError=append:${REPO_ROOT}/logs/api.service.err.log

[Install]
WantedBy=multi-user.target
EOF

cat >"/etc/systemd/system/${WORKER_SERVICE_NAME}" <<EOF
[Unit]
Description=LLM Scheduling Management System Worker
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=${REPO_ROOT}/.env
Environment=LSMS_WORKER_POLL_INTERVAL=${WORKER_POLL_INTERVAL}
Environment=LSMS_WORKER_LIMIT=${WORKER_LIMIT}
ExecStart=${REPO_ROOT}/scripts/services/run-worker.sh
Restart=always
RestartSec=5
StandardOutput=append:${REPO_ROOT}/logs/worker.service.log
StandardError=append:${REPO_ROOT}/logs/worker.service.err.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "${API_SERVICE_NAME}"
systemctl enable --now "${WORKER_SERVICE_NAME}"

echo
echo "Deployment completed."
echo "Repository: ${REPO_ROOT}"
echo "API service: ${API_SERVICE_NAME}"
echo "Worker service: ${WORKER_SERVICE_NAME}"
echo
systemctl --no-pager --full status "${API_SERVICE_NAME}" || true
echo
systemctl --no-pager --full status "${WORKER_SERVICE_NAME}" || true
