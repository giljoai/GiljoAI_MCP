"""
Migration script: Create organizations for existing users.

Handover 0424e: Data migration for organization hierarchy.

This script:
1. Creates a personal organization for each existing user
2. Sets the user as owner of their organization
3. Assigns all user's products to their organization
4. Sets org_id on all user's templates
5. Sets org_id on all user's tasks

SAFE TO RUN MULTIPLE TIMES (idempotent)
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from config or environment."""
    import os

    # Try environment variable first
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Ensure asyncpg driver for async support
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return db_url

    # Try using ConfigManager (preferred method)
    try:
        from src.giljo_mcp.config_manager import get_config
        config = get_config()
        url = config.get_database_url()
        # Ensure asyncpg driver for async support
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    except Exception as e:
        logger.warning(f"Failed to get URL from ConfigManager: {e}")

    # Try config.yaml manually
    config_path = project_root / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                db_config = config.get("database", {})

                host = db_config.get("host", "localhost")
                port = db_config.get("port", 5432)
                database = db_config.get("name", db_config.get("database", "giljo_mcp"))
                user = db_config.get("user", "postgres")
                password = db_config.get("password", "") or os.getenv("DB_PASSWORD", "")

                return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        except Exception:
            pass

    # Default
    return "postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp"


async def create_org_for_user(session: AsyncSession, user) -> "Organization":
    """Create personal organization for user if not exists."""
    from src.giljo_mcp.models.organizations import Organization, OrgMembership

    # Check if user already has an org as owner
    stmt = select(OrgMembership).where(
        OrgMembership.user_id == user.id,
        OrgMembership.role == "owner"
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # User already has an org, fetch and return it
        org_stmt = select(Organization).where(Organization.id == existing.org_id)
        org_result = await session.execute(org_stmt)
        org = org_result.scalar_one()
        logger.info(f"User '{user.username}' already has org '{org.slug}' - skipping creation")
        return org

    # Create new org
    slug = f"{user.username}-workspace"

    # Handle slug collision
    counter = 1
    original_slug = slug
    while True:
        check_stmt = select(Organization).where(Organization.slug == slug)
        check_result = await session.execute(check_stmt)
        if not check_result.scalar_one_or_none():
            break
        slug = f"{original_slug}-{counter}"
        counter += 1

    org = Organization(
        name=f"{user.username}'s Workspace",
        slug=slug
    )
    session.add(org)
    await session.flush()  # Get org.id

    # Create owner membership
    membership = OrgMembership(
        org_id=org.id,
        user_id=user.id,
        role="owner"
    )
    session.add(membership)

    logger.info(f"Created org '{org.slug}' for user '{user.username}'")

    return org


async def assign_products_to_org(
    session: AsyncSession,
    user,
    org
) -> int:
    """Assign user's products to their organization."""
    from src.giljo_mcp.models.products import Product

    stmt = update(Product).where(
        Product.tenant_key == user.tenant_key,
        Product.org_id.is_(None)  # Only update if not already set
    ).values(org_id=org.id)

    result = await session.execute(stmt)
    count = result.rowcount

    if count > 0:
        logger.info(f"Assigned {count} products to org '{org.slug}'")

    return count


async def assign_templates_to_org(
    session: AsyncSession,
    user,
    org
) -> int:
    """Assign user's templates to their organization."""
    from src.giljo_mcp.models.templates import AgentTemplate

    stmt = update(AgentTemplate).where(
        AgentTemplate.tenant_key == user.tenant_key,
        AgentTemplate.org_id.is_(None)
    ).values(org_id=org.id)

    result = await session.execute(stmt)
    count = result.rowcount

    if count > 0:
        logger.info(f"Assigned {count} templates to org '{org.slug}'")

    return count


async def assign_tasks_to_org(
    session: AsyncSession,
    user,
    org
) -> int:
    """Assign user's tasks to their organization."""
    from src.giljo_mcp.models.tasks import Task

    stmt = update(Task).where(
        Task.tenant_key == user.tenant_key,
        Task.org_id.is_(None)
    ).values(org_id=org.id)

    result = await session.execute(stmt)
    count = result.rowcount

    if count > 0:
        logger.info(f"Assigned {count} tasks to org '{org.slug}'")

    return count


async def run_migration():
    """Run full migration for all users."""
    from src.giljo_mcp.models.auth import User

    db_url = get_database_url()
    logger.info(f"Connecting to database...")

    engine = create_async_engine(db_url, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        # Get all users
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()

        logger.info(f"Found {len(users)} users to process")

        if len(users) == 0:
            logger.warning("No users found - nothing to migrate")
            return {"users_processed": 0, "orgs_created": 0, "products_assigned": 0, "templates_assigned": 0, "tasks_assigned": 0}

        stats = {
            "users_processed": 0,
            "orgs_created": 0,
            "products_assigned": 0,
            "templates_assigned": 0,
            "tasks_assigned": 0
        }

        for user in users:
            logger.info(f"Processing user: {user.username} (tenant: {user.tenant_key})")

            # Create org
            org = await create_org_for_user(session, user)
            stats["orgs_created"] += 1

            # Assign products
            stats["products_assigned"] += await assign_products_to_org(session, user, org)

            # Assign templates
            stats["templates_assigned"] += await assign_templates_to_org(session, user, org)

            # Assign tasks
            stats["tasks_assigned"] += await assign_tasks_to_org(session, user, org)

            stats["users_processed"] += 1

        await session.commit()

        logger.info("Migration complete!")
        logger.info(f"Stats: {stats}")

        return stats

    await engine.dispose()


async def verify_migration():
    """Verify migration results."""
    from src.giljo_mcp.models.auth import User
    from src.giljo_mcp.models.organizations import Organization, OrgMembership
    from src.giljo_mcp.models.products import Product
    from src.giljo_mcp.models.templates import AgentTemplate
    from src.giljo_mcp.models.tasks import Task

    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        # Check users without orgs
        users_without_orgs = await session.execute(
            select(User).where(
                ~User.id.in_(
                    select(OrgMembership.user_id).where(OrgMembership.role == "owner")
                )
            )
        )
        orphan_users = users_without_orgs.scalars().all()

        # Check products without org_id
        orphan_products = await session.execute(
            select(Product).where(Product.org_id.is_(None))
        )
        orphan_products_count = len(orphan_products.scalars().all())

        # Check templates without org_id
        orphan_templates = await session.execute(
            select(AgentTemplate).where(AgentTemplate.org_id.is_(None))
        )
        orphan_templates_count = len(orphan_templates.scalars().all())

        # Check tasks without org_id
        orphan_tasks = await session.execute(
            select(Task).where(Task.org_id.is_(None))
        )
        orphan_tasks_count = len(orphan_tasks.scalars().all())

        # Count orgs and memberships
        org_count = await session.execute(select(Organization))
        membership_count = await session.execute(select(OrgMembership))

        print("\n=== VERIFICATION RESULTS ===")
        print(f"Organizations created: {len(org_count.scalars().all())}")
        print(f"Memberships created: {len(membership_count.scalars().all())}")
        print(f"Users without orgs: {len(orphan_users)}")
        print(f"Products without org_id: {orphan_products_count}")
        print(f"Templates without org_id: {orphan_templates_count}")
        print(f"Tasks without org_id: {orphan_tasks_count}")

        if len(orphan_users) == 0 and orphan_products_count == 0 and orphan_templates_count == 0 and orphan_tasks_count == 0:
            print("\nMIGRATION SUCCESSFUL - All data assigned to organizations!")
            return True
        else:
            print("\nWARNING: Some data not migrated. Check above for details.")
            return False

    await engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate existing users to organizations")
    parser.add_argument("--verify", action="store_true", help="Only verify migration status")
    args = parser.parse_args()

    if args.verify:
        asyncio.run(verify_migration())
    else:
        asyncio.run(run_migration())
        asyncio.run(verify_migration())
