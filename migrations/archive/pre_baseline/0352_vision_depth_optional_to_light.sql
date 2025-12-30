-- Migration: Update vision_documents depth from 'optional' to 'light'
-- Handover: 0352_vision_document_depth_refactor.md
-- Date: 2025-12-15
--
-- Purpose: Convert deprecated 'optional' depth value to new default 'light' value
--          for all existing users in the database.
--
-- Safety:
--   - Uses JSONB operations (PostgreSQL 9.4+)
--   - Only updates users with depth_config containing 'optional'
--   - Preserves all other depth_config values
--   - Multi-tenant safe (operates on all tenants)
--
-- Execution:
--   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -f migrations/0352_vision_depth_optional_to_light.sql

BEGIN;

-- Update users with 'optional' vision_documents depth to 'light'
UPDATE users
SET depth_config = jsonb_set(depth_config, '{vision_documents}', '"light"')
WHERE
    depth_config IS NOT NULL
    AND depth_config->>'vision_documents' = 'optional';

-- Verify the migration
DO $$
DECLARE
    remaining_optional_count INT;
    updated_to_light_count INT;
BEGIN
    -- Check if any 'optional' values remain
    SELECT COUNT(*) INTO remaining_optional_count
    FROM users
    WHERE depth_config IS NOT NULL
      AND depth_config->>'vision_documents' = 'optional';

    -- Count users now using 'light'
    SELECT COUNT(*) INTO updated_to_light_count
    FROM users
    WHERE depth_config IS NOT NULL
      AND depth_config->>'vision_documents' = 'light';

    -- Log results
    RAISE NOTICE 'Migration 0352 Results:';
    RAISE NOTICE '  - Remaining "optional" values: %', remaining_optional_count;
    RAISE NOTICE '  - Total users with "light": %', updated_to_light_count;

    -- Ensure no 'optional' values remain
    IF remaining_optional_count > 0 THEN
        RAISE EXCEPTION 'Migration incomplete: % users still have vision_documents = "optional"', remaining_optional_count;
    END IF;

    RAISE NOTICE 'Migration 0352 completed successfully!';
END $$;

COMMIT;

-- Post-migration verification query (optional, for manual inspection)
-- Uncomment to run:
-- SELECT
--     id,
--     username,
--     tenant_key,
--     depth_config->>'vision_documents' AS vision_depth,
--     depth_config
-- FROM users
-- WHERE depth_config IS NOT NULL
-- ORDER BY username;
