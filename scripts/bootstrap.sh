#!/usr/bin/env bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_deps=()
    
    if ! command_exists docker; then
        missing_deps+=("docker")
    fi
    
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        missing_deps+=("docker-compose")
    fi
    
    if ! command_exists poetry; then
        missing_deps+=("poetry")
    fi
    
    if ! command_exists make; then
        missing_deps+=("make")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and run this script again."
        log_info ""
        log_info "Installation instructions:"
        log_info "- Docker: https://docs.docker.com/get-docker/"
        log_info "- Poetry: https://python-poetry.org/docs/#installation"
        log_info "- Make: Usually available via package manager (apt, brew, etc.)"
        exit 1
    fi
    
    log_success "All prerequisites are installed"
}

# Setup environment file
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        log_success "Created .env file from .env.example"
        log_warning "Please review and update .env file with your specific configuration"
    else
        log_info ".env file already exists, skipping creation"
    fi
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    if [ -f pyproject.toml ]; then
        poetry install
        log_success "Python dependencies installed"
    else
        log_error "pyproject.toml not found"
        exit 1
    fi
}

# Pull Docker images
pull_docker_images() {
    log_info "Pulling Docker images..."
    
    if [ -f docker/compose.dev.yml ]; then
        docker compose -f docker/compose.dev.yml pull
        log_success "Docker images pulled"
    else
        log_error "docker/compose.dev.yml not found"
        exit 1
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    local dirs=(
        "logs"
        "data"
        "certs"
        "backups"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    log_success "Directories created"
}

# Generate development certificates
generate_certificates() {
    log_info "Generating development certificates..."
    
    if [ ! -f certs/cert.pem ] || [ ! -f certs/key.pem ]; then
        mkdir -p certs
        openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem \
            -days 365 -nodes -subj "/CN=localhost" >/dev/null 2>&1
        log_success "Development certificates generated"
    else
        log_info "Development certificates already exist"
    fi
}

# Setup Git hooks
setup_git_hooks() {
    log_info "Setting up Git hooks..."
    
    if command_exists pre-commit; then
        poetry run pre-commit install
        log_success "Git hooks installed"
    else
        log_warning "pre-commit not available, skipping Git hooks setup"
    fi
}

# Validate setup
validate_setup() {
    log_info "Validating setup..."
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if required files exist
    local required_files=(
        ".env"
        "docker/compose.dev.yml"
        "pyproject.toml"
        "Makefile"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    
    log_success "Setup validation passed"
}

# Main bootstrap function
main() {
    log_info "🚀 Starting AgenticHR bootstrap process..."
    log_info ""
    
    check_prerequisites
    setup_environment
    create_directories
    generate_certificates
    install_dependencies
    pull_docker_images
    setup_git_hooks
    validate_setup
    
    log_info ""
    log_success "🎉 Bootstrap completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Review and update the .env file with your configuration"
    log_info "2. Run 'make dev.up' to start the development environment"
    log_info "3. Run 'make dev.health' to check service health"
    log_info "4. Visit http://localhost:8000 to access the API gateway"
    log_info "5. Visit http://localhost:8080 to access Keycloak (admin/admin)"
    log_info ""
    log_info "For more information, see the README.md file or run 'make help'"
}

# Run main function
main "$@"
