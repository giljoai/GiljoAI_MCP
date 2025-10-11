# Config Data Migration Guide

**Last Updated**: October 8, 2025
**Version**: 2.0.0
**Audience**: System administrators and DevOps

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Migration Overview](#migration-overview)
4. [Step 1: Backup Database](#step-1-backup-database)
5. [Step 2: Run Alembic Migration](#step-2-run-alembic-migration)
6. [Step 3: Populate config_data](#step-3-populate-config_data)
7. [Step 4: Validate Migration](#step-4-validate-migration)
8. [Step 5: Test Role-Based Filtering](#step-5-test-role-based-filtering)
9. [Rollback Procedures](#rollback-procedures)
10. [Troubleshooting](#troubleshooting)
11. [Schema Evolution](#schema-evolution)

---

## Overview

This guide provides step-by-step instructions for migrating existing GiljoAI MCP deployments to the new **hierarchical context management system** with `config_data` JSONB field.

### What's New

- **config_data JSONB field**: Rich project configuration stored in PostgreSQL
- **GIN Index**: Fast JSONB queries (sub-100ms performance)
- **Role-Based Filtering**: 60% token reduction for worker agents
- **Context Manager**: Hierarchical context loading system

### Migration Impact

- **Database**: Adds `config_data` column and GIN index to `products` table
- **API**: New MCP tools: `get_product_config()`, `update_product_config()`
- **Performance**: Improved query performance with GIN indexing
- **Downtime**: Minimal (< 5 minutes for migration + population)

---

## Prerequisites

### System Requirements

- **PostgreSQL**: Version 14.0+ (JSONB and GIN index support)
- **Python**: Version 3.11+ (for migration scripts)
- **Disk Space**: At least 500MB free for database operations
- **Permissions**: Database superuser or ALTER TABLE privileges

### Backup Requirements

- **Database Backup**: Full PostgreSQL dump before migration
- **Config Files**: Backup of `.env` and `config.yaml`
- **Rollback Plan**: Tested rollback procedure

### Version Compatibility

| GiljoAI MCP Version | Migration Required |
|---------------------|-------------------|
| v1.0 - v1.9 | Yes - Full migration |
| v2.0+ | No - Already migrated |

---

## Migration Overview

### Migration Steps

```
1. Backup Database
   └─> PostgreSQL dump to file

2. Run Alembic Migration
   └─> Add config_data column + GIN index

3. Populate config_data
   └─> Run populate_config_data.py script

4. Validate Migration
   └─> Run validate_orchestrator_upgrade.py script

5. Test Role-Based Filtering
   └─> Verify agents receive correct config
```

### Estimated Timeline

| Step | Duration | Can Run Concurrently |
|------|----------|---------------------|
| Backup Database | 2-5 minutes | No |
| Run Alembic Migration | 1-2 minutes | No |
| Populate config_data | 1-3 minutes | No |
| Validate Migration | 1 minute | Yes |
| Test Filtering | 2-5 minutes | Yes |

**Total**: 7-16 minutes (average: 10 minutes)

---

## Step 1: Backup Database

### Create PostgreSQL Dump

```bash
# Set password (if needed)
export PGPASSWORD=your_db_password

# Create backup directory
mkdir -p backups

# Create full database dump
pg_dump -U postgres -h localhost -d giljo_mcp \
    --format=custom \
    --file=backups/giljo_mcp_pre_migration_$(date +%Y%m%d_%H%M%S).dump

# Verify backup created
ls -lh backups/
```

### Backup Config Files

```bash
# Backup environment and config files
cp .env backups/.env.backup
cp config.yaml backups/config.yaml.backup

# Verify backups
ls -la backups/
```

### Test Restore (Optional but Recommended)

```bash
# Create test database
psql -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Restore to test database
pg_restore -U postgres -d giljo_mcp_test \
    backups/giljo_mcp_pre_migration_*.dump

# Verify restore successful
psql -U postgres -d giljo_mcp_test -c "\dt"

# Clean up test database
psql -U postgres -c "DROP DATABASE giljo_mcp_test;"
```

---

## Step 2: Run Alembic Migration

### Verify Current Database Version

```bash
# Check current Alembic revision
alembic current

# Should show something like:
# abc123 (head)
```

### Run Migration

```bash
# Navigate to project root
cd F:/GiljoAI_MCP

# Activate virtual environment (if using venv)
source venv/Scripts/activate  # Windows Git Bash
# OR
venv\Scripts\activate.bat      # Windows CMD

# Run Alembic upgrade
alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, add config_data to products
# INFO  [alembic.runtime.migration] Running upgrade def456 -> ghi789, create GIN index on config_data
```

### Verify Migration

```bash
# Connect to database
psql -U postgres -d giljo_mcp

# Check products table schema
\d products

# Expected output should include:
# config_data | jsonb |

# Check GIN index exists
\di idx_product_config_data_gin

# Exit psql
\q
```

### Manual Migration (If Alembic Fails)

If Alembic migration fails, run SQL manually:

```sql
-- Connect to database
psql -U postgres -d giljo_mcp

-- Add config_data column
ALTER TABLE products
ADD COLUMN config_data JSONB;

-- Create GIN index
CREATE INDEX idx_product_config_data_gin
ON products USING gin(config_data);

-- Initialize existing products
UPDATE products
SET config_data = '{}'::jsonb
WHERE config_data IS NULL;

-- Verify changes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'products' AND column_name = 'config_data';
```

---

## Step 3: Populate config_data

### Run Population Script

The `populate_config_data.py` script automatically detects project configuration from CLAUDE.md, package files, and codebase structure.

```bash
# Navigate to scripts directory
cd F:/GiljoAI_MCP/scripts

# Run population script
python populate_config_data.py

# Expected output:
# [INFO] Starting config_data population for all products...
# [INFO] Found 3 products to process
# [INFO] Processing product: GiljoAI-MCP (id: abc-123)
#   [SUCCESS] Detected architecture: FastAPI + PostgreSQL + Vue.js
#   [SUCCESS] Detected tech_stack: Python 3.11, PostgreSQL 18, Vue 3
#   [SUCCESS] Detected 8 critical features
#   [SUCCESS] Populated config_data with 13 fields
# [INFO] Processing product: Test-Project (id: def-456)
#   [SUCCESS] Populated config_data with 12 fields
# [INFO] Population complete: 3/3 products updated
```

### What the Script Does

1. **Reads CLAUDE.md**: Extracts architecture, tech stack, deployment modes
2. **Detects Files**: Finds `package.json`, `requirements.txt`, `pyproject.toml`
3. **Analyzes Structure**: Maps directory structure to purposes
4. **Identifies Features**: Extracts critical features from documentation
5. **Populates config_data**: Saves to database with validation

### Configuration Sources

The script sources configuration from:

| Source | Fields Populated |
|--------|------------------|
| `CLAUDE.md` | architecture, tech_stack, deployment_modes, critical_features |
| `package.json` | frontend_framework, tech_stack (Node/npm versions) |
| `requirements.txt` | backend_framework, tech_stack (Python packages) |
| `pyproject.toml` | backend_framework, tech_stack (Python packages) |
| `pytest.ini` / `setup.cfg` | test_config, test_commands |
| Directory structure | codebase_structure |
| Serena MCP presence | serena_mcp_enabled |

### Manual Population (If Script Fails)

If the script fails, manually populate config_data:

```python
# Python script for manual population
import asyncio
from src.giljo_mcp.database import get_db_manager
from sqlalchemy import text

async def manual_populate():
    db = get_db_manager()

    # Define config_data
    config_data = {
        "architecture": "FastAPI + PostgreSQL + Vue.js",
        "tech_stack": [
            "Python 3.11",
            "PostgreSQL 18",
            "Vue 3",
            "FastAPI 0.117",
            "SQLAlchemy 2.0"
        ],
        "codebase_structure": {
            "api": "REST API endpoints",
            "frontend": "Vue.js dashboard",
            "src/giljo_mcp": "Core orchestration engine",
            "installer": "Installation scripts",
            "tests": "Test suites"
        },
        "critical_features": [
            "Multi-tenant isolation",
            "Agent coordination",
            "Context chunking",
            "PostgreSQL-only architecture"
        ],
        "test_commands": [
            "pytest tests/ --cov=src",
            "npm run test"
        ],
        "test_config": {
            "coverage_threshold": 80,
            "test_framework": "pytest"
        },
        "database_type": "postgresql",
        "backend_framework": "fastapi",
        "frontend_framework": "vue",
        "deployment_modes": ["localhost", "server", "lan"],
        "known_issues": [
            "Port conflicts on Windows",
            "WebSocket connection drops under high load"
        ],
        "api_docs": "/docs/guides/API_REFERENCE.md",
        "documentation_style": "Markdown with mermaid diagrams",
        "serena_mcp_enabled": True
    }

    # Update product
    async with db.async_session() as session:
        result = await session.execute(
            text("""
                UPDATE products
                SET config_data = :config_data
                WHERE id = :product_id
            """),
            {
                "config_data": config_data,
                "product_id": "your-product-id-here"
            }
        )
        await session.commit()

    print(f"Updated product with config_data")

asyncio.run(manual_populate())
```

---

## Step 4: Validate Migration

### Run Validation Script

```bash
# Navigate to scripts directory
cd F:/GiljoAI_MCP/scripts

# Run validation script
python validate_orchestrator_upgrade.py

# Expected output:
# ========================================
# Orchestrator Upgrade Validation Report
# ========================================
#
# DATABASE CHECKS
# ✅ config_data column exists
# ✅ GIN index exists on config_data
# ✅ All products have config_data
# ✅ All config_data schemas valid
#
# MCP TOOLS CHECKS
# ✅ get_product_config() registered
# ✅ update_product_config() registered
#
# CONTEXT MANAGER CHECKS
# ✅ context_manager.py exists
# ✅ ROLE_CONFIG_FILTERS defined
# ✅ get_filtered_config() function exists
# ✅ Role filtering logic correct
#
# TEMPLATE CHECKS
# ✅ Orchestrator template exists
# ✅ Template includes discovery workflow
# ✅ Template enforces 30-80-10 principle
#
# PERFORMANCE CHECKS
# ✅ GIN index query time: 0.08ms (target: <100ms)
# ✅ Context loading time: 1.2s (target: <2s)
#
# ========================================
# VALIDATION RESULT: PASSED (12/12 checks)
# ========================================
```

### Validation Checks

The script validates:

1. **Database Structure**: config_data column, GIN index
2. **Data Integrity**: All products have config_data, schemas valid
3. **MCP Tools**: New tools registered and functional
4. **Context Manager**: Filtering logic correct
5. **Performance**: Query and loading times within targets

### If Validation Fails

Check specific failure messages and refer to [Troubleshooting](#troubleshooting) section.

---

## Step 5: Test Role-Based Filtering

### Test Orchestrator (Full Config)

```python
# Test orchestrator receives ALL fields
import asyncio
from src.giljo_mcp.tools.product import get_product_config

async def test_orchestrator():
    config = await get_product_config(
        project_id="your-project-id",
        filtered=False  # Full config for orchestrator
    )

    print(f"Orchestrator config fields: {len(config['config'])}")
    print(f"Expected: 13+ fields")

    # Verify all fields present
    assert "architecture" in config['config']
    assert "test_commands" in config['config']
    assert "api_docs" in config['config']

    print("✅ Orchestrator test passed")

asyncio.run(test_orchestrator())
```

### Test Implementer (Filtered Config)

```python
# Test implementer receives filtered config
async def test_implementer():
    config = await get_product_config(
        project_id="your-project-id",
        filtered=True,
        agent_name="implementer-test"
    )

    print(f"Implementer config fields: {len(config['config'])}")
    print(f"Expected: 8 fields")

    # Verify filtered correctly
    assert "architecture" in config['config']
    assert "tech_stack" in config['config']
    assert "test_commands" not in config['config']  # Should be filtered out
    assert "api_docs" not in config['config']  # Should be filtered out

    print("✅ Implementer test passed")

asyncio.run(test_implementer())
```

### Test Tester (Filtered Config)

```python
# Test tester receives filtered config
async def test_tester():
    config = await get_product_config(
        project_id="your-project-id",
        filtered=True,
        agent_name="tester-integration"
    )

    print(f"Tester config fields: {len(config['config'])}")
    print(f"Expected: 5 fields")

    # Verify filtered correctly
    assert "test_commands" in config['config']
    assert "test_config" in config['config']
    assert "architecture" not in config['config']  # Should be filtered out
    assert "api_docs" not in config['config']  # Should be filtered out

    print("✅ Tester test passed")

asyncio.run(test_tester())
```

---

## Rollback Procedures

### If Migration Fails

#### Option 1: Restore from Backup

```bash
# Drop current database
psql -U postgres -c "DROP DATABASE giljo_mcp;"

# Recreate database
psql -U postgres -c "CREATE DATABASE giljo_mcp;"

# Restore from backup
pg_restore -U postgres -d giljo_mcp \
    backups/giljo_mcp_pre_migration_*.dump

# Verify restore
psql -U postgres -d giljo_mcp -c "\dt"
```

#### Option 2: Manual Rollback (Downgrade)

```bash
# Downgrade Alembic to previous revision
alembic downgrade -1

# Verify downgrade
alembic current
```

### If Population Fails

If population fails but migration succeeded, you can retry population:

```bash
# Re-run population script
python scripts/populate_config_data.py

# Or manually populate via SQL
psql -U postgres -d giljo_mcp

UPDATE products
SET config_data = '{
    "architecture": "FastAPI + PostgreSQL + Vue.js",
    "serena_mcp_enabled": true
}'::jsonb
WHERE id = 'your-product-id';
```

### Restore Config Files

```bash
# Restore backed-up config files
cp backups/.env.backup .env
cp backups/config.yaml.backup config.yaml
```

---

## Troubleshooting

### Problem: Alembic Migration Fails

**Error**: `alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'`

**Solution**:
1. Check Alembic version table:
   ```sql
   SELECT version_num FROM alembic_version;
   ```

2. Stamp current version:
   ```bash
   alembic stamp head
   ```

3. Re-run migration:
   ```bash
   alembic upgrade head
   ```

---

### Problem: GIN Index Creation Fails

**Error**: `ERROR: could not create unique index "idx_product_config_data_gin"`

**Cause**: Concurrent operations on products table

**Solution**:
1. Stop API server and frontend
2. Wait for existing operations to complete
3. Re-run migration:
   ```bash
   alembic upgrade head
   ```

---

### Problem: Population Script Fails

**Error**: `FileNotFoundError: CLAUDE.md not found`

**Cause**: Script running from wrong directory

**Solution**:
1. Ensure you're in project root:
   ```bash
   cd F:/GiljoAI_MCP
   ```

2. Re-run script with absolute path:
   ```bash
   python /f/GiljoAI_MCP/scripts/populate_config_data.py
   ```

---

### Problem: Validation Script Reports Failures

**Error**: `❌ config_data column does not exist`

**Cause**: Migration did not complete successfully

**Solution**:
1. Check if migration ran:
   ```bash
   alembic current
   ```

2. If not at latest revision, re-run migration:
   ```bash
   alembic upgrade head
   ```

3. Verify column exists:
   ```sql
   \d products
   ```

---

### Problem: Agent Receives Empty Config

**Error**: Agent gets `{}` when calling `get_product_config()`

**Cause**: Product config_data not populated

**Solution**:
1. Check if product has config_data:
   ```sql
   SELECT id, name, config_data FROM products WHERE id = 'your-product-id';
   ```

2. If NULL or empty, re-run population:
   ```bash
   python scripts/populate_config_data.py
   ```

---

## Schema Evolution

### Adding New Fields

To add new fields to config_data schema:

1. **No Migration Required**: JSONB is flexible - just add fields via `update_product_config()`

   ```python
   await update_product_config(
       project_id="uuid",
       config_updates={
           "new_field": "new value",
           "another_field": ["array", "of", "values"]
       },
       merge=True  # Deep merge
   )
   ```

2. **Update Role Filters** (if needed):

   Edit `src/giljo_mcp/context_manager.py`:
   ```python
   ROLE_CONFIG_FILTERS = {
       "implementer": [
           # ... existing fields ...
           "new_field"  # Add new field
       ]
   }
   ```

3. **Update Documentation**:
   - Update schema in this guide
   - Update `ROLE_BASED_CONTEXT_FILTERING.md`

### Removing Fields

To remove deprecated fields:

1. **Remove from Role Filters**:
   ```python
   ROLE_CONFIG_FILTERS = {
       "implementer": [
           # Remove deprecated_field
       ]
   }
   ```

2. **Clean Existing Data** (optional):
   ```python
   # Remove field from all products
   await update_product_config(
       project_id="uuid",
       config_updates={
           "deprecated_field": None  # Remove field
       },
       merge=True
   )
   ```

### Renaming Fields

To rename fields while preserving data:

1. **Migration Script**:
   ```python
   # Rename field in all products
   async def rename_field():
       db = get_db_manager()
       async with db.async_session() as session:
           products = await session.execute(
               text("SELECT id, config_data FROM products")
           )

           for product in products:
               config = product.config_data
               if "old_field" in config:
                   config["new_field"] = config.pop("old_field")

                   await session.execute(
                       text("UPDATE products SET config_data = :config WHERE id = :id"),
                       {"config": config, "id": product.id}
                   )

           await session.commit()
   ```

2. **Update Role Filters**:
   ```python
   ROLE_CONFIG_FILTERS = {
       "implementer": [
           "new_field"  # Updated name
       ]
   }
   ```

---

## Post-Migration Checklist

After successful migration:

- [ ] Backup created and verified
- [ ] Alembic migration completed
- [ ] GIN index created
- [ ] config_data populated for all products
- [ ] Validation script passed all checks
- [ ] Role-based filtering tested
- [ ] API server restarted
- [ ] Frontend tested
- [ ] Documentation updated
- [ ] Team notified of new features

---

## Summary

This migration adds powerful hierarchical context management to GiljoAI MCP:

- **60% Token Reduction**: Workers receive only role-relevant config
- **GIN-Indexed JSONB**: Sub-100ms query performance
- **Flexible Schema**: Add/remove fields without migrations
- **Backward Compatible**: Existing functionality unchanged

For questions or issues, refer to:
- [Role-Based Context Filtering Guide](../guides/ROLE_BASED_CONTEXT_FILTERING.md)
- [Technical Architecture](../TECHNICAL_ARCHITECTURE.md)
- [MCP Tools Manual](../manuals/MCP_TOOLS_MANUAL.md)

---

_Last Updated: October 8, 2025_
_Version: 2.0.0_
