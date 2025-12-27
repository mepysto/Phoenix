#!/usr/bin/env bash
#
# Phoenix System Shutdown Script
# Usage: ./scripts/stop.sh [mode]
#   mode: all (default) | docker | dev
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/infrastructure/docker/docker-compose.yml"

MODE="${1:-all}"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║            🔥 PHOENIX - Shutting Down 🔥                      ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

stop_dev_servers() {
    log_info "Stopping development servers..."
    
    if command -v tmux &> /dev/null; then
        if tmux has-session -t phoenix 2>/dev/null; then
            tmux kill-session -t phoenix
            log_success "Killed tmux session 'phoenix'"
        else
            log_warn "No tmux session 'phoenix' found"
        fi
    fi
    
    if [[ -f /tmp/phoenix-api.pid ]]; then
        local api_pid=$(cat /tmp/phoenix-api.pid)
        if kill -0 "$api_pid" 2>/dev/null; then
            kill "$api_pid" 2>/dev/null || true
            log_success "Stopped API server (PID: $api_pid)"
        fi
        rm -f /tmp/phoenix-api.pid
    fi
    
    if [[ -f /tmp/phoenix-web.pid ]]; then
        local web_pid=$(cat /tmp/phoenix-web.pid)
        if kill -0 "$web_pid" 2>/dev/null; then
            kill "$web_pid" 2>/dev/null || true
            log_success "Stopped Web server (PID: $web_pid)"
        fi
        rm -f /tmp/phoenix-web.pid
    fi
    
    pkill -f "uvicorn src.main:app" 2>/dev/null && log_info "Killed uvicorn processes" || true
    pkill -f "next dev" 2>/dev/null && log_info "Killed next dev processes" || true
    pkill -f "next-router-worker" 2>/dev/null || true
}

stop_docker_services() {
    local remove_volumes="${1:-false}"
    
    log_info "Stopping Docker containers..."
    
    cd "$PROJECT_ROOT"
    
    if [[ "$remove_volumes" == "true" ]]; then
        docker compose -f "$DOCKER_COMPOSE_FILE" down -v
        log_success "Docker containers stopped and volumes removed"
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" down
        log_success "Docker containers stopped (volumes preserved)"
    fi
}

main() {
    print_banner
    
    echo -e "${YELLOW}Stopping Phoenix services (mode: ${MODE})...${NC}"
    echo ""
    
    case "$MODE" in
        all)
            stop_dev_servers
            stop_docker_services
            ;;
        docker)
            stop_docker_services
            ;;
        dev)
            stop_dev_servers
            ;;
        clean)
            stop_dev_servers
            stop_docker_services "true"
            log_warn "All data volumes have been removed!"
            ;;
        *)
            echo "Usage: $0 [all|docker|dev|clean]"
            echo "  all    - Stop all services (default)"
            echo "  docker - Stop only Docker containers"
            echo "  dev    - Stop only dev servers (tmux/background processes)"
            echo "  clean  - Stop all and remove Docker volumes"
            exit 1
            ;;
    esac
    
    echo ""
    log_success "Phoenix has been stopped"
}

main "$@"
