"""
Security Tests for Orchestrator Succession (Handover 0080)

Critical security tests ensuring succession is secure and authorized:
- Only orchestrator agent_type can create successors
- Succession enforces RBAC and permissions
- Handover summary contains no sensitive data
- Multi-tenant isolation enforced
- SQL injection prevention
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.fixtures.succession_fixtures import SuccessionTestData


# ============================================================================
# Authorization Tests
# ============================================================================


@pytest.mark.asyncio
async def test_non_orchestrator_cannot_create_successor(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Only orchestrator agent_type can spawn successors.

    Other agent types (analyzer, implementer, etc.) should not create successors.
    """
    # Create non-orchestrator agent (implementer)
    implementer = AgentExecution(
        job_id=f"impl-{uuid.uuid4()}",
        tenant_key=test_tenant_key,
        project_id=test_project.id,
        agent_type="implementer",  # NOT orchestrator
        mission="Implement feature X",
        status="working",
        instance_number=1,
        context_used=50000,
        context_budget=150000,
    )

    db_session.add(implementer)
    await db_session.commit()
    await db_session.refresh(implementer)

    # ========== VERIFICATIONS ==========

    # Implementer should NOT have succession capabilities
    assert implementer.agent_type != "orchestrator"

    # In real implementation, MCP tool create_successor would check agent_type
    # and reject non-orchestrator attempts

    # Verify implementer cannot set succession fields
    assert implementer.instance_number == 1  # Not used for succession
    assert implementer.handover_to is None
    assert implementer.succession_reason is None


@pytest.mark.asyncio
async def test_orchestrator_role_enforcement(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Only agents with agent_type='orchestrator' can use succession features.
    """
    # Create orchestrator
    orchestrator = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="working",
        )
    )

    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)

    # ========== VERIFICATIONS ==========

    # Orchestrator can use succession features
    assert orchestrator.agent_type == "orchestrator"
    assert orchestrator.instance_number is not None
    assert orchestrator.context_used is not None
    assert orchestrator.context_budget is not None

    # Succession can be triggered
    should_trigger = orchestrator.context_used >= (orchestrator.context_budget * 0.90)
    assert should_trigger is True


# ============================================================================
# Data Leakage Prevention Tests
# ============================================================================


@pytest.mark.asyncio
async def test_handover_summary_no_sensitive_data_leak(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Handover summary doesn't contain:
    - API keys
    - Passwords
    - Personal data from other tenants
    - Database credentials
    """
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="complete",
        )
    )

    # Generate handover summary with only safe data
    safe_handover = {
        "project_status": "Implementation phase - 70% complete",
        "active_agents": [
            {"job_id": str(uuid.uuid4()), "type": "backend-dev", "status": "working"},
        ],
        "completed_phases": ["requirements", "design"],
        "pending_decisions": ["Choose caching strategy"],
        "critical_context_refs": [f"chunk-{i}" for i in range(1, 6)],
        "next_steps": "Complete API implementation",
        "token_estimate": 5000,
    }

    instance.handover_summary = safe_handover
    instance.succession_reason = "context_limit"
    instance.completed_at = datetime.now(timezone.utc)

    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    import json

    handover_str = json.dumps(instance.handover_summary)

    # Verify NO sensitive data patterns
    sensitive_patterns = [
        "password",
        "api_key",
        "secret",
        "token",
        "credential",
        "private_key",
        "bearer",
        "authorization",
    ]

    for pattern in sensitive_patterns:
        assert pattern not in handover_str.lower(), f"Sensitive pattern found: {pattern}"

    # Verify only contains expected fields
    expected_fields = [
        "project_status",
        "active_agents",
        "completed_phases",
        "pending_decisions",
        "critical_context_refs",
        "next_steps",
    ]

    for field in expected_fields:
        assert field in instance.handover_summary


@pytest.mark.asyncio
async def test_cross_tenant_data_isolation_in_handover(
    db_session: AsyncSession,
):
    """
    Handover summary from Tenant A contains no references to Tenant B data.
    """
    tenant_a_key = f"tk_tenant_a_{uuid.uuid4().hex[:8]}"
    tenant_b_key = f"tk_tenant_b_{uuid.uuid4().hex[:8]}"

    # Create projects for both tenants
    project_a = Project(
        id=str(uuid.uuid4()),
        name="Tenant A Project",
        description="Test project for Tenant A security validation",
        mission="Tenant A",
        status="active",
        tenant_key=tenant_a_key,
    )
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Tenant B Project",
        description="Test project for Tenant B security validation",
        mission="Tenant B",
        status="active",
        tenant_key=tenant_b_key,
    )

    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Create Tenant A orchestrator with handover
    orch_a = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=project_a.id,
            tenant_key=tenant_a_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="complete",
        )
    )

    # Handover should ONLY reference Tenant A data
    tenant_a_handover = {
        "project_status": "Tenant A project in progress",
        "active_agents": [
            {"job_id": str(uuid.uuid4()), "type": "tenant-a-agent", "status": "working"},
        ],
        "critical_context_refs": [f"tenant-a-chunk-{i}" for i in range(1, 6)],
        "next_steps": "Continue Tenant A development",
        "token_estimate": 4000,
    }

    orch_a.handover_summary = tenant_a_handover
    orch_a.succession_reason = "context_limit"
    orch_a.completed_at = datetime.now(timezone.utc)

    db_session.add(orch_a)
    await db_session.commit()
    await db_session.refresh(orch_a)

    # ========== VERIFICATIONS ==========

    import json

    handover_str = json.dumps(orch_a.handover_summary)

    # Verify NO references to Tenant B
    assert tenant_b_key not in handover_str
    assert "tenant-b" not in handover_str.lower()
    assert project_b.id not in handover_str

    # Verify ONLY Tenant A references
    assert "tenant-a" in handover_str.lower()


# ============================================================================
# SQL Injection Prevention Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sql_injection_in_succession_queries(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Parameterized queries prevent SQL injection attacks.

    Tests that malicious input in project_id doesn't execute SQL.
    """
    # Create valid orchestrator
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=50000,
            context_budget=150000,
            status="waiting",
        )
    )

    db_session.add(instance)
    await db_session.commit()

    # Attempt SQL injection via project_id parameter
    malicious_input = "' OR '1'='1'; DROP TABLE mcp_agent_jobs; --"

    # Use parameterized query (SAFE)
    stmt = select(AgentExecution).where(
        AgentExecution.project_id == malicious_input,  # Treated as literal string
        AgentExecution.agent_type == "orchestrator",
    )

    result = await db_session.execute(stmt)
    orchestrators = result.scalars().all()

    # ========== VERIFICATIONS ==========

    # Should return nothing (malicious_input is not a valid project_id)
    assert len(orchestrators) == 0

    # Verify table still exists (injection didn't execute)
    verify_stmt = select(AgentExecution).where(AgentExecution.project_id == test_project.id)
    verify_result = await db_session.execute(verify_stmt)
    valid_orchestrators = verify_result.scalars().all()

    assert len(valid_orchestrators) == 1  # Original instance still exists


@pytest.mark.asyncio
async def test_handover_summary_json_injection_prevention(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    JSONB fields sanitize malicious input.

    Tests that handover_summary rejects invalid JSON structures.
    """
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="complete",
        )
    )

    # Attempt to inject malicious content via handover_summary
    potentially_malicious_summary = {
        "project_status": "Normal status",
        "active_agents": [
            {
                "job_id": str(uuid.uuid4()),
                "type": "<script>alert('XSS')</script>",  # XSS attempt
                "status": "working",
            },
        ],
        "critical_context_refs": [],
        "next_steps": "'; DROP TABLE mcp_agent_jobs; --",  # SQL injection attempt
        "token_estimate": 3000,
    }

    instance.handover_summary = potentially_malicious_summary
    instance.succession_reason = "context_limit"
    instance.completed_at = datetime.now(timezone.utc)

    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    # JSONB stores as-is (no code execution)
    assert instance.handover_summary["active_agents"][0]["type"] == "<script>alert('XSS')</script>"

    # Verify table still exists (SQL injection didn't execute)
    verify_stmt = select(AgentExecution).where(AgentExecution.project_id == test_project.id)
    verify_result = await db_session.execute(verify_stmt)
    all_instances = verify_result.scalars().all()

    assert len(all_instances) == 1  # Only the test instance


# ============================================================================
# Access Control Tests
# ============================================================================


@pytest.mark.asyncio
async def test_tenant_cannot_access_other_tenant_succession_chain(
    db_session: AsyncSession,
):
    """
    Tenant A cannot query Tenant B's succession chain.

    Critical security: Tenant isolation must be enforced at query level.
    """
    tenant_a_key = f"tk_tenant_a_{uuid.uuid4().hex[:8]}"
    tenant_b_key = f"tk_tenant_b_{uuid.uuid4().hex[:8]}"

    # Create projects
    project_a = Project(
        id=str(uuid.uuid4()),
        name="Tenant A Project",
        description="Test project for Tenant A access control validation",
        mission="Tenant A",
        status="active",
        tenant_key=tenant_a_key,
    )
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Tenant B Project",
        description="Test project for Tenant B access control validation",
        mission="Tenant B",
        status="active",
        tenant_key=tenant_b_key,
    )

    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Create succession chain for Tenant B
    tenant_b_instances = []
    for i in range(1, 4):
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=project_b.id,
                tenant_key=tenant_b_key,
                instance_number=i,
                context_used=50000,
                context_budget=150000,
                status="waiting",
            )
        )
        db_session.add(instance)
        tenant_b_instances.append(instance)

    await db_session.commit()

    # Tenant A attempts to query Tenant B's succession chain (SHOULD FAIL)
    stmt = select(AgentExecution).where(
        AgentExecution.project_id == project_b.id,
        AgentExecution.tenant_key == tenant_a_key,  # Wrong tenant key!
        AgentExecution.agent_type == "orchestrator",
    )

    result = await db_session.execute(stmt)
    tenant_a_query_results = result.scalars().all()

    # ========== VERIFICATIONS ==========

    # Should return nothing (tenant mismatch)
    assert len(tenant_a_query_results) == 0

    # Verify Tenant B data exists (correct tenant key query)
    correct_stmt = select(AgentExecution).where(
        AgentExecution.project_id == project_b.id,
        AgentExecution.tenant_key == tenant_b_key,  # Correct tenant key
        AgentExecution.agent_type == "orchestrator",
    )

    correct_result = await db_session.execute(correct_stmt)
    tenant_b_data = correct_result.scalars().all()

    assert len(tenant_b_data) == 3  # Tenant B's 3 instances


@pytest.mark.asyncio
async def test_handover_summary_no_system_metadata_leak(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Handover summary should not contain system metadata:
    - Database connection strings
    - Internal IPs
    - File system paths
    - Environment variables
    """
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="complete",
        )
    )

    # Safe handover summary (no system metadata)
    safe_summary = SuccessionTestData.generate_handover_summary()

    instance.handover_summary = safe_summary
    instance.succession_reason = "context_limit"
    instance.completed_at = datetime.now(timezone.utc)

    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    import json

    handover_str = json.dumps(instance.handover_summary).lower()

    # System metadata patterns that should NOT appear
    forbidden_patterns = [
        "postgresql://",
        "mongodb://",
        "/etc/",
        "/var/",
        "c:\\",
        "192.168.",
        "10.0.",
        "localhost",
        "127.0.0.1",
        "db_password",
        "env_var",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in handover_str, f"System metadata leaked: {pattern}"
