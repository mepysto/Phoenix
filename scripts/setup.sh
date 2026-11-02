#!/usr/bin/env bash
#
# Phoenix setup — install everything and prepare a working instance.
#
#   scripts/setup.sh                       development: dependencies, .env, database, migrations
#   scripts/setup.sh --seed                ... and load sample events
#   scripts/setup.sh --no-docker           use the database already in DATABASE_URL
#   scripts/setup.sh --prod DOMAIN EMAIL   production on this server: .env with fresh
#                                          secrets, HTTPS via Caddy, all services in Docker
#
# Safe to re-run: existing .env values are kept; only missing secrets are filled.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
API_DIR="$ROOT/apps/api"
COMPOSE_DIR="$ROOT/infrastructure/docker"

MODE=dev
SEED=0
USE_DOCKER=1
DOMAIN=""
ACME_EMAIL=""

c_info=$'\033[0;34m'; c_ok=$'\033[0;32m'; c_warn=$'\033[1;33m'; c_err=$'\033[0;31m'; c_off=$'\033[0m'
info() { echo "${c_info}==>${c_off} $*"; }
ok() { echo "${c_ok} ✓${c_off} $*"; }
warn() { echo "${c_warn} !${c_off} $*"; }
die() { echo "${c_err} ✗ $*${c_off}" >&2; exit 1; }

usage() { sed -n '3,12p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod)
      MODE=prod
      DOMAIN="${2:-}"
      ACME_EMAIL="${3:-}"
      [[ -n "$DOMAIN" && -n "$ACME_EMAIL" ]] || die "--prod needs a domain and an e-mail: --prod phoenix.example.org ops@example.org"
      shift 3
      ;;
    --seed) SEED=1; shift ;;
    --no-docker) USE_DOCKER=0; shift ;;
    -h | --help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
done

# --- helpers -------------------------------------------------------------------

version_ge() { # version_ge 3.12.1 3.11  → true
  [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" == "$2" ]]
}

random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    python3 -c "import secrets; print(secrets.token_hex(24))"
  fi
}

env_get() { # value of KEY in .env (empty if unset or commented out)
  [[ -f "$ENV_FILE" ]] || return 0
  grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true
}

env_set() { # set KEY=VALUE, replacing an existing or commented-out line
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  if grep -qE "^#? ?$key=" "$ENV_FILE"; then
    awk -v k="$key" -v v="$value" '
      !done && $0 ~ "^#? ?" k "=" { print k "=" v; done = 1; next }
      { print }
    ' "$ENV_FILE" >"$tmp"
  else
    cat "$ENV_FILE" >"$tmp"
    printf '%s=%s\n' "$key" "$value" >>"$tmp"
  fi
  cat "$tmp" >"$ENV_FILE"
  rm -f "$tmp"
}

env_default() { # set KEY only when it has no value yet
  [[ -n "$(env_get "$1")" ]] || env_set "$1" "$2"
}

compose() {
  local files=(-f "$COMPOSE_DIR/docker-compose.yml")
  [[ "$MODE" == prod ]] && files+=(-f "$COMPOSE_DIR/docker-compose.prod.yml")
  docker compose "${files[@]}" --env-file "$ENV_FILE" "$@"
}

wait_healthy() { # wait_healthy <container> <seconds>
  local name="$1" limit="$2" waited=0 state
  while (( waited < limit )); do
    state="$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null || echo missing)"
    [[ "$state" == healthy ]] && return 0
    sleep 3; waited=$((waited + 3))
  done
  return 1
}

# --- checks --------------------------------------------------------------------

check_tools() {
  info "Checking tools"
  if [[ "$USE_DOCKER" == 1 || "$MODE" == prod ]]; then
    command -v docker >/dev/null || die "Docker is required (https://docs.docker.com/engine/install/)"
    docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required ('docker compose')"
    docker info >/dev/null 2>&1 || die "Docker is installed but not running (or this user cannot use it)"
    ok "Docker $(docker version --format '{{.Server.Version}}' 2>/dev/null)"
  fi
  [[ "$MODE" == prod ]] && return 0

  command -v node >/dev/null || die "Node.js 20+ is required"
  version_ge "$(node -v | tr -d v)" 20.0.0 || die "Node.js 20+ is required (found $(node -v))"
  ok "Node.js $(node -v)"
  if ! command -v pnpm >/dev/null; then
    command -v corepack >/dev/null || die "pnpm is required (npm install -g pnpm@9)"
    info "Enabling pnpm through corepack"
    corepack enable && corepack prepare pnpm@9.15.1 --activate
  fi
  ok "pnpm $(pnpm -v)"
  command -v python3 >/dev/null || die "Python 3.12 is required"
  local py
  py="$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
  version_ge "$py" 3.11.0 || die "Python 3.11+ is required (found $py; 3.12 recommended)"
  ok "Python $py"
}

# --- .env --------------------------------------------------------------------------

write_env() {
  info "Preparing .env"
  if [[ ! -f "$ENV_FILE" ]]; then
    if [[ "$MODE" == prod ]]; then
      cp "$ROOT/.env.production.example" "$ENV_FILE"
    else
      cp "$ROOT/.env.example" "$ENV_FILE"
    fi
    ok "Created .env from the template"
  else
    ok "Keeping the existing .env (missing values are filled in)"
  fi
  chmod 600 "$ENV_FILE"

  env_default API_SYNC_KEY "$(random_secret)"
  # The template's placeholder is not a secret
  [[ "$(env_get API_SYNC_KEY)" == your-secure-sync-api-key-here ]] && env_set API_SYNC_KEY "$(random_secret)"
  env_default REDIS_PASSWORD "$(random_secret)"

  if [[ "$MODE" == prod ]]; then
    env_set DOMAIN "$DOMAIN"
    env_set ACME_EMAIL "$ACME_EMAIL"
    env_default POSTGRES_PASSWORD "$(random_secret)"
    env_default VAPID_SUBJECT "mailto:$ACME_EMAIL"
  else
    env_default POSTGRES_PASSWORD phoenix
    local pw user db
    pw="$(env_get POSTGRES_PASSWORD)"; user="$(env_get POSTGRES_USER)"; db="$(env_get POSTGRES_DB)"
    if [[ "$USE_DOCKER" == 1 ]]; then
      # Point at the Docker database and Redis this script starts
      env_set DATABASE_URL "postgresql://${user:-phoenix}:${pw}@localhost:25432/${db:-phoenix_db}"
      env_set REDIS_URL "redis://:$(env_get REDIS_PASSWORD)@localhost:26379"
    fi
    # Sign in locally without a mail server (refused in production)
    env_default AUTH_DEV_RETURN_LINK true
  fi
  ok ".env is ready (permissions 600)"
}

vapid_key() { # generate a Web Push key once; needs the API code (venv or image)
  [[ -n "$(env_get VAPID_PRIVATE_KEY)" ]] && return 0
  local line
  if [[ "$MODE" == prod ]]; then
    line="$(compose run --rm --no-deps -T api python -m scripts.gen_vapid_keys | grep '^VAPID_PRIVATE_KEY=')"
  else
    line="$(cd "$API_DIR" && .venv/bin/python -m scripts.gen_vapid_keys | grep '^VAPID_PRIVATE_KEY=')"
  fi
  env_set VAPID_PRIVATE_KEY "${line#VAPID_PRIVATE_KEY=}"
  ok "Generated a Web Push (VAPID) key"
}

# --- development -------------------------------------------------------------------

install_dev() {
  info "Installing web dependencies (pnpm)"
  (cd "$ROOT" && pnpm install --frozen-lockfile)
  ok "Web dependencies installed"

  info "Installing API dependencies (apps/api/.venv)"
  if [[ ! -x "$API_DIR/.venv/bin/python" ]]; then
    python3 -m venv "$API_DIR/.venv" || die "Could not create a virtualenv (on Debian/Ubuntu: apt install python3-venv)"
  fi
  "$API_DIR/.venv/bin/python" -m pip install --quiet --upgrade pip
  "$API_DIR/.venv/bin/python" -m pip install --quiet -r "$API_DIR/requirements-dev.lock"
  "$API_DIR/.venv/bin/python" -m pip install --quiet --no-deps -e "$API_DIR"
  ok "API dependencies installed"
}

database_dev() {
  if [[ "$USE_DOCKER" == 1 ]]; then
    info "Starting PostgreSQL (PostGIS, TimescaleDB) and Redis in Docker"
    compose up -d --build db redis
    wait_healthy phoenix-db 120 || die "The database did not become healthy; see: docker logs phoenix-db"
    ok "Database is up on localhost:25432"
  else
    warn "--no-docker: using DATABASE_URL from .env; it needs PostGIS available"
  fi

  info "Applying database migrations"
  (cd "$API_DIR" && .venv/bin/python -m scripts.migrate)
  ok "Schema is current"

  if [[ "$SEED" == 1 ]]; then
    info "Loading sample events"
    (cd "$API_DIR" && .venv/bin/python -m scripts.seed_data)
    ok "Sample data loaded"
  fi

  info "Running the setup check (pnpm doctor)"
  (cd "$API_DIR" && .venv/bin/python -m scripts.doctor) || warn "Some checks need attention (see above); feeds blocked by a firewall are expected offline"
}

# --- production --------------------------------------------------------------------

deploy_prod() {
  info "Building images"
  compose build
  vapid_key

  if [[ -z "$(env_get SMTP_HOST)" ]]; then
    warn "SMTP_HOST is empty: sign-in links cannot be e-mailed until you set SMTP_* in .env"
  fi
  if [[ -z "$(env_get PLATFORM_ADMIN_EMAILS)" ]]; then
    warn "PLATFORM_ADMIN_EMAILS is empty: nobody can approve organisations yet"
  fi

  info "Starting all services"
  compose up -d
  wait_healthy phoenix-api 240 || die "The API did not become healthy; see: docker logs phoenix-api"
  wait_healthy phoenix-web 180 || die "The web app did not become healthy; see: docker logs phoenix-web"
  ok "Phoenix is running behind Caddy"
  [[ "$SEED" == 1 ]] && compose exec -T api python -m scripts.seed_data && ok "Sample data loaded"

  cat <<EOF

  https://$DOMAIN  (certificate is issued on first visit once DNS points here)

  Next:
   1. DNS: an A/AAAA record for $DOMAIN pointing at this server; ports 80 and 443 open.
   2. Edit .env: PLATFORM_ADMIN_EMAILS and SMTP_*, then: scripts/setup.sh --prod $DOMAIN $ACME_EMAIL
   3. Backups: scripts/backup-db.sh (e.g. daily from cron; see docs/DEPLOYMENT.md)
EOF
}

# --- main ------------------------------------------------------------------------------

main() {
  echo "Phoenix setup ($MODE)"
  check_tools
  write_env
  if [[ "$MODE" == prod ]]; then
    deploy_prod
  else
    install_dev
    vapid_key
    database_dev
    cat <<EOF

  Setup complete. Start the app:  pnpm start   (or: pnpm dev with the database already up)
    Web  http://localhost:23000
    API  http://localhost:28000/docs
  Sign-in links appear in the browser in development (AUTH_DEV_RETURN_LINK=true).
  Add your address to PLATFORM_ADMIN_EMAILS in .env to approve organisations.
EOF
  fi
}

main
