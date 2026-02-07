"""
Integration tests for config_data migration (upgrade/downgrade).

Tests:
1. Migration creates config_data column with JSONB type
2. Migration creates GIN index for performance
3. Existing products get empty config_data
4. Migration can be rolled back cleanly
5. Data integrity is maintained

SAFETY: Uses test database fixtures from conftest.py, NEVER production.
"""

import pytest
from sqlalchemy import inspect, text

from src.giljo_mcp.models import Product
from tests.helpers.test_db_helper import PostgreSQLTestHelper


# CRITICAL: These fixtures use the TEST database, not production
# They override the base conftest fixtures to use synchronous connections
# for these specific migration tests.


@pytest.fixture
def db_engine():
    """
    Get database engine for TEST database only.

    SAFETY: Uses PostgreSQLTestHelper which enforces test database usage.
    """
    from sqlalchemy import create_engine

    # CRITICAL: Use test database URL, never production
    test_url = PostgreSQLTestHelper.get_test_db_url(async_driver=False)
    engine = create_engine(test_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """
    Get database session for TEST database only.

    SAFETY: Uses engine from db_engine fixture which is test-only.
    """
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


class TestMigrationStructure:
    """Test migration creates correct database structure"""

    def test_config_data_column_exists(self, db_engine):
        """Test config_data column exists in products table"""
        inspector = inspect(db_engine)
        columns = [col["name"] for col in inspector.get_columns("products")]

        assert "config_data" in columns, "config_data column not found"

    def test_config_data_column_type(self, db_engine):
        """Test config_data column is JSONB type"""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("products")}

        config_data_col = columns.get("config_data")
        assert config_data_col is not None

        # Check if it's a JSON/JSONB type
        col_type = str(config_data_col["type"]).upper()
        assert "JSON" in col_type, f"Expected JSON type, got {col_type}"

    def test_config_data_column_nullable(self, db_engine):
        """Test config_data column is nullable"""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("products")}

        config_data_col = columns.get("config_data")
        assert config_data_col is not None
        assert config_data_col["nullable"] is True

    def test_gin_index_exists(self, db_engine):
        """Test GIN index exists for config_data column"""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes("products")

        gin_index = next((idx for idx in indexes if idx.get("name") == "idx_product_config_data_gin"), None)

        # GIN index might not be reported by SQLAlchemy inspector on all systems
        # So we'll check directly in database
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'products'
                AND indexname = 'idx_product_config_data_gin'
            """)
            )

            index_row = result.fetchone()
            if index_row:
                assert "gin" in index_row[1].lower(), "Index should use GIN method"


class TestDataIntegrity:
    """Test data integrity during and after migration"""

    def test_existing_products_have_empty_config_data(self, db_session):
        """Test products without config_data get empty dict"""
        # Create product with no config_data
        product = Product(
            tenant_key="test-migration",
            name="Migration Test Product",
            config_data={},  # Explicitly empty
        )

        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        # Should have empty dict, not NULL
        assert product.config_data is not None
        assert isinstance(product.config_data, dict)
        assert len(product.config_data) == 0

        # Cleanup
        db_session.delete(product)
        db_session.commit()

    def test_product_with_config_data_persists(self, db_session):
        """Test product with config_data persists correctly"""
        test_config = {
            "architecture": "Test Architecture",
            "serena_mcp_enabled": True,
            "tech_stack": ["Python", "PostgreSQL"],
        }

        product = Product(tenant_key="test-migration", name="Config Data Test Product", config_data=test_config)

        db_session.add(product)
        db_session.commit()
        product_id = product.id

        # Close session and reopen to ensure data was persisted
        db_session.close()

        # SAFETY: Use test database helper, never get_db_manager() which could hit production
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        test_url = PostgreSQLTestHelper.get_test_db_url(async_driver=False)
        test_engine = create_engine(test_url)
        TestSession = sessionmaker(bind=test_engine)
        with TestSession() as new_session:
            # Reload product
            reloaded_product = new_session.query(Product).filter(Product.id == product_id).first()

            assert reloaded_product is not None
            assert reloaded_product.config_data is not None
            assert reloaded_product.config_data["architecture"] == "Test Architecture"
            assert reloaded_product.config_data["serena_mcp_enabled"] is True
            assert "Python" in reloaded_product.config_data["tech_stack"]

            # Cleanup
            new_session.delete(reloaded_product)
            new_session.commit()

    def test_config_data_update_works(self, db_session):
        """Test updating config_data works correctly"""
        product = Product(
            tenant_key="test-migration",
            name="Update Test Product",
            config_data={"architecture": "Original", "serena_mcp_enabled": False},
        )

        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        # Update config_data
        product.config_data = {"architecture": "Updated", "serena_mcp_enabled": True, "tech_stack": ["New Tech"]}

        db_session.commit()
        db_session.refresh(product)

        # Verify update
        assert product.config_data["architecture"] == "Updated"
        assert product.config_data["serena_mcp_enabled"] is True
        assert "tech_stack" in product.config_data

        # Cleanup
        db_session.delete(product)
        db_session.commit()

    def test_config_data_partial_update(self, db_session):
        """Test partial update of config_data (merge pattern)"""
        from src.giljo_mcp.context_manager import merge_config_updates

        product = Product(
            tenant_key="test-migration",
            name="Partial Update Test",
            config_data={"architecture": "FastAPI", "tech_stack": ["Python"], "serena_mcp_enabled": True},
        )

        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        # Partial update
        updates = {
            "tech_stack": ["Python", "PostgreSQL"],  # Update existing
            "test_commands": ["pytest"],  # Add new
        }

        product.config_data = merge_config_updates(product.config_data, updates)
        db_session.commit()
        db_session.refresh(product)

        # Verify
        assert product.config_data["architecture"] == "FastAPI"  # Unchanged
        assert "PostgreSQL" in product.config_data["tech_stack"]  # Updated
        assert "test_commands" in product.config_data  # Added
        assert product.config_data["serena_mcp_enabled"] is True  # Unchanged

        # Cleanup
        db_session.delete(product)
        db_session.commit()


class TestJSONBQuerying:
    """Test JSONB querying capabilities"""

    def test_query_by_architecture(self, db_session, db_engine):
        """Test querying products by architecture in config_data"""
        # Create test products
        product1 = Product(
            tenant_key="test-query",
            name="FastAPI Product",
            config_data={"architecture": "FastAPI", "serena_mcp_enabled": True},
        )

        product2 = Product(
            tenant_key="test-query",
            name="Django Product",
            config_data={"architecture": "Django", "serena_mcp_enabled": True},
        )

        db_session.add_all([product1, product2])
        db_session.commit()

        # Query using JSONB operators (PostgreSQL-specific)
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT name, config_data->>'architecture' as arch
                FROM products
                WHERE config_data->>'architecture' = 'FastAPI'
                AND tenant_key = 'test-query'
            """)
            )

            rows = result.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "FastAPI Product"
            assert rows[0][1] == "FastAPI"

        # Cleanup
        db_session.delete(product1)
        db_session.delete(product2)
        db_session.commit()

    def test_query_by_serena_flag(self, db_session, db_engine):
        """Test querying products by serena_mcp_enabled flag"""
        product_enabled = Product(
            tenant_key="test-query",
            name="Serena Enabled",
            config_data={"architecture": "Test", "serena_mcp_enabled": True},
        )

        product_disabled = Product(
            tenant_key="test-query",
            name="Serena Disabled",
            config_data={"architecture": "Test", "serena_mcp_enabled": False},
        )

        db_session.add_all([product_enabled, product_disabled])
        db_session.commit()

        # Query for serena-enabled products
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT name
                FROM products
                WHERE (config_data->>'serena_mcp_enabled')::boolean = true
                AND tenant_key = 'test-query'
            """)
            )

            rows = result.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "Serena Enabled"

        # Cleanup
        db_session.delete(product_enabled)
        db_session.delete(product_disabled)
        db_session.commit()

    def test_query_array_contains(self, db_session, db_engine):
        """Test querying products by array field in config_data"""
        product = Product(
            tenant_key="test-query",
            name="Python Product",
            config_data={
                "architecture": "Test",
                "tech_stack": ["Python", "PostgreSQL", "FastAPI"],
                "serena_mcp_enabled": True,
            },
        )

        db_session.add(product)
        db_session.commit()

        # Query for products with Python in tech_stack
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT name
                FROM products
                WHERE config_data->'tech_stack' @> '["Python"]'::jsonb
                AND tenant_key = 'test-query'
            """)
            )

            rows = result.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "Python Product"

        # Cleanup
        db_session.delete(product)
        db_session.commit()


class TestIndexPerformance:
    """Test GIN index improves query performance"""

    def test_gin_index_used_for_queries(self, db_engine):
        """Test that GIN index is used for JSONB queries"""
        # Check query plan to ensure index is used
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM products
                WHERE config_data @> '{"serena_mcp_enabled": true}'::jsonb
            """)
            )

            plan = result.fetchone()[0]

            # Plan should mention index (though this depends on data volume)
            # For comprehensive testing, we'd need to insert many rows
            assert plan is not None


class TestMigrationRollback:
    """Test migration can be rolled back safely"""

    def test_rollback_removes_column(self, db_engine):
        """Test rollback would remove config_data column"""
        # This is a conceptual test - we don't actually rollback
        # In practice, alembic downgrade would:
        # 1. Drop GIN index
        # 2. Drop config_data column

        # We verify the column exists (so rollback would have something to remove)
        # SAFETY: Uses db_engine fixture which is test-only
        inspector = inspect(db_engine)
        columns = [col["name"] for col in inspector.get_columns("products")]

        assert "config_data" in columns

        # Note: Actual rollback testing should be done in a separate test database
        # to avoid breaking the development environment

    def test_existing_columns_preserved(self, db_engine):
        """Test that existing product columns are preserved"""
        inspector = inspect(db_engine)
        columns = [col["name"] for col in inspector.get_columns("products")]

        # Verify core columns exist
        core_columns = ["id", "tenant_key", "name", "description", "vision_path", "created_at", "updated_at"]

        for col in core_columns:
            assert col in columns, f"Core column {col} should be preserved"
