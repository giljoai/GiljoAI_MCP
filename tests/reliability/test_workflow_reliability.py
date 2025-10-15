"""
End-to-End Workflow Reliability Tests

Tests complete spawn -> complete cycles to measure reliability of the
manual workflow tracking system (AgentInteraction logging).

Target: >=95% reliability for complete workflows
"""

import pytest
from datetime import datetime, timezone

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Agent, Project, AgentInteraction, Product
from src.giljo_mcp.tools.agent import _ensure_agent
from sqlalchemy import select


class TestWorkflowReliability:
    """Test reliability of complete agent lifecycle workflows"""

    @pytest.fixture
    async def db_manager(self):
        """Create database manager for tests"""
        return DatabaseManager()

    @pytest.fixture
    async def test_product(self, db_manager):
        """Create test product"""
        async with db_manager.get_session_async() as session:
            product = Product(
                tenant_key="workflow-test-tenant",
                name="Workflow Test Product",
                description="Product for workflow reliability testing"
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product

    @pytest.fixture
    async def test_project(self, db_manager, test_product):
        """Create test project"""
        async with db_manager.get_session_async() as session:
            project = Project(
                tenant_key="workflow-test-tenant",
                product_id=test_product.id,
                name="Workflow Test Project",
                mission="Test workflow reliability"
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            return project

    @pytest.mark.asyncio
    async def test_full_lifecycle_reliability(self, db_manager, test_project):
        """Test 100 complete spawn -> complete cycles"""
        success_count = 0
        failure_count = 0
        spawn_failures = 0
        complete_failures = 0
        errors = []

        # Create parent agent
        async with db_manager.get_session_async() as session:
            parent = Agent(
                project_id=test_project.id,
                tenant_key=test_project.tenant_key,
                name="orchestrator",
                role="orchestrator",
                status="active"
            )
            session.add(parent)
            await session.commit()
            await session.refresh(parent)
            parent_id = parent.id

        for i in range(100):
            interaction_id = None
            try:
                # Step 1: Spawn (create interaction record)
                async with db_manager.get_session_async() as session:
                    interaction = AgentInteraction(
                        tenant_key=test_project.tenant_key,
                        project_id=test_project.id,
                        parent_agent_id=parent_id,
                        sub_agent_name=f"workflow-worker-{i}",
                        interaction_type="SPAWN",
                        mission="Complete workflow test",
                        start_time=datetime.now(timezone.utc)
                    )
                    session.add(interaction)
                    await session.commit()
                    await session.refresh(interaction)
                    interaction_id = interaction.id

                # Step 2: Complete (update interaction record)
                async with db_manager.get_session_async() as session:
                    query = select(AgentInteraction).where(AgentInteraction.id == interaction_id)
                    result = await session.execute(query)
                    interaction = result.scalar_one_or_none()

                    if not interaction:
                        complete_failures += 1
                        errors.append({
                            "iteration": i,
                            "phase": "complete",
                            "error": "Interaction not found"
                        })
                        failure_count += 1
                        continue

                    # Update to COMPLETE state
                    end_time = datetime.now(timezone.utc)
                    interaction.end_time = end_time
                    interaction.duration_seconds = int((end_time - interaction.start_time).total_seconds())
                    interaction.tokens_used = 1000
                    interaction.interaction_type = "COMPLETE"
                    interaction.result = f"Success for workflow-worker-{i}"

                    await session.commit()
                    success_count += 1

            except Exception as e:
                failure_count += 1
                if interaction_id is None:
                    spawn_failures += 1
                    phase = "spawn"
                else:
                    complete_failures += 1
                    phase = "complete"

                errors.append({
                    "iteration": i,
                    "phase": phase,
                    "error": str(e)
                })

        reliability = (success_count / 100) * 100

        print(f"\n=== Full Lifecycle Reliability Test ===")
        print(f"Complete cycles: {success_count}/100")
        print(f"Failed cycles: {failure_count}/100")
        print(f"  - Spawn failures: {spawn_failures}")
        print(f"  - Complete failures: {complete_failures}")
        print(f"Reliability: {reliability}%")

        if errors:
            print(f"\nErrors encountered: {len(errors)}")
            for error in errors[:5]:
                print(f"  - Iteration {error['iteration']} ({error['phase']}): {error['error']}")

        assert reliability >= 95.0, (
            f"Full lifecycle reliability {reliability}% is below target 95%. "
            f"Spawn failures: {spawn_failures}, Complete failures: {complete_failures}"
        )

    @pytest.mark.asyncio
    async def test_error_state_tracking_reliability(self, db_manager, test_project):
        """Test reliability of tracking ERROR state workflows"""
        success_count = 0
        failure_count = 0
        errors = []

        # Create parent agent
        async with db_manager.get_session_async() as session:
            parent = Agent(
                project_id=test_project.id,
                tenant_key=test_project.tenant_key,
                name="orchestrator",
                role="orchestrator",
                status="active"
            )
            session.add(parent)
            await session.commit()
            await session.refresh(parent)
            parent_id = parent.id

        for i in range(50):
            try:
                # Spawn
                async with db_manager.get_session_async() as session:
                    interaction = AgentInteraction(
                        tenant_key=test_project.tenant_key,
                        project_id=test_project.id,
                        parent_agent_id=parent_id,
                        sub_agent_name=f"error-worker-{i}",
                        interaction_type="SPAWN",
                        mission="Fail spectacularly",
                        start_time=datetime.now(timezone.utc)
                    )
                    session.add(interaction)
                    await session.commit()
                    await session.refresh(interaction)
                    interaction_id = interaction.id

                # Log error
                async with db_manager.get_session_async() as session:
                    query = select(AgentInteraction).where(AgentInteraction.id == interaction_id)
                    result = await session.execute(query)
                    interaction = result.scalar_one_or_none()

                    end_time = datetime.now(timezone.utc)
                    interaction.end_time = end_time
                    interaction.duration_seconds = int((end_time - interaction.start_time).total_seconds())
                    interaction.tokens_used = 500
                    interaction.interaction_type = "ERROR"
                    interaction.error_message = f"Simulated error for worker-{i}"

                    await session.commit()
                    success_count += 1

            except Exception as e:
                failure_count += 1
                errors.append({"iteration": i, "error": str(e)})

        reliability = (success_count / 50) * 100

        print(f"\n=== Error State Tracking Reliability Test ===")
        print(f"Successful error logs: {success_count}/50")
        print(f"Failed error logs: {failure_count}/50")
        print(f"Reliability: {reliability}%")

        assert reliability >= 95.0, (
            f"Error tracking reliability {reliability}% is below target 95%"
        )

    @pytest.mark.asyncio
    async def test_token_usage_tracking_reliability(self, db_manager, test_project):
        """Test reliability of token usage tracking across workflows"""
        success_count = 0
        failure_count = 0
        token_tracking_failures = 0

        # Create parent agent
        async with db_manager.get_session_async() as session:
            parent = Agent(
                project_id=test_project.id,
                tenant_key=test_project.tenant_key,
                name="orchestrator",
                role="orchestrator",
                status="active",
                context_used=0
            )
            session.add(parent)
            await session.commit()
            await session.refresh(parent)
            parent_id = parent.id

        for i in range(50):
            try:
                token_amount = (i + 1) * 100  # Varying token amounts

                # Spawn and complete with token tracking
                async with db_manager.get_session_async() as session:
                    interaction = AgentInteraction(
                        tenant_key=test_project.tenant_key,
                        project_id=test_project.id,
                        parent_agent_id=parent_id,
                        sub_agent_name=f"token-worker-{i}",
                        interaction_type="SPAWN",
                        mission="Track tokens",
                        start_time=datetime.now(timezone.utc)
                    )
                    session.add(interaction)
                    await session.commit()
                    await session.refresh(interaction)
                    interaction_id = interaction.id

                # Complete with token usage
                async with db_manager.get_session_async() as session:
                    # Get interaction
                    query = select(AgentInteraction).where(AgentInteraction.id == interaction_id)
                    result = await session.execute(query)
                    interaction = result.scalar_one_or_none()

                    # Update interaction
                    interaction.end_time = datetime.now(timezone.utc)
                    interaction.tokens_used = token_amount
                    interaction.interaction_type = "COMPLETE"
                    interaction.result = "Success"

                    # Update parent agent context
                    parent_query = select(Agent).where(Agent.id == parent_id)
                    parent_result = await session.execute(parent_query)
                    parent = parent_result.scalar_one_or_none()

                    initial_context = parent.context_used
                    parent.context_used += token_amount

                    await session.commit()

                    # Verify token tracking
                    await session.refresh(parent)
                    expected_context = initial_context + token_amount

                    if parent.context_used == expected_context:
                        success_count += 1
                    else:
                        token_tracking_failures += 1
                        failure_count += 1

            except Exception as e:
                failure_count += 1

        reliability = (success_count / 50) * 100

        print(f"\n=== Token Usage Tracking Reliability Test ===")
        print(f"Successful token updates: {success_count}/50")
        print(f"Token tracking failures: {token_tracking_failures}/50")
        print(f"Other failures: {failure_count - token_tracking_failures}/50")
        print(f"Reliability: {reliability}%")

        assert reliability >= 95.0, (
            f"Token tracking reliability {reliability}% is below target 95%"
        )

    @pytest.mark.asyncio
    async def test_ensure_agent_idempotency_reliability(self, db_manager, test_project):
        """Test reliability of ensure_agent idempotency (safe to call multiple times)"""
        success_count = 0
        failure_count = 0

        for i in range(50):
            try:
                async with db_manager.get_session_async() as session:
                    # Call ensure_agent twice for same agent
                    result1 = await _ensure_agent(
                        project_id=str(test_project.id),
                        agent_name=f"idempotent-agent-{i}",
                        mission="Test idempotency",
                        session=session
                    )

                    result2 = await _ensure_agent(
                        project_id=str(test_project.id),
                        agent_name=f"idempotent-agent-{i}",
                        mission="Test idempotency",
                        session=session
                    )

                    # Both should succeed
                    assert result1["success"], "First ensure_agent should succeed"
                    assert result2["success"], "Second ensure_agent should succeed"

                    # Second should return existing agent
                    assert result1["agent_id"] == result2["agent_id"], "Should return same agent"
                    assert result1["is_new"] is True, "First call should create agent"
                    assert result2["is_new"] is False, "Second call should return existing"

                    success_count += 1

            except Exception as e:
                failure_count += 1

        reliability = (success_count / 50) * 100

        print(f"\n=== Ensure Agent Idempotency Reliability Test ===")
        print(f"Successful idempotent calls: {success_count}/50")
        print(f"Failures: {failure_count}/50")
        print(f"Reliability: {reliability}%")

        assert reliability >= 95.0, (
            f"Idempotency reliability {reliability}% is below target 95%"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
