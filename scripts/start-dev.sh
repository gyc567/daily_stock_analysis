#!/usr/bin/env bash
# =================================================================
# Daily Stock Analysis - Development Startup Script
# =================================================================
# Usage:
#   ./scripts/start-dev.sh          # Start both frontend and backend
#   ./scripts/start-dev.sh frontend # Start only frontend
#   ./scripts/start-dev.sh backend  # Start only backend
#   ./scripts/start-dev.sh stop     # Stop all services
# =================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configuration
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
VENV_PATH="${VENV_PATH:-${HOME}/dsa-venv}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
        log_error "Python venv not found at ${VENV_PATH}"
        exit 1
    fi
    
    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js not found"
        exit 1
    fi
    
    log_success "Dependencies OK"
}

# Stop existing services
stop_services() {
    log_info "Stopping existing services..."
    pkill -f "uvicorn server:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    log_success "Services stopped"
}

# Start backend
start_backend() {
    log_info "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}..."
    
    cd "${ROOT_DIR}"
    
    nohup "${VENV_PATH}/bin/python" -m uvicorn server:app \
        --host "${BACKEND_HOST}" \
        --port "${BACKEND_PORT}" \
        > "${ROOT_DIR}/logs/backend.log" 2>&1 &
    
    BACKEND_PID=$!
    echo "Backend PID: ${BACKEND_PID}"
    
    log_info "Waiting for backend..."
    for i in {1..30}; do
        if curl -s "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
            log_success "Backend ready!"
            return 0
        fi
        sleep 1
    done
    
    log_warning "Backend may not be ready, check logs/backend.log"
    return 0
}

# Start frontend
start_frontend() {
    log_info "Starting frontend on ${FRONTEND_PORT}..."
    
    cd "${ROOT_DIR}/apps/dsa-web"
    
    nohup npm run dev -- --host "${BACKEND_HOST}" --port "${FRONTEND_PORT}" \
        > "${ROOT_DIR}/logs/frontend.log" 2>&1 &
    
    FRONTEND_PID=$!
    echo "Frontend PID: ${FRONTEND_PID}"
    
    log_info "Waiting for frontend..."
    for i in {1..30}; do
        if curl -s "http://127.0.0.1:${FRONTEND_PORT}" >/dev/null 2>&1; then
            log_success "Frontend ready!"
            return 0
        fi
        sleep 1
    done
    
    log_warning "Frontend may not be ready, check logs/frontend.log"
    return 0
}

# Main
main() {
    mkdir -p "${ROOT_DIR}/logs"
    
    case "${1:-all}" in
        stop)
            stop_services
            ;;
        frontend)
            check_dependencies
            stop_services
            start_frontend
            ;;
        backend)
            check_dependencies
            stop_services
            start_backend
            ;;
        all|"")
            check_dependencies
            stop_services
            start_backend
            start_frontend
            log_success "========================================="
            log_success "Services started:"
            log_success "  Backend: http://localhost:${BACKEND_PORT}"
            log_success "  Frontend: http://localhost:${FRONTEND_PORT}"
            log_success "========================================="
            ;;
        *)
            echo "Usage: $0 {all|frontend|backend|stop}"
            exit 1
            ;;
    esac
}

main "$@"
