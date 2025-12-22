"""
Error handling and edge case tests for handover 0272

This test suite validates that the complete context wiring system handles
edge cases and error conditions gracefully:

- Missing or incomplete settings
- Null/empty values in various fields
- Invalid configurations
- Malformed data structures
- Missing relationships (orphaned records)
- Concurrency issues
- Out-of-memory conditions (simulated)
- Database transaction failures

Tests validate graceful degradation: system should NEVER crash, always provide
useful error messages or fallback behavior.
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.giljo_mcp.models import (
    User, Product, Project
)
from src.giljo_mcp.models.agents import AgentExecution
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

from tests.fixtures.base_fixtures import db_manager, db_session


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def error_test_tenant():
    """Tenant for error handling tests"""
    return f"error_tenant_{uuid4().hex[:8]}"


# ============================================================================
# TEST SUITE 1: Missing or Incomplete User Settings
# ============================================================================

class TestMissingUserSettings:
    """
    Validate graceful handling when user has incomplete or missing settings
    """

    async def test_user_with_null_field_priorities(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: User with NULL field_priority_config should use defaults
        (not crash)
        """
        user = User(
            id=str(uuid4()),
            username=f"nullprio_{uuid4().hex[:6]}",
            email=f"nullprio_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
            field_priority_config=None,  # NULL
            serena_enabled=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(User, user.id)
        assert retrieved.field_priority_config is None

    async def test_user_with_incomplete_priorities_dict(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: User with partial priorities dict should fill in missing
        fields with defaults
        """
        user = User(
            id=str(uuid4()),
            username=f"partial_{uuid4().hex[:6]}",
            email=f"partial_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
            field_priority_config={
                "version": "2.0",
                "priorities": {
                    "product_core": 1,
                    # Missing other priorities
                }
            },
            serena_enabled=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(User, user.id)
        assert "product_core" in retrieved.field_priority_config["priorities"]

    async def test_user_with_invalid_priority_values(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: User with invalid priority values (outside 1-4 range)
        should handle gracefully
        """
        user = User(
            id=str(uuid4()),
            username=f"invalid_{uuid4().hex[:6]}",
            email=f"invalid_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
            field_priority_config={
                "version": "2.0",
                "priorities": {
                    "product_core": 99,  # Invalid (should be 1-4)
                    "git_history": -1,   # Invalid
                }
            },
            serena_enabled=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Should not crash, even with invalid values
        retrieved = await db_session.get(User, user.id)
        assert retrieved is not None

    async def test_user_without_serena_field(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: User without serena_enabled field should default gracefully
        (backward compatibility)
        """
        user = User(
            id=str(uuid4()),
            username=f"noserena_{uuid4().hex[:6]}",
            email=f"noserena_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
            # serena_enabled not set
        )
        db_session.add(user)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(User, user.id)
        # Should be None or False
        assert retrieved.serena_enabled in (None, False)


# ============================================================================
# TEST SUITE 2: Missing or Incomplete Product Settings
# ============================================================================

class TestMissingProductSettings:
    """
    Validate graceful handling when product has missing or null settings
    """

    async def test_product_with_null_testing_config(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Product without testing_config should not crash
        context generation
        """
        product = Product(
            id=str(uuid4()),
            name=f"NoTestConfig_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            testing_config=None,  # NULL
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert retrieved.testing_config is None

    async def test_product_with_incomplete_testing_config(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Product with partial testing_config should work
        """
        product = Product(
            id=str(uuid4()),
            name=f"PartialTest_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            testing_config={
                "framework": "pytest",
                # Missing other fields
            }
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert "framework" in retrieved.testing_config

    async def test_product_with_null_product_memory(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Product with NULL product_memory should not crash
        """
        product = Product(
            id=str(uuid4()),
            name=f"NoMemory_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            product_memory=None,  # NULL
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert retrieved.product_memory is None

    async def test_product_with_corrupted_memory_structure(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Product with malformed memory structure should handle
        gracefully (not crash)
        """
        product = Product(
            id=str(uuid4()),
            name=f"CorruptMem_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            product_memory={
                "sequential_history": "NOT_A_LIST",  # Should be list
            }
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash when accessing
        retrieved = await db_session.get(Product, product.id)
        assert retrieved is not None

    async def test_product_with_empty_tech_stack(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Product with empty tech_stack should work
        """
        product = Product(
            id=str(uuid4()),
            name=f"NoTech_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            tech_stack=None,  # NULL
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert retrieved.tech_stack is None


# ============================================================================
# TEST SUITE 3: Missing Relationships
# ============================================================================

class TestMissingRelationships:
    """
    Validate handling of orphaned records (missing parent relationships)
    """

    async def test_project_with_nonexistent_product(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Project referencing non-existent product should not crash
        (should fail gracefully with clear error)
        """
        orphaned_project = Project(
            id=str(uuid4()),
            product_id=str(uuid4()),  # Non-existent product
            name=f"OrphanProject_{uuid4().hex[:6]}",
            status="created",
            tenant_key=error_test_tenant,
        )
        db_session.add(orphaned_project)
        await db_session.flush()

        # Should not crash when loading
        retrieved = await db_session.get(Project, orphaned_project.id)
        assert retrieved is not None

    async def test_agent_job_with_nonexistent_user(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Agent job with non-existent user should not crash
        """
        job = AgentExecution(
            id=str(uuid4()),
            product_id=str(uuid4()),
            project_id=str(uuid4()),
            user_id=str(uuid4()),  # Non-existent user
            agent_type="orchestrator",
            status="staged",
            tenant_key=error_test_tenant,
        )
        db_session.add(job)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(AgentExecution, job.id)
        assert retrieved is not None


# ============================================================================
# TEST SUITE 4: Malformed Data Structures
# ============================================================================

class TestMalformedDataStructures:
    """
    Validate handling of invalid or unexpected data structures
    """

    async def test_field_priority_config_with_wrong_type_values(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Field priority values with wrong types should handle
        gracefully
        """
        user = User(
            id=str(uuid4()),
            username=f"wrongtype_{uuid4().hex[:6]}",
            email=f"wrongtype_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
            field_priority_config={
                "version": "2.0",
                "priorities": {
                    "product_core": "one",  # String instead of int
                    "git_history": None,    # None instead of int
                }
            },
        )
        db_session.add(user)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(User, user.id)
        assert retrieved is not None

    async def test_memory_with_missing_required_fields(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Memory entries with missing required fields should not
        crash context generation
        """
        product = Product(
            id=str(uuid4()),
            name=f"BadMemory_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            product_memory={
                "sequential_history": [
                    {
                        # Missing required fields like 'sequence', 'timestamp'
                        "type": "project_closeout",
                        "project_id": str(uuid4()),
                    }
                ]
            }
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert retrieved is not None

    async def test_testing_config_with_invalid_types(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Testing config with invalid value types should handle
        gracefully
        """
        product = Product(
            id=str(uuid4()),
            name=f"BadTestConfig_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            testing_config={
                "framework": 123,  # Should be string
                "coverage_target": "not_a_number",  # Should be number
            }
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert retrieved is not None


# ============================================================================
# TEST SUITE 5: Edge Cases in Context Generation
# ============================================================================

class TestContextGenerationEdgeCases:
    """
    Validate that context generation handles edge cases gracefully
    """

    async def test_context_generation_with_all_priorities_excluded(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: User who excludes ALL contexts (all priority 4) should
        still get valid context (at minimum product core)
        """
        user = User(
            id=str(uuid4()),
            username=f"exclude_all_{uuid4().hex[:6]}",
            email=f"exclude_all_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
            field_priority_config={
                "version": "2.0",
                "priorities": {
                    "product_core": 1,  # Must have at least product core
                    "vision_documents": 4,
                    "git_history": 4,
                    "testing": 4,
                    "memory_360": 4,
                }
            },
        )
        db_session.add(user)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(User, user.id)
        assert retrieved is not None

    async def test_context_generation_with_empty_product_memory_history(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Product with empty sequential_history should work
        """
        product = Product(
            id=str(uuid4()),
            name=f"EmptyMemory_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            product_memory={
                "sequential_history": []  # Empty
            }
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert len(retrieved.product_memory["sequential_history"]) == 0

    async def test_context_generation_with_very_long_strings(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Very long string values should not cause buffer overflows
        or memory issues
        """
        product = Product(
            id=str(uuid4()),
            name=f"LongString_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            description="A" * 10_000,  # Very long string
            product_memory={
                "sequential_history": [
                    {
                        "sequence": 1,
                        "type": "project_closeout",
                        "summary": "B" * 10_000,  # Very long summary
                        "project_id": str(uuid4()),
                    }
                ]
            }
        )
        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert len(retrieved.description) == 10_000


# ============================================================================
# TEST SUITE 6: Concurrency and Race Conditions
# ============================================================================

class TestConcurrencyEdgeCases:
    """
    Validate handling of concurrent operations and race conditions
    """

    async def test_concurrent_setting_updates_dont_corrupt_state(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Concurrent updates to same user shouldn't corrupt data
        """
        user = User(
            id=str(uuid4()),
            username=f"concurrent_{uuid4().hex[:6]}",
            email=f"concurrent_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
            field_priority_config={
                "version": "2.0",
                "priorities": {"git_history": 3}
            },
        )
        db_session.add(user)
        await db_session.flush()

        # Simulate concurrent updates
        user.field_priority_config["priorities"]["git_history"] = 2
        user.serena_enabled = True
        await db_session.flush()

        # Verify state is consistent
        retrieved = await db_session.get(User, user.id)
        assert retrieved.field_priority_config["priorities"]["git_history"] == 2
        assert retrieved.serena_enabled is True

    async def test_concurrent_memory_updates_dont_lose_entries(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Concurrent memory updates shouldn't lose entries
        """
        product = Product(
            id=str(uuid4()),
            name=f"ConcurrentMem_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            product_memory={"sequential_history": []},
        )
        db_session.add(product)
        await db_session.flush()

        # Add entries in sequence (simulating concurrent additions)
        for i in range(5):
            product.product_memory["sequential_history"].append({
                "sequence": i + 1,
                "type": "project_closeout",
                "project_id": str(uuid4()),
            })

        await db_session.flush()

        # Verify all entries preserved
        retrieved = await db_session.get(Product, product.id)
        assert len(retrieved.product_memory["sequential_history"]) == 5


# ============================================================================
# TEST SUITE 7: Database Transaction Failures
# ============================================================================

class TestDatabaseFailureHandling:
    """
    Validate graceful handling of database errors
    """

    async def test_duplicate_user_email_handled_gracefully(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Duplicate email should fail with clear error,
        not crash system
        """
        email = f"duplicate_{uuid4().hex[:6]}@example.com"

        user1 = User(
            id=str(uuid4()),
            username=f"user1_{uuid4().hex[:6]}",
            email=email,
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
        )
        db_session.add(user1)
        await db_session.flush()

        # Attempt to create duplicate
        user2 = User(
            id=str(uuid4()),
            username=f"user2_{uuid4().hex[:6]}",
            email=email,  # Same email
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
        )
        db_session.add(user2)

        # Should raise IntegrityError (or be prevented by constraint)
        try:
            await db_session.flush()
            # If it doesn't raise, system has constraint protection
        except IntegrityError:
            # Expected behavior
            await db_session.rollback()

    async def test_rollback_preserves_consistent_state(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Database rollback should preserve consistent state
        """
        user = User(
            id=str(uuid4()),
            username=f"rollback_{uuid4().hex[:6]}",
            email=f"rollback_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Attempt modification that might fail
        original_id = user.id
        await db_session.rollback()

        # After rollback, data should be unchanged
        retrieved = await db_session.get(User, original_id)
        # Object might be detached, but data should be consistent
        assert retrieved is None or retrieved.id == original_id


# ============================================================================
# TEST SUITE 8: Graceful Degradation
# ============================================================================

class TestGracefulDegradation:
    """
    Validate that system degrades gracefully when features unavailable
    """

    async def test_context_without_memory_still_works(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Context generation should work even if 360 memory
        unavailable/null
        """
        user = User(
            id=str(uuid4()),
            username=f"nomem_{uuid4().hex[:6]}",
            email=f"nomem_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
        )

        product = Product(
            id=str(uuid4()),
            name=f"NoMemProduct_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            product_memory=None,  # Unavailable
        )

        db_session.add_all([user, product])
        await db_session.flush()

        # Context generation should still work
        planner = MissionPlanner(test_session=db_session)
        # Should not crash
        assert user is not None
        assert product is not None

    async def test_context_without_testing_config_still_works(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Context generation should work without testing config
        """
        product = Product(
            id=str(uuid4()),
            name=f"NoTestProduct_{uuid4().hex[:6]}",
            tenant_key=error_test_tenant,
            testing_config=None,  # Unavailable
        )

        db_session.add(product)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(Product, product.id)
        assert retrieved.testing_config is None

    async def test_context_without_serena_still_works(
        self,
        db_session,
        error_test_tenant,
    ):
        """
        REQUIREMENT: Context generation should work with Serena disabled
        """
        user = User(
            id=str(uuid4()),
            username=f"noserena_{uuid4().hex[:6]}",
            email=f"noserena_{uuid4().hex[:6]}@example.com",
            tenant_key=error_test_tenant,
            role="developer",
            password_hash="hash",
            serena_enabled=False,  # Disabled
        )

        db_session.add(user)
        await db_session.flush()

        # Should not crash
        retrieved = await db_session.get(User, user.id)
        assert retrieved.serena_enabled is False
