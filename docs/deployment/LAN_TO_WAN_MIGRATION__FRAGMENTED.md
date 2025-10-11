# GiljoAI MCP - LAN to WAN Migration Guide

## Overview

This guide walks you through upgrading your GiljoAI MCP deployment from LAN (local network) mode to WAN (internet-facing) mode safely and efficiently.

**Migration Time**: 2-4 hours (depending on experience)
**Downtime**: 30 minutes to 2 hours (can be reduced with parallel infrastructure)
**Difficulty**: Intermediate to Advanced

## Prerequisites

Before beginning migration:

- [ ] Working LAN deployment (fully tested)
- [ ] Domain name registered and DNS access
- [ ] SSL certificate obtained or Let's Encrypt access
- [ ] Reverse proxy knowledge (nginx/Caddy/IIS)
- [ ] Complete backup of current deployment
- [ ] Access to production server (if different from LAN server)
- [ ] This migration guide and WAN_DEPLOYMENT_GUIDE.md

## Migration Strategy Options

### Option A: In-Place Migration (Same Server)

**Best for**: Upgrading existing server to WAN access
**Downtime**: 30-60 minutes
**Risk**: Medium (modifying live system)

### Option B: Parallel Migration (New Server)

**Best for**: Production environments requiring zero downtime
**Downtime**: < 5 minutes (DNS cutover only)
**Risk**: Low (rollback available)
**Recommended for production**

### Option C: Hybrid (Staged Rollout)

**Best for**: Testing WAN before full cutover
**Downtime**: Minimal (gradual traffic shift)
**Risk**: Low

## Phase 1: Pre-Migration Assessment

### Step 1: Document Current State

```bash
# Capture current configuration
cd /path/to/giljo-mcp
cp config.yaml config.yaml.lan.backup
cp .env .env.lan.backup

# Document database state
psql -U giljo_user -d giljo_mcp -c "\dt" > database_tables.txt
psql -U giljo_user -d giljo_mcp -c "SELECT COUNT(*) FROM projects;" > project_count.txt

# Document service versions
python --version > versions.txt
psql --version >> versions.txt
redis-server --version >> versions.txt

# Save to migration folder
mkdir -p migration_$(date +%Y%m%d)
mv *.backup *.txt migration_$(date +%Y%m%d)/
```

### Step 2: Create Complete Backup

**Critical: Do not proceed without a verified backup.**

```bash
# Backup script (Linux)
./scripts/deployment/backup_lan.sh

# Verify backup
ls -lh backups/
# Ensure backup files exist and are recent
```

**Windows**:

```powershell
# Backup PostgreSQL
$BackupPath = "C:\Backups\giljo_mcp_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $BackupPath

$env:PGPASSWORD="your-password"
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U giljo_user -d giljo_mcp -F c -f "$BackupPath\database.backup"

# Backup configuration and data
Copy-Item config.yaml -Destination $BackupPath
Copy-Item .env -Destination $BackupPath
Copy-Item -Recurse data -Destination $BackupPath
Copy-Item -Recurse uploads -Destination $BackupPath
```

### Step 3: Test Backup Restoration

**Do this on a test system, not production**:

```bash
# Create test database
psql -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Restore backup
pg_restore -U postgres -d giljo_mcp_test /path/to/backup.sql

# Verify
psql -U postgres -d giljo_mcp_test -c "SELECT COUNT(*) FROM projects;"
```

### Step 4: Security Audit

Review current security:

- [ ] Are default passwords still in use?
- [ ] Are secrets committed to git?
- [ ] Is PostgreSQL accessible from outside?
- [ ] Are all dependencies up to date?

## Phase 2: WAN Infrastructure Preparation

### Step 1: Provision WAN Server (Parallel Migration)

If using a new server:

```bash
# Provision cloud server (example: AWS)
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key \
  --security-group-ids sg-xxxxx \
  --subnet-id subnet-xxxxx

# Or provision with DigitalOcean
doctl compute droplet create giljo-mcp-wan \
  --region nyc3 \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --ssh-keys your-ssh-key-id
```

### Step 2: Install WAN Dependencies

```bash
# On new WAN server
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y postgresql-14 redis-server nginx python3-pip python3-venv

# Secure SSH
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no, PermitRootLogin no
sudo systemctl restart sshd
```

### Step 3: Configure DNS

**Before going live**, set up DNS records:

```
A Record:
  yourdomain.com        ->  [WAN Server IP]

CNAME Records:
  www.yourdomain.com    ->  yourdomain.com
  api.yourdomain.com    ->  yourdomain.com (optional)
```

**Set low TTL initially** (300 seconds) for quick rollback.

### Step 4: Obtain SSL Certificate

**Option A: Let's Encrypt (Recommended)**

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (requires DNS to be pointed to server)
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com --email admin@yourdomain.com --agree-tos
```

**Option B: Commercial Certificate**

1. Generate CSR
2. Submit to CA
3. Download certificate
4. Install certificate files

## Phase 3: Data Migration

### Step 1: Export LAN Data

**On LAN server**:

```bash
# Stop application (to ensure data consistency)
sudo systemctl stop giljo-mcp

# Export database
pg_dump -U giljo_user -d giljo_mcp -F c -f giljo_mcp_export.backup

# Export uploads and data
tar -czf giljo_data.tar.gz data/ uploads/ docs/vision/

# Calculate checksums
sha256sum giljo_mcp_export.backup > checksums.txt
sha256sum giljo_data.tar.gz >> checksums.txt
```

### Step 2: Transfer to WAN Server

```bash
# Secure transfer
scp giljo_mcp_export.backup giljo_data.tar.gz checksums.txt user@wan-server:/tmp/

# On WAN server, verify checksums
ssh user@wan-server
cd /tmp
sha256sum -c checksums.txt
# All should report OK
```

### Step 3: Import Data on WAN Server

```bash
# On WAN server
# Create database
sudo -u postgres psql -c "CREATE USER giljo_user WITH PASSWORD 'new-strong-password';"
sudo -u postgres psql -c "CREATE DATABASE giljo_mcp OWNER giljo_user;"

# Restore backup
sudo -u postgres pg_restore -d giljo_mcp /tmp/giljo_mcp_export.backup

# Extract data files
cd /opt/giljo-mcp  # Or your installation directory
tar -xzf /tmp/giljo_data.tar.gz

# Set permissions
chown -R www-data:www-data data/ uploads/
```

## Phase 4: WAN Configuration

### Step 1: Update config.yaml for WAN

```yaml
installation:
  mode: server  # Changed from localhost
  environment: production

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp
  user: giljo_user
  ssl_mode: require  # NEW: Enforce SSL

services:
  api:
    host: 127.0.0.1  # Bind to localhost (reverse proxy handles external)
    port: 7272

features:
  ssl_enabled: true  # NEW
  api_keys_required: true  # NEW
  jwt_auth: true  # NEW
  rate_limiting: true  # NEW
  cors_enabled: true  # NEW
  cors_origins:
    - "https://yourdomain.com"
    - "https://www.yourdomain.com"

security:  # NEW section
  secret_key: "${SECRET_KEY}"
  jwt_algorithm: HS256
  jwt_expiry_hours: 24
  api_key_rotation_days: 90

rate_limiting:  # NEW section
  enabled: true
  backend: redis
  redis_url: "redis://localhost:6379/0"
  default_rate: "100/minute"
  auth_rate: "5/minute"

logging:
  level: INFO  # Changed from DEBUG
  format: json  # NEW: Structured logging
```

### Step 2: Update .env for WAN

```bash
# Create new .env with WAN settings
cat > .env << EOF
# Database
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=giljo_mcp
DB_USER=giljo_user
DB_PASSWORD=$(openssl rand -base64 32)

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (CRITICAL: Generate new secrets)
SECRET_KEY=$(openssl rand -hex 32)
API_KEY=gai_$(openssl rand -hex 16)

# Application
GILJO_MCP_MODE=wan
GILJO_MCP_ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

chmod 600 .env
```

### Step 3: Configure Reverse Proxy

**nginx**:

```bash
# Copy configuration
sudo cp configs/wan/nginx.conf /etc/nginx/sites-available/giljo-mcp

# Update domain
sudo sed -i "s/yourdomain.com/$(hostname -f)/g" /etc/nginx/sites-available/giljo-mcp

# Enable site
sudo ln -s /etc/nginx/sites-available/giljo-mcp /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

**Caddy** (automatic HTTPS):

```bash
# Copy Caddyfile
sudo cp configs/wan/Caddyfile /etc/caddy/Caddyfile

# Update domain and email
sudo sed -i "s/yourdomain.com/$(hostname -f)/g" /etc/caddy/Caddyfile
sudo sed -i "s/admin@yourdomain.com/your@email.com/g" /etc/caddy/Caddyfile

# Reload Caddy
sudo systemctl reload caddy
```

### Step 4: Configure PostgreSQL SSL

```bash
# Generate SSL certificates for PostgreSQL
sudo -u postgres openssl req -new -x509 -days 365 -nodes -text \
  -out /var/lib/postgresql/18/main/server.crt \
  -keyout /var/lib/postgresql/18/main/server.key \
  -subj "/CN=localhost"

sudo chmod 600 /var/lib/postgresql/18/main/server.key
sudo chown postgres:postgres /var/lib/postgresql/18/main/server.*

# Update postgresql.conf
sudo nano /etc/postgresql/18/main/postgresql.conf
# Add:
# ssl = on
# ssl_cert_file = '/var/lib/postgresql/18/main/server.crt'
# ssl_key_file = '/var/lib/postgresql/18/main/server.key'

# Update pg_hba.conf (require SSL)
sudo nano /etc/postgresql/18/main/pg_hba.conf
# Change:
# hostssl all all 0.0.0.0/0 scram-sha-256

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## Phase 5: Security Hardening

### Step 1: Configure Firewall

```bash
# UFW (Ubuntu/Debian)
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw status verbose
```

### Step 2: Install and Configure fail2ban

```bash
sudo apt install -y fail2ban

# Create jail for GiljoAI
sudo cat > /etc/fail2ban/jail.d/giljo-mcp.conf << EOF
[giljo-api]
enabled = true
port = http,https
filter = giljo-api
logpath = /var/log/nginx/giljo_error.log
maxretry = 5
findtime = 600
bantime = 3600
EOF

# Create filter
sudo cat > /etc/fail2ban/filter.d/giljo-api.conf << EOF
[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD).*" (401|403|404) .*$
ignoreregex =
EOF

sudo systemctl restart fail2ban
```

### Step 3: Rotate All Secrets

```bash
# Generate new secrets
export NEW_SECRET_KEY=$(openssl rand -hex 32)
export NEW_API_KEY=gai_$(openssl rand -hex 16)

# Update .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET_KEY/" .env
sed -i "s/API_KEY=.*/API_KEY=$NEW_API_KEY/" .env

# Update database passwords
sudo -u postgres psql -c "ALTER USER giljo_user WITH PASSWORD '$(openssl rand -base64 32)';"
```

## Phase 6: Testing

### Step 1: Local Testing

```bash
# Start services
sudo systemctl start giljo-mcp
sudo systemctl start nginx

# Test health endpoint
curl -k https://localhost/health
# Should return: {"status": "healthy"}

# Test API endpoint
curl -k https://localhost/api/projects -H "Authorization: Bearer $API_KEY"
```

### Step 2: External Testing

**Before updating DNS**, test with /etc/hosts:

```bash
# On test machine
echo "WAN_SERVER_IP  yourdomain.com" | sudo tee -a /etc/hosts

# Test from external machine
curl https://yourdomain.com/health
curl https://yourdomain.com/api/projects -H "Authorization: Bearer $API_KEY"
```

### Step 3: SSL/TLS Validation

```bash
# Test SSL configuration
testssl.sh https://yourdomain.com

# Or online: https://www.ssllabs.com/ssltest/
```

### Step 4: Load Testing

```bash
# Install Apache Bench
sudo apt install -y apache2-utils

# Basic load test
ab -n 1000 -c 10 https://yourdomain.com/health

# Expected: 0 failed requests
```

## Phase 7: Cutover

### Step 1: Final Data Sync

If LAN server was still running:

```bash
# On LAN server (stop accepting new data)
sudo systemctl stop giljo-mcp

# Export incremental changes
pg_dump -U giljo_user -d giljo_mcp -F c -f incremental.backup

# Transfer and merge on WAN server
# (Restore incremental backup)
```

### Step 2: Update DNS

```bash
# Update DNS A record to point to WAN server IP
# Use your DNS provider's interface or API

# Example with CloudFlare API:
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"content":"WAN_SERVER_IP"}'
```

### Step 3: Monitor DNS Propagation

```bash
# Check DNS propagation
watch -n 5 dig +short yourdomain.com

# Should show new WAN server IP after TTL expires
```

### Step 4: Verify Production Access

```bash
# Test from multiple locations
curl https://yourdomain.com/health

# Check SSL
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

## Phase 8: Post-Migration

### Step 1: Monitor Everything

```bash
# Monitor logs
tail -f /var/log/nginx/giljo_access.log
tail -f /var/log/giljo_mcp/app.log

# Monitor system resources
htop

# Monitor database
psql -U giljo_user -d giljo_mcp -c "SELECT COUNT(*) FROM pg_stat_activity;"
```

### Step 2: Enable Monitoring (if not already)

```bash
# Start monitoring stack
docker compose -f docker-compose.wan.yml --profile monitoring up -d

# Access Grafana
https://yourdomain.com:3000
# Default: admin / (password from .env)
```

### Step 3: Complete Security Checklist

Review and complete: `docs/deployment/WAN_SECURITY_CHECKLIST.md`

### Step 4: Document Changes

Create migration summary:

```markdown
# Migration Summary

**Date**: 2025-XX-XX
**Duration**: X hours
**Downtime**: X minutes

## Changes Made:
- Migrated from LAN (server1) to WAN (server2)
- SSL certificate: Let's Encrypt
- Reverse proxy: nginx
- Database: Migrated successfully
- All secrets rotated

## Issues Encountered:
- (None / List any issues)

## Rollback Plan:
- DNS TTL: 300s (can revert quickly)
- LAN server backup: /backups/pre-wan-migration/
- Database backup: /backups/pre-wan-migration/database.backup

## Next Steps:
- Monitor for 48 hours
- Increase DNS TTL to 3600s
- Decommission LAN server (after 7 days)
- Schedule security audit
```

## Rollback Procedure

If issues occur:

### Immediate Rollback (DNS)

```bash
# Revert DNS to LAN server IP
# Update DNS A record back to original IP

# DNS will propagate within TTL window (5 minutes if you used 300s)
```

### Full Rollback (Restore LAN)

```bash
# On LAN server
# Restore from pre-migration backup
pg_restore -U giljo_user -d giljo_mcp /backups/pre-wan-migration/database.backup

# Restore configuration
cp /backups/pre-wan-migration/config.yaml config.yaml
cp /backups/pre-wan-migration/.env .env

# Restart services
sudo systemctl start giljo-mcp
```

## Common Migration Issues

### Issue: SSL Certificate Not Working

**Symptom**: Browser shows "Your connection is not private"

**Solution**:
```bash
# Verify certificate files
sudo certbot certificates

# Renew if needed
sudo certbot renew

# Check nginx configuration
sudo nginx -t
```

### Issue: Database Connection Refused

**Symptom**: API cannot connect to PostgreSQL

**Solution**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify pg_hba.conf allows connections
sudo nano /etc/postgresql/18/main/pg_hba.conf

# Check .env has correct credentials
cat .env | grep DB_
```

### Issue: High Response Times

**Symptom**: API responds slowly after migration

**Solution**:
```bash
# Check database connection pool
psql -U giljo_user -d giljo_mcp -c "SELECT COUNT(*) FROM pg_stat_activity;"

# Increase workers in config
# Restart services
sudo systemctl restart giljo-mcp
```

## Success Criteria

Migration is successful when:

- [ ] All health checks pass
- [ ] SSL/TLS grade A or A+ (ssllabs.com)
- [ ] API response time < 500ms (p95)
- [ ] Zero errors in last hour
- [ ] All data migrated (verify counts)
- [ ] WebSocket connections working
- [ ] Authentication functioning
- [ ] No failed login attempts from legitimate users
- [ ] Monitoring dashboards operational
- [ ] Backup automation running

## Post-Migration Cleanup

After 7 days of stable WAN operation:

```bash
# On LAN server (decommission)
sudo systemctl stop giljo-mcp
sudo systemctl disable giljo-mcp

# Archive LAN backups
tar -czf lan_server_final_backup.tar.gz /opt/giljo-mcp/

# Transfer to secure storage
# Then decommission server
```

## Conclusion

Congratulations on migrating to WAN! Your deployment is now internet-accessible and production-ready.

**Next Steps**:
1. Monitor closely for 48 hours
2. Complete security audit
3. Set up automated backups
4. Configure alerting
5. Document operational procedures
6. Train team on incident response

**Resources**:
- WAN_DEPLOYMENT_GUIDE.md
- WAN_SECURITY_CHECKLIST.md
- WAN_ARCHITECTURE.md

For support: docs@giljoai.com
