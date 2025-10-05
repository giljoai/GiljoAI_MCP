#!/bin/bash

# GiljoAI MCP - WAN Deployment Script for Linux
# This script automates the deployment of GiljoAI MCP in WAN mode on Linux systems
# Supports: Ubuntu 20.04+, Debian 11+, RHEL 8+, CentOS 8+
#
# Usage:
#   sudo ./deploy_wan_linux.sh --domain yourdomain.com --email admin@yourdomain.com
#
# Options:
#   --domain DOMAIN       Your domain name (required)
#   --email EMAIL         Email for Let's Encrypt (required)
#   --proxy nginx|caddy   Reverse proxy to use (default: nginx)
#   --docker              Use Docker deployment (default: native)
#   --monitoring          Enable monitoring stack (Prometheus + Grafana)
#   --skip-certbot        Skip Let's Encrypt certificate generation
#   --help                Show this help message

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROXY="nginx"
DOMAIN=""
EMAIL=""
USE_DOCKER=false
ENABLE_MONITORING=false
SKIP_CERTBOT=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Functions
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

show_help() {
    cat << EOF
GiljoAI MCP - WAN Deployment Script for Linux

Usage:
    sudo ./deploy_wan_linux.sh [OPTIONS]

Required Options:
    --domain DOMAIN       Your domain name (e.g., yourdomain.com)
    --email EMAIL         Email address for Let's Encrypt notifications

Optional:
    --proxy nginx|caddy   Reverse proxy to use (default: nginx)
    --docker              Use Docker deployment instead of native
    --monitoring          Enable Prometheus + Grafana monitoring
    --skip-certbot        Skip automatic SSL certificate generation
    --help                Show this help message

Examples:
    # Basic nginx deployment
    sudo ./deploy_wan_linux.sh --domain example.com --email admin@example.com

    # Caddy deployment with monitoring
    sudo ./deploy_wan_linux.sh --domain example.com --email admin@example.com --proxy caddy --monitoring

    # Docker deployment with all features
    sudo ./deploy_wan_linux.sh --domain example.com --email admin@example.com --docker --monitoring

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --proxy)
            PROXY="$2"
            shift 2
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --monitoring)
            ENABLE_MONITORING=true
            shift
            ;;
        --skip-certbot)
            SKIP_CERTBOT=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$DOMAIN" ]] || [[ -z "$EMAIL" ]]; then
    log_error "Missing required parameters: --domain and --email"
    show_help
    exit 1
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

# Detect Linux distribution
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    else
        log_error "Cannot detect Linux distribution"
        exit 1
    fi
    log_info "Detected: $DISTRO $VERSION"
}

# Install dependencies based on distribution
install_dependencies() {
    log_info "Installing dependencies..."

    case $DISTRO in
        ubuntu|debian)
            apt-get update
            apt-get install -y curl wget git python3 python3-pip python3-venv \
                postgresql-client openssl ufw fail2ban
            ;;
        rhel|centos|rocky|almalinux)
            yum install -y curl wget git python3 python3-pip \
                postgresql openssl firewalld fail2ban
            ;;
        *)
            log_error "Unsupported distribution: $DISTRO"
            exit 1
            ;;
    esac

    log_success "Dependencies installed"
}

# Install Docker and Docker Compose
install_docker() {
    if command -v docker &> /dev/null; then
        log_info "Docker already installed"
        return
    fi

    log_info "Installing Docker..."

    case $DISTRO in
        ubuntu|debian)
            # Add Docker's official GPG key
            install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$DISTRO/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            chmod a+r /etc/apt/keyrings/docker.gpg

            # Add Docker repository
            echo \
              "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$DISTRO \
              $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
              tee /etc/apt/sources.list.d/docker.list > /dev/null

            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        rhel|centos|rocky|almalinux)
            yum install -y yum-utils
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            systemctl start docker
            systemctl enable docker
            ;;
    esac

    log_success "Docker installed"
}

# Install nginx
install_nginx() {
    if command -v nginx &> /dev/null; then
        log_info "nginx already installed"
        return
    fi

    log_info "Installing nginx..."

    case $DISTRO in
        ubuntu|debian)
            apt-get install -y nginx
            ;;
        rhel|centos|rocky|almalinux)
            yum install -y nginx
            ;;
    esac

    systemctl enable nginx
    log_success "nginx installed"
}

# Install Caddy
install_caddy() {
    if command -v caddy &> /dev/null; then
        log_info "Caddy already installed"
        return
    fi

    log_info "Installing Caddy..."

    case $DISTRO in
        ubuntu|debian)
            apt install -y debian-keyring debian-archive-keyring apt-transport-https
            curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
            curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
            apt update
            apt install -y caddy
            ;;
        rhel|centos|rocky|almalinux)
            yum install -y yum-plugin-copr
            yum copr enable @caddy/caddy -y
            yum install -y caddy
            ;;
    esac

    systemctl enable caddy
    log_success "Caddy installed"
}

# Install Certbot for Let's Encrypt
install_certbot() {
    if [[ "$SKIP_CERTBOT" = true ]]; then
        log_warning "Skipping Certbot installation"
        return
    fi

    if command -v certbot &> /dev/null; then
        log_info "Certbot already installed"
        return
    fi

    log_info "Installing Certbot..."

    case $DISTRO in
        ubuntu|debian)
            if [[ "$PROXY" = "nginx" ]]; then
                apt-get install -y certbot python3-certbot-nginx
            else
                apt-get install -y certbot
            fi
            ;;
        rhel|centos|rocky|almalinux)
            yum install -y certbot
            if [[ "$PROXY" = "nginx" ]]; then
                yum install -y python3-certbot-nginx
            fi
            ;;
    esac

    log_success "Certbot installed"
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."

    case $DISTRO in
        ubuntu|debian)
            # UFW
            ufw --force enable
            ufw allow ssh
            ufw allow http
            ufw allow https
            ufw status verbose
            ;;
        rhel|centos|rocky|almalinux)
            # firewalld
            systemctl enable firewalld
            systemctl start firewalld
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --permanent --add-service=ssh
            firewall-cmd --reload
            firewall-cmd --list-all
            ;;
    esac

    log_success "Firewall configured"
}

# Generate SSL certificate with Let's Encrypt
generate_ssl_cert() {
    if [[ "$SKIP_CERTBOT" = true ]]; then
        log_warning "Skipping SSL certificate generation"
        return
    fi

    log_info "Generating SSL certificate for $DOMAIN..."

    if [[ "$PROXY" = "nginx" ]]; then
        certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos --email "$EMAIL"
    elif [[ "$PROXY" = "caddy" ]]; then
        log_info "Caddy will automatically obtain SSL certificate"
    else
        certbot certonly --standalone -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos --email "$EMAIL"
    fi

    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -

    log_success "SSL certificate generated"
}

# Configure nginx
configure_nginx() {
    log_info "Configuring nginx..."

    # Copy nginx configuration
    cp "$PROJECT_ROOT/configs/wan/nginx.conf" /etc/nginx/sites-available/giljo-mcp

    # Replace domain placeholder
    sed -i "s/yourdomain.com/$DOMAIN/g" /etc/nginx/sites-available/giljo-mcp

    # Enable site
    ln -sf /etc/nginx/sites-available/giljo-mcp /etc/nginx/sites-enabled/

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default

    # Generate DH parameters
    if [[ ! -f /etc/ssl/certs/dhparam.pem ]]; then
        log_info "Generating DH parameters (this may take a while)..."
        openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
    fi

    # Test configuration
    nginx -t

    # Restart nginx
    systemctl restart nginx

    log_success "nginx configured"
}

# Configure Caddy
configure_caddy() {
    log_info "Configuring Caddy..."

    # Copy Caddy configuration
    cp "$PROJECT_ROOT/configs/wan/Caddyfile" /etc/caddy/Caddyfile

    # Replace domain and email placeholders
    sed -i "s/yourdomain.com/$DOMAIN/g" /etc/caddy/Caddyfile
    sed -i "s/admin@yourdomain.com/$EMAIL/g" /etc/caddy/Caddyfile

    # Test configuration
    caddy validate --config /etc/caddy/Caddyfile

    # Restart Caddy
    systemctl restart caddy

    log_success "Caddy configured"
}

# Deploy with Docker
deploy_docker() {
    log_info "Deploying with Docker..."

    cd "$PROJECT_ROOT"

    # Create .env file
    if [[ ! -f .env ]]; then
        log_info "Creating .env file..."
        cat > .env << EOF
# Generated by deploy_wan_linux.sh
DB_NAME=giljo_mcp
DB_USER=giljo_user
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)
API_KEY=gai_$(openssl rand -hex 16)
DOMAIN=$DOMAIN
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)
LOG_LEVEL=INFO
WORKERS=4
EOF
        chmod 600 .env
    fi

    # Build and start containers
    if [[ "$ENABLE_MONITORING" = true ]]; then
        docker compose -f docker-compose.wan.yml --profile monitoring up -d --build
    else
        docker compose -f docker-compose.wan.yml up -d --build
    fi

    log_success "Docker deployment complete"
}

# Deploy natively (without Docker)
deploy_native() {
    log_info "Deploying natively..."

    cd "$PROJECT_ROOT"

    # Create Python virtual environment
    if [[ ! -d venv ]]; then
        python3 -m venv venv
    fi

    # Activate venv and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    # Create systemd service
    cat > /etc/systemd/system/giljo-mcp.service << EOF
[Unit]
Description=GiljoAI MCP API Service
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$PROJECT_ROOT/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$PROJECT_ROOT/venv/bin/gunicorn api.app:app \\
    --bind 127.0.0.1:7272 \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --access-logfile /var/log/giljo_mcp/access.log \\
    --error-logfile /var/log/giljo_mcp/error.log \\
    --log-level info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

    # Create log directory
    mkdir -p /var/log/giljo_mcp
    chown www-data:www-data /var/log/giljo_mcp

    # Reload systemd and start service
    systemctl daemon-reload
    systemctl enable giljo-mcp
    systemctl start giljo-mcp

    log_success "Native deployment complete"
}

# Configure fail2ban
configure_fail2ban() {
    log_info "Configuring fail2ban..."

    cat > /etc/fail2ban/jail.d/giljo-mcp.conf << EOF
[giljo-api]
enabled = true
port = http,https
filter = giljo-api
logpath = /var/log/nginx/giljo_error.log
maxretry = 5
findtime = 600
bantime = 3600
EOF

    cat > /etc/fail2ban/filter.d/giljo-api.conf << EOF
[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD).*" (401|403|404) .*$
ignoreregex =
EOF

    systemctl restart fail2ban

    log_success "fail2ban configured"
}

# Main deployment flow
main() {
    log_info "Starting GiljoAI MCP WAN deployment for $DOMAIN"

    detect_distro
    install_dependencies

    if [[ "$USE_DOCKER" = true ]]; then
        install_docker
        deploy_docker
    else
        deploy_native
    fi

    # Install and configure reverse proxy
    if [[ "$PROXY" = "nginx" ]]; then
        install_nginx
        install_certbot
        generate_ssl_cert
        configure_nginx
    elif [[ "$PROXY" = "caddy" ]]; then
        install_caddy
        configure_caddy
    fi

    configure_firewall
    configure_fail2ban

    log_success "================================"
    log_success "Deployment Complete!"
    log_success "================================"
    log_info ""
    log_info "Access your deployment at:"
    log_info "  - https://$DOMAIN"
    log_info "  - https://www.$DOMAIN"
    log_info ""

    if [[ "$ENABLE_MONITORING" = true ]]; then
        log_info "Monitoring dashboards:"
        log_info "  - Grafana: https://$DOMAIN:3000"
        log_info "  - Prometheus: https://$DOMAIN:9090"
        log_info ""
    fi

    log_info "Next steps:"
    log_info "  1. Review configuration files"
    log_info "  2. Update DNS records to point to this server"
    log_info "  3. Complete security checklist: docs/deployment/WAN_SECURITY_CHECKLIST.md"
    log_info "  4. Test all endpoints and WebSocket connections"
    log_info "  5. Set up monitoring alerts"
    log_info ""
    log_warning "IMPORTANT: Review and secure all credentials in .env file!"
}

# Run main deployment
main
