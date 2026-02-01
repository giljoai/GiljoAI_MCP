# Database Schema Comparison Report
**Date**: 2026-01-28
**Production DB**: giljo_mcp (password: 4010)
**Test DB**: giljo_mcp_test (password: 4010)

## Executive Summary

The test database (`giljo_mcp_test`) has a **modernized schema** with critical improvements over production (`giljo_mcp`). The production database is missing key columns and constraints required for proper message counter functionality (Handover 0387i).

### Critical Impact
- **Production is outdated** - Missing message counter columns that are essential for agent communication
- **Breaking changes** - Production uses `agent_id` as primary key, test uses `id`
- **Missing tables** - Production has 3 additional tables not in test
- **Data migration required** - Cannot simply copy data due to schema incompatibility

---

## 1. agent_executions Table Differences

### 1.1 Missing Columns in Production (CRITICAL)
Production is **missing 4 critical columns** added in Handover 0387i (Counter-Based Message Architecture):

| Column Name | Type | Nullable | Purpose |
|------------|------|----------|---------|
| `id` | varchar(36) | NOT NULL | **NEW PRIMARY KEY** (modern schema) |
| `messages_sent_count` | integer | NOT NULL | Counter for outbound messages |
| `messages_waiting_count` | integer | NOT NULL | Counter for inbound messages pending read |
| `messages_read_count` | integer | NOT NULL | Counter for inbound messages acknowledged |

**Impact**: Production cannot support counter-based message tracking. The system will fail when trying to update message counts.

### 1.2 Primary Key Difference (BREAKING CHANGE)

| Database | Primary Key Column | Index Name |
|----------|-------------------|------------|
| **Production** | `agent_id` | `agent_executions_pkey` PRIMARY KEY (agent_id) |
| **Test** | `id` | `agent_executions_pkey` PRIMARY KEY (id) |

**Impact**: This is a BREAKING change. Production treats `agent_id` as the primary key, while test uses a separate `id` column. This requires careful migration to avoid data loss.

### 1.3 Index Differences

**Test database has ONE additional index** not in production:
```sql
-- Test only (ensures agent_id + instance_number uniqueness)
"uq_agent_instance" UNIQUE CONSTRAINT, btree (agent_id, instance_number)

-- Test also has this index (production missing)
"ix_agent_executions_agent_id" btree (agent_id)
```

**Production has NO unique constraint** on (agent_id, instance_number), which could lead to duplicate agent instances.

### 1.4 Column Order Difference

Production and test have **different column orders**:

**Production order** (28 columns):
1. agent_id (PK)
2. job_id
3. tenant_key
4. agent_display_name
5. status
6. ... (23 more columns)
28. instance_number (last)

**Test order** (32 columns):
1. id (PK)
2. agent_id
3. job_id
4. tenant_key
5. agent_display_name
6. instance_number (early in list)
7. ... (26 more columns)
32. agent_name (last)

---

## 2. Table Existence Differences

### 2.1 Tables in Production ONLY (Missing from Test)

| Table Name | Purpose | Impact |
|-----------|---------|--------|
| `alembic_version` | Alembic migration tracking | Migration history - safe to skip |
| `sessions` | User session management | **CRITICAL** - May break authentication |
| `template_augmentations` | Template customization | Feature-specific - check if used |

**Production has 35 tables**, **Test has 32 tables** (3 missing).

### 2.2 Analysis

- **alembic_version**: This is an Alembic migration metadata table. Test database likely uses a different migration approach (Nuclear Reset strategy per Handover 0601).
- **sessions**: This table stores user authentication sessions. **CRITICAL** - If production relies on this for session management, test database will break authentication workflows.
- **template_augmentations**: Template customization feature. Check if this feature is still active in codebase.

---

## 3. Other Table Comparisons

### 3.1 agent_jobs Table
**Status**: IDENTICAL (no differences found)
- Same columns (10 columns)
- Same indexes (7 indexes)
- Same constraints (1 check constraint)
- Same foreign keys (2 FKs)

**Note**: Test has one additional foreign key reference from `tasks` table:
```sql
-- Test only
TABLE "tasks" CONSTRAINT "tasks_job_id_fkey" FOREIGN KEY (job_id) REFERENCES agent_jobs(job_id)
```

---

## 4. Migration Requirements

### 4.1 Critical Changes Needed in Production

**Priority 1 (BLOCKING)**: Add message counter columns
```sql
ALTER TABLE agent_executions
ADD COLUMN messages_sent_count integer NOT NULL DEFAULT 0,
ADD COLUMN messages_waiting_count integer NOT NULL DEFAULT 0,
ADD COLUMN messages_read_count integer NOT NULL DEFAULT 0;
```

**Priority 2 (BREAKING)**: Migrate primary key from agent_id to id
```sql
-- Step 1: Add id column
ALTER TABLE agent_executions ADD COLUMN id varchar(36);

-- Step 2: Populate id column with agent_id values (or generate new UUIDs)
UPDATE agent_executions SET id = agent_id;

-- Step 3: Set id as NOT NULL
ALTER TABLE agent_executions ALTER COLUMN id SET NOT NULL;

-- Step 4: Drop old primary key
ALTER TABLE agent_executions DROP CONSTRAINT agent_executions_pkey;

-- Step 5: Create new primary key on id
ALTER TABLE agent_executions ADD PRIMARY KEY (id);

-- Step 6: Add index on agent_id (now a regular column)
CREATE INDEX ix_agent_executions_agent_id ON agent_executions(agent_id);

-- Step 7: Add unique constraint
ALTER TABLE agent_executions ADD CONSTRAINT uq_agent_instance UNIQUE (agent_id, instance_number);
```

**Priority 3 (DATA INTEGRITY)**: Add unique constraint
```sql
ALTER TABLE agent_executions
ADD CONSTRAINT uq_agent_instance UNIQUE (agent_id, instance_number);
```

### 4.2 Table Creation Requirements

**Missing tables in test** (if needed):
```sql
-- If session management is required
CREATE TABLE sessions (...);  -- Schema from production

-- If template augmentation is required
CREATE TABLE template_augmentations (...);  -- Schema from production
```

### 4.3 Recommended Migration Strategy

**Option A: Nuclear Reset (Handover 0601 Approach)**
- Drop production database entirely
- Recreate from SQLAlchemy models (fresh schema)
- **WARNING**: Loses all existing data

**Option B: Incremental Migration (Data Preservation)**
1. Backup production database
2. Add new columns with DEFAULT values
3. Migrate primary key (complex, multi-step process)
4. Add missing indexes and constraints
5. Validate data integrity
6. Update application code to use new schema

**Option C: Dual Database Transition**
1. Keep production as-is (read-only)
2. Create new test database with modern schema
3. Migrate data selectively (ETL process)
4. Switch over once validated

**Recommendation**: Option B (Incremental Migration) if production data must be preserved. Option A (Nuclear Reset) if starting fresh is acceptable.

---

## 5. Risk Assessment

### 5.1 High Risk Issues

1. **Primary Key Change** (agent_id → id)
   - Risk: Data corruption, FK constraint violations
   - Mitigation: Multi-step migration with validation

2. **Message Counter Columns Missing**
   - Risk: Application crashes when updating counters
   - Mitigation: Add with DEFAULT 0, backfill from messages JSONB

3. **Missing Unique Constraint**
   - Risk: Duplicate agent instances
   - Mitigation: Add constraint after deduplicating data

### 5.2 Medium Risk Issues

1. **Missing sessions Table**
   - Risk: Authentication failures in test environment
   - Mitigation: Create table or update auth to not depend on it

2. **Missing template_augmentations Table**
   - Risk: Feature breaks if in use
   - Mitigation: Check codebase for usage, create if needed

### 5.3 Low Risk Issues

1. **alembic_version Table**
   - Risk: Migration tracking confusion
   - Mitigation: Document that test uses different migration approach

---

## 6. Action Items

### Immediate (Do Now)
- [ ] Backup production database before ANY changes
- [ ] Add message counter columns to production (Priority 1)
- [ ] Verify application code expects new columns

### Short Term (This Week)
- [ ] Plan primary key migration strategy
- [ ] Test migration on development copy of database
- [ ] Check if sessions table is required (auth dependency)
- [ ] Check if template_augmentations is used in codebase

### Long Term (Next Sprint)
- [ ] Execute primary key migration (if going with Option B)
- [ ] Add unique constraint on (agent_id, instance_number)
- [ ] Validate all indexes match test database
- [ ] Update documentation with new schema

---

## 7. SQL Migration Script (Production → Test Schema)

**WARNING**: Run on development copy first. ALWAYS backup before executing.

```sql
-- ============================================
-- PRODUCTION DATABASE MIGRATION SCRIPT
-- Target: Match giljo_mcp_test schema
-- ============================================

-- STEP 1: BACKUP (CRITICAL)
-- Run: pg_dump -U postgres -d giljo_mcp > giljo_mcp_backup_20260128.sql

-- STEP 2: Add message counter columns (Priority 1)
BEGIN;

ALTER TABLE agent_executions
ADD COLUMN IF NOT EXISTS messages_sent_count integer NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS messages_waiting_count integer NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS messages_read_count integer NOT NULL DEFAULT 0;

-- Backfill from messages JSONB if data exists
-- (Optional: Add logic to count existing messages)

COMMIT;

-- STEP 3: Add id column (prepare for PK migration)
BEGIN;

ALTER TABLE agent_executions ADD COLUMN IF NOT EXISTS id varchar(36);
UPDATE agent_executions SET id = agent_id WHERE id IS NULL;
ALTER TABLE agent_executions ALTER COLUMN id SET NOT NULL;

COMMIT;

-- STEP 4: Migrate primary key (BREAKING - Do after testing)
BEGIN;

-- Drop old PK
ALTER TABLE agent_executions DROP CONSTRAINT agent_executions_pkey;

-- Create new PK on id
ALTER TABLE agent_executions ADD PRIMARY KEY (id);

-- Add index on agent_id (now regular column)
CREATE INDEX IF NOT EXISTS ix_agent_executions_agent_id ON agent_executions(agent_id);

COMMIT;

-- STEP 5: Add unique constraint
BEGIN;

-- Check for duplicates first
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM agent_executions
    GROUP BY agent_id, instance_number
    HAVING COUNT(*) > 1
  ) THEN
    ALTER TABLE agent_executions
    ADD CONSTRAINT uq_agent_instance UNIQUE (agent_id, instance_number);
  ELSE
    RAISE NOTICE 'Duplicate (agent_id, instance_number) found - resolve before adding constraint';
  END IF;
END $$;

COMMIT;

-- STEP 6: Verify migration
SELECT
  'agent_executions' as table_name,
  COUNT(*) as row_count,
  COUNT(DISTINCT id) as unique_ids,
  COUNT(DISTINCT agent_id) as unique_agent_ids
FROM agent_executions;

-- Check column existence
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'agent_executions'
  AND column_name IN ('id', 'messages_sent_count', 'messages_waiting_count', 'messages_read_count')
ORDER BY column_name;
```

---

## 8. Validation Queries

Run these after migration to verify success:

```sql
-- 1. Check all new columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'agent_executions'
  AND column_name IN ('id', 'messages_sent_count', 'messages_waiting_count', 'messages_read_count');

-- 2. Verify primary key changed
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'agent_executions'
  AND constraint_type = 'PRIMARY KEY';

-- 3. Check unique constraint exists
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_name = 'agent_executions'
  AND constraint_name = 'uq_agent_instance';

-- 4. Verify no duplicate agent instances
SELECT agent_id, instance_number, COUNT(*)
FROM agent_executions
GROUP BY agent_id, instance_number
HAVING COUNT(*) > 1;

-- 5. Check message counters are populated
SELECT
  COUNT(*) as total_rows,
  COUNT(*) FILTER (WHERE messages_sent_count > 0) as with_sent,
  COUNT(*) FILTER (WHERE messages_waiting_count > 0) as with_waiting,
  COUNT(*) FILTER (WHERE messages_read_count > 0) as with_read
FROM agent_executions;
```

---

## 9. Conclusion

**Production database (giljo_mcp) is significantly outdated** compared to test database (giljo_mcp_test). The primary issues are:

1. **Missing message counter architecture** (Handover 0387i)
2. **Outdated primary key design** (agent_id vs id)
3. **Missing data integrity constraints** (unique constraint on agent instances)
4. **3 missing tables** (sessions, template_augmentations, alembic_version)

**Recommended Path Forward**:
1. Add message counter columns immediately (blocking issue)
2. Plan primary key migration carefully (breaking change)
3. Test all migrations on development copy first
4. Validate application code works with new schema
5. Execute migration in production with backup

**Estimated Migration Complexity**: HIGH (4-6 hours with testing)
**Risk Level**: HIGH (breaking changes to primary key)
**Data Loss Risk**: MEDIUM (if migration fails partway through)

**ALWAYS BACKUP BEFORE MIGRATION.**
