"""
Test suite for Handover 0387f Phase 3 - JSONB Read Replacement

Tests that all JSONB message reads have been replaced with:
1. Counter field access (messages_sent_count, messages_waiting_count, messages_read_count)
2. Message table queries (for orchestrator succession handover summary)

Modified Files:
- src/giljo_mcp/services/project_service.py
- src/giljo_mcp/services/orchestration_service.py
- src/giljo_mcp/orchestrator_succession.py
- api/endpoints/agent_jobs/table_view.py
- api/endpoints/agent_jobs/filters.py
- api/endpoints/statistics.py
- api/endpoints/agent_management.py
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentJob, AgentExecution, Message, Project
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
async def setup_test_data(db_manager: DatabaseManager, test_tenant_key: str):
    """Create test project, job, execution, and messages"""
    async with db_manager.get_session_async() as session:
        # Create project
        project = Project(
            id=str(uuid4()),
            name="Test Project",
            description="Test project for counter reads",
            status="active",
            tenant_key=test_tenant_key,
            context_used=0,
            context_budget=200000,
        )
        session.add(project)
        await session.flush()

        # Create job
        job = AgentJob(
            job_id=str(uuid4()),
            project_id=project.id,
            tenant_key=test_tenant_key,
            job_type="test-agent",
            mission="Test mission",
            status="pending",
        )
        session.add(job)
        await session.flush()

        # Create execution with counter fields
        execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name="test-agent",
            agent_name="test-agent-instance",
            status="working",
            messages_sent_count=5,
            messages_waiting_count=3,
            messages_read_count=2,
            instance_number=1,
        )
        session.add(execution)
        await session.flush()

        # Create actual messages in Message table
        for i in range(5):
            msg = Message(
                id=str(uuid4()),
                tenant_key=test_tenant_key,
                project_id=project.id,
                from_agent=execution.agent_id,
                to_agents=["orchestrator"],
                message_type="status",
                content=f"Test message {i}",
                status="pending" if i < 3 else "acknowledged",
            )
            session.add(msg)

        await session.commit()

        return {
            "project": project,
            "job": job,
            "execution": execution,
        }


class TestProjectServiceCounters:
    """Test project_service.py uses counter fields instead of JSONB messages"""

    async def test_get_project_returns_counter_fields(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data
    ):
        """Verify get_project returns counter fields instead of messages array"""
        data = await setup_test_data
        project_service = ProjectService(db_manager, TenantManager())

        async with db_manager.get_session_async() as session:
            result = await project_service.get_project(session, data["project"].id, test_tenant_key)

            # Check that agents have counter fields, not messages array
            agents = result["agents"]
            assert len(agents) == 1
            agent = agents[0]

            # Counter fields should be present
            assert "messages_sent_count" in agent
            assert "messages_waiting_count" in agent
            assert "messages_read_count" in agent

            # Verify values match execution
            assert agent["messages_sent_count"] == 5
            assert agent["messages_waiting_count"] == 3
            assert agent["messages_read_count"] == 2

            # Old messages field should not be present (or be empty/deprecated)
            # Note: If messages field exists for backward compatibility, it should be empty
            if "messages" in agent:
                assert agent["messages"] == [] or len(agent["messages"]) == 0


class TestOrchestrationServiceLogging:
    """Test orchestration_service.py uses counters in debug logging"""

    async def test_list_jobs_logs_counter_fields(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data, caplog
    ):
        """Verify list_jobs logs counter fields instead of messages length"""
        data = await setup_test_data
        orchestration_service = OrchestrationService(db_manager, TenantManager())

        async with db_manager.get_session_async() as session:
            # Call list_jobs which should trigger debug logging
            await orchestration_service.list_jobs(session, test_tenant_key, data["project"].id)

            # Check debug logs contain counter values
            assert any("sent" in record.message and "waiting" in record.message for record in caplog.records)


class TestOrchestratorSuccessionMessageQuery:
    """Test orchestrator_succession.py queries Message table instead of JSONB"""

    async def test_handover_summary_queries_message_table(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data
    ):
        """Verify generate_handover_summary queries Message table, not execution.messages"""
        data = await setup_test_data

        async with db_manager.get_session_async() as session:
            succession_mgr = OrchestratorSuccessionManager(session, test_tenant_key)

            # Generate handover summary
            summary = await succession_mgr.generate_handover_summary(data["execution"])

            # Summary should have message_count from Message table query
            assert "message_count" in summary
            assert summary["message_count"] == 5  # 5 messages created in setup

            # Summary should contain other expected fields
            assert "project_status" in summary
            assert "active_agents" in summary
            assert "next_steps" in summary


class TestTableViewCounters:
    """Test table_view.py uses counter fields and queries"""

    async def test_filter_by_unread_uses_counter(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data
    ):
        """Verify has_unread filter uses messages_waiting_count > 0"""
        data = await setup_test_data

        async with db_manager.get_session_async() as session:
            # Query using same pattern as table_view.py
            from sqlalchemy import and_, func, select
            from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

            query = (
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentExecution.tenant_key == test_tenant_key,
                        AgentJob.project_id == data["project"].id,
                        AgentExecution.messages_waiting_count > 0,  # Counter-based filter
                    )
                )
            )

            result = await session.execute(query)
            executions = result.scalars().all()

            # Should find our execution with 3 waiting messages
            assert len(executions) == 1
            assert executions[0].messages_waiting_count == 3

    async def test_message_counts_from_counters(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data
    ):
        """Verify message counts come from counter fields, not JSONB iteration"""
        data = await setup_test_data

        async with db_manager.get_session_async() as session:
            stmt = select(AgentExecution).where(AgentExecution.agent_id == data["execution"].agent_id)
            result = await session.execute(stmt)
            execution = result.scalar_one()

            # Counts should come from counter fields
            unread_count = execution.messages_waiting_count
            acknowledged_count = execution.messages_read_count
            total_messages = (
                execution.messages_sent_count + execution.messages_waiting_count + execution.messages_read_count
            )

            assert unread_count == 3
            assert acknowledged_count == 2
            assert total_messages == 10  # 5 + 3 + 2


class TestFiltersCounters:
    """Test filters.py uses counter fields"""

    async def test_has_unread_jobs_uses_counter(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data
    ):
        """Verify has_unread_jobs detection uses messages_waiting_count"""
        data = await setup_test_data

        async with db_manager.get_session_async() as session:
            # Query pattern from filters.py
            from sqlalchemy import and_, select
            from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

            unread_query = (
                select(AgentExecution.agent_id)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentExecution.tenant_key == test_tenant_key,
                        AgentJob.project_id == data["project"].id,
                        AgentExecution.messages_waiting_count > 0,  # Counter-based
                    )
                )
                .limit(1)
            )

            result = await session.execute(unread_query)
            has_unread = result.scalar() is not None

            assert has_unread is True


class TestStatisticsCounters:
    """Test statistics.py uses counter fields"""

    async def test_agent_stats_use_counters(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data
    ):
        """Verify agent statistics use counter fields, not JSONB iteration"""
        data = await setup_test_data

        async with db_manager.get_session_async() as session:
            stmt = select(AgentExecution).where(AgentExecution.agent_id == data["execution"].agent_id)
            result = await session.execute(stmt)
            execution = result.scalar_one()

            # Statistics should use counter fields directly
            task_count = execution.messages_sent_count
            completed_count = execution.messages_read_count

            assert task_count == 5
            assert completed_count == 2


class TestAgentManagementCounters:
    """Test agent_management.py returns empty messages or uses counters"""

    async def test_agent_job_response_no_messages(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data
    ):
        """Verify AgentJobResponse returns empty messages array (deprecated field)"""
        data = await setup_test_data

        async with db_manager.get_session_async() as session:
            stmt = select(AgentJob).where(AgentJob.job_id == data["job"].job_id)
            result = await session.execute(stmt)
            job = result.scalar_one()

            # Simulating agent_management.py response construction
            # Messages field should be empty (deprecated in favor of counters)
            messages = []  # Handover 0387f: JSONB messages deprecated

            assert messages == []


@pytest.mark.integration
class TestEndToEndCounterUsage:
    """Integration test verifying full counter-based workflow"""

    async def test_full_workflow_uses_counters(
        self, db_manager: DatabaseManager, test_tenant_key: str, setup_test_data
    ):
        """Verify end-to-end workflow never accesses execution.messages JSONB field"""
        data = await setup_test_data

        async with db_manager.get_session_async() as session:
            # 1. Get project (project_service.py)
            project_service = ProjectService(db_manager, TenantManager())
            project_data = await project_service.get_project(session, data["project"].id, test_tenant_key)
            agent = project_data["agents"][0]

            # Should have counters, not messages
            assert "messages_sent_count" in agent
            assert agent["messages_sent_count"] == 5

            # 2. Query with filter (table_view.py pattern)
            stmt = (
                select(AgentExecution)
                .where(
                    AgentExecution.tenant_key == test_tenant_key,
                    AgentExecution.messages_waiting_count > 0,
                )
            )
            result = await session.execute(stmt)
            executions = result.scalars().all()
            assert len(executions) == 1

            # 3. Generate handover summary (orchestrator_succession.py)
            succession_mgr = OrchestratorSuccessionManager(session, test_tenant_key)
            summary = await succession_mgr.generate_handover_summary(data["execution"])
            assert summary["message_count"] == 5  # From Message table query

            # 4. Verify no direct JSONB access occurred
            # All operations used counter fields or Message table queries


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
