# Rollback Procedures

**Last Updated**: October 8, 2025
**Version**: 2.0.0
**Audience**: System administrators and DevOps teams

---

## Table of Contents

1. [Overview](#overview)
2. [When to Rollback](#when-to-rollback)
3. [Database Rollback](#database-rollback)
4. [Data Migration Rollback](#data-migration-rollback)
5. [Verification Steps](#verification-steps)
6. [Emergency Rollback](#emergency-rollback)
7. [Post-Rollback Procedures](#post-rollback-procedures)

---

## Overview

This document provides comprehensive rollback procedures for the GiljoAI MCP Orchestrator v2.0 upgrade. Rollback procedures restore the system to the pre-upgrade state (v1.x) when issues occur during or after deployment.

### Rollback Scope

**What gets rolled back:**
- Database schema (config_data column and GIN index removed)
- Alembic migration state (reverted to pre-v2.0)
- Application code (if deployed separately)
- Configuration files (if modified)

**What doesn't get rolled back (preserved):**
- User data (projects, agents, messages, tasks)
- API keys and authentication credentials
- System logs (kept for analysis)
- Backup files (retained for investigation)

### Rollback Methods

**Method 1: Database Restore (Fastest)**
- Full database restore from backup
- Complete rollback in 5-10 minutes
- Loses any data created since backup
- **Recommended for**: Critical failures, data corruption

**Method 2: Alembic Downgrade (Safest)**
- Programmatic schema rollback via Alembic
- Preserves data created since migration
- Takes 10-20 minutes
- **Recommended for**: Migration issues, schema conflicts

**Method 3: Manual Rollback (Most Control)**
- SQL-based manual rollback
- Fine-grained control over changes
- Takes 15-30 minutes
- **Recommended for**: Partial rollbacks, specific issues

---

## When to Rollback

### Decision Matrix

| Situation | Severity | Action | Method |
|-----------|----------|--------|--------|
| Migration fails during upgrade | High | Rollback immediately | Method 2 (Alembic) |
| config_data not populated | Medium | Fix forward or rollback | Method 2 (Alembic) |
| GIN index performance poor | Low | Fix forward | N/A |
| API errors after deployment | High | Investigate, then decide | Method 1 or 2 |
| Data corruption detected | Critical | Rollback immediately | Method 1 (Restore) |
| Critical functionality broken | Critical | Rollback immediately | Method 1 (Restore) |
| Minor performance degradation | Low | Fix forward | N/A |
| Token reduction not working | Medium | Fix forward | N/A |

### Fix Forward vs Rollback

**Fix Forward (Preferred):**
- Issue is minor and doesn't affect core functionality
- Fix is quick and low-risk
- No data corruption
- System still usable

**Rollback (Required):**
- Critical functionality broken
- Data corruption detected
- Unable to fix within 1 hour
- System unusable for users

---

## Database Rollback

### Method 1: Full Database Restore

**Duration**: 5-10 minutes
**Data Loss**: Yes (since backup)
**Complexity**: Low

**Pre-Rollback Checklist:**

- [ ] Verify backup file exists and is valid
- [ ] Stop all services (API, frontend)
- [ ] Disconnect all users
- [ ] Create emergency backup of current state (optional)
- [ ] Notify team of rollback

**Step 1: Stop Services**

```bash
# Windows
stop_giljo.bat

# Linux
sudo systemctl stop giljo-mcp.service

# macOS
sudo launchctl stop com.giljoai.mcp

# Verify services stopped
[Windows]
Get-Process | Where-Object {$_.ProcessName -like "*python*" -or $_.ProcessName -like "*node*"}

[Linux/macOS]
ps aux | grep -E "run_api|npm"

# Expected: No GiljoAI processes running
```

**Step 2: Verify Backup**

```bash
# List available backups
ls -lht backups/

# Expected: giljo_mcp_pre_v2_YYYYMMDD_HHMMSS.dump

# Verify backup integrity
pg_restore --list backups/giljo_mcp_pre_v2_*.dump | head -20

# Expected: Valid PostgreSQL dump file listing
```

**Step 3: Drop Current Database**

```bash
# CAUTION: This deletes all data since backup
# Ensure backup is valid before proceeding

# Set password
export PGPASSWORD=your_db_password  # Linux/macOS
$env:PGPASSWORD="your_db_password"  # Windows PowerShell

# Drop database
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# Expected output:
# DROP DATABASE
```

**Step 4: Recreate Database**

```bash
# Create fresh database
psql -U postgres -c "CREATE DATABASE giljo_mcp;"

# Verify creation
psql -U postgres -c "\l giljo_mcp"

# Expected: giljo_mcp database listed
```

**Step 5: Restore Backup**

```bash
# Restore from backup
pg_restore -U postgres -d giljo_mcp \
    --format=custom \
    --verbose \
    backups/giljo_mcp_pre_v2_*.dump

# Monitor output for errors
# Expected: "creating INDEX", "creating CONSTRAINT", "setting owner"

# Common warnings (can be ignored):
# - "role does not exist" (if role names differ)
# - "already exists" (if restoring to non-empty database)

# Serious errors (stop and investigate):
# - "invalid dump file"
# - "out of memory"
# - "permission denied"
```

**Step 6: Verify Restore**

```bash
# Check table structure
psql -U postgres -d giljo_mcp -c "\dt"

# Expected: products, agents, messages, tasks, etc.

# Verify products table schema (pre-v2.0)
psql -U postgres -d giljo_mcp -c "\d products"

# Expected: NO config_data column

# Count records
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM products;"

# Expected: Same count as before migration
```

**Step 7: Update Alembic State**

```bash
# Stamp database with pre-v2.0 revision
cd /path/to/giljo_mcp
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate.ps1  # Windows

alembic stamp 11b1e4318444

# Verify
alembic current

# Expected: 11b1e4318444 (head), Add User and APIKey tables for LAN auth
```

**Step 8: Restart Services**

```bash
# Windows
start_giljo.bat

# Linux
sudo systemctl start giljo-mcp.service

# macOS
sudo launchctl start com.giljoai.mcp

# Wait 30 seconds for startup
sleep 30

# Verify services running
curl http://localhost:7272/health

# Expected: {"status":"healthy","database":"connected"}
```

**Step 9: Smoke Tests**

```bash
# Test API endpoints
curl http://localhost:7272/api/products/

# Test database queries
psql -U postgres -d giljo_mcp -c "SELECT id, name FROM products LIMIT 5;"

# Expected: Data returned successfully
```

---

### Method 2: Alembic Downgrade

**Duration**: 10-20 minutes
**Data Loss**: No (preserves data created since migration)
**Complexity**: Medium

**When to Use:**
- Migration completed but issues discovered
- Want to preserve data created since migration
- No data corruption

**Step 1: Stop Services**

```bash
# Same as Method 1, Step 1
stop_giljo.bat  # Windows
sudo systemctl stop giljo-mcp.service  # Linux
sudo launchctl stop com.giljoai.mcp  # macOS
```

**Step 2: Create Safety Backup**

```bash
# Create backup of current state (includes v2.0 data)
pg_dump -U postgres -h localhost -d giljo_mcp \
    --format=custom \
    --file=backups/giljo_mcp_rollback_safety_$(date +%Y%m%d_%H%M%S).dump

# Verify backup
ls -lh backups/giljo_mcp_rollback_safety_*.dump
```

**Step 3: Check Current Alembic Revision**

```bash
# Activate virtual environment
cd /path/to/giljo_mcp
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate.ps1  # Windows

# Check current revision
alembic current

# Expected: 8406a7a6dcc5 (head), add_config_data_to_product
```

**Step 4: Run Alembic Downgrade**

```bash
# Downgrade to pre-v2.0 revision
alembic downgrade 11b1e4318444

# Expected output:
# INFO  [alembic.runtime.migration] Running downgrade 8406a7a6dcc5 -> 11b1e4318444, remove config_data from products

# Monitor for errors
# If errors occur, stop and use Method 1 (Full Restore)
```

**Step 5: Verify Downgrade**

```bash
# Check Alembic state
alembic current

# Expected: 11b1e4318444 (head), Add User and APIKey tables for LAN auth

# Verify database schema
psql -U postgres -d giljo_mcp -c "\d products"

# Expected: NO config_data column

# Verify GIN index removed
psql -U postgres -d giljo_mcp -c "\di idx_product_config_data_gin"

# Expected: No rows (index should be removed)
```

**Step 6: Verify Data Integrity**

```bash
# Check that user data is intact
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM products;"
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM agents;"
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM messages;"

# Compare counts to pre-migration (should be same or higher)

# Sample data check
psql -U postgres -d giljo_mcp -c "SELECT id, name, created_at FROM products ORDER BY created_at DESC LIMIT 5;"

# Expected: Recent projects visible
```

**Step 7: Restart Services**

```bash
# Same as Method 1, Step 8
start_giljo.bat  # Windows
sudo systemctl start giljo-mcp.service  # Linux
sudo launchctl start com.giljoai.mcp  # macOS

# Wait and verify
sleep 30
curl http://localhost:7272/health
```

**Step 8: Functional Tests**

```bash
# Test core functionality
curl http://localhost:7272/api/products/
curl http://localhost:7272/api/agents/

# Test database operations
python -c "
from src.giljo_mcp.database import get_db_manager
db = get_db_manager()
# Test should complete without errors
print('✓ Database connection OK')
"

# Expected: All tests pass
```

---

### Method 3: Manual SQL Rollback

**Duration**: 15-30 minutes
**Data Loss**: No (if done correctly)
**Complexity**: High

**When to Use:**
- Alembic downgrade fails
- Need fine-grained control
- Partial rollback required

**Step 1: Stop Services and Backup**

```bash
# Same as Method 2, Steps 1-2
stop_giljo.bat
pg_dump -U postgres -d giljo_mcp --format=custom \
    --file=backups/giljo_mcp_manual_rollback_$(date +%Y%m%d_%H%M%S).dump
```

**Step 2: Remove GIN Index**

```bash
# Connect to database
psql -U postgres -d giljo_mcp

# Drop GIN index
DROP INDEX IF EXISTS idx_product_config_data_gin;

# Verify removal
\di idx_product_config_data_gin

-- Expected: No rows
```

**Step 3: Remove config_data Column**

```bash
# Still in psql

-- Remove config_data column
ALTER TABLE products DROP COLUMN IF EXISTS config_data;

-- Verify removal
\d products

-- Expected: config_data column NOT present
```

**Step 4: Update Alembic Version**

```bash
# Still in psql

-- Update Alembic version table
UPDATE alembic_version
SET version_num = '11b1e4318444'
WHERE version_num = '8406a7a6dcc5';

-- Verify update
SELECT version_num FROM alembic_version;

-- Expected: 11b1e4318444

-- Exit psql
\q
```

**Step 5: Verify Schema**

```bash
# Verify with Alembic
alembic current

# Expected: 11b1e4318444 (head)

# Verify database schema
psql -U postgres -d giljo_mcp -c "\d products"

# Expected: Pre-v2.0 schema (no config_data)
```

**Step 6: Restart and Test**

```bash
# Same as Method 2, Steps 7-8
start_giljo.bat
sleep 30
curl http://localhost:7272/health
```

---

## Data Migration Rollback

### config_data to Legacy Fields

If you need to preserve config_data information in legacy fields before rollback:

**Step 1: Export config_data**

```python
# scripts/export_config_data.py

import asyncio
import json
from src.giljo_mcp.database import get_db_manager
from sqlalchemy import text

async def export_config_data():
    db = get_db_manager()

    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT id, name, config_data FROM products WHERE config_data IS NOT NULL")
        )

        products = result.fetchall()

        # Export to JSON file
        export_data = []
        for product in products:
            export_data.append({
                'id': product.id,
                'name': product.name,
                'config_data': product.config_data
            })

        with open('backups/config_data_export.json', 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"✓ Exported config_data for {len(products)} products")

asyncio.run(export_config_data())
```

**Run export:**

```bash
python scripts/export_config_data.py

# Verify export file
cat backups/config_data_export.json | head -20
```

**Step 2: Map to Legacy Fields (if needed)**

If you have legacy fields that should be populated from config_data:

```python
# scripts/migrate_to_legacy_fields.py

import asyncio
import json
from src.giljo_mcp.database import get_db_manager
from sqlalchemy import text

async def migrate_to_legacy():
    db = get_db_manager()

    # Load exported data
    with open('backups/config_data_export.json', 'r') as f:
        export_data = json.load(f)

    async with db.async_session() as session:
        for product_data in export_data:
            config = product_data['config_data']

            # Map config_data to legacy fields (example)
            # Adjust based on your legacy schema
            await session.execute(
                text("""
                    UPDATE products
                    SET
                        architecture = :architecture,
                        tech_stack = :tech_stack,
                        database_type = :database_type
                    WHERE id = :product_id
                """),
                {
                    'architecture': config.get('architecture'),
                    'tech_stack': json.dumps(config.get('tech_stack', [])),
                    'database_type': config.get('database_type'),
                    'product_id': product_data['id']
                }
            )

        await session.commit()
        print(f"✓ Migrated config_data to legacy fields for {len(export_data)} products")

asyncio.run(migrate_to_legacy())
```

---

## Verification Steps

### Post-Rollback Verification Checklist

**1. Database Schema Verification:**

```bash
# Verify products table schema
psql -U postgres -d giljo_mcp -c "\d products"

# Checklist:
# [ ] config_data column absent
# [ ] Legacy columns present (if applicable)
# [ ] Primary key intact
# [ ] Foreign keys intact

# Verify indexes
psql -U postgres -d giljo_mcp -c "\di"

# Checklist:
# [ ] idx_product_config_data_gin absent
# [ ] Legacy indexes present
```

**2. Data Integrity Verification:**

```bash
# Count records in all tables
psql -U postgres -d giljo_mcp -c "
SELECT 'products' as table_name, COUNT(*) as count FROM products
UNION ALL
SELECT 'agents', COUNT(*) FROM agents
UNION ALL
SELECT 'messages', COUNT(*) FROM messages
UNION ALL
SELECT 'tasks', COUNT(*) FROM tasks;
"

# Compare to pre-migration counts
# Acceptable: Same or slightly higher (if data created during migration)
# Unacceptable: Significantly lower (data loss)

# Sample data verification
psql -U postgres -d giljo_mcp -c "
SELECT id, name, created_at FROM products ORDER BY created_at DESC LIMIT 10;
"

# Verify recent projects visible
```

**3. Alembic State Verification:**

```bash
# Check Alembic revision
alembic current

# Expected: 11b1e4318444 (head), Add User and APIKey tables for LAN auth

# Verify migrations directory
alembic history

# Expected: Migration history intact, current revision correct
```

**4. API Functionality Verification:**

```bash
# Test health endpoint
curl http://localhost:7272/health

# Expected: {"status":"healthy","database":"connected","version":"1.x.x"}

# Test products endpoint
curl http://localhost:7272/api/products/

# Expected: HTTP 200, JSON array of products

# Test agents endpoint
curl http://localhost:7272/api/agents/

# Expected: HTTP 200, JSON array of agents

# Test authentication (if LAN mode)
curl -H "X-API-Key: your_api_key" http://localhost:7272/api/products/

# Expected: HTTP 200 (not 401)
```

**5. Frontend Verification:**

```bash
# Access dashboard
# URL: http://localhost:7274

# Checklist:
# [ ] Dashboard loads without errors
# [ ] Projects list displays
# [ ] Agents list displays
# [ ] WebSocket connection established (real-time updates)
# [ ] No JavaScript console errors
```

**6. MCP Tools Verification:**

```bash
# Test MCP tools (should work with v1.x code)
python -c "
from src.giljo_mcp.tools.project import create_project
import asyncio

async def test():
    # Test should work with v1.x tools
    # (v2.0 tools like get_product_config should be reverted)
    print('✓ MCP tools functional')

asyncio.run(test())
"
```

---

## Emergency Rollback

### Critical Failure During Production

**Scenario**: Production system down, users affected, immediate rollback required.

**Time Target**: < 10 minutes

**Procedure:**

```bash
#!/bin/bash
# emergency_rollback.sh - Execute in emergency

set -e  # Exit on any error

echo "[EMERGENCY ROLLBACK] Starting..."

# 1. Stop services immediately
echo "[1/6] Stopping services..."
sudo systemctl stop giljo-mcp.service  # Adjust for your OS
sleep 5

# 2. Drop database
echo "[2/6] Dropping database..."
export PGPASSWORD=your_db_password
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# 3. Recreate database
echo "[3/6] Recreating database..."
psql -U postgres -c "CREATE DATABASE giljo_mcp;"

# 4. Restore latest backup
echo "[4/6] Restoring backup..."
LATEST_BACKUP=$(ls -t backups/giljo_mcp_pre_v2_*.dump | head -1)
pg_restore -U postgres -d giljo_mcp --format=custom $LATEST_BACKUP

# 5. Update Alembic state
echo "[5/6] Updating Alembic..."
cd /opt/mcp-orchestrator  # Adjust path
source venv/bin/activate
alembic stamp 11b1e4318444

# 6. Restart services
echo "[6/6] Restarting services..."
sudo systemctl start giljo-mcp.service
sleep 30

# Verify
curl http://localhost:7272/health || echo "FAILED - Manual intervention required"

echo "[EMERGENCY ROLLBACK] Complete"
```

**Make script executable:**

```bash
chmod +x emergency_rollback.sh

# Test (dry run)
bash -n emergency_rollback.sh  # Syntax check only

# Execute (in emergency only)
./emergency_rollback.sh
```

---

## Post-Rollback Procedures

### 1. Incident Documentation

Create post-rollback incident report:

```markdown
# Rollback Incident Report

**Date**: YYYY-MM-DD HH:MM UTC
**System**: GiljoAI MCP Production
**Incident**: v2.0 Rollback

## Timeline

- **HH:MM** - Issue detected: [description]
- **HH:MM** - Decision to rollback made
- **HH:MM** - Rollback started (Method: [1/2/3])
- **HH:MM** - Services stopped
- **HH:MM** - Database restored/downgraded
- **HH:MM** - Services restarted
- **HH:MM** - Verification complete
- **HH:MM** - System operational

## Root Cause

[Detailed description of why rollback was necessary]

## Rollback Method

- **Method**: [Full Restore / Alembic Downgrade / Manual]
- **Data Loss**: [Yes/No - if yes, describe]
- **Duration**: [X minutes]
- **Issues Encountered**: [Any problems during rollback]

## Verification Results

- [ ] Database schema correct (pre-v2.0)
- [ ] Alembic state correct (11b1e4318444)
- [ ] All services operational
- [ ] API endpoints functional
- [ ] Data integrity verified
- [ ] User workflows tested

## Next Steps

1. [Action item 1]
2. [Action item 2]
3. [Action item 3]

## Lessons Learned

[What we learned and how to prevent in future]
```

### 2. User Communication

```markdown
Subject: GiljoAI MCP Service Restoration - v2.0 Rollback Complete

Team,

We have completed a rollback of the v2.0 orchestrator upgrade:

**What Happened**:
[Brief description of issue]

**Actions Taken**:
- Rolled back to v1.x (pre-upgrade state)
- All data restored from backup
- Services fully operational

**Impact**:
- Downtime: [X minutes]
- Data Loss: [Yes/No - if yes, describe timeframe]
- Affected Users: [Number or "All users"]

**Current Status**:
- System operational on v1.x
- All services healthy
- Performance normal

**Next Steps**:
- Root cause analysis in progress
- v2.0 deployment postponed until issues resolved
- Will communicate new deployment timeline within 48 hours

We apologize for the disruption. If you experience any issues, please contact support immediately.

DevOps Team
```

### 3. Root Cause Analysis

Conduct thorough investigation:

**Questions to Answer**:
1. Why did the migration fail?
2. Were pre-deployment checks insufficient?
3. Were there warning signs we missed?
4. Did we follow rollback procedures correctly?
5. What can prevent this in future?

**Analysis Areas**:
- Pre-deployment testing
- Migration validation
- Rollback procedures
- Communication process
- Monitoring and alerting

### 4. Improvement Plan

Document improvements based on lessons learned:

```markdown
# v2.0 Rollback - Improvement Plan

## Testing Improvements

1. [ ] Add comprehensive migration tests
2. [ ] Test rollback procedures in staging
3. [ ] Validate GIN index performance before prod
4. [ ] Add config_data population verification

## Deployment Improvements

1. [ ] Implement canary deployment
2. [ ] Add automated rollback triggers
3. [ ] Improve monitoring during deployment
4. [ ] Enhanced smoke tests post-deployment

## Rollback Improvements

1. [ ] Automate rollback procedures
2. [ ] Pre-create emergency rollback script
3. [ ] Test rollback monthly
4. [ ] Document decision matrix more clearly

## Communication Improvements

1. [ ] Earlier notification to users
2. [ ] Real-time status page
3. [ ] Better incident escalation
4. [ ] Post-mortem transparency
```

### 5. Re-deployment Planning

When ready to retry v2.0 deployment:

**Pre-Deployment Requirements**:
1. Address root cause of previous failure
2. Implement improvement plan items
3. Test thoroughly in staging environment
4. Test rollback procedures in staging
5. Review and update deployment checklist
6. Schedule longer maintenance window
7. Ensure full team availability

**Validation Checklist**:
- [ ] All tests passing (unit, integration, performance)
- [ ] Staging deployment successful
- [ ] Rollback tested successfully in staging
- [ ] Monitoring and alerting configured
- [ ] Team trained on new procedures
- [ ] Documentation updated
- [ ] Communication plan ready

---

## Summary

This rollback procedure document provides comprehensive guidance for reverting the GiljoAI MCP v2.0 orchestrator upgrade:

- **Three rollback methods** (Database Restore, Alembic Downgrade, Manual)
- **Decision matrix** for when to rollback vs fix forward
- **Step-by-step procedures** with verification at each step
- **Emergency rollback script** for critical failures
- **Post-rollback procedures** for incident management

**Key Principles**:
1. Always backup before rollback
2. Verify each step before proceeding
3. Test thoroughly after rollback
4. Document the incident
5. Learn and improve

**Related Documentation**:
- [Production Deployment Checklist](PRODUCTION_DEPLOYMENT_CHECKLIST.md)
- [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
- [Monitoring Setup](MONITORING_SETUP.md)
- [Config Data Migration Guide](CONFIG_DATA_MIGRATION.md)

---

**Document Status**: Production Ready
**Next Review**: After first rollback event (or annually)

---

_Last Updated: October 8, 2025_
_Version: 2.0.0_
