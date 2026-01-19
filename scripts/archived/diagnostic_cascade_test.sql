-- Diagnostic script to check CASCADE DELETE constraints on products table
-- Run with: psql -U postgres -d giljo_mcp -f diagnostic_cascade_test.sql

-- 1. Check foreign key constraints that reference products table
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

-- 2. Create a test product with related records
BEGIN;

DO $$
DECLARE
    test_product_id VARCHAR(36) := 'test-cascade-product-123';
    test_tenant VARCHAR(36) := 'test_cascade_tenant';
BEGIN
    -- Insert test product
    INSERT INTO products (id, tenant_key, name, description, vision_type, chunked)
    VALUES (test_product_id, test_tenant, 'Test Cascade Product', 'For testing CASCADE', 'none', false);

    -- Insert related project
    INSERT INTO projects (id, tenant_key, product_id, name, alias, description, mission, status)
    VALUES ('test-proj-123', test_tenant, test_product_id, 'Test Project', 'TST001', 'Test description', 'Test', 'active');

    -- Insert related task
    INSERT INTO tasks (id, tenant_key, product_id, project_id, title, status)
    VALUES ('test-task-123', test_tenant, test_product_id, 'test-proj-123', 'Test Task', 'pending');

    -- Insert related vision document
    INSERT INTO vision_documents (id, tenant_key, product_id, filename, document_type, content, display_order, chunked)
    VALUES ('test-vision-123', test_tenant, test_product_id, 'test.md', 'file', '# Test', 1, false);

    -- Insert related context chunk
    INSERT INTO mcp_context_index (tenant_key, chunk_id, product_id, vision_document_id, content, keywords, chunk_order, token_count)
    VALUES (test_tenant, 'test-chunk-123', test_product_id, 'test-vision-123', 'Test content', '["test"]', 1, 10);

    -- Show counts before deletion
    RAISE NOTICE '=== BEFORE DELETION ===';
    RAISE NOTICE 'Products: %', (SELECT COUNT(*) FROM products WHERE id = test_product_id);
    RAISE NOTICE 'Projects: %', (SELECT COUNT(*) FROM projects WHERE product_id = test_product_id);
    RAISE NOTICE 'Tasks: %', (SELECT COUNT(*) FROM tasks WHERE product_id = test_product_id);
    RAISE NOTICE 'Vision Docs: %', (SELECT COUNT(*) FROM vision_documents WHERE product_id = test_product_id);
    RAISE NOTICE 'Chunks: %', (SELECT COUNT(*) FROM mcp_context_index WHERE product_id = test_product_id);

    -- Attempt to delete product
    RAISE NOTICE '=== ATTEMPTING DELETION ===';
    BEGIN
        DELETE FROM products WHERE id = test_product_id;
        RAISE NOTICE 'Deletion succeeded!';
    EXCEPTION
        WHEN foreign_key_violation THEN
            RAISE NOTICE 'Deletion FAILED: Foreign key constraint violation!';
            RAISE NOTICE 'Error: %', SQLERRM;
        WHEN OTHERS THEN
            RAISE NOTICE 'Deletion FAILED: %', SQLERRM;
    END;

    -- Show counts after deletion attempt
    RAISE NOTICE '=== AFTER DELETION ATTEMPT ===';
    RAISE NOTICE 'Products: %', (SELECT COUNT(*) FROM products WHERE id = test_product_id);
    RAISE NOTICE 'Projects: %', (SELECT COUNT(*) FROM projects WHERE product_id = test_product_id);
    RAISE NOTICE 'Tasks: %', (SELECT COUNT(*) FROM tasks WHERE product_id = test_product_id);
    RAISE NOTICE 'Vision Docs: %', (SELECT COUNT(*) FROM vision_documents WHERE product_id = test_product_id);
    RAISE NOTICE 'Chunks: %', (SELECT COUNT(*) FROM mcp_context_index WHERE product_id = test_product_id);

END$$;

ROLLBACK;  -- Don't commit test data
