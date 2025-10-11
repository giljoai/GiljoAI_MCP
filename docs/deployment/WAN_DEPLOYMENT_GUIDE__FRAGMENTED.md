# GiljoAI MCP - WAN Deployment Guide

## Overview

This guide covers deploying GiljoAI MCP for internet-facing (WAN) access. WAN deployment is designed for production SaaS, public APIs, remote teams, and enterprise environments requiring global accessibility.

**Warning**: WAN deployment exposes your system to the public internet. Follow all security guidelines meticulously.

### What is WAN Mode?

WAN (Wide Area Network) mode configures GiljoAI MCP for secure internet access:

- HTTPS/TLS encryption mandatory
- Advanced authentication (JWT + API keys)
- DDoS protection and rate limiting
- Security hardening and monitoring
- Scalable architecture for global access

### Use Cases

- SaaS offerings with multi-tenant access
- Remote development teams across geographies
- Public API services
- Enterprise deployments with WAN access
- Cloud-hosted development platforms

### Prerequisites

Before beginning WAN deployment:

- [ ] Working LAN deployment (test locally first)
- [ ] Domain name with DNS access
- [ ] SSL/TLS certificates (Let's Encrypt or commercial)
- [ ] Reverse proxy knowledge (nginx/Caddy/IIS)
- [ ] Firewall and network security experience
- [ ] Production server (cloud or dedicated)
- [ ] Budget for infrastructure costs

### Risk Assessment

WAN deployment introduces significant security risks:

- **High Risk**: Public exposure to attacks (DDoS, brute force, injection)
- **Medium Risk**: Certificate management, configuration errors
- **Low Risk**: Performance degradation, scaling issues

**Mitigation**: Follow this guide completely, implement all security measures, and perform regular audits.

## Architecture Overview

### WAN vs LAN Deployment

| Aspect | LAN Mode | WAN Mode |
|--------|----------|----------|
| Network | Local network only | Public internet |
| SSL/TLS | Optional | Mandatory |
| Authentication | API keys | JWT + API keys + OAuth (optional) |
| Firewall | Basic | Advanced (WAF) |
| Rate Limiting | None | Required |
| DDoS Protection | None | Required |
| Monitoring | Basic | Comprehensive |
| Reverse Proxy | Optional | Required |
| Cost | Minimal | Moderate to high |

### Component Stack

```
Internet
    ↓
CloudFlare / AWS WAF (DDoS protection)
    ↓
Load Balancer (optional)
    ↓
Nginx / Caddy / IIS (Reverse Proxy + SSL termination)
    ↓
GiljoAI MCP API (FastAPI + Uvicorn)
    ↓
PostgreSQL (SSL/TLS enabled)
    ↓
Redis (distributed state)
```

## Cross-Platform WAN Deployment

### Platform Support

GiljoAI MCP supports WAN deployment on:

- **Linux**: Ubuntu 20.04+, Debian 11+, RHEL 8+, CentOS 8+
- **Windows**: Windows Server 2019+, Windows 10/11 Pro
- **macOS**: macOS 12+ (less common for production)
- **Cloud**: AWS, Azure, GCP, DigitalOcean, Linode

### Platform Selection Guide

**Recommended for WAN**:
- **Linux** (Ubuntu/Debian): Best performance, cost-effective, extensive tooling
- **Cloud Platforms**: Managed services, auto-scaling, integrated security

**Use With Caution**:
- **Windows Server**: Higher licensing costs, less automation tooling
- **macOS**: Limited to development/testing, not production-grade

## Phase 1: Harden LAN Deployment for Internet

### Step 1: Review LAN Configuration

Before exposing to WAN, verify your LAN deployment:

```bash
# Check service status
python scripts/giltest.py --check-services

# Verify database connectivity
psql -U giljo_user -d giljo_mcp -c "SELECT version();"

# Test API endpoints
curl http://localhost:7272/health
curl http://localhost:7272/ready

# Review configuration
cat config.yaml
```

### Step 2: Security Hardening

**Update config.yaml for WAN**:

```yaml
installation:
  mode: server  # Enable server mode
  environment: production

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp
  user: giljo_user
  ssl_mode: require  # CRITICAL: Enforce SSL
  pool_size: 20  # Increase for WAN
  max_overflow: 40

services:
  api:
    host: 127.0.0.1  # Bind to localhost (reverse proxy handles external)
    port: 7272
    workers: 4  # Adjust based on CPU cores
  frontend:
    port: 7274

features:
  ssl_enabled: true  # MANDATORY for WAN
  api_keys_required: true
  jwt_auth: true
  rate_limiting: true
  cors_enabled: true
  cors_origins:
    - "https://yourdomain.com"
    - "https://app.yourdomain.com"

security:
  secret_key: "${SECRET_KEY}"  # Use strong random key
  jwt_algorithm: HS256
  jwt_expiry_hours: 24
  api_key_rotation_days: 90
  password_min_length: 12
  max_login_attempts: 5
  lockout_duration_minutes: 30

rate_limiting:
  enabled: true
  backend: redis
  redis_url: "redis://localhost:6379/0"
  default_rate: "100/minute"
  auth_rate: "5/minute"
  api_rate: "1000/hour"

logging:
  level: INFO  # Use INFO for production, not DEBUG
  format: json  # Structured logging for analysis
  file: /var/log/giljo_mcp/app.log
  max_size: 100MB
  backup_count: 30
```

**Generate secure secrets**:

```bash
# Generate SECRET_KEY (Linux/macOS)
openssl rand -hex 32

# Generate SECRET_KEY (Windows PowerShell)
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})

# Set in environment
export SECRET_KEY="your-generated-secret-key"
```

### Step 3: Database SSL Configuration

**PostgreSQL SSL Setup**:

```bash
# Generate SSL certificates for PostgreSQL
cd /var/lib/postgresql/18/main

# Self-signed (development/testing)
sudo openssl req -new -x509 -days 365 -nodes -text \
  -out server.crt -keyout server.key -subj "/CN=localhost"
sudo chmod 600 server.key
sudo chown postgres:postgres server.key server.crt

# Update pg_hba.conf
sudo nano /etc/postgresql/18/main/pg_hba.conf
```

**pg_hba.conf for WAN**:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Allow localhost connections without SSL
local   all             postgres                                peer

# Require SSL for network connections
hostssl all             giljo_user      127.0.0.1/32            scram-sha-256
hostssl all             giljo_user      ::1/128                 scram-sha-256
hostssl all             giljo_user      0.0.0.0/0               scram-sha-256 clientcert=0
```

**postgresql.conf SSL settings**:

```ini
ssl = on
ssl_cert_file = '/var/lib/postgresql/18/main/server.crt'
ssl_key_file = '/var/lib/postgresql/18/main/server.key'
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL'
ssl_prefer_server_ciphers = on
ssl_min_protocol_version = 'TLSv1.2'
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### Step 4: Install Redis for Distributed State

**Linux (Ubuntu/Debian)**:

```bash
sudo apt update
sudo apt install redis-server -y

# Configure Redis for production
sudo nano /etc/redis/redis.conf
```

**Redis configuration for WAN**:

```ini
# Bind to localhost only (accessed via API)
bind 127.0.0.1 ::1

# Enable persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass "your-strong-redis-password"
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_a8f5b329c4"

# Performance
maxmemory 256mb
maxmemory-policy allkeys-lru
```

Start Redis:

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

**Windows**:

Download Redis from https://github.com/tporadowski/redis/releases

```powershell
# Install as Windows service
redis-server --service-install redis.windows.conf

# Start service
redis-server --service-start
```

**Update .env with Redis**:

```env
REDIS_URL=redis://:your-strong-redis-password@localhost:6379/0
```

## Phase 2: SSL/TLS and Reverse Proxy

### SSL Certificate Options

#### Option 1: Let's Encrypt (Free, Automated)

**Recommended for production**. Automated renewal, trusted by browsers.

**Linux with Certbot**:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate (nginx)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

#### Option 2: Commercial Certificate

Purchase from CA (DigiCert, Sectigo, GlobalSign). Follow CA instructions for CSR generation and installation.

#### Option 3: Self-Signed (Development Only)

**Never use self-signed certificates in production WAN**.

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/giljo-selfsigned.key \
  -out /etc/ssl/certs/giljo-selfsigned.crt
```

### Reverse Proxy Setup

#### nginx (Linux - Recommended)

**Install nginx**:

```bash
sudo apt update
sudo apt install nginx -y
```

**Configuration**: `/etc/nginx/sites-available/giljo-mcp`

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
limit_conn_zone $binary_remote_addr zone=addr:10m;

# Upstream backend
upstream giljo_api {
    least_conn;
    server 127.0.0.1:7272 max_fails=3 fail_timeout=30s;
    # Add more backends for load balancing
    # server 127.0.0.1:7273 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/yourdomain.com/chain.pem;

    # SSL protocols and ciphers (Mozilla Modern config)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # SSL session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss://yourdomain.com; frame-ancestors 'none';" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Remove version disclosure
    server_tokens off;

    # Logging
    access_log /var/log/nginx/giljo_access.log combined;
    error_log /var/log/nginx/giljo_error.log warn;

    # File upload size
    client_max_body_size 100M;
    client_body_timeout 120s;

    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Root and index
    root /var/www/giljo-mcp;
    index index.html;

    # Frontend (Vue app)
    location / {
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API endpoints
    location /api/ {
        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn addr 10;

        proxy_pass http://giljo_api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # Disable buffering for SSE/WebSocket
        proxy_buffering off;
        proxy_cache off;

        # Timeouts for long-polling
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # WebSocket endpoint
    location /ws {
        limit_req zone=api_limit burst=10 nodelay;

        proxy_pass http://giljo_api/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Authentication endpoints (stricter rate limiting)
    location ~ ^/api/(auth|login|register) {
        limit_req zone=auth_limit burst=3 nodelay;

        proxy_pass http://giljo_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health checks (no rate limiting)
    location ~ ^/(health|ready) {
        access_log off;
        proxy_pass http://giljo_api;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~ \.(env|yaml|yml|ini|log|bak|sql)$ {
        deny all;
    }
}
```

**Enable and start nginx**:

```bash
# Test configuration
sudo nginx -t

# Create symlink
sudo ln -s /etc/nginx/sites-available/giljo-mcp /etc/nginx/sites-enabled/

# Reload nginx
sudo systemctl reload nginx

# Enable on boot
sudo systemctl enable nginx
```

#### Caddy (Linux/Windows - Automatic HTTPS)

**Simpler alternative with automatic HTTPS**.

**Install Caddy (Linux)**:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy -y
```

**Caddyfile** (`/etc/caddy/Caddyfile`):

```caddy
yourdomain.com www.yourdomain.com {
    # Automatic HTTPS via Let's Encrypt

    # Security headers
    header {
        Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "no-referrer-when-downgrade"
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' wss://yourdomain.com"
        -Server
    }

    # Logging
    log {
        output file /var/log/caddy/giljo.log
        format json
        level INFO
    }

    # Rate limiting (requires caddy-ratelimit plugin)
    rate_limit {
        zone api {
            key {remote_host}
            events 100
            window 1m
        }
        zone auth {
            key {remote_host}
            events 5
            window 1m
        }
    }

    # Frontend (Vue app)
    root * /var/www/giljo-mcp
    encode gzip
    file_server

    # API endpoints
    handle /api/* {
        rate_limit api
        reverse_proxy localhost:7272 {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
        }
    }

    # WebSocket
    handle /ws {
        rate_limit api
        reverse_proxy localhost:7272 {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
        }
    }

    # Auth endpoints
    handle_path /api/auth/* {
        rate_limit auth
        reverse_proxy localhost:7272
    }

    # Health checks
    handle /health {
        reverse_proxy localhost:7272
    }

    handle /ready {
        reverse_proxy localhost:7272
    }

    # SPA fallback
    try_files {path} /index.html
}
```

**Start Caddy**:

```bash
sudo systemctl enable caddy
sudo systemctl start caddy
```

#### IIS (Windows Server)

**Prerequisites**:
- Windows Server 2019+
- IIS with Application Request Routing (ARR)
- URL Rewrite module

**Install ARR**:

1. Download Web Platform Installer
2. Install "Application Request Routing 3.0"
3. Install "URL Rewrite 2.1"

**Configure ARR Proxy**:

1. Open IIS Manager
2. Select server node → Application Request Routing Cache → Server Proxy Settings
3. Enable proxy, set timeout to 3600 seconds
4. Apply changes

**web.config** (place in wwwroot):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <!-- URL Rewrite rules -->
        <rewrite>
            <rules>
                <!-- Redirect HTTP to HTTPS -->
                <rule name="HTTP to HTTPS" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{HTTPS}" pattern="off" />
                    </conditions>
                    <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
                </rule>

                <!-- API endpoints -->
                <rule name="API Proxy" stopProcessing="true">
                    <match url="^api/(.*)" />
                    <action type="Rewrite" url="http://localhost:7272/{R:1}" />
                </rule>

                <!-- WebSocket -->
                <rule name="WebSocket Proxy" stopProcessing="true">
                    <match url="^ws$" />
                    <action type="Rewrite" url="http://localhost:7272/ws" />
                </rule>

                <!-- SPA fallback -->
                <rule name="SPA Fallback" stopProcessing="true">
                    <match url=".*" />
                    <conditions logicalGrouping="MatchAll">
                        <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
                        <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
                    </conditions>
                    <action type="Rewrite" url="/" />
                </rule>
            </rules>
        </rewrite>

        <!-- Security headers -->
        <httpProtocol>
            <customHeaders>
                <add name="Strict-Transport-Security" value="max-age=63072000; includeSubDomains; preload" />
                <add name="X-Frame-Options" value="DENY" />
                <add name="X-Content-Type-Options" value="nosniff" />
                <add name="X-XSS-Protection" value="1; mode=block" />
                <remove name="X-Powered-By" />
            </customHeaders>
        </httpProtocol>

        <!-- Request filtering -->
        <security>
            <requestFiltering>
                <fileExtensions>
                    <add fileExtension=".env" allowed="false" />
                    <add fileExtension=".yaml" allowed="false" />
                    <add fileExtension=".log" allowed="false" />
                </fileExtensions>
            </requestFiltering>
        </security>
    </system.webServer>
</configuration>
```

**SSL Certificate Binding**:

```powershell
# Import certificate
Import-PfxCertificate -FilePath "C:\certs\certificate.pfx" -CertStoreLocation Cert:\LocalMachine\My -Password (ConvertTo-SecureString -String "password" -AsPlainText -Force)

# Bind to site
New-WebBinding -Name "GiljoAI MCP" -Protocol https -Port 443
$cert = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object {$_.Subject -like "*yourdomain.com*"}
$binding = Get-WebBinding -Name "GiljoAI MCP" -Protocol https
$binding.AddSslCertificate($cert.Thumbprint, "My")
```

## Phase 3: Advanced Security

### Web Application Firewall (WAF)

#### CloudFlare (Recommended)

**Benefits**: DDoS protection, CDN, free SSL, easy setup.

1. Sign up at https://www.cloudflare.com
2. Add your domain
3. Update nameservers at registrar
4. Configure SSL/TLS: Full (strict)
5. Enable security features:
   - DDoS protection (automatic)
   - Rate limiting (paid plan)
   - Bot Fight Mode
   - Firewall rules

**Firewall Rules** (CloudFlare Dashboard):

```
# Block common attack patterns
(http.request.uri.path contains "/admin" and not ip.src in {YOUR_ADMIN_IPS})
(http.request.uri.path contains "wp-admin")
(http.request.uri.path contains "phpmyadmin")

# Rate limit API
(http.request.uri.path contains "/api/" and rate(1m) > 100)

# Challenge suspicious User-Agents
(http.user_agent contains "bot" and not cf.client.bot)
```

#### AWS WAF

**For AWS deployments**:

```bash
# Create Web ACL
aws wafv2 create-web-acl \
  --name giljo-mcp-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json
```

**waf-rules.json**:

```json
[
  {
    "Name": "RateLimitRule",
    "Priority": 1,
    "Statement": {
      "RateBasedStatement": {
        "Limit": 2000,
        "AggregateKeyType": "IP"
      }
    },
    "Action": {
      "Block": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "RateLimitRule"
    }
  },
  {
    "Name": "SQLInjectionRule",
    "Priority": 2,
    "Statement": {
      "ManagedRuleGroupStatement": {
        "VendorName": "AWS",
        "Name": "AWSManagedRulesSQLiRuleSet"
      }
    },
    "OverrideAction": {
      "None": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "SQLInjectionRule"
    }
  }
]
```

### Fail2Ban (Linux)

**Install and configure**:

```bash
sudo apt install fail2ban -y

# Create custom jail
sudo nano /etc/fail2ban/jail.d/giljo-mcp.conf
```

**giljo-mcp.conf**:

```ini
[giljo-api]
enabled = true
port = https,http
filter = giljo-api
logpath = /var/log/nginx/giljo_error.log
maxretry = 5
findtime = 600
bantime = 3600
action = iptables-multiport[name=giljo-api, port="http,https", protocol=tcp]

[giljo-auth]
enabled = true
port = https,http
filter = giljo-auth
logpath = /var/log/giljo_mcp/app.log
maxretry = 3
findtime = 300
bantime = 7200
action = iptables-multiport[name=giljo-auth, port="http,https", protocol=tcp]
```

**Filter** (`/etc/fail2ban/filter.d/giljo-api.conf`):

```ini
[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD).*" (401|403|404) .*$
ignoreregex =
```

Start Fail2Ban:

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Phase 4: Monitoring and Observability

### Prometheus + Grafana

**Deploy with Docker** (see `docker-compose.wan.yml`).

**Prometheus targets** (`docker/prometheus.yml`):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'giljo-api'
    static_configs:
      - targets: ['backend:7272']
    metrics_path: '/metrics'

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Log Aggregation

**Loki + Promtail** (lightweight alternative to ELK):

**docker-compose addition**:

```yaml
loki:
  image: grafana/loki:latest
  ports:
    - "3100:3100"
  volumes:
    - ./docker/loki-config.yaml:/etc/loki/local-config.yaml
    - loki_data:/loki

promtail:
  image: grafana/promtail:latest
  volumes:
    - ./logs:/var/log/giljo
    - /var/log/nginx:/var/log/nginx
    - ./docker/promtail-config.yaml:/etc/promtail/config.yml
  command: -config.file=/etc/promtail/config.yml
```

## Phase 5: Backup and Disaster Recovery

### Automated Backups

**Backup script** (`scripts/deployment/backup_wan.sh`):

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups/giljo-mcp"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="s3://your-backup-bucket/giljo-mcp"

# Create backup directory
mkdir -p "$BACKUP_DIR/$TIMESTAMP"

# Backup PostgreSQL
PGPASSWORD="$DB_PASSWORD" pg_dump -U giljo_user -h localhost giljo_mcp | \
  gzip > "$BACKUP_DIR/$TIMESTAMP/database.sql.gz"

# Backup configuration
cp config.yaml "$BACKUP_DIR/$TIMESTAMP/"
cp .env "$BACKUP_DIR/$TIMESTAMP/env.bak"

# Backup uploads/data
tar -czf "$BACKUP_DIR/$TIMESTAMP/data.tar.gz" ./data ./uploads

# Upload to S3 (optional)
if command -v aws &> /dev/null; then
  aws s3 sync "$BACKUP_DIR/$TIMESTAMP" "$S3_BUCKET/$TIMESTAMP/"
fi

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR/$TIMESTAMP"
```

**Cron job** (daily at 2 AM):

```bash
crontab -e
```

```
0 2 * * * /opt/giljo-mcp/scripts/deployment/backup_wan.sh >> /var/log/giljo_backup.log 2>&1
```

### Disaster Recovery Plan

**Recovery Time Objective (RTO)**: < 4 hours
**Recovery Point Objective (RPO)**: < 24 hours

**Recovery Steps**:

1. Provision new server (same specs)
2. Install dependencies (PostgreSQL, Redis, nginx)
3. Restore latest backup from S3
4. Restore database: `gunzip -c database.sql.gz | psql -U giljo_user giljo_mcp`
5. Deploy application code
6. Update DNS records
7. Verify all services operational

## Platform-Specific Configurations

### AWS Deployment

**Use AWS services for managed infrastructure**:

- **EC2**: t3.medium or larger
- **RDS PostgreSQL**: db.t3.medium with Multi-AZ
- **ElastiCache Redis**: cache.t3.micro
- **Application Load Balancer**: For SSL termination and HA
- **CloudFront**: CDN for frontend assets
- **Route 53**: DNS management
- **S3**: Backups and static assets
- **CloudWatch**: Monitoring and logs

**Architecture**:

```
Route 53 (DNS)
    ↓
CloudFront (CDN)
    ↓
Application Load Balancer (SSL termination)
    ↓
EC2 Auto Scaling Group (2+ instances)
    ↓
RDS PostgreSQL (Multi-AZ) + ElastiCache Redis
```

**Deployment script** (`scripts/deployment/deploy_aws.sh`):

```bash
#!/bin/bash
# AWS deployment automation
# Prerequisites: AWS CLI configured, appropriate IAM permissions

# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file aws-infrastructure.yaml \
  --stack-name giljo-mcp-production \
  --parameter-overrides \
    Environment=production \
    InstanceType=t3.medium \
    DBInstanceClass=db.t3.medium \
  --capabilities CAPABILITY_IAM

# Deploy application
aws deploy create-deployment \
  --application-name giljo-mcp \
  --deployment-group-name production \
  --s3-location bucket=giljo-mcp-deploys,key=app-latest.zip,bundleType=zip
```

### Azure Deployment

**Azure services**:

- **App Service**: Linux Web App (B2 or higher)
- **Azure Database for PostgreSQL**: Flexible Server
- **Azure Cache for Redis**: Standard tier
- **Application Gateway**: SSL termination and WAF
- **Azure CDN**: Frontend assets
- **Azure Monitor**: Logging and metrics

### Google Cloud Platform

**GCP services**:

- **Compute Engine**: e2-medium or n2-standard-2
- **Cloud SQL for PostgreSQL**: db-custom-2-7680
- **Memorystore for Redis**: Standard tier
- **Cloud Load Balancing**: HTTPS load balancer
- **Cloud CDN**: Frontend assets
- **Cloud Logging**: Centralized logs

### DigitalOcean (Cost-Effective)

**Recommended droplet**: $24/mo (2 vCPU, 4GB RAM)

```bash
# Deploy with doctl
doctl apps create --spec digitalocean-app.yaml

# Database cluster
doctl databases create giljo-postgres --engine pg --version 16 --region nyc3 --size db-s-2vcpu-4gb
```

## WAN Testing Strategy

### Pre-Deployment Testing

**Security Scan**:

```bash
# OWASP ZAP automated scan
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://yourdomain.com

# Nikto web scanner
nikto -h https://yourdomain.com
```

**SSL/TLS Validation**:

```bash
# Test SSL configuration
testssl.sh https://yourdomain.com

# Online: https://www.ssllabs.com/ssltest/
```

**Load Testing**:

```bash
# Apache Bench
ab -n 10000 -c 100 https://yourdomain.com/api/health

# wrk
wrk -t12 -c400 -d30s https://yourdomain.com/api/projects

# Locust (Python)
locust -f tests/load/wan_load_test.py --host=https://yourdomain.com
```

**Penetration Testing**:

Hire professional penetration testers before going live. Recommended services:

- Bugcrowd
- HackerOne
- Synack

### Post-Deployment Monitoring

**Synthetic Monitoring**:

```bash
# Uptime monitoring (every 5 minutes)
curl -fsS https://yourdomain.com/health || alert_admin

# Use commercial services:
# - UptimeRobot (free tier available)
# - Pingdom
# - StatusCake
```

**Real User Monitoring (RUM)**:

Integrate Sentry or Datadog for frontend error tracking.

## Troubleshooting

### SSL Certificate Issues

**Problem**: Certificate expired

```bash
# Check expiry
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# Renew Let's Encrypt
sudo certbot renew
sudo systemctl reload nginx
```

**Problem**: Mixed content warnings

Ensure all assets loaded via HTTPS. Update `Content-Security-Policy` header.

### Performance Bottlenecks

**Diagnose with**:

```bash
# nginx status
curl http://localhost/nginx_status

# PostgreSQL slow queries
sudo -u postgres psql -d giljo_mcp -c "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Redis stats
redis-cli INFO stats
```

**Optimize**:

- Enable PostgreSQL query caching
- Increase Redis memory
- Add application-level caching
- Use CDN for static assets
- Enable HTTP/2 and compression

### Security Alerts

**Incident Response Plan**:

1. **Detect**: Monitor logs, SIEM alerts, WAF notifications
2. **Contain**: Block malicious IPs via firewall/WAF
3. **Investigate**: Analyze logs, check for data breaches
4. **Remediate**: Patch vulnerabilities, rotate secrets
5. **Document**: Write post-mortem, update security policies

**Rotate compromised secrets**:

```bash
# Generate new SECRET_KEY
export NEW_SECRET_KEY=$(openssl rand -hex 32)

# Update config.yaml and .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET_KEY/" .env

# Restart services
sudo systemctl restart giljo-api
```

## Production Operations Checklist

- [ ] SSL/TLS enforced with HSTS
- [ ] Reverse proxy configured and tested
- [ ] WAF enabled (CloudFlare/AWS WAF)
- [ ] Rate limiting active
- [ ] DDoS protection verified
- [ ] Database SSL/TLS enabled
- [ ] Redis password protected
- [ ] Secrets stored securely (not in git)
- [ ] Monitoring dashboards operational
- [ ] Log aggregation configured
- [ ] Backup automation tested
- [ ] Disaster recovery plan documented
- [ ] Incident response plan in place
- [ ] Security audit completed
- [ ] Performance testing passed
- [ ] DNS records configured
- [ ] Firewall rules applied
- [ ] Fail2Ban active (Linux)
- [ ] OS and dependencies updated
- [ ] GDPR/compliance requirements met

## Cost Considerations

### Infrastructure Costs (Monthly Estimates)

**Small Deployment** (< 1000 users):
- VPS/Cloud: $20-50 (DigitalOcean Droplet, AWS t3.medium)
- PostgreSQL: $15-30 (Managed database)
- Redis: $10-20 (Managed cache)
- CDN: $0-10 (CloudFlare free or AWS CloudFront)
- SSL: $0 (Let's Encrypt)
- **Total**: ~$45-110/month

**Medium Deployment** (1000-10,000 users):
- Compute: $100-300 (Multiple instances, load balancer)
- PostgreSQL: $100-200 (Larger instance, backups)
- Redis: $30-50 (Increased capacity)
- CDN: $20-50
- Monitoring: $20-50 (Datadog/New Relic)
- **Total**: ~$270-650/month

**Large Deployment** (10,000+ users):
- Compute: $500-2000 (Auto-scaling, multi-region)
- PostgreSQL: $300-1000 (High availability, read replicas)
- Redis: $100-300 (Cluster mode)
- CDN: $100-500
- Monitoring: $100-300
- WAF: $20-200 (CloudFlare Pro/Business)
- **Total**: ~$1,120-4,300/month

## Compliance Considerations

### GDPR (EU)

- Implement data retention policies
- Provide user data export (GDPR Article 20)
- Enable account deletion
- Log data processing activities
- Use EU data centers for EU users

### SOC 2

- Enable comprehensive audit logging
- Implement access controls
- Encrypt data at rest and in transit
- Regular security assessments
- Incident response procedures

### HIPAA (Healthcare)

- Use HIPAA-compliant hosting (AWS/Azure HIPAA-eligible services)
- Encrypt all PHI (Protected Health Information)
- Business Associate Agreements (BAAs) with vendors
- Enhanced access controls and audit logs

## Next Steps

1. Review LAN_TO_WAN_MIGRATION.md for upgrade path
2. Complete WAN_SECURITY_CHECKLIST.md
3. Study WAN_ARCHITECTURE.md for system design
4. Deploy to staging environment first
5. Conduct security audit and penetration testing
6. Perform load testing
7. Configure monitoring and alerting
8. Document runbooks for operations team
9. Train team on incident response
10. Go live with gradual traffic rollout

## Getting Help

- **Documentation**: https://docs.giljoai.com
- **Community**: https://community.giljoai.com
- **Enterprise Support**: support@giljoai.com
- **Security Issues**: security@giljoai.com (responsible disclosure)

---

**Remember**: WAN deployment is complex and high-risk. Take time to implement all security measures. When in doubt, consult security professionals.
