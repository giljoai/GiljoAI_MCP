# Migration Guide: GiljoAI MCP v3.0 → v3.1

**Handover 0045 - Multi-Tool Agent Orchestration System**

This guide provides comprehensive instructions for upgrading existing GiljoAI MCP v3.0 installations to v3.1.

## Table of Contents

1. [Overview](#overview)
2. [What's New in v3.1](#whats-new-in-v31)
3. [Prerequisites](#prerequisites)
4. [Backup Procedures](#backup-procedures)
5. [Migration Steps](#migration-steps)
6. [Verification](#verification)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Overview

Version 3.1 introduces multi-tool agent orchestration capabilities, enabling GiljoAI MCP to coordinate work across Claude Code, Codex, and Gemini CLI agents through a unified MCP coordination protocol.

**Migration Complexity**: Low
**Estimated Time**: 5-10 minutes
**Downtime Required**: Yes (5 minutes)
**Data Loss Risk**: None (if backup created)

---

## What's New in v3.1

### Database Schema Changes

**New Columns in `agents` Table**:
- `job_id` (VARCHAR(36), nullable, indexed) - Links agents to MCP coordination jobs
- `mode` (VARCHAR(20), default='claude') - Specifies agent tool (claude/codex/gemini)

### Feature Additions

1. **Multi-Tool Agent Support**
   - Orchestrator can spawn agents across Claude Code, Codex, and Gemini CLI
   - Intelligent routing based on task characteristics
   - Unified coordination protocol

2. **MCP Coordination Protocol**
   - 7 new MCP tools for agent coordination
   - Job acknowledgment, progress reporting, error handling
   - Orchestrator-agent bidirectional messaging

3. **Enhanced Agent Templates**
   - All templates updated with MCP communication protocol instructions
   - Phase-based checkpoint guidance (acknowledgment, progress, completion)
   - Error handling protocol

### Backward Compatibility

✅ **Fully backward compatible** - Existing agents, projects, and workflows continue functioning unchanged.

- Existing agents default to `mode='claude'`
- `job_id` remains `NULL` for non-coordinated agents
- Legacy agent spawning continues to work

---

## Prerequisites

### Required
- GiljoAI MCP v3.0 currently installed and running
- PostgreSQL 14+ (18 recommended)
- Python 3.10+
- Database administrator access (for schema changes)

### Recommended
- Backup of current database
- Access to PostgreSQL command line tools (psql)
- 5 minutes of scheduled downtime

### Environment Check

Run this command to verify your current version:

```bash
python -c "import sys; sys.path.insert(0, 'src'); from giljo_mcp import __version__; print(f'Current version: {__version__}')"
```

Expected output for v3.0:
```
Current version: 3.0.0
```

---

## Backup Procedures

### Step 1: Stop Services

```bash
# Ctrl+C to stop if running in terminal
# OR find and kill processes
taskkill /IM "python.exe" /F /FI "WINDOWTITLE eq *run_api*"  # Windows
pkill -f "python.*run_api.py"  # Linux/macOS
```

### Step 2: Create Database Backup

**Full Database Backup**:
```bash
# Windows
"C:\Program Files\PostgreSQL\18\bin\pg_dump" -U postgres -d giljo_mcp > backup_v3_0_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql

# Linux/macOS
pg_dump -U postgres -d giljo_mcp > backup_v3_0_$(date +%Y%m%d).sql
```

**Table-Specific Backup** (faster):
```bash
pg_dump -U postgres -d giljo_mcp -t agents -t agent_templates > agents_backup_v3_0.sql
```

### Step 3: Verify Backup

```bash
# Check file size (should be > 0)
ls -lh backup_v3_0_*.sql  # Linux/macOS
dir backup_v3_0_*.sql  # Windows

# Verify backup integrity
pg_restore --list backup_v3_0_*.sql > /dev/null  # Should complete without errors
```

---

## Migration Steps

### Option 1: Automated Migration (Recommended)

**Step 1: Pull Latest Code**

```bash
cd F:\GiljoAI_MCP  # Adjust to your installation directory
git pull origin master
```

**Step 2: Run Migration Script**

```bash
python migrate_v3_0_to_v3_1.py
```

**Step 3: Review and Confirm**

The script will:
1. ✅ Verify database connection
2. ✅ Check migration status
3. ⚠️  Request confirmation (type `yes` to proceed)
4. ✅ Add `job_id` and `mode` columns
5. ✅ Create index on `job_id`
6. ✅ Update agent templates with MCP coordination
7. ✅ Verify migration success

**Step 4: Restart Services**

```bash
python startup.py
```

### Option 2: Manual Migration

If you prefer manual control:

**Step 1: Schema Changes**

```sql
-- Connect to database
psql -U postgres -d giljo_mcp

-- Add job_id column
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS job_id VARCHAR(36);

-- Add mode column with default
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS mode VARCHAR(20) DEFAULT 'claude';

-- Create index on job_id
CREATE INDEX IF NOT EXISTS idx_agent_job_id
ON agents(job_id);

-- Verify changes
\d agents
```

**Step 2: Update Templates (Python)**

```python
# Run this script to update templates
python -c "
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, 'src')

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import AgentTemplate
from giljo_mcp.template_seeder import _get_mcp_coordination_section
from sqlalchemy import select
import os
from dotenv import load_dotenv

load_dotenv()

async def update_templates():
    db_url = os.getenv('DATABASE_URL')
    db_manager = DatabaseManager(database_url=db_url, is_async=True)
    mcp_section = _get_mcp_coordination_section()

    async with db_manager.get_session_async() as session:
        result = await session.execute(select(AgentTemplate))
        templates = result.scalars().all()

        for template in templates:
            if 'MCP COMMUNICATION PROTOCOL' not in template.template_content:
                template.template_content += '\n\n' + mcp_section

        await session.commit()

    await db_manager.close_async()
    print('Templates updated successfully')

asyncio.run(update_templates())
"
```

**Step 3: Verify Migration**

```bash
python test_handover_0045_installation.py
```

Expected output:
```
Total Tests: 5
Passed: 5 ✅
Failed: 0 ❌
Success Rate: 100.0%
```

**Step 4: Restart Services**

```bash
python startup.py
```

---

## Verification

### Database Schema Verification

**Check Columns Exist**:
```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'agents'
AND column_name IN ('job_id', 'mode');
```

Expected output:
```
 column_name |     data_type     | column_default
-------------+-------------------+----------------
 job_id      | character varying | NULL
 mode        | character varying | 'claude'
```

**Check Index Exists**:
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'agents'
AND indexname = 'idx_agent_job_id';
```

### Template Verification

```sql
SELECT name,
       CASE
         WHEN template_content LIKE '%MCP COMMUNICATION PROTOCOL%' THEN 'YES'
         ELSE 'NO'
       END AS has_mcp_section
FROM agent_templates;
```

All templates should show `YES` in the `has_mcp_section` column.

### MCP Tools Verification

```python
python -c "
import sys
sys.path.insert(0, 'src')
from giljo_mcp.tools import register_agent_coordination_tools
print('✅ MCP coordination tools module loaded successfully')
"
```

### Application Health Check

```bash
# Start services
python startup.py

# Wait for API to initialize (30 seconds)
# Then check health endpoint
curl http://localhost:7272/health
```

Expected response:
```json
{"status":"healthy","version":"3.1.0"}
```

---

## Rollback Procedures

If you encounter issues and need to rollback to v3.0:

### Step 1: Stop Services

```bash
# Ctrl+C or kill processes as shown in Backup Procedures
```

### Step 2: Restore Database

**Full Restore**:
```bash
# WARNING: This drops and recreates the entire database
dropdb -U postgres giljo_mcp
createdb -U postgres giljo_mcp
psql -U postgres -d giljo_mcp < backup_v3_0_YYYYMMDD.sql
```

**Partial Restore** (remove new columns only):
```sql
-- Connect to database
psql -U postgres -d giljo_mcp

-- Remove new columns
ALTER TABLE agents DROP COLUMN IF EXISTS job_id;
ALTER TABLE agents DROP COLUMN IF EXISTS mode;

-- Drop index
DROP INDEX IF EXISTS idx_agent_job_id;
```

**Restore Templates Only**:
```bash
psql -U postgres -d giljo_mcp < agents_backup_v3_0.sql
```

### Step 3: Restore Code

```bash
git checkout tags/v3.0.0  # Or your v3.0 branch
```

### Step 4: Restart Services

```bash
python startup.py
```

### Step 5: Verify v3.0 Restored

```bash
python -c "import sys; sys.path.insert(0, 'src'); from giljo_mcp import __version__; print(f'Current version: {__version__}')"
```

---

## Troubleshooting

### Issue: "Column already exists" Error

**Symptom**:
```
ERROR: column "job_id" of relation "agents" already exists
```

**Solution**: Migration is idempotent - this is safe. The script will skip existing columns. Continue with migration.

### Issue: "Permission denied" Error

**Symptom**:
```
ERROR: permission denied to create extension "pg_trgm"
```

**Solution**: This is unrelated to v3.1 migration. The pg_trgm extension is created during initial installation. Ignore this error during migration.

### Issue: Templates Not Updated

**Symptom**:
```
Templates still missing MCP section
```

**Solution**:
```python
# Force template update
python -c "
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, 'src')
from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import AgentTemplate
from giljo_mcp.template_seeder import _get_mcp_coordination_section
from sqlalchemy import select, update
import os
from dotenv import load_dotenv

load_dotenv()

async def force_update():
    db_url = os.getenv('DATABASE_URL')
    db_manager = DatabaseManager(database_url=db_url, is_async=True)
    mcp_section = _get_mcp_coordination_section()

    async with db_manager.get_session_async() as session:
        await session.execute(
            update(AgentTemplate).values(
                template_content=AgentTemplate.template_content + '\n\n' + mcp_section
            ).where(~AgentTemplate.template_content.like('%MCP COMMUNICATION PROTOCOL%'))
        )
        await session.commit()

    await db_manager.close_async()
    print('Templates force-updated')

asyncio.run(force_update())
"
```

### Issue: Migration Verification Fails

**Symptom**:
```
Test suite shows failures
```

**Solution**:
1. Check database connection: `psql -U postgres -d giljo_mcp -c "SELECT 1;"`
2. Verify columns exist: Run SQL queries from Verification section
3. Check DATABASE_URL in `.env` file
4. Review migration logs for errors

### Issue: Services Won't Start After Migration

**Symptom**:
```
ImportError: cannot import name 'Agent'
```

**Solution**:
1. Clear Python cache: `find . -type d -name __pycache__ -exec rm -rf {} +`
2. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
3. Verify venv activated: `which python` should show venv path

---

## FAQ

### Q: Is downtime required?

**A:** Yes, approximately 5 minutes. Stop services before migration, restart after.

### Q: Will my existing agents stop working?

**A:** No. All existing agents remain functional with `mode='claude'` by default.

### Q: Do I need to update my product vision documents?

**A:** No. Vision documents are unchanged. The orchestrator automatically uses new coordination features when available.

### Q: Can I run v3.0 and v3.1 simultaneously?

**A:** No. The database schema changes are incompatible with v3.0 code.

### Q: What happens if migration fails midway?

**A:** The migration script uses database transactions where possible. If migration fails:
1. Check error logs
2. Fix the issue (e.g., permissions)
3. Rerun migration script (it's idempotent)
4. If unrecoverable, restore from backup

### Q: How do I verify migration succeeded?

**A:** Run the verification test suite:
```bash
python test_handover_0045_installation.py
```

All 5 tests should pass (100% success rate).

### Q: Can I skip the backup step?

**A:** Not recommended. Backups are essential for rollback. Migration is low-risk, but backups protect against unexpected issues.

### Q: Will this break my MCP server connections?

**A:** No. MCP server connections continue working. New coordination tools are additions, not replacements.

### Q: Do I need to reconfigure anything?

**A:** No. All configuration remains unchanged. New features are automatically available.

### Q: How long does the migration take?

**A:** Typical times:
- Schema changes: 5-10 seconds
- Template updates: 10-30 seconds (depends on template count)
- Verification: 20 seconds
- **Total: 1-2 minutes** (excluding backup and restart)

---

## Support

If you encounter issues not covered in this guide:

1. **Check Logs**:
   ```bash
   tail -f logs/api_stderr.log
   ```

2. **Run Diagnostics**:
   ```bash
   python test_handover_0045_installation.py
   ```

3. **Review Handover Documentation**:
   ```
   docs/handovers/0045/
   ```

4. **Rollback and Report**:
   - Follow rollback procedures
   - Document error messages
   - Create GitHub issue with details

---

## Post-Migration Checklist

After successful migration:

- [ ] All verification tests pass (100%)
- [ ] API server starts successfully
- [ ] Frontend loads without errors
- [ ] Existing projects visible in dashboard
- [ ] New agent can be spawned successfully
- [ ] Agent templates include MCP section
- [ ] Database backup saved in secure location

---

## Next Steps

After migration, explore new v3.1 features:

1. **Multi-Tool Orchestration**: Spawn agents using different tools
2. **MCP Coordination**: Monitor agent jobs via API
3. **Enhanced Templates**: Review updated agent templates with MCP instructions

Refer to Handover 0045 documentation for detailed usage guides.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Migration Script**: `migrate_v3_0_to_v3_1.py`
**Test Script**: `test_handover_0045_installation.py`
