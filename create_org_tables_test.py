"""
Create organization tables in test database.
Handover 0424a - Organization Database Schema
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def create_tables():
    # Test database URL
    database_url = "postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp_test"

    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        # Create organizations table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS organizations (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(100) NOT NULL UNIQUE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                settings JSONB NOT NULL DEFAULT '{}'::jsonb
            )
        """))
        print("Created organizations table")

        # Create org_memberships table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS org_memberships (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL DEFAULT 'member',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                invited_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                CONSTRAINT uq_org_membership_user UNIQUE (org_id, user_id),
                CONSTRAINT ck_org_membership_role CHECK (role IN ('owner', 'admin', 'member', 'viewer'))
            )
        """))
        print("Created org_memberships table")

        # Add org_id to products
        await conn.execute(text("""
            ALTER TABLE products ADD COLUMN IF NOT EXISTS org_id VARCHAR(36) REFERENCES organizations(id) ON DELETE SET NULL
        """))
        print("Added org_id to products")

        # Add org_id to agent_templates
        await conn.execute(text("""
            ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS org_id VARCHAR(36) REFERENCES organizations(id) ON DELETE SET NULL
        """))
        print("Added org_id to agent_templates")

        # Add org_id to tasks
        await conn.execute(text("""
            ALTER TABLE tasks ADD COLUMN IF NOT EXISTS org_id VARCHAR(36) REFERENCES organizations(id) ON DELETE SET NULL
        """))
        print("Added org_id to tasks")

        # Create indexes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_organizations_active ON organizations(is_active)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_org_memberships_org ON org_memberships(org_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_org_memberships_user ON org_memberships(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_org_memberships_role ON org_memberships(role)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_org_memberships_active ON org_memberships(is_active)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_org ON products(org_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_templates_org ON agent_templates(org_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_org ON tasks(org_id)"))
        print("Created indexes")

    await engine.dispose()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(create_tables())
