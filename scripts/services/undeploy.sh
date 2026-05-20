#!/usr/bin/env bash
set -euo pipefail

API_SERVICE_NAME="${LSMS_API_SERVICE_NAME:-llms-api.service}"
WORKER_SERVICE_NAME="${LSMS_WORKER_SERVICE_NAME:-llms-worker.service}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This script must be run as root." >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is required for Linux service undeployment." >&2
  exit 1
fi

for service_name in "${API_SERVICE_NAME}" "${WORKER_SERVICE_NAME}"; do
  systemctl stop "${service_name}" || true
  systemctl disable "${service_name}" || true
  rm -f "/etc/systemd/system/${service_name}"
done

systemctl daemon-reload
systemctl reset-failed

echo
echo "Systemd services removed."
echo "API service: ${API_SERVICE_NAME}"
echo "Worker service: ${WORKER_SERVICE_NAME}"
