"""
Tenant isolation regression tests for OrchestrationService (BATCH 1 Security Fix).

Verifies that cross-tenant data leaks are prevented for:
- report_progress() AgentJob lookup, AgentTodoItem DELETE/SELECT (requires tenant_key filter)
- get_agent_mission() Project lookup (replaced session.get with tenant-scoped query)
- acknowledge_job() AgentJob lookup + Project lookup (requires tenant_key filter)
- complete_job() AgentExecution other_active_stmt (requires tenant_key filter)
- report_error() AgentJob lookup (requires tenant_key filter)

Test Strategy:
- Create entities in two tenants (A and B)
- Attempt cross-tenant operations from tenant A against tenant B's data
- Verify all cross-tenant attempts are blocked (ResourceNotFoundError)
- Verify same-tenant operations succeed

Follows patterns from: test_project_tenant_isolation_regression.py
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob, AgentTodoItem
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture(scope="function")
async def two_tenant_orchestration(db_session, db_manager):
    """
    Create orchestration entities in two separate tenants for isolation testing.

    Tenant A: product_a, project_a, job_a, execution_a (active, working)
    Tenant B: product_b, project_b, job_b, execution_b (active, working)
    """
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    # Create products
    product_a = Product(
        id=str(uuid.uuid4()),
        name="Tenant A Product",
        description="Product for tenant A",
        tenant_key=tenant_a,
        is_active=True,
    )
    product_b = Product(
        id=str(uuid.uuid4()),
        name="Tenant B Product",
        description="Product for tenant B",
        tenant_key=tenant_b,
        is_active=True,
    )
    db_session.add(product_a)
    db_session.add(product_b)
    await db_session.commit()

    # Create projects (required FK for agent jobs)
    project_a = Project(
        id=str(uuid.uuid4()),
        name="Tenant A Project",
        description="Project for tenant A",
        mission="Tenant A mission",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="active",
        implementation_launched_at=datetime.now(timezone.utc),
    )
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Tenant B Project",
        description="Project for tenant B",
        mission="Tenant B mission",
        tenant_key=tenant_b,
        product_id=product_b.id,
        status="active",
        implementation_launched_at=datetime.now(timezone.utc),
    )
    db_session.add(project_a)
    db_session.add(project_b)
    await db_session.commit()

    # Create agent jobs
    job_a = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        project_id=project_a.id,
        job_type="implementer",
        mission="Implement feature for tenant A",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    job_b = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        project_id=project_b.id,
        job_type="implementer",
        mission="Implement feature for tenant B",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    db_session.add(job_a)
    db_session.add(job_b)
    await db_session.commit()

    # Create agent executions
    exec_a = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job_a.job_id,
        tenant_key=tenant_a,
        agent_display_name="implementer",
        status="working",
        started_at=datetime.now(timezone.utc),
        mission_acknowledged_at=datetime.now(timezone.utc),
    )
    exec_b = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job_b.job_id,
        tenant_key=tenant_b,
        agent_display_name="implementer",
        status="working",
        started_at=datetime.now(timezone.utc),
        mission_acknowledged_at=datetime.now(timezone.utc),
    )
    db_session.add(exec_a)
    db_session.add(exec_b)
    await db_session.commit()

    for obj in [job_a, job_b, exec_a, exec_b]:
        await db_session.refresh(obj)

    # Create service
    tenant_manager = TenantManager()
    service = OrchestrationService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "product_a": product_a,
        "product_b": product_b,
        "project_a": project_a,
        "project_b": project_b,
        "job_a": job_a,
        "job_b": job_b,
        "exec_a": exec_a,
        "exec_b": exec_b,
        "service": service,
    }


# ============================================================================
# report_progress() -- Cross-Tenant Tests
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_report_progress_blocks_cross_tenant(db_session, two_tenant_orchestration):
    """
    REGRESSION: report_progress() must filter AgentJob by tenant_key.

    Bug: AgentJob lookup had no tenant_key filter, allowing any tenant to
    report progress on another tenant's job if they knew the job_id.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_b = two_tenant_orchestration["job_b"]
    service = two_tenant_orchestration["service"]

    with pytest.raises(ResourceNotFoundError):
        await service.report_progress(
            job_id=job_b.job_id,
            todo_items=[{"content": "Cross-tenant task", "status": "pending"}],
            tenant_key=tenant_a,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_report_progress_same_tenant_succeeds(db_session, two_tenant_orchestration):
    """
    Verify that same-tenant report_progress still works correctly.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_a = two_tenant_orchestration["job_a"]
    service = two_tenant_orchestration["service"]

    result = await service.report_progress(
        job_id=job_a.job_id,
        todo_items=[{"content": "Same-tenant task", "status": "in_progress"}],
        tenant_key=tenant_a,
    )

    assert result.status == "success"


# ============================================================================
# get_agent_mission() -- Cross-Tenant Tests
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_agent_mission_blocks_cross_tenant(db_session, two_tenant_orchestration):
    """
    REGRESSION: get_agent_mission() must scope Project lookup by tenant_key.

    Bug: Used session.get(Project, job.project_id) which fetches by PK only,
    allowing cross-tenant project data to be included in mission response.
    Now uses select().where(Project.tenant_key == tenant_key).
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_b = two_tenant_orchestration["job_b"]
    service = two_tenant_orchestration["service"]

    # Tenant A tries to get mission for tenant B's job
    with pytest.raises(ResourceNotFoundError):
        await service.get_agent_mission(
            job_id=job_b.job_id,
            tenant_key=tenant_a,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_agent_mission_same_tenant_succeeds(db_session, two_tenant_orchestration):
    """
    Verify that same-tenant get_agent_mission still works correctly.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_a = two_tenant_orchestration["job_a"]
    service = two_tenant_orchestration["service"]

    result = await service.get_agent_mission(
        job_id=job_a.job_id,
        tenant_key=tenant_a,
    )

    assert result.job_id == job_a.job_id
    assert "Implement feature for tenant A" in result.mission


# ============================================================================
# acknowledge_job() -- Cross-Tenant Tests
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_acknowledge_job_blocks_cross_tenant(db_session, two_tenant_orchestration):
    """
    REGRESSION: acknowledge_job() must filter AgentJob AND Project by tenant_key.

    Bug: AgentJob lookup and session.get(Project) had no tenant_key filter,
    allowing cross-tenant job acknowledgment.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_b = two_tenant_orchestration["job_b"]
    service = two_tenant_orchestration["service"]

    with pytest.raises(ResourceNotFoundError):
        await service.acknowledge_job(
            job_id=job_b.job_id,
            tenant_key=tenant_a,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_acknowledge_job_same_tenant_succeeds(db_session, two_tenant_orchestration):
    """
    Verify that same-tenant acknowledge_job still works correctly.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_a = two_tenant_orchestration["job_a"]
    service = two_tenant_orchestration["service"]

    result = await service.acknowledge_job(
        job_id=job_a.job_id,
        tenant_key=tenant_a,
    )

    assert result.job is not None


# ============================================================================
# complete_job() -- Cross-Tenant Tests
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_complete_job_blocks_cross_tenant(db_session, two_tenant_orchestration):
    """
    REGRESSION: complete_job() must scope AgentExecution queries by tenant_key.

    Bug: The other_active_stmt for decommissioning sibling executions had
    no tenant_key filter, potentially decommissioning cross-tenant executions.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_b = two_tenant_orchestration["job_b"]
    exec_b = two_tenant_orchestration["exec_b"]
    service = two_tenant_orchestration["service"]

    with pytest.raises(ResourceNotFoundError):
        await service.complete_job(
            job_id=job_b.job_id,
            result={"output": "Cross-tenant completion"},
            tenant_key=tenant_a,
        )

    # Verify tenant B's execution was NOT modified
    await db_session.refresh(exec_b)
    assert exec_b.status == "working", (
        "Cross-tenant complete_job modified another tenant's execution!"
    )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_complete_job_same_tenant_succeeds(db_session, two_tenant_orchestration):
    """
    Verify that same-tenant complete_job still works correctly.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_a = two_tenant_orchestration["job_a"]
    service = two_tenant_orchestration["service"]

    result = await service.complete_job(
        job_id=job_a.job_id,
        result={"output": "Same-tenant completion"},
        tenant_key=tenant_a,
    )

    assert result.job_id == job_a.job_id


# ============================================================================
# report_error() -- Cross-Tenant Tests
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_report_error_blocks_cross_tenant(db_session, two_tenant_orchestration):
    """
    REGRESSION: report_error() must filter AgentJob by tenant_key.

    Bug: AgentJob lookup had no tenant_key filter, allowing any tenant to
    report errors on another tenant's job.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_b = two_tenant_orchestration["job_b"]
    exec_b = two_tenant_orchestration["exec_b"]
    service = two_tenant_orchestration["service"]

    with pytest.raises(ResourceNotFoundError):
        await service.report_error(
            job_id=job_b.job_id,
            error="Cross-tenant error report",
            tenant_key=tenant_a,
        )

    # Verify tenant B's execution was NOT modified
    await db_session.refresh(exec_b)
    assert exec_b.status == "working", (
        "Cross-tenant report_error modified another tenant's execution!"
    )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_report_error_same_tenant_succeeds(db_session, two_tenant_orchestration):
    """
    Verify that same-tenant report_error still works correctly.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_a = two_tenant_orchestration["job_a"]
    service = two_tenant_orchestration["service"]

    result = await service.report_error(
        job_id=job_a.job_id,
        error="Same-tenant error report",
        tenant_key=tenant_a,
    )

    assert result.job_id == job_a.job_id


# ============================================================================
# Combined -- Full Cross-Tenant Audit
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_orchestration_service_cross_tenant_audit(db_session, two_tenant_orchestration):
    """
    Integration test: Attempt every cross-tenant orchestration operation from
    tenant A against tenant B's data. All must be blocked.
    """
    tenant_a = two_tenant_orchestration["tenant_a"]
    job_b = two_tenant_orchestration["job_b"]
    exec_b = two_tenant_orchestration["exec_b"]
    service = two_tenant_orchestration["service"]

    violations = []

    # 1. report_progress cross-tenant
    try:
        await service.report_progress(
            job_id=job_b.job_id,
            todo_items=[{"content": "Cross-tenant", "status": "pending"}],
            tenant_key=tenant_a,
        )
        violations.append("report_progress() allowed cross-tenant progress report")
    except (ResourceNotFoundError, ValidationError):
        pass

    # 2. get_agent_mission cross-tenant
    try:
        await service.get_agent_mission(
            job_id=job_b.job_id,
            tenant_key=tenant_a,
        )
        violations.append("get_agent_mission() allowed cross-tenant mission fetch")
    except (ResourceNotFoundError, ValidationError):
        pass

    # 3. acknowledge_job cross-tenant
    try:
        await service.acknowledge_job(
            job_id=job_b.job_id,
            tenant_key=tenant_a,
        )
        violations.append("acknowledge_job() allowed cross-tenant acknowledgment")
    except (ResourceNotFoundError, ValidationError):
        pass

    # 4. complete_job cross-tenant
    try:
        await service.complete_job(
            job_id=job_b.job_id,
            result={"output": "Cross-tenant"},
            tenant_key=tenant_a,
        )
        violations.append("complete_job() allowed cross-tenant completion")
    except (ResourceNotFoundError, ValidationError):
        pass

    # 5. report_error cross-tenant
    try:
        await service.report_error(
            job_id=job_b.job_id,
            error="Cross-tenant error",
            tenant_key=tenant_a,
        )
        violations.append("report_error() allowed cross-tenant error report")
    except (ResourceNotFoundError, ValidationError):
        pass

    # Verify tenant B's execution was NEVER modified
    await db_session.refresh(exec_b)
    if exec_b.status != "working":
        violations.append(
            f"Tenant B execution status changed from 'working' to '{exec_b.status}'"
        )

    assert len(violations) == 0, (
        "CRITICAL: Tenant isolation violated!\nViolations:\n"
        + "\n".join(f"- {v}" for v in violations)
    )
