# Production Deployment Guide - GiljoAI MCP v3.0.0

**Version**: 3.0.0
**Last Updated**: 2025-10-09
**Estimated Time**: 30-60 minutes

---

## Overview

This guide walks through deploying GiljoAI MCP v3.0.0 to production, including pre-deployment checks, migration from v2.x, configuration, testing, and rollback procedures.

**Key Changes in v3.0**:
- Unified network binding (always 0.0.0.0)
- Firewall-based access control
- Auto-login for localhost clients
- Simplified configuration structure

---

## Pre-Deployment Checklist

### System Requirements

**Hardware**:
- CPU: 2+ cores recommended
- RAM: 4GB minimum, 8GB recommended
- Storage: 10GB free space
- Network: Stable connection

**Software**:
- Python 3.10+ installed
- PostgreSQL 18 installed and running
- Git installed
- Node.js 20+ and npm 8+ (for frontend build)

### Backup Current System

**CRITICAL**: Always backup before deployment!

```bash
# 1. Backup database
pg_dump -U postgres giljo_mcp > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Backup configuration
cp config.yaml config.yaml.backup
cp .env .env.backup

# 3. Backup data directory
tar -czf data_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/

# 4. Note current version
python -c "import giljo_mcp; print(giljo_mcp.__version__)"
```

### Network Planning

Decide your access pattern:
- **Localhost only**: No firewall changes needed
- **LAN access**: Configure firewall for subnet
- **Internet access**: Setup reverse proxy + TLS

See `docs/guides/FIREWALL_CONFIGURATION.md` for detailed instructions.

---

## Deployment Steps

### Step 1: Stop Current Services

```bash
# Stop all services
python stop_giljo.py

# Verify stopped
ps aux | grep giljo
netstat -tlnp | grep -E "7272|7274"
```

### Step 2: Get v3.0.0 Code

```bash
# Fetch latest code
git fetch origin
git fetch --tags

# Checkout v3.0.0
git checkout v3.0.0

# Verify version
git describe --tags
```

### Step 3: Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
npm run build
cd ..
```

### Step 4: Migrate Configuration

#### Automatic Migration

```bash
python installer/cli/install.py --migrate-config
```

This will:
- Detect existing v2.x config
- Convert to v3.0 format
- Backup old configuration
- Generate new config.yaml

#### Manual Migration

If automatic migration fails, manually update config.yaml:

**Before (v2.x)**:
```yaml
installation:
  mode: localhost  # or 'server'

services:
  api:
    host: 127.0.0.1  # or 0.0.0.0
    port: 7272

security:
  require_auth_for_modes:
    - server
```

**After (v3.0)**:
```yaml
services:
  api:
    host: 0.0.0.0  # Always 0.0.0.0
    port: 7272
  frontend:
    port: 7274

security:
  cors:
    allowed_origins:
      - http://localhost:7274
      - http://127.0.0.1:7274
```

### Step 5: Database Migration

#### Check Current Schema

```bash
# Connect to database
psql -U postgres -d giljo_mcp

# Check for v3.0 columns
\d users
```

Look for `is_system_user` column. If missing, run migrations:

```bash
# Run Alembic migrations
alembic upgrade head

# Verify
psql -U postgres -d giljo_mcp -c "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_system_user';"
```

#### Create Localhost User

v3.0 requires a localhost user for auto-login:

```python
# Python script to ensure localhost user
python -c "
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.auth.localhost_user import ensure_localhost_user
import asyncio

async def create_user():
    db = DatabaseManager('postgresql://postgres:password@localhost/giljo_mcp')
    async with db.get_session_async() as session:
        await ensure_localhost_user(session)
    await db.close_async()

asyncio.run(create_user())
"
```

### Step 6: Configure Firewall

Based on your chosen access pattern:

#### Localhost Only

No firewall changes needed - default blocks external access.

#### LAN Access

```bash
# Linux with UFW
sudo ufw allow from 192.168.1.0/24 to any port 7272
sudo ufw allow from 192.168.1.0/24 to any port 7274

# Windows PowerShell (as Admin)
New-NetFirewallRule -DisplayName "GiljoAI MCP" `
  -Direction Inbound -Protocol TCP -LocalPort 7272,7274 `
  -Action Allow -RemoteAddress 192.168.1.0/24
```

#### Internet Access

Setup reverse proxy with TLS (nginx example):

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;

    location / {
        proxy_pass http://localhost:7272;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Step 7: Start Services

```bash
# Start all services
python start_giljo.py

# Or start individually
python api/run_api.py &
cd frontend && npm run serve &
```

### Step 8: Verify Deployment

#### Health Check

```bash
# API health
curl http://localhost:7272/health

# Expected response
{"status": "healthy", "checks": {"api": "healthy", "database": "healthy"}}
```

#### Dashboard Access

Open browser:
- Localhost: http://localhost:7274
- LAN: http://<server-ip>:7274
- Internet: https://yourdomain.com

#### Test Authentication

**Localhost (Auto-login)**:
```bash
curl http://localhost:7272/api/v1/projects
# Should return projects without authentication
```

**Network (Requires API key)**:
```bash
curl -H "X-API-Key: your-api-key" http://<server-ip>:7272/api/v1/projects
```

### Step 9: Smoke Tests

Run basic smoke tests:

```bash
# Run smoke test suite
pytest tests/smoke/ -v

# Or manual tests
python scripts/smoke_test.py
```

Manual test checklist:
- [ ] Create a project
- [ ] Spawn an agent
- [ ] Send a message between agents
- [ ] View dashboard real-time updates
- [ ] Generate MCP installer script
- [ ] Download installer via share link

---

## Post-Deployment

### Monitor Logs

```bash
# API logs
tail -f logs/api.log

# Error logs
tail -f logs/error.log

# Access logs
tail -f logs/access.log
```

### Performance Monitoring

```bash
# Check resource usage
htop  # or top

# Check connections
netstat -an | grep -E "7272|7274" | wc -l

# Database connections
psql -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE datname='giljo_mcp';"
```

### Security Hardening

1. **Change default passwords**:
```sql
ALTER USER postgres PASSWORD 'new_secure_password';
ALTER USER giljo_user PASSWORD 'new_secure_password';
```

2. **Rotate API keys**:
```bash
python scripts/rotate_api_keys.py
```

3. **Enable audit logging**:
```yaml
# config.yaml
logging:
  audit:
    enabled: true
    file: logs/audit.log
```

4. **Configure rate limiting**:
```yaml
# config.yaml
security:
  rate_limiting:
    enabled: true
    requests_per_minute: 60
```

---

## Rollback Procedures

If deployment fails, follow these rollback steps:

### Quick Rollback (< 5 minutes)

```bash
# 1. Stop v3.0 services
python stop_giljo.py

# 2. Checkout previous version
git checkout v2.x.x

# 3. Restore configuration
cp config.yaml.backup config.yaml
cp .env.backup .env

# 4. Restart services
python start_giljo.py
```

### Full Rollback (with database)

```bash
# 1. Stop all services
python stop_giljo.py

# 2. Restore database
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"
psql -U postgres -c "CREATE DATABASE giljo_mcp;"
psql -U postgres giljo_mcp < backup_20251009_120000.sql

# 3. Restore code
git checkout v2.x.x

# 4. Restore configuration
cp config.yaml.backup config.yaml
cp .env.backup .env

# 5. Restore data directory
tar -xzf data_backup_20251009_120000.tar.gz

# 6. Install old dependencies
pip install -r requirements.txt

# 7. Start services
python start_giljo.py
```

---

## Troubleshooting

### Service Won't Start

**Check ports**:
```bash
netstat -tlnp | grep -E "7272|7274"
# Kill if occupied
kill -9 <PID>
```

**Check logs**:
```bash
tail -100 logs/error.log
```

**Check configuration**:
```bash
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### Database Connection Failed

**Verify PostgreSQL running**:
```bash
systemctl status postgresql
# or
pg_isready
```

**Test connection**:
```bash
psql -U postgres -d giljo_mcp -c "SELECT 1;"
```

**Check credentials**:
```bash
grep -E "DATABASE_URL|POSTGRES" .env
```

### Frontend Not Loading

**Check build**:
```bash
cd frontend
npm run build
ls -la dist/
```

**Check CORS**:
```yaml
# config.yaml
security:
  cors:
    allowed_origins:
      - http://localhost:7274
      - http://your-server-ip:7274
```

### Authentication Issues

**Localhost not auto-logging in**:
```bash
# Verify localhost user exists
psql -U postgres -d giljo_mcp -c "SELECT * FROM users WHERE username='localhost_user';"
```

**Network clients rejected**:
```bash
# Check API key configuration
grep API_KEY .env
```

---

## Production Best Practices

### High Availability

1. **Database replication**:
   - Setup PostgreSQL streaming replication
   - Use connection pooling (pgbouncer)

2. **Load balancing**:
   - Run multiple API instances
   - Use nginx/HAProxy for load balancing

3. **Session management**:
   - Use Redis for session storage
   - Enable sticky sessions for WebSocket

### Monitoring

1. **Application monitoring**:
   - Prometheus + Grafana
   - Application Performance Monitoring (APM)

2. **Log aggregation**:
   - ELK stack (Elasticsearch, Logstash, Kibana)
   - Splunk or similar

3. **Alerting**:
   - PagerDuty integration
   - Email/SMS alerts for critical issues

### Backup Strategy

1. **Database**:
   - Daily automated backups
   - Point-in-time recovery setup
   - Offsite backup storage

2. **Configuration**:
   - Version control for config files
   - Encrypted storage for sensitive data

3. **Testing**:
   - Regular restore tests
   - Documented restore procedures

### Security

1. **Network security**:
   - TLS/SSL for all connections
   - VPN for admin access
   - Regular security scans

2. **Access control**:
   - Principle of least privilege
   - Regular access audits
   - Multi-factor authentication

3. **Updates**:
   - Security patch schedule
   - Dependency vulnerability scanning
   - Regular penetration testing

---

## Deployment Automation

### Using Ansible

```yaml
# deploy-giljoai.yml
---
- name: Deploy GiljoAI MCP v3.0.0
  hosts: production
  become: yes
  tasks:
    - name: Stop services
      command: python stop_giljo.py
      args:
        chdir: /opt/giljoai

    - name: Backup database
      postgresql_db:
        name: giljo_mcp
        state: dump
        target: /backups/giljo_mcp_{{ ansible_date_time.iso8601 }}.sql

    - name: Pull v3.0.0
      git:
        repo: https://github.com/giljoai/giljo-mcp.git
        dest: /opt/giljoai
        version: v3.0.0

    - name: Install Python dependencies
      pip:
        requirements: /opt/giljoai/requirements.txt

    - name: Build frontend
      npm:
        path: /opt/giljoai/frontend

    - name: Run migrations
      command: alembic upgrade head
      args:
        chdir: /opt/giljoai

    - name: Start services
      command: python start_giljo.py
      args:
        chdir: /opt/giljoai
```

### Using Docker

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 7272 7274

CMD ["python", "start_giljo.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "7272:7272"
      - "7274:7274"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db/giljo_mcp
    depends_on:
      - db

  db:
    image: postgres:18
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=giljo_mcp
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## Validation Checklist

Before considering deployment complete:

- [ ] All services started successfully
- [ ] Health check returns "healthy"
- [ ] Dashboard loads without errors
- [ ] Authentication working (auto-login for localhost, API keys for network)
- [ ] Can create/update/delete projects
- [ ] Agent spawning works
- [ ] Message passing between agents works
- [ ] WebSocket real-time updates working
- [ ] MCP installer generation works
- [ ] Share links generate and expire correctly
- [ ] Logs showing no critical errors
- [ ] Firewall rules verified
- [ ] Backups completed and tested
- [ ] Monitoring configured
- [ ] Documentation updated

---

## Support

### Getting Help

- **Documentation**: https://github.com/giljoai/giljo-mcp/docs
- **Issues**: https://github.com/giljoai/giljo-mcp/issues
- **Discord**: https://discord.gg/giljoai
- **Email**: support@giljoai.com

### Emergency Contacts

- **Critical Issues**: emergency@giljoai.com
- **Security Issues**: security@giljoai.com

---

**Deployment Guide Version**: 3.0.0
**Last Updated**: 2025-10-09
**Next Review**: v3.1.0 release