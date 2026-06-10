#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="short-drama-backend"
INSTALL_ROOT="/opt/short-drama"
RUNTIME_ENV_PATH="/etc/short-drama/backend.env"
SYSTEMD_SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
MYSQL_CONTAINER_NAME="short-drama-mysql"
MINIO_CONTAINER_NAME="short-drama-minio"

PURGE_DATA="false"
PURGE_ALL="false"

for arg in "$@"; do
  case "$arg" in
    --purge-data)
      PURGE_DATA="true"
      ;;
    --purge-all)
      PURGE_DATA="true"
      PURGE_ALL="true"
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: sudo bash ./clean.sh [--purge-data] [--purge-all]"
      exit 1
      ;;
  esac
done

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Please run as root or with sudo."
    exit 1
  fi
}

stop_backend_service() {
  if systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
    log "stopping and disabling ${SERVICE_NAME}"
    systemctl stop "${SERVICE_NAME}" || true
    systemctl disable "${SERVICE_NAME}" || true
  else
    log "systemd service ${SERVICE_NAME} not found, skipping"
  fi
}

remove_backend_service() {
  if [[ -f "${SYSTEMD_SERVICE_PATH}" ]]; then
    log "removing systemd service file"
    rm -f "${SYSTEMD_SERVICE_PATH}"
    systemctl daemon-reload
  fi
}

remove_containers() {
  log "removing MySQL and MinIO containers if present"
  docker rm -f "${MYSQL_CONTAINER_NAME}" "${MINIO_CONTAINER_NAME}" >/dev/null 2>&1 || true
}

remove_runtime_files() {
  log "removing runtime env and backend binary"
  rm -f "${RUNTIME_ENV_PATH}" || true
  rm -f "${INSTALL_ROOT}/bin/${SERVICE_NAME}" || true
}

remove_logs() {
  log "removing backend logs"
  rm -f "${INSTALL_ROOT}/logs/backend.log" || true
  rm -f "${INSTALL_ROOT}/logs/backend-error.log" || true
}

purge_data() {
  log "removing MySQL and MinIO data directories"
  rm -rf "${INSTALL_ROOT}/mysql/data" || true
  rm -rf "${INSTALL_ROOT}/minio/data" || true
}

purge_all() {
  log "removing remaining install directories"
  rm -rf "${INSTALL_ROOT}/bin" || true
  rm -rf "${INSTALL_ROOT}/logs" || true
  rm -rf "${INSTALL_ROOT}/mysql" || true
  rm -rf "${INSTALL_ROOT}/minio" || true
}

print_summary() {
  cat <<EOF

Cleanup complete.

What was removed:
  - systemd service stop/disable for ${SERVICE_NAME}
  - containers: ${MYSQL_CONTAINER_NAME}, ${MINIO_CONTAINER_NAME}
  - runtime env: ${RUNTIME_ENV_PATH}
  - backend binary: ${INSTALL_ROOT}/bin/${SERVICE_NAME}

Optional flags:
  --purge-data   also delete MySQL and MinIO data
  --purge-all    also delete install directories under ${INSTALL_ROOT}
EOF
}

main() {
  require_root
  stop_backend_service
  remove_backend_service
  remove_containers
  remove_runtime_files
  remove_logs

  if [[ "${PURGE_DATA}" == "true" ]]; then
    purge_data
  fi

  if [[ "${PURGE_ALL}" == "true" ]]; then
    purge_all
  fi

  print_summary
}

main "$@"
