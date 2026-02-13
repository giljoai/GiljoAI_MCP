# Handover 0424l: Fresh Install & Backup Restore Verification

**Status:** Ready for Execution
**Color:** `#2196F3` (Blue - Verification/Testing)
**Prerequisites:** 0424k (Baseline Migration Update)
**Spawns:** NONE (FINAL handover in extended chain)
**Chain:** 0424 Organization Hierarchy Series (Extended)

---

## Overview

Verify that fresh installs and backup restores work correctly after the baseline migration update in 0424k.

**What This Accomplishes:**
- Confirms fresh install creates all org tables and columns
- Confirms backup restore works (org_id nullable allows restore)
- Confirms post-restore data integrity
- Validates customer deployment readiness

**Testing Strategy:**
1. Drop test database and recreate (simulates fresh install)
2. Run install.py migrations
3. Verify all org tables exist
4. Restore backup
5. Verify data integrity
6. Run org-related tests

---

## Prerequisites

**Required Handovers:**
- 0424k: Baseline migration updated with org tables (MUST be complete)

**Verify Before Starting:**
```powershell
# Check migration has org tables (should find matches now)
grep -c "organizations" migrations/versions/baseline_v32_unified.py

# Check backup exists
ls -la "F:\GiljoAI_MCP\backups\giljo_mcp_pre_fresh_install_20260130_231101.dump"
```

---

## Implementation Phases

### Phase 1: Create Fresh Test Database

**WARNING: This drops and recreates the TEST database only!**

```powershell
# Drop test database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp_test_fresh;"

# Create fresh test database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "CREATE DATABASE giljo_mcp_test_fresh;"
```

### Phase 2: Run Migrations on Fresh Database

```powershell
# Set environment to use test database
$env:DATABASE_URL = "postgresql://postgres:***@localhost:5432/giljo_mcp_test_fresh"

# Run alembic migrations
cd F:\GiljoAI_MCP
alembic upgrade head
```

### Phase 3: Verify Organization Tables Created

```powershell
# Check organizations table exists
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test_fresh -c "\d organizations"

# Check org_memberships table exists
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test_fresh -c "\d org_memberships"

# Check users has org_id column
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test_fresh -c "\d users" | grep org_id

# Check products has org_id column
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test_fresh -c "\d products" | grep org_id

# Check agent_templates has org_id column
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test_fresh -c "\d agent_templates" | grep org_id

# Check tasks has org_id column
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test_fresh -c "\d tasks" | grep org_id
```

**Expected Output for Each:**
- organizations: Table with id, tenant_key, name, slug, settings, is_active, created_at, updated_at
- org_memberships: Table with id, org_id, user_id, role, invited_by, tenant_key, is_active, joined_at
- users.org_id: `org_id | character varying(36) |` (nullable)
- products.org_id: Similar
- etc.

### Phase 4: Test Backup Restore

```powershell
# Restore backup to fresh database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/pg_restore.exe -U postgres -d giljo_mcp_test_fresh --clean --if-exists "F:\GiljoAI_MCP\backups\giljo_mcp_pre_fresh_install_20260130_231101.dump" 2>&1

# Check for errors (some warnings are OK, errors are not)
```

**Expected:** Restore completes without errors. Warnings about "does not exist" during --clean are OK.

### Phase 5: Verify Restored Data

```powershell
# Count records
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test_fresh -c "
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'organizations', COUNT(*) FROM organizations
UNION ALL
SELECT 'org_memberships', COUNT(*) FROM org_memberships
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'tasks', COUNT(*) FROM tasks;
"

# Verify org relationships
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test_fresh -c "
SELECT u.username, o.name as org_name, om.role
FROM users u
LEFT JOIN organizations o ON u.org_id = o.id
LEFT JOIN org_memberships om ON om.user_id = u.id AND om.org_id = o.id;
"
```

### Phase 6: Run Organization Tests

```powershell
# Set test database
$env:DATABASE_URL = "postgresql://postgres:***@localhost:5432/giljo_mcp_test_fresh"

# Run org-specific tests
pytest tests/models/test_organization_models.py -v
pytest tests/services/test_organization_service.py -v
pytest tests/api/test_organizations_api.py -v
```

### Phase 7: Cleanup Test Database

```powershell
# Drop test database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp_test_fresh;"
```

---

## Success Criteria

**Fresh Install:**
- [ ] `organizations` table created with all columns
- [ ] `org_memberships` table created with all columns
- [ ] `users.org_id` column exists (nullable)
- [ ] `products.org_id` column exists (nullable)
- [ ] `agent_templates.org_id` column exists (nullable)
- [ ] `tasks.org_id` column exists (nullable)
- [ ] All FK constraints present
- [ ] All indexes created

**Backup Restore:**
- [ ] pg_restore completes without errors
- [ ] All data restored correctly
- [ ] Organization relationships intact
- [ ] User/membership data valid

**Tests:**
- [ ] Model tests pass
- [ ] Service tests pass
- [ ] API tests pass

---

## Chain Execution Instructions

**CRITICAL: This is the FINAL handover in the extended 0424 chain.**

### Step 1: Read Chain Context

```powershell
cat prompts/0424_chain/chain_log.json
```

Verify 0424k status is "complete".

### Step 2: Mark Session In Progress

Update `prompts/0424_chain/chain_log.json` - set 0424l:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover

**CRITICAL: Use Task Tool Subagents**

```javascript
Task.create({
  subagent_type: 'backend-integration-tester',
  prompt: `Execute handover 0424l verification phases. Read F:\\GiljoAI_MCP\\handovers\\0424l_fresh_install_verification.md for full instructions.

Your tasks:
1. Create fresh test database (giljo_mcp_test_fresh)
2. Run alembic migrations
3. Verify all org tables and columns exist
4. Restore backup from F:\\GiljoAI_MCP\\backups\\giljo_mcp_pre_fresh_install_20260130_231101.dump
5. Verify restored data integrity
6. Run organization tests
7. Cleanup test database
8. Report all findings

IMPORTANT:
- Use PGPASSWORD=$DB_PASSWORD for all psql commands
- PostgreSQL binaries at /f/PostgreSQL/bin/
- Report any errors or unexpected behavior
- This simulates what a customer would experience on fresh install`
})
```

### Step 4: Commit Verification Results

If any issues found, fix them first. Otherwise:

```bash
git add -A && git commit -m "test(0424l): Verify fresh install and backup restore

- Verified fresh install creates all org tables
- Verified backup restore works with nullable org_id
- Verified data integrity post-restore
- All organization tests passing

Handover: 0424l (FINAL)
Chain: 0424 Organization Hierarchy (Extended) - COMPLETE
Status: Customer deployment ready

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 5: Mark Chain COMPLETE

Update `prompts/0424_chain/chain_log.json`:

```json
{
  "session_id": "0424l",
  "status": "complete",
  "completed_at": "<timestamp>",
  "tasks_completed": [
    "Created fresh test database",
    "Ran migrations - all org tables created",
    "Verified organizations table structure",
    "Verified org_memberships table structure",
    "Verified users.org_id column",
    "Verified products/templates/tasks org_id columns",
    "Restored backup successfully",
    "Verified data integrity",
    "All org tests passing"
  ],
  "summary": "Fresh install and backup restore verified. Customer deployment ready."
}
```

Also update:
```json
"chain_summary": "Organization Hierarchy Series (0424a-l) COMPLETE. Phase 1 (a-e): Core org infrastructure. Phase 2 (f-j): User.org_id integration. Phase 3 (k-l): Migration fix and verification. Fresh install and backup restore validated.",
"final_status": "complete"
```

### Step 6: CHAIN COMPLETE - NO TERMINAL SPAWN

**This is the FINAL handover. DO NOT SPAWN another terminal.**

Announce completion:
```powershell
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "0424 Chain COMPLETE (Extended)!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green
Write-Host "Handovers: 0424a-l (12 total)" -ForegroundColor Cyan
Write-Host "Fresh Install: VERIFIED" -ForegroundColor Green
Write-Host "Backup Restore: VERIFIED" -ForegroundColor Green
Write-Host "`nCustomer deployment READY!`n" -ForegroundColor Yellow
```

---

## Troubleshooting

**Migration fails with syntax error:**
- Check 0424k changes for typos
- Run: `python -m py_compile migrations/versions/baseline_v32_unified.py`

**pg_restore fails with FK constraint error:**
- Ensure org_id columns are nullable in migration
- Check restore order (may need `--disable-triggers`)

**Tests fail after restore:**
- Check org_id values populated correctly
- May need to run: `scripts/migrate_to_orgs.py` to populate org_ids

---

## Notes

**What This Validates:**
- Fresh install path (new customer)
- Upgrade path (existing customer with backup)
- Data migration path (org_id population)

**Customer Deployment Ready When:**
- 0424l status = "complete"
- All verification checks pass
- No errors in fresh install or restore

---

**Chain Status:** FINAL (0424l is the last handover)
