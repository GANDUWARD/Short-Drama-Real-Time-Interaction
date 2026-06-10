#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/one_step.env}"

SERVICE_NAME="short-drama-backend"
INSTALL_ROOT="/opt/short-drama"
BIN_DIR="$INSTALL_ROOT/bin"
BIN_PATH="$BIN_DIR/$SERVICE_NAME"
LOG_DIR="$INSTALL_ROOT/logs"
RUNTIME_ENV_PATH="/etc/short-drama/backend.env"
SYSTEMD_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"

MYSQL_CONTAINER_NAME="short-drama-mysql"
MINIO_CONTAINER_NAME="short-drama-minio"

GO_ARCH=""
PKG_MANAGER=""

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

die() {
  log "ERROR: $*"
  exit 1
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "please run this script as root or with sudo"
  fi
}

load_env() {
  [[ -f "$ENV_FILE" ]] || die "env file not found: $ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
}

validate_env() {
  local required=(
    APP_PORT
    APP_USER
    APP_GROUP
    GO_VERSION
    GO_PROXY
    GO_SUMDB
    MYSQL_IMAGE
    MYSQL_TAG
    MYSQL_ROOT_PASSWORD
    MYSQL_HOST
    MYSQL_PORT
    MYSQL_DATABASE
    MYSQL_APP_USER
    MYSQL_APP_PASSWORD
    MYSQL_DATA_DIR
    MINIO_IMAGE
    MINIO_TAG
    MC_IMAGE
    MC_TAG
    MINIO_ROOT_USER
    MINIO_ROOT_PASSWORD
    MINIO_BUCKET
    MINIO_DATA_DIR
    MINIO_API_PORT
    MINIO_CONSOLE_PORT
    PUBLIC_IP
    BACKEND_PUBLIC_SCHEME
    MINIO_PUBLIC_SCHEME
  )

  local key
  for key in "${required[@]}"; do
    [[ -n "${!key:-}" ]] || die "missing required env: $key"
  done

  [[ -f "$BACKEND_DIR/go.mod" ]] || die "go.mod not found under $BACKEND_DIR; clone the repo first"

  if [[ "${MINIO_IMAGE}" == *"/aistor/"* || "${MINIO_IMAGE}" == *"aistor"* ]]; then
    die "MINIO_IMAGE is pointing to AIStor (${MINIO_IMAGE}). Use community MinIO such as quay.io/minio/minio to avoid license errors."
  fi
}

detect_package_manager() {
  if command -v dnf >/dev/null 2>&1; then
    PKG_MANAGER="dnf"
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    PKG_MANAGER="yum"
    return
  fi
  if command -v apt-get >/dev/null 2>&1; then
    PKG_MANAGER="apt"
    return
  fi
  die "no supported package manager found; expected dnf, yum, or apt-get"
}

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64)
      GO_ARCH="amd64"
      ;;
    aarch64|arm64)
      GO_ARCH="arm64"
      ;;
    *)
      die "unsupported architecture: $(uname -m)"
      ;;
  esac
}

install_base_packages() {
  detect_package_manager
  log "installing base packages with ${PKG_MANAGER}"

  case "$PKG_MANAGER" in
    dnf)
      dnf makecache
      dnf install -y ca-certificates curl git tar gzip firewalld wget
      ;;
    yum)
      yum makecache
      yum install -y ca-certificates curl git tar gzip firewalld wget
      ;;
    apt)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y ca-certificates curl git tar gzip docker.io ufw
      ;;
  esac
}

install_go() {
  detect_arch
  local go_tar="go${GO_VERSION}.linux-${GO_ARCH}.tar.gz"
  local go_urls=(
    "https://go.dev/dl/${go_tar}"
    "https://dl.google.com/go/${go_tar}"
    "https://golang.google.cn/dl/${go_tar}"
  )
  local downloaded="false"
  local url=""

  log "installing Go ${GO_VERSION}"

  for url in "${go_urls[@]}"; do
    log "trying Go download: ${url}"
    if curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 "$url" -o "/tmp/${go_tar}"; then
      downloaded="true"
      break
    fi
  done

  if [[ "$downloaded" != "true" ]]; then
    die "failed to download ${go_tar} from all configured Go mirrors"
  fi

  rm -rf /usr/local/go
  tar -C /usr/local -xzf "/tmp/${go_tar}"

  cat >/etc/profile.d/go.sh <<'EOF'
export PATH=/usr/local/go/bin:$PATH
EOF
  chmod 0644 /etc/profile.d/go.sh
  export PATH="/usr/local/go/bin:$PATH"
}

prepare_directories() {
  log "preparing runtime directories"
  mkdir -p "$BIN_DIR" "$LOG_DIR" "$MYSQL_DATA_DIR" "$MINIO_DATA_DIR"
  mkdir -p "$(dirname "$RUNTIME_ENV_PATH")"
}

dir_has_files() {
  local dir="$1"
  [[ -d "$dir" ]] && find "$dir" -mindepth 1 -print -quit 2>/dev/null | grep -q .
}

cleanup_old_docker_packages() {
  log "removing conflicting container packages"

  case "$PKG_MANAGER" in
    dnf)
      rm -f /etc/yum.repos.d/docker*.repo
      dnf -y remove \
        podman-docker \
        docker \
        docker-client \
        docker-client-latest \
        docker-common \
        docker-latest \
        docker-latest-logrotate \
        docker-logrotate \
        docker-engine \
        docker-ce \
        docker-ce-cli \
        docker-buildx-plugin \
        docker-compose-plugin \
        docker-ce-rootless-extras \
        containerd.io \
        runc || true
      ;;
    yum)
      rm -f /etc/yum.repos.d/docker*.repo
      yum -y remove \
        podman-docker \
        docker \
        docker-client \
        docker-client-latest \
        docker-common \
        docker-latest \
        docker-latest-logrotate \
        docker-logrotate \
        docker-engine \
        docker-ce \
        docker-ce-cli \
        docker-buildx-plugin \
        docker-compose-plugin \
        docker-ce-rootless-extras \
        containerd.io \
        runc || true
      ;;
    apt)
      for pkg in docker.io docker-buildx-plugin docker-ce-cli docker-ce-rootless-extras docker-compose-plugin docker-doc docker-compose podman-docker containerd runc; do
        apt-get remove -y "$pkg" || true
      done
      ;;
  esac
}

install_docker_engine() {
  log "installing Docker engine"

  case "$PKG_MANAGER" in
    dnf)
      wget -O /etc/yum.repos.d/docker-ce.repo http://mirrors.cloud.aliyuncs.com/docker-ce/linux/centos/docker-ce.repo
      sed -i 's|https://mirrors.aliyun.com|http://mirrors.cloud.aliyuncs.com|g' /etc/yum.repos.d/docker-ce.repo
      dnf -y install dnf-plugin-releasever-adapter --repo alinux3-plus || true
      dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || true
      ;;
    yum)
      wget -O /etc/yum.repos.d/docker-ce.repo http://mirrors.cloud.aliyuncs.com/docker-ce/linux/centos/docker-ce.repo
      sed -i 's|https://mirrors.aliyun.com|http://mirrors.cloud.aliyuncs.com|g' /etc/yum.repos.d/docker-ce.repo
      yum install -y yum-plugin-releasever-adapter --disablerepo='*' --enablerepo=plus || true
      yum -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || true
      ;;
    apt)
      :
      ;;
  esac
}

docker_service_exists() {
  [[ -f /usr/lib/systemd/system/docker.service || -f /etc/systemd/system/docker.service ]]
}

install_docker_fallback() {
  log "docker.service still missing; falling back to Docker convenience script"
  case "$PKG_MANAGER" in
    dnf)
      dnf -y remove podman-docker docker docker-ce docker-ce-cli containerd.io runc || true
      ;;
    yum)
      yum -y remove podman-docker docker docker-ce docker-ce-cli containerd.io runc || true
      ;;
    apt)
      apt-get remove -y podman-docker docker.io docker-ce docker-ce-cli containerd.io runc || true
      ;;
  esac
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
}

ensure_docker_installed() {
  if command -v docker >/dev/null 2>&1 && docker_service_exists; then
    return
  fi

  install_docker_fallback

  if ! command -v docker >/dev/null 2>&1; then
    die "docker command is still unavailable after installation"
  fi
  if ! docker_service_exists; then
    die "docker.service is still unavailable after installation"
  fi
}

start_docker() {
  ensure_docker_installed
  log "starting Docker"
  systemctl daemon-reload

  if systemctl enable --now docker; then
    return
  fi

  log "docker service failed to start from current install, retrying with fallback installer"
  install_docker_fallback
  systemctl daemon-reload
  systemctl enable --now docker
}

recreate_container_if_exists() {
  local name="$1"
  if docker ps -a --format '{{.Names}}' | grep -Fxq "$name"; then
    log "removing existing container: $name"
    docker rm -f "$name" >/dev/null
  fi
}

start_mysql_container() {
  log "starting MySQL container ${MYSQL_IMAGE}:${MYSQL_TAG}"
  if dir_has_files "$MYSQL_DATA_DIR"; then
    log "detected existing MySQL data directory at ${MYSQL_DATA_DIR}; initialization passwords from current env may be ignored"
  fi
  recreate_container_if_exists "$MYSQL_CONTAINER_NAME"

  docker run -d \
    --name "$MYSQL_CONTAINER_NAME" \
    --restart unless-stopped \
    -e MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
    -e MYSQL_DATABASE="$MYSQL_DATABASE" \
    -e MYSQL_USER="$MYSQL_APP_USER" \
    -e MYSQL_PASSWORD="$MYSQL_APP_PASSWORD" \
    -p "127.0.0.1:${MYSQL_PORT}:3306" \
    -v "${MYSQL_DATA_DIR}:/var/lib/mysql" \
    "${MYSQL_IMAGE}:${MYSQL_TAG}" >/dev/null
}

init_mysql() {
  log "waiting for MySQL to become ready"
  until docker exec "$MYSQL_CONTAINER_NAME" mysqladmin ping -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent >/dev/null 2>&1; do
    sleep 3
  done

  log "verifying MySQL login and waiting for SQL execution readiness"
  local attempts=20
  local i
  for ((i=1; i<=attempts; i++)); do
    if docker exec "$MYSQL_CONTAINER_NAME" mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1;" >/dev/null 2>&1; then
      break
    fi

    if (( i == attempts )); then
      log "MySQL container logs:"
      docker logs "$MYSQL_CONTAINER_NAME" || true
      die "mysql root authentication or readiness check failed. The data directory at ${MYSQL_DATA_DIR} may have been initialized earlier with a different MYSQL_ROOT_PASSWORD, or MySQL may still be restarting."
    fi

    sleep 3
  done

  log "creating database schema in MySQL"
  for ((i=1; i<=attempts; i++)); do
    if docker exec -i "$MYSQL_CONTAINER_NAME" mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_APP_USER}'@'%' IDENTIFIED BY '${MYSQL_APP_PASSWORD}';
ALTER USER '${MYSQL_APP_USER}'@'%' IDENTIFIED BY '${MYSQL_APP_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_APP_USER}'@'%';
FLUSH PRIVILEGES;

USE \`${MYSQL_DATABASE}\`;

CREATE TABLE IF NOT EXISTS drama(
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    cover_url VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS episode(
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    drama_id BIGINT NOT NULL,
    episode_no INT NOT NULL,
    video_url VARCHAR(500) NOT NULL,
    duration INT NOT NULL,
    UNIQUE KEY idx_drama_episode_no (drama_id, episode_no),
    CONSTRAINT fk_episode_drama FOREIGN KEY (drama_id) REFERENCES drama(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS highlight_event(
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    episode_id BIGINT NOT NULL,
    trigger_time INT NOT NULL,
    duration INT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    heat_level INT NOT NULL,
    payload JSON,
    KEY idx_episode_trigger (episode_id, trigger_time),
    KEY idx_event_type (event_type),
    CONSTRAINT fk_highlight_episode FOREIGN KEY (episode_id) REFERENCES episode(id) ON DELETE CASCADE ON UPDATE CASCADE
);
SQL
    then
      return
    fi

    if (( i == attempts )); then
      log "MySQL container logs:"
      docker logs "$MYSQL_CONTAINER_NAME" || true
      die "failed to initialize MySQL schema after ${attempts} attempts"
    fi

    sleep 3
  done
}

start_minio_container() {
  log "starting MinIO container ${MINIO_IMAGE}:${MINIO_TAG}"
  recreate_container_if_exists "$MINIO_CONTAINER_NAME"

  docker run -d \
    --name "$MINIO_CONTAINER_NAME" \
    --restart unless-stopped \
    -e MINIO_ROOT_USER="$MINIO_ROOT_USER" \
    -e MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD" \
    -p "${MINIO_API_PORT}:9000" \
    -p "${MINIO_CONSOLE_PORT}:9001" \
    -v "${MINIO_DATA_DIR}:/data" \
    "${MINIO_IMAGE}:${MINIO_TAG}" server /data --console-address ":9001" >/dev/null
}

init_minio_bucket() {
  log "creating MinIO bucket and prefixes"
  docker run --rm --network host --entrypoint /bin/sh "${MC_IMAGE}:${MC_TAG}" -c "
    set -e;
    until mc alias set local http://127.0.0.1:${MINIO_API_PORT} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}; do
      sleep 2;
    done;
    mc mb local/${MINIO_BUCKET} --ignore-existing;
    printf '' | mc pipe local/${MINIO_BUCKET}/videos/.keep;
    printf '' | mc pipe local/${MINIO_BUCKET}/covers/.keep;
    printf '' | mc pipe local/${MINIO_BUCKET}/effects/.keep;
    mc anonymous set download local/${MINIO_BUCKET};
  "
}

build_backend() {
  log "building backend executable"
  export PATH="/usr/local/go/bin:$PATH"
  export GOPROXY="${GO_PROXY}"
  export GOSUMDB="${GO_SUMDB}"
  export GOTOOLCHAIN="local"
  export GOMODCACHE="$BACKEND_DIR/.gocache/mod"
  export GOCACHE="$BACKEND_DIR/.gocache/build"

  cd "$BACKEND_DIR"
  log "using GOPROXY=${GOPROXY}"
  log "using GOSUMDB=${GOSUMDB}"
  /usr/local/go/bin/go mod tidy
  /usr/local/go/bin/go build -buildvcs=false -o "$BIN_PATH" .
  chmod 0755 "$BIN_PATH"
}

write_backend_env() {
  log "writing backend env file"
  cat >"$RUNTIME_ENV_PATH" <<EOF
APP_PORT=${APP_PORT}
MYSQL_DSN=${MYSQL_APP_USER}:${MYSQL_APP_PASSWORD}@tcp(${MYSQL_HOST}:${MYSQL_PORT})/${MYSQL_DATABASE}?charset=utf8mb4&parseTime=True&loc=Local
MINIO_ENABLED=true
MINIO_ENDPOINT=127.0.0.1:${MINIO_API_PORT}
MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
MINIO_BUCKET=${MINIO_BUCKET}
MINIO_USE_SSL=false
MINIO_PUBLIC_BASE_URL=${MINIO_PUBLIC_SCHEME}://${PUBLIC_IP}:${MINIO_API_PORT}/${MINIO_BUCKET}
EOF
  chmod 0600 "$RUNTIME_ENV_PATH"
}

write_systemd_service() {
  log "writing and starting systemd service"
  cat >"$SYSTEMD_SERVICE_PATH" <<EOF
[Unit]
Description=Short Drama Backend Service
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${BACKEND_DIR}
EnvironmentFile=${RUNTIME_ENV_PATH}
ExecStartPre=/bin/bash -c 'until (echo >/dev/tcp/${MYSQL_HOST}/${MYSQL_PORT}) >/dev/null 2>&1; do sleep 2; done'
ExecStartPre=/bin/bash -c 'until (echo >/dev/tcp/127.0.0.1/${MINIO_API_PORT}) >/dev/null 2>&1; do sleep 2; done'
ExecStart=${BIN_PATH}
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/backend.log
StandardError=append:${LOG_DIR}/backend-error.log

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable --now "$SERVICE_NAME"
}

configure_firewall() {
  if [[ "${ENABLE_UFW:-true}" != "true" ]]; then
    log "skipping OS firewall configuration"
    return
  fi

  if command -v ufw >/dev/null 2>&1; then
    log "opening firewall ports with ufw"
    ufw allow OpenSSH || true
    ufw allow "${APP_PORT}/tcp" || true
    ufw allow "${MINIO_API_PORT}/tcp" || true
    ufw allow "${MINIO_CONSOLE_PORT}/tcp" || true
    ufw --force enable
    return
  fi

  if command -v firewall-cmd >/dev/null 2>&1; then
    log "opening firewall ports with firewalld"
    systemctl enable --now firewalld || true
    firewall-cmd --permanent --add-port="${APP_PORT}/tcp" || true
    firewall-cmd --permanent --add-port="${MINIO_API_PORT}/tcp" || true
    firewall-cmd --permanent --add-port="${MINIO_CONSOLE_PORT}/tcp" || true
    firewall-cmd --reload || true
    return
  fi

  log "no supported firewall tool found; skipping OS firewall changes"
}

print_summary() {
  cat <<EOF

Deployment complete.

Backend:
  ${BACKEND_PUBLIC_SCHEME}://${PUBLIC_IP}:${APP_PORT}
  Health: ${BACKEND_PUBLIC_SCHEME}://${PUBLIC_IP}:${APP_PORT}/health

MinIO:
  API: ${MINIO_PUBLIC_SCHEME}://${PUBLIC_IP}:${MINIO_API_PORT}
  Console: ${MINIO_PUBLIC_SCHEME}://${PUBLIC_IP}:${MINIO_CONSOLE_PORT}
  Bucket: ${MINIO_BUCKET}

Useful commands:
  systemctl status ${SERVICE_NAME}
  journalctl -u ${SERVICE_NAME} -f
  docker ps
  docker logs -f ${MYSQL_CONTAINER_NAME}
  docker logs -f ${MINIO_CONTAINER_NAME}

If public access still fails, check the cloud provider security group for ports ${APP_PORT}, ${MINIO_API_PORT}, and ${MINIO_CONSOLE_PORT}.
EOF
}

main() {
  require_root
  load_env
  validate_env
  install_base_packages
  cleanup_old_docker_packages
  install_docker_engine
  install_go
  prepare_directories
  start_docker
  start_mysql_container
  init_mysql
  start_minio_container
  init_minio_bucket
  build_backend
  write_backend_env
  write_systemd_service
  configure_firewall
  print_summary
}

main "$@"
