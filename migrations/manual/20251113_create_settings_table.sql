-- Manual Migration: Create Settings Table
-- Date: 2025-11-13
-- Handover: 0506 (Settings Endpoints)
-- Reason: CCW implementation didn't include database migration
-- Applied: Yes (2025-11-13 via psql)

-- Create settings table for tenant-scoped system settings
CREATE TABLE IF NOT EXISTS settings (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_key VARCHAR(36) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'general', 'network', 'database'
    settings_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_settings_tenant_category UNIQUE(tenant_key, category)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_settings_tenant ON settings(tenant_key);
CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);

-- Verification query
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'settings'
-- ORDER BY ordinal_position;
