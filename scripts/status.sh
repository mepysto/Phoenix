#!/usr/bin/env bash
#
# Phoenix System Status Script
# Usage: ./scripts/status.sh
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║            🔥 PHOENIX - System Status 🔥                      ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_container() {
    local container_name="$1"
    local display_name="$2"
    local port="$3"
    
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        local status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null)
        local health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "N/A")
        
        if [[ "$status" == "running" ]]; then
            if [[ "$health" == "healthy" ]]; then
                echo -e "  ${GREEN}●${NC} ${display_name} (port ${port}) - ${GREEN}running (healthy)${NC}"
            else
                echo -e "  ${YELLOW}●${NC} ${display_name} (port ${port}) - ${YELLOW}running${NC}"
            fi
        else
            echo -e "  ${RED}●${NC} ${display_name} (port ${port}) - ${RED}${status}${NC}"
        fi
    else
        echo -e "  ${RED}○${NC} ${display_name} (port ${port}) - ${RED}not running${NC}"
    fi
}

check_process() {
    local pattern="$1"
    local display_name="$2"
    local port="$3"
    
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo -e "  ${GREEN}●${NC} ${display_name} (port ${port}) - ${GREEN}running${NC}"
    else
        echo -e "  ${RED}○${NC} ${display_name} (port ${port}) - ${RED}not running${NC}"
    fi
}

check_port() {
    local port="$1"
    local display_name="$2"
    
    if command -v nc &> /dev/null; then
        if nc -z localhost "$port" 2>/dev/null; then
            echo -e "  ${GREEN}●${NC} Port ${port} (${display_name}) - ${GREEN}open${NC}"
        else
            echo -e "  ${RED}○${NC} Port ${port} (${display_name}) - ${RED}closed${NC}"
        fi
    elif command -v curl &> /dev/null; then
        if curl -s --connect-timeout 1 "http://localhost:$port" > /dev/null 2>&1; then
            echo -e "  ${GREEN}●${NC} Port ${port} (${display_name}) - ${GREEN}open${NC}"
        else
            echo -e "  ${RED}○${NC} Port ${port} (${display_name}) - ${RED}closed${NC}"
        fi
    else
        echo -e "  ${YELLOW}?${NC} Port ${port} (${display_name}) - ${YELLOW}unable to check${NC}"
    fi
}

check_tmux_session() {
    if command -v tmux &> /dev/null; then
        if tmux has-session -t phoenix 2>/dev/null; then
            echo -e "  ${GREEN}●${NC} tmux session 'phoenix' - ${GREEN}active${NC}"
            echo -e "    ${BLUE}→${NC} Attach: tmux attach -t phoenix"
        else
            echo -e "  ${YELLOW}○${NC} tmux session 'phoenix' - ${YELLOW}not found${NC}"
        fi
    fi
}

main() {
    print_banner
    
    echo -e "${BLUE}Docker Containers:${NC}"
    check_container "phoenix-db" "PostgreSQL+TimescaleDB" "25432"
    check_container "phoenix-redis" "Redis" "26379"
    check_container "phoenix-api" "API (Docker)" "28000"
    check_container "phoenix-web" "Web (Docker)" "23000"
    echo ""
    
    echo -e "${BLUE}Local Processes:${NC}"
    check_process "uvicorn src.main:app" "API (uvicorn)" "28000"
    check_process "next dev" "Web (next dev)" "23000"
    echo ""
    
    echo -e "${BLUE}Port Status:${NC}"
    check_port 23000 "Frontend"
    check_port 28000 "API"
    check_port 25432 "Database"
    check_port 26379 "Redis"
    echo ""
    
    echo -e "${BLUE}Development Session:${NC}"
    check_tmux_session
    echo ""
    
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "  ${BLUE}Frontend:${NC}  http://localhost:23000"
    echo -e "  ${BLUE}API:${NC}       http://localhost:28000"
    echo -e "  ${BLUE}API Docs:${NC}  http://localhost:28000/docs"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

main "$@"
