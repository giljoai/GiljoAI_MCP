-- Migration: Rename setup_state.completed to database_initialized
-- Author: Database Expert Agent
-- Date: 2025-10-11
-- Purpose: Improve semantic clarity - 'completed' is confusing because it's set
--          when database tables are created (by install.py), not when setup wizard
--          is completed. New name 'database_initialized' accurately reflects this.
--
-- IMPORTANT: This migration is for existing databases only.
--            Fresh installations via install.py will use the new names automatically.
--
-- Database: PostgreSQL 18
-- Target Database: giljo_mcp
-- Password: 4010 (development)

-- ============================================================================
-- FORWARD MIGRATION
-- ============================================================================

BEGIN;

-- Step 1: Rename columns
ALTER TABLE setup_state
    RENAME COLUMN completed TO database_initialized;

ALTER TABLE setup_state
    RENAME COLUMN completed_at TO database_initialized_at;

-- Step 2: Update constraint
-- Drop the old constraint
ALTER TABLE setup_state
    DROP CONSTRAINT IF EXISTS ck_completed_at_required;

-- Add the new constraint with updated logic
ALTER TABLE setup_state
    ADD CONSTRAINT ck_database_initialized_at_required
    CHECK (
        (database_initialized = false) OR
        (database_initialized = true AND database_initialized_at IS NOT NULL)
    );

-- Step 3: Rename indexes
ALTER INDEX IF EXISTS idx_setup_completed
    RENAME TO idx_setup_database_initialized;

ALTER INDEX IF EXISTS idx_setup_incomplete
    RENAME TO idx_setup_database_incomplete;

-- Step 4: Update comments for clarity
COMMENT ON COLUMN setup_state.database_initialized IS
    'True when database tables have been created by installer (NOT setup wizard completion)';

COMMENT ON COLUMN setup_state.database_initialized_at IS
    'Timestamp when database tables were created and initialized';

-- Verify changes
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'setup_state'
    AND column_name IN ('database_initialized', 'database_initialized_at')
ORDER BY ordinal_position;

COMMIT;

-- ============================================================================
-- ROLLBACK MIGRATION (run only if needed to revert)
-- ============================================================================

-- Uncomment the following block to rollback:
/*
BEGIN;

-- Step 1: Rename columns back
ALTER TABLE setup_state
    RENAME COLUMN database_initialized TO completed;

ALTER TABLE setup_state
    RENAME COLUMN database_initialized_at TO completed_at;

-- Step 2: Update constraint back
ALTER TABLE setup_state
    DROP CONSTRAINT IF EXISTS ck_database_initialized_at_required;

ALTER TABLE setup_state
    ADD CONSTRAINT ck_completed_at_required
    CHECK (
        (completed = false) OR
        (completed = true AND completed_at IS NOT NULL)
    );

-- Step 3: Rename indexes back
ALTER INDEX IF EXISTS idx_setup_database_initialized
    RENAME TO idx_setup_completed;

ALTER INDEX IF EXISTS idx_setup_database_incomplete
    RENAME TO idx_setup_incomplete;

-- Step 4: Remove comments
COMMENT ON COLUMN setup_state.completed IS NULL;
COMMENT ON COLUMN setup_state.completed_at IS NULL;

COMMIT;
*/

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check table structure
\d setup_state

-- Check constraints
SELECT
    con.conname AS constraint_name,
    pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
WHERE rel.relname = 'setup_state'
    AND con.conname LIKE '%database_initialized%';

-- Check indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'setup_state'
    AND indexname LIKE '%database_initialized%';

-- Check sample data
SELECT
    id,
    tenant_key,
    database_initialized,
    database_initialized_at,
    default_password_active,
    created_at
FROM setup_state
LIMIT 5;
