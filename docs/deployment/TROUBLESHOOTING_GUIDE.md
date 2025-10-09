# Troubleshooting Guide

**Last Updated**: October 8, 2025
**Version**: 2.0.0
**Audience**: System administrators and support engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Orchestrator Issues](#orchestrator-issues)
3. [Database Issues](#database-issues)
4. [Performance Issues](#performance-issues)
5. [Authentication Issues](#authentication-issues)
6. [Network Issues](#network-issues)
7. [Migration Issues](#migration-issues)
8. [Diagnostic Commands](#diagnostic-commands)

---

## Overview

This troubleshooting guide provides solutions for common issues encountered with the GiljoAI MCP Orchestrator v2.0 upgrade. Each issue includes symptoms, diagnostic procedures, and step-by-step resolution.

### Severity Levels

- **Critical**: System down, data loss risk, security vulnerability
- **High**: Major functionality broken, significant performance degradation
- **Medium**: Minor functionality issues, workarounds available
- **Low**: Cosmetic issues, minimal impact

### Getting Help

If this guide doesn't resolve your issue:
1. Check the [Technical Architecture](../TECHNICAL_ARCHITECTURE.md) documentation
2. Review the [Config Data Migration Guide](CONFIG_DATA_MIGRATION.md)
3. Search GitHub issues: https://github.com/giljoai/mcp-orchestrator/issues
4. Contact support with diagnostic output

---

## Orchestrator Issues

### Issue 1: Orchestrator Not Receiving Full Context

**Severity**: High

**Symptoms:**
- Orchestrator agent sees filtered config (missing fields)
- Context loading incomplete
- Token reduction applied incorrectly to orchestrator

**Diagnostic:**

```bash
# Test orchestrator config loading
python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    config = await get_product_config(
        project_id='your-project-id',
        filtered=False  # Should be False for orchestrators
    )
    print(f'Config fields: {len(config.get(\"config\", {}))}')
    print(f'Fields: {list(config.get(\"config\", {}).keys())}')

asyncio.run(test())
"

# Expected: 13+ fields for orchestrator
# If fewer fields, filtering is being incorrectly applied
```

**Root Causes:**
1. `filtered=True` passed when it should be `filtered=False`
2. Agent name incorrectly detected as worker role
3. Context manager ROLE_CONFIG_FILTERS misconfigured

**Resolution:**

```python
# Option 1: Verify MCP tool call
# In your orchestrator agent code, ensure:
config = await get_product_config(
    project_id=current_project_id,
    filtered=False  # CRITICAL: Orchestrators must use filtered=False
)

# Option 2: Check agent name detection
# The context manager detects orchestrators by name
# Ensure agent name contains "orchestrator" (case-insensitive)
# Valid names: "orchestrator", "Orchestrator-Main", "project-orchestrator"

# Option 3: Verify context_manager.py
# Open src/giljo_mcp/context_manager.py
# Verify detect_role() function includes:
def detect_role(agent_name, agent_role=None):
    """Detect agent role from name or explicit role"""
    agent_name_lower = agent_name.lower()

    if "orchestrator" in agent_name_lower:
        return "orchestrator"  # Returns full config

# Option 4: Manual override
# If agent name doesn't contain "orchestrator", pass explicit role
from src.giljo_mcp.context_manager import get_filtered_config
config = get_filtered_config("orchestrator", product)  # Force orchestrator role
```

**Verification:**

```bash
# After fix, verify orchestrator gets all fields
python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    config = await get_product_config(
        project_id='your-project-id',
        filtered=False
    )
    expected_fields = [
        'architecture', 'tech_stack', 'codebase_structure',
        'critical_features', 'test_commands', 'test_config',
        'database_type', 'backend_framework', 'frontend_framework',
        'deployment_modes', 'known_issues', 'api_docs',
        'documentation_style', 'serena_mcp_enabled'
    ]

    present = [f for f in expected_fields if f in config.get('config', {})]
    print(f'✓ {len(present)}/{len(expected_fields)} expected fields present')

asyncio.run(test())
"
```

---

### Issue 2: Worker Agent Receives Too Much Context

**Severity**: Medium

**Symptoms:**
- Worker agents receive full config instead of filtered
- Token usage not reduced as expected
- Workers see orchestrator-only fields (api_docs, documentation_style)

**Diagnostic:**

```bash
# Test worker agent config
python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    # Test implementer
    config = await get_product_config(
        project_id='your-project-id',
        filtered=True,
        agent_name='implementer-test'
    )
    print(f'Implementer fields: {len(config.get(\"config\", {}))}')
    print(f'Fields: {list(config.get(\"config\", {}).keys())}')

asyncio.run(test())
"

# Expected: 8 fields for implementer
# If 13+ fields, filtering not working
```

**Root Causes:**
1. `filtered=False` when it should be `filtered=True`
2. Agent role not detected correctly
3. ROLE_CONFIG_FILTERS not applied

**Resolution:**

```python
# Option 1: Verify MCP tool call
# In worker agent code, ensure:
config = await get_product_config(
    project_id=current_project_id,
    filtered=True,  # CRITICAL: Workers must use filtered=True
    agent_name=current_agent_name  # Pass agent name for role detection
)

# Option 2: Verify role detection
# Check agent name matches expected pattern
# Implementer: "implementer", "implementer-auth", "dev-implementer"
# Tester: "tester", "tester-integration", "qa-tester"
# Documenter: "documenter", "doc-writer", "documentation-agent"

# Option 3: Check context_manager.py ROLE_CONFIG_FILTERS
# Ensure role filters are defined:
ROLE_CONFIG_FILTERS = {
    "implementer": [
        "architecture",
        "tech_stack",
        "codebase_structure",
        "critical_features",
        "database_type",
        "backend_framework",
        "frontend_framework",
        "deployment_modes"
    ],
    "tester": [
        "test_commands",
        "test_config",
        "critical_features",
        "known_issues",
        "tech_stack"
    ],
    # ...
}
```

**Verification:**

```bash
# Verify filtering for each role
python -c "
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    roles = [
        ('implementer-test', 8),
        ('tester-integration', 5),
        ('documenter-api', 5)
    ]

    for agent_name, expected_count in roles:
        config = await get_product_config(
            project_id='your-project-id',
            filtered=True,
            agent_name=agent_name
        )
        actual_count = len(config.get('config', {}))
        status = '✓' if actual_count == expected_count else '✗'
        print(f'{status} {agent_name}: {actual_count} fields (expected {expected_count})')

asyncio.run(test())
"
```

---

### Issue 3: Context Loading Slow (> 2 seconds)

**Severity**: Medium

**Symptoms:**
- Agent activation slow
- `get_product_config()` takes > 2 seconds
- Database query timeout

**Diagnostic:**

```bash
# Measure context loading time
python -c "
import time
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    start = time.time()
    config = await get_product_config(
        project_id='your-project-id',
        filtered=False
    )
    duration = time.time() - start
    print(f'Context loading time: {duration:.2f}s')
    if duration > 2.0:
        print('⚠ Slower than target (2s)')
    else:
        print('✓ Within target')

asyncio.run(test())
"

# Also check GIN index usage
psql -U postgres -d giljo_mcp -c "
EXPLAIN ANALYZE
SELECT config_data FROM products WHERE id = 'your-project-id';
"
```

**Root Causes:**
1. GIN index not created or not being used
2. Database connection pool exhausted
3. Large config_data payload
4. Network latency (for remote databases)

**Resolution:**

```bash
# Option 1: Verify GIN index exists
psql -U postgres -d giljo_mcp -c "\di idx_product_config_data_gin"

# If missing, create it:
psql -U postgres -d giljo_mcp -c "
CREATE INDEX idx_product_config_data_gin
ON products USING gin(config_data);
"

# Option 2: Force index rebuild
psql -U postgres -d giljo_mcp -c "REINDEX INDEX idx_product_config_data_gin;"

# Option 3: Analyze table statistics
psql -U postgres -d giljo_mcp -c "ANALYZE products;"

# Option 4: Check database connection pool
# In config.yaml, increase pool size:
# database:
#   pool_size: 20  # Increase from default 10
#   max_overflow: 40  # Increase from default 20

# Option 5: Enable query caching (if not already)
# Add to src/giljo_mcp/database.py:
# @lru_cache(maxsize=100)
# async def get_product_by_id(product_id: str):
#     # Cache product lookups
```

**Verification:**

```bash
# After optimization, measure again
python -c "
import time
from src.giljo_mcp.tools.product import get_product_config
import asyncio

async def test():
    # Warm up cache
    await get_product_config(project_id='your-project-id', filtered=False)

    # Measure cached performance
    start = time.time()
    config = await get_product_config(project_id='your-project-id', filtered=False)
    duration = time.time() - start

    print(f'Cached context loading: {duration:.3f}s')
    if duration < 1.0:
        print('✓ Excellent performance (<1s)')
    elif duration < 2.0:
        print('✓ Good performance (<2s)')
    else:
        print('⚠ Still slow (>2s)')

asyncio.run(test())
"
```

---

## Database Issues

### Issue 4: Migration Conflicts (Alembic)

**Severity**: Critical

**Symptoms:**
- `alembic upgrade head` fails
- "Can't locate revision" error
- Multiple heads detected
- Database schema mismatch

**Diagnostic:**

```bash
# Check current Alembic state
alembic current

# Check for multiple heads
alembic heads

# Check migration history
alembic history

# Check database schema
psql -U postgres -d giljo_mcp -c "\d products"
```

**Root Causes:**
1. Database out of sync with migrations
2. Manual schema changes bypassed Alembic
3. Multiple migration branches
4. Corrupted alembic_version table

**Resolution:**

```bash
# Option 1: Resolve multiple heads
# If alembic heads shows multiple branches:
alembic merge <head1> <head2> -m "merge branches"
alembic upgrade head

# Option 2: Stamp database to current state
# If database schema is correct but Alembic state wrong:
alembic stamp head

# Option 3: Reset Alembic version table
# CAUTION: Only if you're sure database schema is correct
psql -U postgres -d giljo_mcp -c "TRUNCATE alembic_version;"
alembic stamp 8406a7a6dcc5  # Latest revision

# Option 4: Manual migration (if Alembic broken)
# Add config_data column manually:
psql -U postgres -d giljo_mcp -c "
ALTER TABLE products
ADD COLUMN IF NOT EXISTS config_data JSONB;

CREATE INDEX IF NOT EXISTS idx_product_config_data_gin
ON products USING gin(config_data);

UPDATE products
SET config_data = '{}'::jsonb
WHERE config_data IS NULL;
"

# Then stamp as migrated:
alembic stamp 8406a7a6dcc5
```

**Verification:**

```bash
# Verify migration state
alembic current
# Expected: 8406a7a6dcc5 (head), add_config_data_to_product

# Verify schema
psql -U postgres -d giljo_mcp -c "\d products"
# Expected: config_data | jsonb column present

# Verify index
psql -U postgres -d giljo_mcp -c "\di idx_product_config_data_gin"
# Expected: Index exists and is type gin
```

---

### Issue 5: JSONB Query Performance (GIN Index Not Used)

**Severity**: High

**Symptoms:**
- Queries slow despite GIN index
- EXPLAIN ANALYZE shows Seq Scan instead of Index Scan
- Database CPU high during config queries

**Diagnostic:**

```bash
# Check if GIN index is being used
psql -U postgres -d giljo_mcp -c "
EXPLAIN ANALYZE
SELECT * FROM products
WHERE config_data @> '{\"database_type\": \"postgresql\"}';
"

# Expected: "Index Scan using idx_product_config_data_gin"
# If shows "Seq Scan on products", index not being used
```

**Root Causes:**
1. Index not created
2. Statistics outdated
3. Query doesn't match index type
4. Database planner chooses sequential scan (small table)

**Resolution:**

```bash
# Option 1: Verify index exists
psql -U postgres -d giljo_mcp -c "
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'products' AND indexname = 'idx_product_config_data_gin';
"

# If missing, create:
psql -U postgres -d giljo_mcp -c "
CREATE INDEX idx_product_config_data_gin
ON products USING gin(config_data);
"

# Option 2: Update table statistics
psql -U postgres -d giljo_mcp -c "ANALYZE products;"

# Option 3: Rebuild index
psql -U postgres -d giljo_mcp -c "REINDEX INDEX idx_product_config_data_gin;"

# Option 4: Force index usage (for testing)
psql -U postgres -d giljo_mcp -c "
SET enable_seqscan = OFF;
EXPLAIN ANALYZE
SELECT * FROM products
WHERE config_data @> '{\"database_type\": \"postgresql\"}';
SET enable_seqscan = ON;
"

# Option 5: Use correct JSONB operators
# Containment operator @>
SELECT * FROM products WHERE config_data @> '{"key": "value"}';

# Key existence operator ?
SELECT * FROM products WHERE config_data ? 'key_name';

# Path operator #>
SELECT config_data #> '{nested,key}' FROM products;
```

**Verification:**

```bash
# Verify index is used
psql -U postgres -d giljo_mcp -c "
EXPLAIN ANALYZE
SELECT * FROM products
WHERE config_data @> '{\"database_type\": \"postgresql\"}';
" | grep -i "index scan"

# Expected output includes: "Index Scan using idx_product_config_data_gin"

# Verify query performance
psql -U postgres -d giljo_mcp -c "
EXPLAIN (ANALYZE, BUFFERS, TIMING)
SELECT * FROM products
WHERE config_data @> '{\"database_type\": \"postgresql\"}';
" | grep "Execution Time"

# Expected: Execution Time < 100ms
```

---

### Issue 6: Database Connection Pool Exhausted

**Severity**: High

**Symptoms:**
- "QueuePool limit exceeded" errors
- "Too many connections" errors
- API requests timing out
- High database connection count

**Diagnostic:**

```bash
# Check active database connections
psql -U postgres -d giljo_mcp -c "
SELECT count(*) as connection_count,
       state
FROM pg_stat_activity
WHERE datname='giljo_mcp'
GROUP BY state;
"

# Check connection pool configuration
# In config.yaml or .env, check:
# DATABASE_POOL_SIZE=10
# DATABASE_MAX_OVERFLOW=20
```

**Root Causes:**
1. Connection pool too small for load
2. Connections not being released (connection leaks)
3. Long-running queries holding connections
4. PostgreSQL max_connections too low

**Resolution:**

```bash
# Option 1: Increase connection pool size
# Edit config.yaml:
database:
  pool_size: 20  # Increase from 10
  max_overflow: 40  # Increase from 20
  pool_timeout: 30  # Seconds to wait for connection
  pool_recycle: 3600  # Recycle connections after 1 hour

# Option 2: Increase PostgreSQL max_connections
psql -U postgres -c "SHOW max_connections;"
# Default: 100

# Edit postgresql.conf:
# max_connections = 200

# Restart PostgreSQL:
sudo systemctl restart postgresql  # Linux
brew services restart postgresql@18  # macOS
Restart-Service postgresql-x64-18  # Windows

# Option 3: Find and fix connection leaks
# Check for long-running queries:
psql -U postgres -d giljo_mcp -c "
SELECT pid, age(clock_timestamp(), query_start), usename, query
FROM pg_stat_activity
WHERE state != 'idle' AND query NOT ILIKE '%pg_stat_activity%'
ORDER BY query_start;
"

# Kill stuck connections (if needed):
# psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <pid>;"

# Option 4: Enable connection pooling middleware
# Use PgBouncer for connection pooling:
# sudo apt install pgbouncer  # Linux
# Edit /etc/pgbouncer/pgbouncer.ini:
# [databases]
# giljo_mcp = host=localhost port=5432 dbname=giljo_mcp
#
# [pgbouncer]
# pool_mode = transaction
# max_client_conn = 100
# default_pool_size = 20
```

**Verification:**

```bash
# After restart, verify connection pool
python -c "
from src.giljo_mcp.database import get_db_manager
db = get_db_manager()
print(f'Pool size: {db.engine.pool.size()}')
print(f'Checked out: {db.engine.pool.checkedout()}')
"

# Monitor connections during load
watch -n 5 "psql -U postgres -d giljo_mcp -c \"
SELECT count(*) FROM pg_stat_activity WHERE datname='giljo_mcp';
\""
```

---

## Performance Issues

### Issue 7: Slow Config Loading (Missing GIN Index)

**Severity**: Medium

**Symptoms:**
- `get_product_config()` takes > 1 second
- Database CPU spikes during config queries
- EXPLAIN shows Seq Scan

**Diagnostic:**

```bash
# Check if GIN index exists
psql -U postgres -d giljo_mcp -c "
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename = 'products' AND indexname = 'idx_product_config_data_gin';
"

# If empty output, index is missing
```

**Resolution:**

```bash
# Create GIN index
psql -U postgres -d giljo_mcp -c "
CREATE INDEX idx_product_config_data_gin
ON products USING gin(config_data);
"

# Verify creation
psql -U postgres -d giljo_mcp -c "\di idx_product_config_data_gin"

# Analyze table
psql -U postgres -d giljo_mcp -c "ANALYZE products;"
```

**Verification:**

```bash
# Test query performance
psql -U postgres -d giljo_mcp -c "
EXPLAIN ANALYZE
SELECT * FROM products WHERE config_data @> '{\"database_type\": \"postgresql\"}';
" | grep "Execution Time"

# Expected: < 100ms
```

---

### Issue 8: High Memory Usage (Context Loading)

**Severity**: Medium

**Symptoms:**
- Python process using excessive memory
- Out of memory errors
- System swap usage high

**Diagnostic:**

```bash
# Check Python process memory
[Linux/macOS]
ps aux | grep python | grep -i giljo

[Windows]
Get-Process python | Where-Object {$_.CommandLine -like "*giljo*"} | Select-Object WorkingSet64

# Check system memory
[Linux]
free -h

[macOS]
vm_stat

[Windows]
Get-WmiObject Win32_OperatingSystem | Select-Object FreePhysicalMemory,TotalVisibleMemorySize
```

**Root Causes:**
1. Large config_data payloads
2. Memory leaks in context manager
3. Caching without size limits
4. Too many concurrent agent sessions

**Resolution:**

```bash
# Option 1: Limit config_data size
# Trim unnecessary fields from config_data
python -c "
from src.giljo_mcp.tools.product import update_product_config
import asyncio

async def trim():
    # Remove verbose fields
    config_updates = {
        'verbose_field': None,  # Remove
        'large_array': None  # Remove
    }
    await update_product_config(
        project_id='your-project-id',
        config_updates=config_updates,
        merge=True
    )
    print('✓ Trimmed config_data')

asyncio.run(trim())
"

# Option 2: Implement LRU cache with size limit
# Edit src/giljo_mcp/tools/product.py:
from functools import lru_cache

@lru_cache(maxsize=100)  # Limit cache size
def get_filtered_config_cached(role, product_id):
    # Cached version
    pass

# Option 3: Limit concurrent agents
# In config.yaml:
orchestrator:
  max_concurrent_agents: 10  # Limit simultaneous agents

# Option 4: Increase system memory (if available)
# Or use swap:
# sudo fallocate -l 4G /swapfile
# sudo chmod 600 /swapfile
# sudo mkswap /swapfile
# sudo swapon /swapfile
```

**Verification:**

```bash
# Monitor memory after changes
watch -n 5 "ps aux | grep python | grep giljo"

# Expected: Memory usage stable, not continuously increasing
```

---

## Authentication Issues

### Issue 9: API Key Authentication Failing (LAN Mode)

**Severity**: High

**Symptoms:**
- HTTP 401 Unauthorized errors
- "Invalid API key" messages
- API key header not recognized

**Diagnostic:**

```bash
# Test API key authentication
curl -v -H "X-API-Key: your_api_key_here" http://localhost:7272/api/products/

# Check for:
# - HTTP 401 response
# - "WWW-Authenticate" header in response
# - Error message in response body

# Verify API key file exists
[Linux/macOS]
ls -la ~/.giljo-mcp/api_keys.json

[Windows]
ls $env:USERPROFILE\.giljo-mcp\api_keys.json

# Check API key format
cat ~/.giljo-mcp/api_keys.json
# Expected format:
# {
#   "keys": [
#     {
#       "key": "gk_xxxxxxxxxxxxxxxxxxxx",
#       "created_at": "2025-10-08T12:00:00Z",
#       "description": "LAN deployment"
#     }
#   ]
# }
```

**Root Causes:**
1. Wrong API key header name
2. API key not in database/file
3. Mode not set to LAN (authentication disabled)
4. API key expired or revoked

**Resolution:**

```bash
# Option 1: Verify API key header
# Must be "X-API-Key" (case-sensitive)
curl -H "X-API-Key: gk_your_key" http://localhost:7272/api/products/

# NOT "Authorization: Bearer" (that's for OAuth)

# Option 2: Regenerate API key
python -c "
from src.giljo_mcp.auth import AuthManager
auth = AuthManager()
new_key = auth.generate_api_key('replacement-key')
print(f'New API key: {new_key}')
# Save this key securely
"

# Option 3: Verify mode is LAN
# Check config.yaml:
grep "mode:" config.yaml
# Expected: mode: lan (or server)

# If mode is localhost, authentication is disabled
# Set to lan or server to enable

# Option 4: Check API key in database
psql -U postgres -d giljo_mcp -c "
SELECT id, key_hash, description, created_at, expires_at
FROM api_keys
WHERE is_active = true;
"

# If no results, no active keys exist - regenerate
```

**Verification:**

```bash
# Test authentication with new key
curl -H "X-API-Key: gk_your_new_key" http://localhost:7272/api/products/

# Expected: HTTP 200, JSON response with products

# Test without key (should fail)
curl http://localhost:7272/api/products/

# Expected: HTTP 401 Unauthorized
```

---

### Issue 10: JWT Token Expired (WAN Mode)

**Severity**: Medium

**Symptoms:**
- "Token expired" errors
- Frequent re-authentication required
- OAuth flow loops

**Diagnostic:**

```bash
# Decode JWT token
TOKEN="your.jwt.token.here"
echo $TOKEN | cut -d'.' -f2 | base64 -d | python -m json.tool

# Check "exp" field (expiration timestamp)
# Compare to current time: date +%s
```

**Root Causes:**
1. Token TTL too short
2. Clock skew between client and server
3. Refresh token not being used

**Resolution:**

```bash
# Option 1: Increase token TTL
# Edit config.yaml:
security:
  jwt:
    access_token_ttl: 3600  # 1 hour (increase from 900s / 15 min)
    refresh_token_ttl: 86400  # 24 hours

# Restart API server

# Option 2: Synchronize clocks (NTP)
[Linux]
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd

[macOS]
sudo sntp -sS time.apple.com

[Windows]
w32tm /resync

# Option 3: Implement refresh token flow
# In client code, use refresh token before access token expires:
# if token_expires_in < 300:  # 5 minutes
#     new_token = refresh_access_token(refresh_token)
```

**Verification:**

```bash
# Verify token expiration
# Decode new token and check exp field
# Should be current_time + access_token_ttl

# Test authentication with new token
curl -H "Authorization: Bearer $NEW_TOKEN" https://api.giljoai.com/api/products/

# Expected: HTTP 200
```

---

## Network Issues

### Issue 11: Port Conflicts (Port 7272 Already in Use)

**Severity**: High

**Symptoms:**
- "Address already in use" error
- API fails to start
- Cannot bind to port 7272

**Diagnostic:**

```bash
# Check what's using port 7272
[Windows]
netstat -ano | findstr :7272

[Linux/macOS]
lsof -i :7272
# Or:
netstat -tulpn | grep 7272
```

**Root Causes:**
1. Previous API server process still running
2. Another application using port 7272
3. Port not released by OS

**Resolution:**

```bash
# Option 1: Stop existing process
[Windows]
$process = Get-NetTCPConnection -LocalPort 7272 | Select-Object -ExpandProperty OwningProcess
Stop-Process -Id $process -Force

[Linux/macOS]
kill $(lsof -t -i:7272)

# Option 2: Use different port
# Edit config.yaml:
services:
  api:
    port: 7273  # Change to available port

# Or use environment variable:
export GILJO_PORT=7273
python api/run_api.py

# Option 3: Wait for port release (Windows)
# Sometimes takes 2-4 minutes for OS to release port
# Wait and retry

# Option 4: Use PortManager to auto-select port
# Already implemented in run_api.py
# Will try 7272, 7273, 7274, etc. until available port found
```

**Verification:**

```bash
# Verify API started on new port
curl http://localhost:7273/health

# Update CORS origins if port changed
# Edit config.yaml:
# security:
#   cors:
#     allowed_origins:
#       - http://localhost:7273
```

---

### Issue 12: CORS Errors (Frontend Access Denied)

**Severity**: Medium

**Symptoms:**
- Browser console: "CORS policy blocked"
- "Access-Control-Allow-Origin" errors
- Dashboard fails to load data from API

**Diagnostic:**

```bash
# Check CORS configuration
grep -A 5 "cors:" config.yaml

# Test CORS with curl
curl -H "Origin: http://localhost:7274" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     http://localhost:7272/api/products/ \
     -v

# Check for "Access-Control-Allow-Origin" in response headers
```

**Root Causes:**
1. Frontend origin not in allowed_origins list
2. Wildcard (*) not allowed with credentials
3. Port changed but CORS config not updated

**Resolution:**

```bash
# Option 1: Add frontend origin to CORS
# Edit config.yaml:
security:
  cors:
    allowed_origins:
      - http://localhost:7274  # Frontend
      - http://127.0.0.1:7274  # Alternative localhost
      - http://10.1.0.164:7274  # LAN IP (if applicable)

# Option 2: Allow all origins (DEVELOPMENT ONLY)
# NOT RECOMMENDED for production
security:
  cors:
    allow_all_origins: true  # Only for development

# Option 3: Dynamic origin (if frontend port varies)
# In api/app.py, add:
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DEV ONLY
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Restart API server
```

**Verification:**

```bash
# Test CORS headers
curl -H "Origin: http://localhost:7274" \
     http://localhost:7272/api/products/ \
     -v | grep "Access-Control-Allow-Origin"

# Expected: Access-Control-Allow-Origin: http://localhost:7274

# Test from browser console
fetch('http://localhost:7272/api/products/', {credentials: 'include'})
  .then(r => r.json())
  .then(d => console.log(d))

# Expected: No CORS errors, data returned
```

---

### Issue 13: WebSocket Connection Drops

**Severity**: Medium

**Symptoms:**
- Dashboard real-time updates stop working
- "WebSocket connection closed" errors
- Frequent reconnection attempts

**Diagnostic:**

```bash
# Check WebSocket endpoint
curl -i -N \
     -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" \
     -H "Sec-WebSocket-Key: $(echo -n 'test' | base64)" \
     http://localhost:6003/ws

# Expected: HTTP 101 Switching Protocols

# Check WebSocket server logs
# In API logs, look for WebSocket connection/disconnection messages
```

**Root Causes:**
1. Reverse proxy timeout (Nginx, Apache)
2. Firewall closing idle connections
3. Client timeout configuration
4. Network instability

**Resolution:**

```bash
# Option 1: Increase Nginx proxy timeout (if using Nginx)
# Edit nginx.conf:
location /ws {
    proxy_pass http://localhost:6003;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;  # 1 hour
    proxy_send_timeout 3600s;
}

# Reload Nginx
sudo nginx -t && sudo nginx -s reload

# Option 2: Implement WebSocket ping/pong
# In api/websocket.py, add heartbeat:
import asyncio

async def websocket_heartbeat(websocket):
    while True:
        try:
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(30)  # Ping every 30s
        except:
            break

# Option 3: Client-side reconnection logic
# In frontend WebSocket client:
let reconnectInterval = 1000;
function connect() {
    ws = new WebSocket('ws://localhost:6003/ws');
    ws.onclose = () => {
        setTimeout(connect, reconnectInterval);
        reconnectInterval = Math.min(reconnectInterval * 2, 30000);  // Exponential backoff
    };
    ws.onopen = () => {
        reconnectInterval = 1000;  // Reset backoff
    };
}

# Option 4: Check firewall timeout
[Linux]
sudo sysctl net.netfilter.nf_conntrack_tcp_timeout_established
# Increase if too low:
sudo sysctl -w net.netfilter.nf_conntrack_tcp_timeout_established=7200

[Windows]
# Check Windows Firewall idle timeout
# Increase in Windows Firewall advanced settings
```

**Verification:**

```bash
# Test WebSocket connection stability
# Use wscat (npm install -g wscat)
wscat -c ws://localhost:6003/ws

# Leave connection open for 5+ minutes
# Should not disconnect

# Monitor WebSocket connections
psql -U postgres -d giljo_mcp -c "
SELECT COUNT(*) FROM pg_stat_activity
WHERE application_name LIKE '%websocket%';
"
```

---

## Migration Issues

### Issue 14: config_data NULL After Migration

**Severity**: High

**Symptoms:**
- Products have config_data column but values are NULL
- `get_product_config()` returns empty config
- Population script skipped

**Diagnostic:**

```bash
# Check for NULL config_data
psql -U postgres -d giljo_mcp -c "
SELECT id, name, config_data
FROM products
WHERE config_data IS NULL;
"

# If results returned, config_data not populated
```

**Root Causes:**
1. Population script not run
2. Population script failed silently
3. Migration added column but didn't set defaults

**Resolution:**

```bash
# Option 1: Run population script
python scripts/populate_config_data.py

# Option 2: Manual population
psql -U postgres -d giljo_mcp -c "
UPDATE products
SET config_data = '{
    \"architecture\": \"FastAPI + PostgreSQL + Vue.js\",
    \"database_type\": \"postgresql\",
    \"serena_mcp_enabled\": true
}'::jsonb
WHERE config_data IS NULL;
"

# Option 3: Set default empty JSON
psql -U postgres -d giljo_mcp -c "
UPDATE products
SET config_data = '{}'::jsonb
WHERE config_data IS NULL;
"

# Then populate properly with script
```

**Verification:**

```bash
# Check all products have config_data
psql -U postgres -d giljo_mcp -c "
SELECT COUNT(*) as total,
       COUNT(config_data) as populated,
       COUNT(*) - COUNT(config_data) as null_count
FROM products;
"

# Expected: null_count = 0
```

---

### Issue 15: Rollback to Pre-Migration State

**Severity**: Critical

**Symptoms:**
- Migration failed
- Data corruption
- Need to return to pre-v2.0 state

**Diagnostic:**

```bash
# Check if backup exists
ls -lh backups/

# Verify backup integrity
pg_restore --list backups/giljo_mcp_pre_v2_*.dump | head -20
```

**Resolution:**

See [ROLLBACK_PROCEDURES.md](ROLLBACK_PROCEDURES.md) for complete rollback instructions.

**Quick rollback:**

```bash
# 1. Stop services
stop_giljo.bat  # Windows
sudo systemctl stop giljo-mcp.service  # Linux

# 2. Drop database
psql -U postgres -c "DROP DATABASE giljo_mcp;"

# 3. Recreate database
psql -U postgres -c "CREATE DATABASE giljo_mcp;"

# 4. Restore backup
pg_restore -U postgres -d giljo_mcp backups/giljo_mcp_pre_v2_*.dump

# 5. Downgrade Alembic
alembic downgrade 11b1e4318444

# 6. Restart services
start_giljo.bat  # Windows
sudo systemctl start giljo-mcp.service  # Linux
```

---

## Diagnostic Commands

### Quick Health Check

```bash
#!/bin/bash
# quick_health_check.sh

echo "=== GiljoAI MCP v2.0 Health Check ==="

# 1. API Health
echo -n "API Server: "
curl -s http://localhost:7272/health | grep -q "healthy" && echo "✓" || echo "✗"

# 2. Database
echo -n "Database: "
psql -U postgres -d giljo_mcp -t -c "SELECT 1;" > /dev/null 2>&1 && echo "✓" || echo "✗"

# 3. config_data
echo -n "config_data: "
COUNT=$(psql -U postgres -d giljo_mcp -t -c "SELECT COUNT(*) FROM products WHERE config_data IS NOT NULL;")
echo "✓ ($COUNT products)"

# 4. GIN Index
echo -n "GIN Index: "
psql -U postgres -d giljo_mcp -t -c "\di idx_product_config_data_gin" | grep -q "idx_product_config_data_gin" && echo "✓" || echo "✗"

echo "==================================="
```

### Performance Diagnostics

```bash
# Check query performance
psql -U postgres -d giljo_mcp -c "
EXPLAIN (ANALYZE, BUFFERS, TIMING)
SELECT * FROM products WHERE config_data @> '{\"database_type\": \"postgresql\"}';
"

# Check database statistics
psql -U postgres -d giljo_mcp -c "
SELECT schemaname, tablename, last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename = 'products';
"

# Check index usage
psql -U postgres -d giljo_mcp -c "
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexrelname = 'idx_product_config_data_gin';
"
```

### Connection Diagnostics

```bash
# Active connections
psql -U postgres -d giljo_mcp -c "
SELECT count(*), state
FROM pg_stat_activity
WHERE datname = 'giljo_mcp'
GROUP BY state;
"

# Long-running queries
psql -U postgres -d giljo_mcp -c "
SELECT pid, usename, state, query_start, query
FROM pg_stat_activity
WHERE datname = 'giljo_mcp' AND state != 'idle'
ORDER BY query_start;
"

# Connection pool status
python -c "
from src.giljo_mcp.database import get_db_manager
db = get_db_manager()
print(f'Pool size: {db.engine.pool.size()}')
print(f'Checked out: {db.engine.pool.checkedout()}')
print(f'Overflow: {db.engine.pool.overflow()}')
"
```

---

## Summary

This troubleshooting guide covers the most common issues encountered with the GiljoAI MCP v2.0 orchestrator upgrade. For issues not covered here:

1. Check logs: `logs/api.log`, `logs/database.log`
2. Review documentation: `docs/TECHNICAL_ARCHITECTURE.md`
3. Search GitHub issues: https://github.com/giljoai/mcp-orchestrator/issues
4. Contact support with diagnostic output

**Related Documentation:**
- [Production Deployment Checklist](PRODUCTION_DEPLOYMENT_CHECKLIST.md)
- [Rollback Procedures](ROLLBACK_PROCEDURES.md)
- [Monitoring Setup](MONITORING_SETUP.md)
- [Config Data Migration Guide](CONFIG_DATA_MIGRATION.md)

---

**Document Status**: Production Ready
**Next Review**: After first month of production use

---

_Last Updated: October 8, 2025_
_Version: 2.0.0_
