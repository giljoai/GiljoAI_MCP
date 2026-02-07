"""
Verification script for Handover 0433 migration: Task.product_id NOT NULL

This script verifies the migration was successful by checking:
1. product_id column is NOT NULL
2. UUID CHECK constraint exists
3. No tasks with NULL product_id
4. Foreign key integrity maintained
5. Cascade delete is configured correctly

Run with: python tests/migrations/verify_0433_migration.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import text
from dotenv import load_dotenv

# Load environment
load_dotenv()

from giljo_mcp.database import DatabaseManager

# ASCII-only symbols for Windows compatibility
PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"


async def verify_migration():
    """Verify the 0433 migration was successful."""

    print("=" * 70)
    print("HANDOVER 0433 MIGRATION VERIFICATION")
    print("=" * 70)
    print()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL not set in environment")
        return False

    db_manager = DatabaseManager(db_url, is_async=True)
    all_checks_passed = True

    try:
        async with db_manager.get_session_async() as session:

            # Check 1: Verify product_id is NOT NULL
            print("Check 1: Verifying product_id column is NOT NULL...")
            result = await session.execute(text("""
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_name = 'tasks'
                  AND column_name = 'product_id'
            """))
            is_nullable = result.scalar()

            if is_nullable == 'NO':
                print("  ✅ PASS: product_id column is NOT NULL")
            else:
                print(f"  ❌ FAIL: product_id is_nullable = {is_nullable}")
                all_checks_passed = False
            print()

            # Check 2: Verify UUID CHECK constraint exists
            print("Check 2: Verifying UUID format CHECK constraint exists...")
            result = await session.execute(text("""
                SELECT constraint_name
                FROM information_schema.constraint_column_usage
                WHERE table_name = 'tasks'
                  AND constraint_name = 'ck_task_product_id_uuid_format'
            """))
            constraint = result.scalar()

            if constraint:
                print(f"  ✅ PASS: CHECK constraint '{constraint}' exists")
            else:
                print("  ❌ FAIL: UUID CHECK constraint not found")
                all_checks_passed = False
            print()

            # Check 3: Verify no tasks with NULL product_id
            print("Check 3: Verifying no tasks with NULL product_id...")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM tasks WHERE product_id IS NULL
            """))
            null_count = result.scalar()

            if null_count == 0:
                print(f"  ✅ PASS: No tasks with NULL product_id (count: {null_count})")
            else:
                print(f"  ❌ FAIL: Found {null_count} tasks with NULL product_id")
                all_checks_passed = False
            print()

            # Check 4: Verify foreign key integrity
            print("Check 4: Verifying foreign key integrity...")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM tasks t
                LEFT JOIN products p ON t.product_id = p.id
                WHERE p.id IS NULL
            """))
            orphaned_count = result.scalar()

            if orphaned_count == 0:
                print(f"  ✅ PASS: All tasks reference valid products (orphaned: {orphaned_count})")
            else:
                print(f"  ❌ FAIL: Found {orphaned_count} tasks with invalid product_id")
                all_checks_passed = False
            print()

            # Check 5: Verify CASCADE delete is configured
            print("Check 5: Verifying CASCADE delete on foreign key...")
            result = await session.execute(text("""
                SELECT delete_rule
                FROM information_schema.referential_constraints
                WHERE constraint_name = 'tasks_product_id_fkey'
            """))
            delete_rule = result.scalar()

            if delete_rule == 'CASCADE':
                print(f"  ✅ PASS: CASCADE delete configured (delete_rule: {delete_rule})")
            else:
                print(f"  ⚠️  WARNING: delete_rule = {delete_rule} (expected: CASCADE)")
            print()

            # Check 6: Verify tenant isolation
            print("Check 6: Verifying tenant isolation (no cross-tenant references)...")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM tasks t
                JOIN products p ON t.product_id = p.id
                WHERE t.tenant_key != p.tenant_key
            """))
            cross_tenant_count = result.scalar()

            if cross_tenant_count == 0:
                print(f"  ✅ PASS: No cross-tenant task-product references (count: {cross_tenant_count})")
            else:
                print(f"  ❌ FAIL: Found {cross_tenant_count} cross-tenant references!")
                all_checks_passed = False
            print()

            # Summary
            print("=" * 70)
            if all_checks_passed:
                print("✅ ALL CHECKS PASSED - Migration successful!")
            else:
                print("❌ SOME CHECKS FAILED - Review errors above")
            print("=" * 70)

    except Exception as e:
        print(f"❌ ERROR during verification: {e}")
        import traceback
        traceback.print_exc()
        all_checks_passed = False
    finally:
        await db_manager.close_async()

    return all_checks_passed


if __name__ == "__main__":
    success = asyncio.run(verify_migration())
    sys.exit(0 if success else 1)
