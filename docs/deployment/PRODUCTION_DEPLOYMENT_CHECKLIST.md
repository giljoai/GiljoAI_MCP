# Production Deployment Checklist

**Last Updated**: October 8, 2025
**Version**: 2.0.0
**Audience**: System administrators and DevOps teams

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Verification](#pre-deployment-verification)
3. [Deployment Procedures by Mode](#deployment-procedures-by-mode)
4. [Post-Deployment Validation](#post-deployment-validation)
5. [Health Check Procedures](#health-check-procedures)
6. [Smoke Tests](#smoke-tests)
7. [Production Readiness Checklist](#production-readiness-checklist)

---

## Overview

This checklist ensures safe, comprehensive deployment of the GiljoAI MCP Orchestrator v2.0 upgrade to production environments. The orchestrator upgrade introduces hierarchical context loading, role-based filtering, and config_data management.

### Deployment Scope

- **Database Migration**: Alembic migration to add config_data column with GIN index
- **New MCP Tools**: get_product_config(), update_product_config()
- **Context Manager**: Role-based filtering for 60% token reduction
- **Performance**: GIN-indexed JSONB for sub-100ms queries

### Critical Success Factors

- Complete backup before migration
- Validate migration success before resuming operations
- Test role-based filtering for all agent types
- Verify performance metrics meet targets
- Document any deviations or issues

---

## Pre-Deployment Verification

### 1. System Requirements Check

**Database:**

```bash
# Verify PostgreSQL version (18.0+ required for GIN indexing)
psql -U postgres -c "SELECT version();"

# Expected: PostgreSQL 18.x or higher
```

**Disk Space:**

```bash
# Check available disk space (500MB+ required)
[Windows]
Get-PSDrive C | Select-Object Used,Free

[Linux/macOS]
df -h /var/lib/postgresql
```

**Backup Verification:**

```bash
# Verify recent backup exists
[Windows]
ls backups/giljo_mcp_*.dump -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1

[Linux/macOS]
ls -lht backups/giljo_mcp_*.dump | head -n 1
```

**Expected**: Backup created within last 24 hours

### 2. Migration Status Check

**Alembic Current Revision:**

```bash
# Check current database version
alembic current

# Expected output (before upgrade):
# 11b1e4318444 (head) - Add User and APIKey tables for LAN auth
```

**Database Schema Verification:**

```bash
# Verify products table exists
psql -U postgres -d giljo_mcp -c "\d products"

# Should show existing columns but NO config_data yet
```

### 3. Test Results Verification

**Unit Tests:**

```bash
# Run unit tests for new components
pytest tests/unit/test_context_manager.py -v
pytest tests/unit/test_product_tools.py -v

# Expected: All tests passing
```

**Integration Tests:**

```bash
# Run integration tests
pytest tests/integration/test_orchestrator_upgrade.py -v

# Expected: All tests passing
```

### 4. Code Review Checklist

Review completed pull requests/commits:

- [ ] Database migration reviewed (config_data column, GIN index)
- [ ] MCP tools reviewed (get_product_config, update_product_config)
- [ ] Context manager reviewed (role filtering logic)
- [ ] Template updates reviewed (orchestrator discovery workflow)
- [ ] Documentation reviewed (CONFIG_DATA_MIGRATION.md, guides)
- [ ] All tests passing in CI/CD pipeline
- [ ] No outstanding critical issues or blockers

### 5. Team Notification

- [ ] Team notified of deployment window
- [ ] Maintenance window scheduled (if applicable)
- [ ] Rollback plan communicated
- [ ] On-call engineer identified
- [ ] Communication channels confirmed (Slack, email, etc.)

---

## Deployment Procedures by Mode

### Localhost Mode Deployment

**Characteristics:**
- Single-user environment
- Minimal downtime impact
- No API authentication
- Local PostgreSQL database

**Deployment Steps:**

#### Step 1: Stop Services

```bash
# Windows
stop_giljo.bat

# Linux/macOS
./scripts/stop_services.sh

# Verify services stopped
[Windows]
Get-Process | Where-Object {$_.ProcessName -like "*python*" -or $_.ProcessName -like "*node*"}

[Linux/macOS]
ps aux | grep -E "run_api|npm"
```

#### Step 2: Create Backup

```bash
# Set password (development default: 4010)
export PGPASSWORD=4010  # Linux/macOS
$env:PGPASSWORD="4010"  # Windows PowerShell

# Create backup directory
mkdir -p backups

# Full database dump
pg_dump -U postgres -h localhost -d giljo_mcp \
    --format=custom \
    --file=backups/giljo_mcp_pre_v2_$(date +%Y%m%d_%H%M%S).dump

# Verify backup
ls -lh backups/
```

#### Step 3: Run Alembic Migration

```bash
# Navigate to project root
cd F:/GiljoAI_MCP

# Activate virtual environment
source venv/Scripts/activate  # Git Bash
.\venv\Scripts\activate.ps1   # PowerShell

# Run migration
alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade 11b1e4318444 -> 8406a7a6dcc5, add_config_data_to_product
```

#### Step 4: Populate config_data

```bash
# Run population script
python scripts/populate_config_data.py

# Expected output:
# [INFO] Starting config_data population for all products...
# [INFO] Found X products to process
# [SUCCESS] Populated config_data with 13 fields
```

#### Step 5: Validate Migration

```bash
# Run validation script
python scripts/validate_orchestrator_upgrade.py

# Expected output:
# ========================================
# VALIDATION RESULT: PASSED (12/12 checks)
# ========================================
```

#### Step 6: Restart Services

```bash
# Windows
start_giljo.bat

# Linux/macOS
./scripts/start_services.sh

# Wait 30 seconds for startup
sleep 30

# Verify services running
curl http://localhost:7272/health
```

#### Step 7: Smoke Tests

```bash
# Test MCP tools
python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    config = await get_product_config(project_id='test', filtered=False)
    print(f'Config loaded: {len(config.get(\"config\", {}))} fields')

asyncio.run(test())
"

# Expected: Config loaded: 13+ fields
```

---

### LAN Mode Deployment

**Characteristics:**
- Multi-user team environment
- Network-accessible (0.0.0.0 binding)
- API key authentication required
- Coordinated downtime

**Deployment Steps:**

#### Step 1: Pre-Deployment Communication

```bash
# Send notification to all users
# Example message:

Subject: GiljoAI MCP Maintenance - October 8, 2025 14:00-14:30 UTC

Team,

We will be deploying the orchestrator v2.0 upgrade today:
- Downtime window: 14:00-14:30 UTC (30 minutes)
- New features: Hierarchical context loading, 60% token reduction for workers
- Impact: All active sessions will be terminated
- Rollback plan: Available if issues occur

Please save your work and disconnect before 14:00 UTC.

Questions? Contact DevOps on Slack #giljo-support.
```

#### Step 2: Graceful Shutdown

```bash
# Send warning to connected clients (via dashboard notification)
# Wait 5 minutes for users to disconnect

# Stop services
[Windows]
Stop-Service -Name "GiljoAI-MCP"

[Linux]
sudo systemctl stop giljo-mcp.service

[macOS]
sudo launchctl stop com.giljoai.mcp

# Verify no active connections
psql -U postgres -d giljo_mcp -c "SELECT count(*) FROM pg_stat_activity WHERE datname='giljo_mcp';"

# Expected: 0 or 1 (your own connection)
```

#### Step 3: Create Backup

```bash
# Create backup directory with timestamp
BACKUP_DIR="backups/deployment_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U postgres -h localhost -d giljo_mcp \
    --format=custom \
    --file=$BACKUP_DIR/giljo_mcp_pre_v2.dump

# Config files backup
cp config.yaml $BACKUP_DIR/config.yaml.backup
cp .env $BACKUP_DIR/.env.backup

# Verify backups
ls -lh $BACKUP_DIR/

# Test restore (optional but recommended)
# Create test database
psql -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Restore to test database
pg_restore -U postgres -d giljo_mcp_test $BACKUP_DIR/giljo_mcp_pre_v2.dump

# Verify restore successful
psql -U postgres -d giljo_mcp_test -c "\dt"

# Clean up test database
psql -U postgres -c "DROP DATABASE giljo_mcp_test;"
```

#### Step 4: Run Alembic Migration

```bash
# Navigate to project root
cd /opt/mcp-orchestrator  # Linux
cd /usr/local/mcp-orchestrator  # macOS
cd C:\mcp-orchestrator  # Windows

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\Activate.ps1  # Windows

# Verify current revision
alembic current

# Run migration
alembic upgrade head

# Verify new revision
alembic current

# Expected: 8406a7a6dcc5 (head), add_config_data_to_product
```

#### Step 5: Populate config_data

```bash
# Run population script
python scripts/populate_config_data.py

# Monitor output for errors
# Expected: All products populated successfully
```

#### Step 6: Validate Migration

```bash
# Run validation script
python scripts/validate_orchestrator_upgrade.py

# Expected: All checks passing (12/12)

# If validation fails, see ROLLBACK_PROCEDURES.md
```

#### Step 7: Restart Services

```bash
# Start services
[Windows]
Start-Service -Name "GiljoAI-MCP"

[Linux]
sudo systemctl start giljo-mcp.service

[macOS]
sudo launchctl start com.giljoai.mcp

# Check service status
[Windows]
Get-Service -Name "GiljoAI-MCP"

[Linux]
sudo systemctl status giljo-mcp.service

[macOS]
sudo launchctl list | grep giljo
```

#### Step 8: Health Checks

```bash
# Get server LAN IP
LOCAL_IP=$(hostname -I | awk '{print $1}')  # Linux
LOCAL_IP=$(ipconfig getifaddr en0)  # macOS
$LOCAL_IP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias Ethernet).IPAddress  # Windows

# Test API health
curl http://$LOCAL_IP:7272/health

# Test with API key
curl -H "X-API-Key: your_api_key" http://$LOCAL_IP:7272/api/products/

# Expected: HTTP 200 OK
```

#### Step 9: Smoke Tests

```bash
# Test new MCP tools
python -c "
from src.giljo_mcp.tools.product import get_product_config, update_product_config
import asyncio

async def test():
    # Test get_product_config
    config = await get_product_config(project_id='test-project', filtered=False)
    print(f'✓ get_product_config: {len(config.get(\"config\", {}))} fields')

    # Test update_product_config
    await update_product_config(
        project_id='test-project',
        config_updates={'test_field': 'test_value'},
        merge=True
    )
    print('✓ update_product_config: Success')

asyncio.run(test())
"
```

#### Step 10: User Notification

```bash
# Send deployment complete notification
# Example message:

Subject: GiljoAI MCP Maintenance Complete - v2.0 Live

Team,

Deployment completed successfully:
- Duration: 25 minutes (5 min ahead of schedule)
- All services operational
- New features:
  * Hierarchical context loading
  * Role-based filtering (60% token reduction for workers)
  * config_data management with GIN indexing

You can now reconnect and resume work.

What's new:
- Orchestrators receive full project context
- Workers receive filtered, role-specific context
- Faster config queries (sub-100ms)

Documentation: docs/deployment/CONFIG_DATA_MIGRATION.md

Questions? Contact DevOps on Slack #giljo-support.
```

---

### WAN Mode Deployment

**Characteristics:**
- Internet-facing deployment
- TLS/SSL required
- OAuth + API key authentication
- High security requirements
- Potential for global users

**Deployment Steps:**

#### Step 1: Schedule Maintenance Window

```bash
# Best practices for WAN deployments:
# - Schedule during lowest traffic period (analyze usage metrics)
# - Provide 48-72 hours notice
# - Create status page with real-time updates
# - Coordinate with all timezone regions

# Example status page update:
Status: Scheduled Maintenance
Start: 2025-10-08 02:00 UTC
End: 2025-10-08 03:00 UTC
Impact: Service unavailable during maintenance
Updates: Every 15 minutes via status.giljoai.com
```

#### Step 2: Pre-Deployment Health Check

```bash
# Verify current system health
curl https://api.giljoai.com/health

# Check database connections
psql -U postgres -d giljo_mcp -c "SELECT count(*) FROM pg_stat_activity WHERE datname='giljo_mcp';"

# Check disk space (need 2GB+ for large deployments)
df -h /var/lib/postgresql

# Check memory usage
free -h

# Check CPU load
uptime
```

#### Step 3: Enable Maintenance Mode

```bash
# Create maintenance mode flag file
touch /opt/mcp-orchestrator/maintenance.flag

# Nginx configuration for maintenance page
cat > /etc/nginx/sites-available/giljo-maintenance.conf << 'EOF'
server {
    listen 443 ssl;
    server_name api.giljoai.com;

    ssl_certificate /etc/letsencrypt/live/api.giljoai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.giljoai.com/privkey.pem;

    return 503 "Service temporarily unavailable. Maintenance in progress. ETA: 02:00-03:00 UTC.";
}
EOF

# Reload Nginx
sudo nginx -t && sudo nginx -s reload
```

#### Step 4: Graceful Shutdown with Connection Draining

```bash
# Send shutdown signal to API (allows 60 seconds for requests to complete)
sudo systemctl stop giljo-mcp.service

# Wait for connections to drain
sleep 60

# Force stop if still running
sudo systemctl kill giljo-mcp.service

# Verify stopped
sudo systemctl status giljo-mcp.service
```

#### Step 5: Create Backup

```bash
# Create backup with metadata
BACKUP_DIR="/opt/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Database backup with compression
pg_dump -U postgres -h localhost -d giljo_mcp \
    --format=custom \
    --compress=9 \
    --file=$BACKUP_DIR/giljo_mcp_pre_v2.dump

# Config files
cp -r /opt/mcp-orchestrator/config.yaml $BACKUP_DIR/
cp /opt/mcp-orchestrator/.env $BACKUP_DIR/

# Backup Nginx config
cp /etc/nginx/sites-available/giljo-mcp.conf $BACKUP_DIR/

# Create backup metadata
cat > $BACKUP_DIR/metadata.json << EOF
{
  "backup_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "database_version": "$(psql -U postgres -d giljo_mcp -t -c 'SELECT version();')",
  "alembic_revision": "$(alembic current)",
  "backup_type": "pre-deployment",
  "deployment_version": "v2.0.0"
}
EOF

# Verify backup integrity
pg_restore --list $BACKUP_DIR/giljo_mcp_pre_v2.dump | head -20

# Upload backup to remote storage (S3, etc.)
# aws s3 cp $BACKUP_DIR s3://giljo-backups/$(date +%Y%m%d_%H%M%S)/ --recursive
```

#### Step 6: Run Alembic Migration

```bash
# Run migration
cd /opt/mcp-orchestrator
source venv/bin/activate
alembic upgrade head

# Verify migration completed
alembic current

# Expected: 8406a7a6dcc5 (head), add_config_data_to_product
```

#### Step 7: Populate config_data

```bash
# Run population script
python scripts/populate_config_data.py 2>&1 | tee -a deployment.log

# Verify all products populated
psql -U postgres -d giljo_mcp -c "SELECT id, name, jsonb_object_keys(config_data) FROM products LIMIT 5;"
```

#### Step 8: Validate Migration

```bash
# Run validation
python scripts/validate_orchestrator_upgrade.py 2>&1 | tee -a deployment.log

# If validation fails, STOP and rollback
# See ROLLBACK_PROCEDURES.md
```

#### Step 9: Start Services

```bash
# Start API service
sudo systemctl start giljo-mcp.service

# Wait for startup (check logs)
sudo journalctl -u giljo-mcp.service -f

# Wait for "Application startup complete" message
```

#### Step 10: Health Checks

```bash
# Internal health check
curl http://localhost:7272/health

# External health check (via public IP)
curl https://api.giljoai.com/health

# Database connection check
curl https://api.giljoai.com/api/products/ -H "Authorization: Bearer $API_KEY"
```

#### Step 11: Disable Maintenance Mode

```bash
# Remove maintenance flag
rm /opt/mcp-orchestrator/maintenance.flag

# Restore Nginx production config
sudo ln -sf /etc/nginx/sites-available/giljo-mcp.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo nginx -s reload
```

#### Step 12: Post-Deployment Monitoring

```bash
# Monitor error logs for 30 minutes
sudo journalctl -u giljo-mcp.service -f

# Monitor database performance
psql -U postgres -d giljo_mcp -c "SELECT * FROM pg_stat_activity WHERE datname='giljo_mcp';"

# Monitor application metrics (if Prometheus/Grafana available)
# - Request latency
# - Error rate
# - Database query time
# - GIN index usage
```

#### Step 13: Update Status Page

```bash
# Update status page:
Status: Operational
Message: Deployment completed successfully. All systems operational.
Features: v2.0 - Hierarchical context loading now live
```

---

## Post-Deployment Validation

### 1. Database Integrity Check

```bash
# Verify config_data column exists
psql -U postgres -d giljo_mcp -c "\d products"

# Expected output includes:
# config_data | jsonb |

# Verify GIN index exists
psql -U postgres -d giljo_mcp -c "\di idx_product_config_data_gin"

# Verify all products have config_data
psql -U postgres -d giljo_mcp -c "
SELECT COUNT(*) as total_products,
       COUNT(config_data) as products_with_config,
       COUNT(*) - COUNT(config_data) as missing_config
FROM products;
"

# Expected: missing_config = 0
```

### 2. MCP Tools Validation

```bash
# Test get_product_config
python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    try:
        config = await get_product_config(project_id='test', filtered=False)
        print('✓ get_product_config works')
        print(f'  Fields: {len(config.get(\"config\", {}))}')
    except Exception as e:
        print(f'✗ get_product_config failed: {e}')

asyncio.run(test())
"

# Test update_product_config
python -c "
from src.giljo_mcp.tools.product import update_product_config
import asyncio

async def test():
    try:
        await update_product_config(
            project_id='test',
            config_updates={'test_key': 'test_value'},
            merge=True
        )
        print('✓ update_product_config works')
    except Exception as e:
        print(f'✗ update_product_config failed: {e}')

asyncio.run(test())
"
```

### 3. Context Manager Validation

```bash
# Test role-based filtering
python -c "
from src.giljo_mcp.context_manager import get_filtered_config
from src.giljo_mcp.models import Product
import asyncio

async def test():
    # Mock product with full config_data
    class MockProduct:
        config_data = {
            'architecture': 'FastAPI + PostgreSQL',
            'test_commands': ['pytest'],
            'api_docs': '/docs/api.md'
        }

    product = MockProduct()

    # Test orchestrator (full config)
    orchestrator_config = get_filtered_config('orchestrator', product)
    print(f'✓ Orchestrator config: {len(orchestrator_config)} fields')

    # Test implementer (filtered config)
    implementer_config = get_filtered_config('implementer-test', product)
    print(f'✓ Implementer config: {len(implementer_config)} fields (filtered)')

    # Verify filtering worked
    if len(orchestrator_config) > len(implementer_config):
        print('✓ Filtering works correctly')
    else:
        print('✗ Filtering not working as expected')

asyncio.run(test())
"
```

### 4. Performance Validation

```bash
# Test GIN index query performance
psql -U postgres -d giljo_mcp -c "
EXPLAIN ANALYZE
SELECT id, name, config_data->'architecture' as arch
FROM products
WHERE config_data @> '{\"database_type\": \"postgresql\"}';
"

# Expected: Query time < 100ms, Index Scan using idx_product_config_data_gin
```

### 5. API Endpoint Validation

```bash
# Test API endpoints
curl http://localhost:7272/health
# Expected: {"status":"healthy","database":"connected","version":"2.0.0"}

curl http://localhost:7272/api/products/
# Expected: HTTP 200, list of products

curl http://localhost:7272/api/agents/
# Expected: HTTP 200, list of agents
```

---

## Health Check Procedures

### Automated Health Checks

Create a health check script:

```bash
#!/bin/bash
# health_check.sh - Comprehensive health check for GiljoAI MCP v2.0

set -e

echo "========================================="
echo "GiljoAI MCP v2.0 Health Check"
echo "========================================="
echo ""

# 1. API Server Health
echo "[1/6] API Server Health..."
API_HEALTH=$(curl -s http://localhost:7272/health)
if echo "$API_HEALTH" | grep -q "healthy"; then
    echo "✓ API server healthy"
else
    echo "✗ API server unhealthy: $API_HEALTH"
    exit 1
fi

# 2. Database Connection
echo "[2/6] Database Connection..."
DB_CHECK=$(psql -U postgres -d giljo_mcp -t -c "SELECT 1;")
if [ "$DB_CHECK" = " 1" ]; then
    echo "✓ Database connected"
else
    echo "✗ Database connection failed"
    exit 1
fi

# 3. config_data Migration
echo "[3/6] config_data Migration..."
CONFIG_DATA_COUNT=$(psql -U postgres -d giljo_mcp -t -c "SELECT COUNT(*) FROM products WHERE config_data IS NOT NULL;")
if [ "$CONFIG_DATA_COUNT" -gt "0" ]; then
    echo "✓ config_data populated ($CONFIG_DATA_COUNT products)"
else
    echo "✗ config_data not populated"
    exit 1
fi

# 4. GIN Index Performance
echo "[4/6] GIN Index Performance..."
QUERY_TIME=$(psql -U postgres -d giljo_mcp -t -c "
    EXPLAIN ANALYZE SELECT * FROM products WHERE config_data @> '{\"database_type\": \"postgresql\"}';
" | grep "Execution Time" | awk '{print $3}')
QUERY_TIME_MS=$(echo "$QUERY_TIME" | cut -d'.' -f1)
if [ "$QUERY_TIME_MS" -lt "100" ]; then
    echo "✓ GIN index performing well (${QUERY_TIME}ms)"
else
    echo "⚠ GIN index slow (${QUERY_TIME}ms, target: <100ms)"
fi

# 5. MCP Tools
echo "[5/6] MCP Tools..."
MCP_TEST=$(python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio
async def test():
    try:
        await get_product_config(project_id='test', filtered=False)
        print('OK')
    except Exception as e:
        print(f'ERROR: {e}')
asyncio.run(test())
" 2>&1)
if echo "$MCP_TEST" | grep -q "OK"; then
    echo "✓ MCP tools functional"
else
    echo "✗ MCP tools error: $MCP_TEST"
    exit 1
fi

# 6. Context Manager
echo "[6/6] Context Manager..."
CONTEXT_TEST=$(python -c "
from src.giljo_mcp.context_manager import get_filtered_config
class Mock:
    config_data = {'test': 'value'}
try:
    get_filtered_config('orchestrator', Mock())
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)
if echo "$CONTEXT_TEST" | grep -q "OK"; then
    echo "✓ Context manager functional"
else
    echo "✗ Context manager error: $CONTEXT_TEST"
    exit 1
fi

echo ""
echo "========================================="
echo "All health checks passed ✓"
echo "========================================="
```

**Run health check:**

```bash
chmod +x health_check.sh
./health_check.sh
```

---

## Smoke Tests

### Smoke Test Suite

Create comprehensive smoke tests:

```bash
#!/bin/bash
# smoke_tests.sh - Post-deployment smoke tests for v2.0

echo "========================================="
echo "GiljoAI MCP v2.0 Smoke Tests"
echo "========================================="
echo ""

# Test 1: Orchestrator Context Loading
echo "[Test 1] Orchestrator Full Context Loading..."
python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    config = await get_product_config(project_id='test-project', filtered=False)
    fields = len(config.get('config', {}))
    if fields >= 13:
        print(f'✓ Orchestrator receives full config ({fields} fields)')
        return True
    else:
        print(f'✗ Orchestrator config incomplete ({fields} fields, expected 13+)')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
"

# Test 2: Worker Agent Filtering
echo "[Test 2] Worker Agent Context Filtering..."
python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    config = await get_product_config(
        project_id='test-project',
        filtered=True,
        agent_name='implementer-test'
    )
    fields = len(config.get('config', {}))
    if fields < 13:
        print(f'✓ Worker receives filtered config ({fields} fields)')
        return True
    else:
        print(f'✗ Worker filtering not working ({fields} fields, expected <13)')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
"

# Test 3: Config Update
echo "[Test 3] Config Update Functionality..."
python -c "
from src.giljo_mcp.tools.product import update_product_config, get_product_config
import asyncio

async def test():
    # Update config
    await update_product_config(
        project_id='test-project',
        config_updates={'smoke_test_key': 'smoke_test_value'},
        merge=True
    )

    # Verify update
    config = await get_product_config(project_id='test-project', filtered=False)
    if config.get('config', {}).get('smoke_test_key') == 'smoke_test_value':
        print('✓ Config update successful')
        return True
    else:
        print('✗ Config update failed')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
"

# Test 4: Performance (GIN Index)
echo "[Test 4] GIN Index Query Performance..."
QUERY_TIME=$(psql -U postgres -d giljo_mcp -t -c "
    EXPLAIN ANALYZE SELECT * FROM products WHERE config_data @> '{\"database_type\": \"postgresql\"}';
" | grep "Execution Time" | awk '{print $3}')
QUERY_TIME_MS=$(echo "$QUERY_TIME" | cut -d'.' -f1)
if [ "$QUERY_TIME_MS" -lt "100" ]; then
    echo "✓ GIN index query time: ${QUERY_TIME}ms (target: <100ms)"
else
    echo "⚠ GIN index query time: ${QUERY_TIME}ms (slower than target <100ms)"
fi

# Test 5: API Endpoints
echo "[Test 5] API Endpoint Availability..."
curl -s http://localhost:7272/health | grep -q "healthy" && echo "✓ Health endpoint OK" || echo "✗ Health endpoint failed"
curl -s http://localhost:7272/api/products/ | grep -q "\[" && echo "✓ Products endpoint OK" || echo "✗ Products endpoint failed"

echo ""
echo "========================================="
echo "Smoke tests complete"
echo "========================================="
```

**Run smoke tests:**

```bash
chmod +x smoke_tests.sh
./smoke_tests.sh
```

---

## Production Readiness Checklist

### Pre-Deployment Checklist

- [ ] **Backup Verified**: Full PostgreSQL dump created and tested
- [ ] **Tests Passing**: All unit and integration tests passing
- [ ] **Code Review**: All changes reviewed and approved
- [ ] **Documentation Updated**: Migration guide and architecture docs current
- [ ] **Team Notified**: Deployment window communicated
- [ ] **Rollback Plan**: Tested and documented

### Migration Checklist

- [ ] **Services Stopped**: All services gracefully shut down
- [ ] **Backup Created**: Database and config files backed up
- [ ] **Alembic Migration**: config_data column added successfully
- [ ] **GIN Index Created**: idx_product_config_data_gin exists
- [ ] **config_data Populated**: All products have config_data
- [ ] **Validation Passed**: validate_orchestrator_upgrade.py passed

### Post-Deployment Checklist

- [ ] **Services Started**: All services running without errors
- [ ] **Health Checks Passed**: API, database, MCP tools functional
- [ ] **Smoke Tests Passed**: Orchestrator and worker filtering works
- [ ] **Performance Verified**: GIN index queries < 100ms
- [ ] **Monitoring Active**: Logs and metrics being collected
- [ ] **Team Notified**: Deployment complete notification sent

### Production Validation Checklist

- [ ] **User Acceptance**: Sample user workflows tested
- [ ] **Performance Metrics**: Token reduction verified (60% for workers)
- [ ] **Error Monitoring**: No critical errors in logs (first 24 hours)
- [ ] **Database Performance**: Query times within targets
- [ ] **Documentation**: All docs updated and accessible
- [ ] **Lessons Learned**: Deployment notes documented

---

## Summary

This checklist ensures comprehensive, safe deployment of the orchestrator v2.0 upgrade across all deployment modes. Key success factors:

- Complete backups before migration
- Validation at every step
- Thorough testing post-deployment
- Clear communication with users
- Documented rollback procedures

For issues during deployment, refer to:
- [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
- [Rollback Procedures](ROLLBACK_PROCEDURES.md)
- [Monitoring Setup](MONITORING_SETUP.md)

---

**Document Status**: Production Ready
**Next Review**: After first production deployment

---

_Last Updated: October 8, 2025_
_Version: 2.0.0_
