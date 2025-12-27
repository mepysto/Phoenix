#!/usr/bin/env bash
#
# Phoenix System Startup Script
# Usage: ./scripts/start.sh [mode]
#   mode: dev (default) | docker | db-only
#
# Modes:
#   dev      - Start DB/Redis in Docker + API/Web locally (for development)
#   docker   - Start all services in Docker containers
#   db-only  - Start only database and Redis containers
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/infrastructure/docker/docker-compose.yml"

# Default mode
MODE="${1:-dev}"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║   🔥 PHOENIX - Digital Twin Humanitarian Platform 🔥          ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check for dev mode requirements
    if [[ "$MODE" == "dev" ]]; then
        if ! command -v pnpm &> /dev/null; then
            log_error "pnpm is not installed. Please install pnpm first."
            exit 1
        fi
        
        if ! command -v python3 &> /dev/null; then
            log_error "Python 3 is not installed. Please install Python 3.11+ first."
            exit 1
        fi
    fi
    
    log_success "All requirements satisfied"
}

start_docker_services() {
    local services="$1"
    
    log_info "Starting Docker services: ${services:-all}..."
    
    cd "$PROJECT_ROOT"
    
    if [[ -n "$services" ]]; then
        docker compose -f "$DOCKER_COMPOSE_FILE" up -d $services
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" up -d
    fi
    
    log_success "Docker services started"
}

wait_for_db() {
    log_info "Waiting for database to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker exec phoenix-db pg_isready -U phoenix -d phoenix_db &> /dev/null; then
            log_success "Database is ready"
            return 0
        fi
        
        echo -ne "\r${YELLOW}[WAIT]${NC} Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    echo ""
    log_error "Database failed to start within timeout"
    exit 1
}

wait_for_redis() {
    log_info "Waiting for Redis to be ready..."
    
    local max_attempts=15
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker exec phoenix-redis redis-cli ping &> /dev/null; then
            log_success "Redis is ready"
            return 0
        fi
        
        echo -ne "\r${YELLOW}[WAIT]${NC} Attempt $attempt/$max_attempts..."
        sleep 1
        ((attempt++))
    done
    
    echo ""
    log_error "Redis failed to start within timeout"
    exit 1
}

run_migrations() {
    log_info "Running database migrations..."
    
    cd "$PROJECT_ROOT/apps/api"
    
    if [[ -f "alembic.ini" ]]; then
        # Use uv if available, otherwise use pip
        if command -v uv &> /dev/null; then
            uv run alembic upgrade head 2>/dev/null || log_warn "Migration skipped (may already be up to date)"
        else
            python3 -m alembic upgrade head 2>/dev/null || log_warn "Migration skipped (may already be up to date)"
        fi
    else
        log_warn "No alembic.ini found, skipping migrations"
    fi
    
    cd "$PROJECT_ROOT"
}

start_dev_servers() {
    log_info "Starting development servers..."
    
    cd "$PROJECT_ROOT"
    
    # Create a tmux session or use background processes
    if command -v tmux &> /dev/null; then
        # Kill existing session if exists
        tmux kill-session -t phoenix 2>/dev/null || true
        
        # Create new tmux session
        tmux new-session -d -s phoenix -n api
        tmux send-keys -t phoenix:api "cd $PROJECT_ROOT/apps/api && .venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 28000 --reload" C-m
        
        tmux new-window -t phoenix -n web
        tmux send-keys -t phoenix:web "cd $PROJECT_ROOT && pnpm dev:web" C-m
        
        log_success "Development servers started in tmux session 'phoenix'"
        echo ""
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  To attach to the session:${NC}  tmux attach -t phoenix"
        echo -e "${GREEN}  To switch windows:${NC}         Ctrl+B, then 0 (api) or 1 (web)"
        echo -e "${GREEN}  To detach:${NC}                 Ctrl+B, then D"
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    else
        log_warn "tmux not found. Starting servers in background..."
        
        # Start API server
        cd "$PROJECT_ROOT/apps/api"
        nohup .venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 28000 --reload > /tmp/phoenix-api.log 2>&1 &
        echo $! > /tmp/phoenix-api.pid
        
        # Start Web server
        cd "$PROJECT_ROOT"
        nohup pnpm dev:web > /tmp/phoenix-web.log 2>&1 &
        echo $! > /tmp/phoenix-web.pid
        
        log_success "Development servers started in background"
        echo ""
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  API logs:${NC}  tail -f /tmp/phoenix-api.log"
        echo -e "${GREEN}  Web logs:${NC}  tail -f /tmp/phoenix-web.log"
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    fi
}

print_status() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Phoenix is running! 🚀${NC}"
    echo ""
    echo -e "  ${BLUE}Frontend:${NC}  http://localhost:23000"
    echo -e "  ${BLUE}API:${NC}       http://localhost:28000"
    echo -e "  ${BLUE}API Docs:${NC}  http://localhost:28000/docs"
    echo -e "  ${BLUE}Database:${NC}  localhost:25432 (PostgreSQL + TimescaleDB)"
    echo -e "  ${BLUE}Redis:${NC}     localhost:26379"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

# Main execution
main() {
    print_banner
    
    echo -e "${YELLOW}Starting Phoenix in '${MODE}' mode...${NC}"
    echo ""
    
    check_requirements
    
    case "$MODE" in
        dev)
            start_docker_services "db redis"
            wait_for_db
            wait_for_redis
            run_migrations
            start_dev_servers
            print_status
            ;;
        docker)
            start_docker_services
            wait_for_db
            wait_for_redis
            print_status
            ;;
        db-only)
            start_docker_services "db redis"
            wait_for_db
            wait_for_redis
            echo ""
            log_success "Database and Redis are ready"
            echo -e "  ${BLUE}Database:${NC}  localhost:25432"
            echo -e "  ${BLUE}Redis:${NC}     localhost:26379"
            ;;
        *)
            log_error "Unknown mode: $MODE"
            echo "Usage: $0 [dev|docker|db-only]"
            exit 1
            ;;
    esac
}

main "$@"
