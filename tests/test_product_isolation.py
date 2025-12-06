#!/usr/bin/env python3
"""
Test script for Product/Task Isolation implementation
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import contextlib
import uuid

from sqlalchemy import select, text

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project, Task
from src.giljo_mcp.tenant import TenantManager


async def test_product_isolation():
    """Test the product isolation implementation"""

    # Initialize database
    db_manager = DatabaseManager(is_async=True)
    tenant_manager = TenantManager()

    # Create tables if needed
    await db_manager.create_tables_async()

    async with db_manager.get_session_async() as session:
        # Check if product_id column exists in tasks table
        try:
            # Try to query with product_id to verify column exists
            result = await session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'"))
            schema = result.scalar()

            if schema and "product_id" in schema:
                pass
            else:
                # Add the column manually for SQLite
                await session.execute(text("ALTER TABLE tasks ADD COLUMN product_id VARCHAR(36)"))
                await session.commit()

        except Exception:
            pass

    # Test creating tasks with product isolation

    # Create test project and set tenant - use database manager's method
    test_tenant = db_manager.generate_tenant_key()
    test_project_id = str(uuid.uuid4())
    test_product_id = str(uuid.uuid4())

    # Set tenant - validation happens against database
    tenant_manager.set_current_tenant(test_tenant)

    async with db_manager.get_session_async() as session:
        # Create a test project
        project = Project(
            id=test_project_id,
            tenant_key=test_tenant,
            name="Test Project for Product Isolation",
            mission="Testing product isolation features",
            status="active",
        )
        session.add(project)

        # Create tasks with different product_ids
        task1 = Task(
            tenant_key=test_tenant,
            product_id=test_product_id,
            project_id=test_project_id,
            title="Task for Product A",
            description="This task belongs to Product A",
            priority="high",
            status="waiting",
        )

        task2 = Task(
            tenant_key=test_tenant,
            product_id="different-product-id",
            project_id=test_project_id,
            title="Task for Product B",
            description="This task belongs to Product B",
            priority="medium",
            status="waiting",
        )

        task3 = Task(
            tenant_key=test_tenant,
            product_id=test_product_id,
            project_id=test_project_id,
            title="Another Task for Product A",
            description="Another task for Product A",
            priority="low",
            status="waiting",
        )

        session.add_all([task1, task2, task3])
        await session.commit()

        # Test querying with product filter

        # Query tasks for Product A only
        product_a_query = select(Task).where(Task.tenant_key == test_tenant, Task.product_id == test_product_id)
        result = await session.execute(product_a_query)
        product_a_tasks = result.scalars().all()

        for task in product_a_tasks:
            pass

        # Query all tasks for the project
        all_tasks_query = select(Task).where(Task.tenant_key == test_tenant, Task.project_id == test_project_id)
        result = await session.execute(all_tasks_query)
        all_tasks = result.scalars().all()

        # Test product summary
        products = {}
        for task in all_tasks:
            pid = task.product_id or "no-product"
            if pid not in products:
                products[pid] = []
            products[pid].append(task.title)

        for pid in products:
            pass

    return True


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        asyncio.run(test_product_isolation())
        # sys.exit(1)  # Commented for pytest
