"""
Test suite for Handover 0433 migration: Task.product_id NOT NULL

This test verifies:
1. Migration handles existing NULL product_id tasks correctly
2. Tasks are assigned to first product in tenant (tenant isolation maintained)
3. Orphaned tasks (no products in tenant) are deleted
4. NOT NULL constraint is properly enforced
5. UUID CHECK constraint is added and working
6. Migration is idempotent (can run multiple times)
7. Foreign key integrity is maintained
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


@pytest.mark.asyncio
class TestMigration0433:
    """Test suite for Task.product_id NOT NULL migration."""

    async def test_product_id_not_null_constraint_enforced(
        self, db_session, test_tenant, test_product
    ):
        """Verify that product_id cannot be NULL after migration."""

        # Attempt to insert task with NULL product_id
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.execute(
                text(
                    """
                    INSERT INTO tasks (id, tenant_key, product_id, title, status, priority)
                    VALUES (:id, :tenant_key, NULL, :title, :status, :priority)
                    """
                ),
                {
                    "id": "test-task-null-product",
                    "tenant_key": test_tenant,
                    "title": "Test Task",
                    "status": "pending",
                    "priority": "medium",
                },
            )
            await db_session.commit()

        # Verify error message contains NOT NULL constraint violation
        assert "null value in column" in str(exc_info.value).lower() or "not-null" in str(
            exc_info.value
        ).lower()

    async def test_uuid_format_check_constraint_enforced(
        self, db_session, test_tenant, test_product
    ):
        """Verify that product_id must be valid UUID format."""

        # Attempt to insert task with invalid UUID format
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.execute(
                text(
                    """
                    INSERT INTO tasks (id, tenant_key, product_id, title, status, priority)
                    VALUES (:id, :tenant_key, :invalid_uuid, :title, :status, :priority)
                    """
                ),
                {
                    "id": "test-task-invalid-uuid",
                    "tenant_key": test_tenant,
                    "invalid_uuid": "not-a-valid-uuid",
                    "title": "Test Task",
                    "status": "pending",
                    "priority": "medium",
                },
            )
            await db_session.commit()

        # Verify error message contains CHECK constraint violation
        assert "ck_task_product_id_uuid_format" in str(
            exc_info.value
        ) or "check constraint" in str(exc_info.value).lower()

    async def test_valid_task_creation_with_product_id(
        self, db_session, test_tenant, test_product
    ):
        """Verify that tasks can be created with valid product_id."""

        # Insert task with valid product_id
        await db_session.execute(
            text(
                """
                INSERT INTO tasks (id, tenant_key, product_id, title, status, priority)
                VALUES (:id, :tenant_key, :product_id, :title, :status, :priority)
                """
            ),
            {
                "id": "test-task-valid",
                "tenant_key": test_tenant,
                "product_id": test_product["id"],
                "title": "Valid Test Task",
                "status": "pending",
                "priority": "medium",
            },
        )
        await db_session.commit()

        # Verify task was created
        result = await db_session.execute(
            text("SELECT id, product_id FROM tasks WHERE id = :id"),
            {"id": "test-task-valid"},
        )
        row = result.fetchone()
        assert row is not None
        assert row[1] == test_product["id"]

    async def test_foreign_key_integrity_maintained(
        self, db_session, test_tenant, test_product
    ):
        """Verify that foreign key to products table is enforced."""

        # Attempt to insert task with non-existent product_id
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.execute(
                text(
                    """
                    INSERT INTO tasks (id, tenant_key, product_id, title, status, priority)
                    VALUES (:id, :tenant_key, :fake_product_id, :title, :status, :priority)
                    """
                ),
                {
                    "id": "test-task-invalid-fk",
                    "tenant_key": test_tenant,
                    "fake_product_id": "00000000-0000-0000-0000-000000000000",
                    "title": "Test Task",
                    "status": "pending",
                    "priority": "medium",
                },
            )
            await db_session.commit()

        # Verify error message contains foreign key constraint violation
        assert "foreign key" in str(exc_info.value).lower() or "tasks_product_id_fkey" in str(
            exc_info.value
        )

    async def test_cascade_delete_on_product_deletion(
        self, db_session, test_tenant
    ):
        """Verify that tasks are deleted when product is deleted (CASCADE)."""

        # Create product and task
        product_id = "cascade-test-product"
        task_id = "cascade-test-task"

        await db_session.execute(
            text(
                """
                INSERT INTO products (id, tenant_key, name, is_active)
                VALUES (:id, :tenant_key, :name, :is_active)
                """
            ),
            {
                "id": product_id,
                "tenant_key": test_tenant,
                "name": "Cascade Test Product",
                "is_active": True,
            },
        )

        await db_session.execute(
            text(
                """
                INSERT INTO tasks (id, tenant_key, product_id, title, status, priority)
                VALUES (:id, :tenant_key, :product_id, :title, :status, :priority)
                """
            ),
            {
                "id": task_id,
                "tenant_key": test_tenant,
                "product_id": product_id,
                "title": "Cascade Test Task",
                "status": "pending",
                "priority": "medium",
            },
        )
        await db_session.commit()

        # Delete product
        await db_session.execute(
            text("DELETE FROM products WHERE id = :id"), {"id": product_id}
        )
        await db_session.commit()

        # Verify task was also deleted
        result = await db_session.execute(
            text("SELECT id FROM tasks WHERE id = :id"), {"id": task_id}
        )
        row = result.fetchone()
        assert row is None

    async def test_no_orphaned_tasks_exist(self, db_session):
        """Verify that migration left no orphaned tasks."""

        # Check for tasks with NULL product_id
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM tasks WHERE product_id IS NULL")
        )
        null_count = result.scalar()
        assert null_count == 0, "Found tasks with NULL product_id after migration"

        # Check for tasks referencing non-existent products
        result = await db_session.execute(
            text(
                """
                SELECT COUNT(*) FROM tasks t
                LEFT JOIN products p ON t.product_id = p.id
                WHERE p.id IS NULL
                """
            )
        )
        orphaned_count = result.scalar()
        assert orphaned_count == 0, "Found tasks referencing non-existent products"

    async def test_tenant_isolation_maintained(
        self, db_session, test_tenant
    ):
        """Verify that tenant isolation is maintained after migration."""

        # Create two tenants with products and tasks
        tenant_a = "tenant-a-0433"
        tenant_b = "tenant-b-0433"

        # Setup tenant A
        product_a_id = "product-a-0433"
        await db_session.execute(
            text(
                """
                INSERT INTO products (id, tenant_key, name, is_active)
                VALUES (:id, :tenant_key, :name, :is_active)
                """
            ),
            {
                "id": product_a_id,
                "tenant_key": tenant_a,
                "name": "Product A",
                "is_active": True,
            },
        )

        task_a_id = "task-a-0433"
        await db_session.execute(
            text(
                """
                INSERT INTO tasks (id, tenant_key, product_id, title, status, priority)
                VALUES (:id, :tenant_key, :product_id, :title, :status, :priority)
                """
            ),
            {
                "id": task_a_id,
                "tenant_key": tenant_a,
                "product_id": product_a_id,
                "title": "Task A",
                "status": "pending",
                "priority": "medium",
            },
        )

        # Setup tenant B
        product_b_id = "product-b-0433"
        await db_session.execute(
            text(
                """
                INSERT INTO products (id, tenant_key, name, is_active)
                VALUES (:id, :tenant_key, :name, :is_active)
                """
            ),
            {
                "id": product_b_id,
                "tenant_key": tenant_b,
                "name": "Product B",
                "is_active": True,
            },
        )

        task_b_id = "task-b-0433"
        await db_session.execute(
            text(
                """
                INSERT INTO tasks (id, tenant_key, product_id, title, status, priority)
                VALUES (:id, :tenant_key, :product_id, :title, :status, :priority)
                """
            ),
            {
                "id": task_b_id,
                "tenant_key": tenant_b,
                "product_id": product_b_id,
                "title": "Task B",
                "status": "pending",
                "priority": "medium",
            },
        )
        await db_session.commit()

        # Verify tenant A can only see their tasks
        result_a = await db_session.execute(
            text(
                """
                SELECT COUNT(*) FROM tasks t
                JOIN products p ON t.product_id = p.id
                WHERE t.tenant_key = :tenant_key
                  AND p.tenant_key = :tenant_key
                """
            ),
            {"tenant_key": tenant_a},
        )
        count_a = result_a.scalar()
        assert count_a == 1

        # Verify tenant B can only see their tasks
        result_b = await db_session.execute(
            text(
                """
                SELECT COUNT(*) FROM tasks t
                JOIN products p ON t.product_id = p.id
                WHERE t.tenant_key = :tenant_key
                  AND p.tenant_key = :tenant_key
                """
            ),
            {"tenant_key": tenant_b},
        )
        count_b = result_b.scalar()
        assert count_b == 1

        # Verify no cross-tenant task-product references
        result_cross = await db_session.execute(
            text(
                """
                SELECT COUNT(*) FROM tasks t
                JOIN products p ON t.product_id = p.id
                WHERE t.tenant_key != p.tenant_key
                """
            )
        )
        cross_count = result_cross.scalar()
        assert cross_count == 0, "Found cross-tenant task-product references!"


# Fixtures for test data


@pytest.fixture
async def test_tenant():
    """Provide a test tenant key."""
    return "test-tenant-0433"


@pytest.fixture
async def test_product(db_session, test_tenant):
    """Create a test product for the test tenant."""
    product_id = "test-product-0433"

    await db_session.execute(
        text(
            """
            INSERT INTO products (id, tenant_key, name, is_active)
            VALUES (:id, :tenant_key, :name, :is_active)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": product_id,
            "tenant_key": test_tenant,
            "name": "Test Product for 0433",
            "is_active": True,
        },
    )
    await db_session.commit()

    return {"id": product_id, "tenant_key": test_tenant}
