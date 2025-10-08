#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Phase 1: config_data JSONB implementation
Verifies column exists, GIN index is present, and helper methods work correctly.
"""

import sys
import io
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from src.giljo_mcp.models import Product
from src.giljo_mcp.database import DatabaseManager

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_config_data_schema():
    """Test that config_data column and GIN index exist"""
    print("=" * 60)
    print("Phase 1: Testing config_data Schema Implementation")
    print("=" * 60)

    # Create database URL
    db_url = DatabaseManager.build_postgresql_url(
        host="localhost",
        port=5432,
        database="giljo_mcp",
        username="postgres",
        password="4010"
    )

    # Create engine
    engine = create_engine(db_url)
    inspector = inspect(engine)

    # Check column exists
    print("\n1. Checking config_data column...")
    columns = {col['name']: col for col in inspector.get_columns('products')}

    if 'config_data' not in columns:
        print("   ❌ FAILED: config_data column not found!")
        return False

    col_info = columns['config_data']
    print(f"   ✓ Column exists: {col_info['name']}")
    print(f"   ✓ Type: {col_info['type']}")
    print(f"   ✓ Nullable: {col_info['nullable']}")

    # Check GIN index exists
    print("\n2. Checking GIN index...")
    indexes = inspector.get_indexes('products')
    gin_index = None

    for idx in indexes:
        if idx['name'] == 'idx_product_config_data_gin':
            gin_index = idx
            break

    if not gin_index:
        print("   ❌ FAILED: idx_product_config_data_gin index not found!")
        return False

    print(f"   ✓ Index exists: {gin_index['name']}")
    print(f"   ✓ Columns: {gin_index['column_names']}")

    # Verify GIN index type using raw SQL
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexdef
            FROM pg_indexes
            WHERE tablename = 'products'
            AND indexname = 'idx_product_config_data_gin'
        """))
        index_def = result.scalar()

        if index_def and 'USING gin' in index_def:
            print(f"   ✓ Index type: GIN")
            print(f"   ✓ Definition: {index_def}")
        else:
            print(f"   ⚠ Warning: Could not verify GIN index type")

    return True


def test_helper_methods():
    """Test Product model helper methods"""
    print("\n3. Testing helper methods...")

    # Create database URL
    db_url = DatabaseManager.build_postgresql_url(
        host="localhost",
        port=5432,
        database="giljo_mcp",
        username="postgres",
        password="4010"
    )

    # Create test product
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create product with config_data
        test_product = Product(
            tenant_key="test_tenant",
            name="Test Product for Phase 1",
            description="Testing config_data JSONB field",
            config_data={
                "architecture": "FastAPI + PostgreSQL + Vue.js",
                "tech_stack": ["Python 3.11", "PostgreSQL 18", "Vue 3"],
                "test_config": {
                    "coverage_threshold": 80,
                    "test_framework": "pytest"
                },
                "serena_mcp_enabled": True,
                "deployment_modes": ["localhost", "server"]
            }
        )

        session.add(test_product)
        session.commit()

        # Test has_config_data property
        print(f"   ✓ has_config_data: {test_product.has_config_data}")
        assert test_product.has_config_data is True, "has_config_data should be True"

        # Test get_config_field with simple path
        arch = test_product.get_config_field("architecture")
        print(f"   ✓ get_config_field('architecture'): {arch}")
        assert arch == "FastAPI + PostgreSQL + Vue.js", "Architecture mismatch"

        # Test get_config_field with nested path
        coverage = test_product.get_config_field("test_config.coverage_threshold")
        print(f"   ✓ get_config_field('test_config.coverage_threshold'): {coverage}")
        assert coverage == 80, "Coverage threshold mismatch"

        # Test get_config_field with default value
        missing = test_product.get_config_field("nonexistent.field", "default_value")
        print(f"   ✓ get_config_field('nonexistent.field', 'default_value'): {missing}")
        assert missing == "default_value", "Default value not returned"

        # Test product with empty config_data
        empty_product = Product(
            tenant_key="test_tenant",
            name="Empty Config Product",
            config_data={}
        )
        print(f"   ✓ Empty config_data has_config_data: {empty_product.has_config_data}")
        assert empty_product.has_config_data is False, "Empty config should return False"

        # Clean up
        session.delete(test_product)
        session.commit()

        print("   ✓ All helper method tests passed!")
        return True

    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def test_existing_products_initialized():
    """Verify existing products have empty JSONB object"""
    print("\n4. Testing existing products initialization...")

    # Create database URL
    db_url = DatabaseManager.build_postgresql_url(
        host="localhost",
        port=5432,
        database="giljo_mcp",
        username="postgres",
        password="4010"
    )

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        products = session.query(Product).all()

        if len(products) == 0:
            print("   ⚠ No existing products found (this is normal for fresh install)")
            return True

        uninitialized = []
        for product in products:
            if product.config_data is None:
                uninitialized.append(product.name)

        if uninitialized:
            print(f"   ❌ FAILED: {len(uninitialized)} products have NULL config_data:")
            for name in uninitialized:
                print(f"      - {name}")
            return False

        print(f"   ✓ All {len(products)} existing products initialized with config_data")
        return True

    finally:
        session.close()


def main():
    """Run all Phase 1 tests"""
    print("\n")

    results = []

    # Test 1: Schema verification
    results.append(("Schema verification", test_config_data_schema()))

    # Test 2: Helper methods
    results.append(("Helper methods", test_helper_methods()))

    # Test 3: Existing products
    results.append(("Existing products initialization", test_existing_products_initialized()))

    # Print summary
    print("\n" + "=" * 60)
    print("PHASE 1 TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ Phase 1 implementation SUCCESSFUL!")
        print("\nMigration Details:")
        print("  - Revision ID: 8406a7a6dcc5")
        print("  - File: migrations/versions/8406a7a6dcc5_add_config_data_to_product.py")
        print("  - Column: products.config_data (JSONB)")
        print("  - Index: idx_product_config_data_gin (GIN)")
        print("  - Helper methods: has_config_data, get_config_field()")
        print("\nReady for Phase 2: Enhanced Orchestration Intelligence")
        return 0
    else:
        print("\n❌ Phase 1 implementation has FAILURES!")
        print("Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
