-- Fix for Product Deletion Bug
-- Adds CASCADE DELETE to foreign keys referencing products table
--
-- Run with: psql -U postgres -d giljo_mcp -f fix_product_cascade.sql
--
-- SAFE TO RUN: This script preserves all existing data

BEGIN;

-- 1. Fix projects.product_id foreign key
ALTER TABLE projects
  DROP CONSTRAINT IF EXISTS projects_product_id_fkey CASCADE,
  ADD CONSTRAINT projects_product_id_fkey
    FOREIGN KEY (product_id)
    REFERENCES products(id)
    ON DELETE CASCADE;

-- 2. Fix tasks.product_id foreign key
ALTER TABLE tasks
  DROP CONSTRAINT IF EXISTS tasks_product_id_fkey CASCADE,
  ADD CONSTRAINT tasks_product_id_fkey
    FOREIGN KEY (product_id)
    REFERENCES products(id)
    ON DELETE CASCADE;

-- 3. Fix mcp_context_index.product_id foreign key
ALTER TABLE mcp_context_index
  DROP CONSTRAINT IF EXISTS mcp_context_index_product_id_fkey CASCADE,
  ADD CONSTRAINT mcp_context_index_product_id_fkey
    FOREIGN KEY (product_id)
    REFERENCES products(id)
    ON DELETE CASCADE;

-- 4. Verify the changes
SELECT
    tc.table_name,
    kcu.column_name,
    rc.delete_rule AS cascade_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'products'
ORDER BY tc.table_name, kcu.column_name;

-- Show confirmation message
DO $$
BEGIN
    RAISE NOTICE '✓ Fixed CASCADE constraints on foreign keys';
    RAISE NOTICE '✓ projects.product_id -> CASCADE';
    RAISE NOTICE '✓ tasks.product_id -> CASCADE';
    RAISE NOTICE '✓ mcp_context_index.product_id -> CASCADE';
    RAISE NOTICE 'Product deletion will now work correctly!';
END$$;

COMMIT;
