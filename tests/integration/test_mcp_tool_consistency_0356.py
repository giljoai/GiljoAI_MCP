"""
TDD Tests for MCP Tool Consistency (Handover 0356 - RED Phase)

Handover 0356: MCP Tool Tenant & Identity Consistency

This test suite documents the expected behavior for:
1. Tenant key consistency across all MCP tools
2. Identity naming standardization (agent_id vs job_id vs orchestrator_id)
3. Service-schema alignment for tenant isolation

These tests WILL FAIL initially (RED phase) because the issues exist.
After implementation (GREEN phase), all tests should pass.

Key Issues Tested:
- HIGH Priority: get_orchestrator_instructions uses legacy orchestrator_id instead of job_id
- MEDIUM Priority: 7 tools missing tenant_key in MCP schema
  (report_progress, complete_job, report_error,
   send_message, receive_messages, list_messages, gil_handover)
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.message_service import MessageService


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def multi_tenant_setup(db_session, db_manager, tenant_manager):
    """
    Create two separate tenants with projects and jobs for cross-tenant testing.

    Tenant A: "tenant-a" with Product A, Project A, Job A, Execution A
    Tenant B: "tenant-b" with Product B, Project B, Job B, Execution B
    """
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    # Tenant A setup
    product_a = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        name="Product A",
        description="Product for tenant A",
        is_active=True,
    )
    db_session.add(product_a)
    await db_session.commit()
    await db_session.refresh(product_a)

    project_a = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        name="Project A",
        description="Project for tenant A",
        product_id=product_a.id,
        mission="Build feature A",
        status="active",
    )
    db_session.add(project_a)
    await db_session.commit()
    await db_session.refresh(project_a)

    job_a = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        project_id=project_a.id,
        mission="Implement feature A",
        job_type="orchestrator",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job_a)

    exec_a = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job_a.job_id,
        tenant_key=tenant_a,
        agent_display_name="orchestrator",
        status="working",
        started_at=datetime.now(timezone.utc),
        progress=50,
    )
    db_session.add(exec_a)

    # Tenant B setup
    product_b = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        name="Product B",
        description="Product for tenant B",
        is_active=True,
    )
    db_session.add(product_b)
    await db_session.commit()
    await db_session.refresh(product_b)

    project_b = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        name="Project B",
        description="Project for tenant B",
        product_id=product_b.id,
        mission="Build feature B",
        status="active",
    )
    db_session.add(project_b)
    await db_session.commit()
    await db_session.refresh(project_b)

    job_b = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        project_id=project_b.id,
        mission="Implement feature B",
        job_type="orchestrator",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job_b)

    exec_b = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job_b.job_id,
        tenant_key=tenant_b,
        agent_display_name="orchestrator",
        status="working",
        started_at=datetime.now(timezone.utc),
        progress=25,
    )
    db_session.add(exec_b)

    await db_session.commit()
    await db_session.refresh(job_a)
    await db_session.refresh(exec_a)
    await db_session.refresh(job_b)
    await db_session.refresh(exec_b)

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
        "db_manager": db_manager,
        "tenant_manager": tenant_manager,
    }


# ============================================================================
# TEST 1: HIGH PRIORITY - Identity Naming (orchestrator_id → job_id)
# ============================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_uses_job_id_not_orchestrator_id(db_manager):
    """
    Test: get_orchestrator_instructions should use job_id (not orchestrator_id)

    Issue: MCP schema defines "orchestrator_id" but 0366 identity model uses:
    - job_id = work order (AgentJob)
    - agent_id = executor (AgentExecution)

    Expected (after fix):
    - MCP schema parameter: "job_id" (not "orchestrator_id")
    - Description: "Orchestrator job UUID (work order identifier)"

    This test WILL FAIL initially because the schema still uses orchestrator_id.
    """
    import inspect

    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    tenant_manager = TenantManager()
    tool_accessor = ToolAccessor(db_manager, tenant_manager)

    # Get method signature
    sig = inspect.signature(tool_accessor.get_orchestrator_instructions)
    params = list(sig.parameters.keys())

    # Assert: Should accept job_id (not orchestrator_id)
    assert "job_id" in params, (
        f"get_orchestrator_instructions should use 'job_id' (not 'orchestrator_id'). Found params: {params}"
    )

    assert "orchestrator_id" not in params, (
        f"get_orchestrator_instructions should NOT use legacy 'orchestrator_id'. Found params: {params}"
    )


@pytest.mark.asyncio
async def test_mcp_schema_has_no_orchestrator_id_references():
    """
    Test: MCP HTTP schema should not reference orchestrator_id anywhere

    After fix, ALL tools should use the 0366 identity model:
    - job_id for work orders (AgentJob)
    - agent_id for executors (AgentExecution)

    This test WILL FAIL initially because get_orchestrator_instructions still uses orchestrator_id.
    """
    from pathlib import Path

    # Read MCP HTTP schema
    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Assert: No orchestrator_id references
    assert "orchestrator_id" not in content, (
        "MCP schema should not use legacy 'orchestrator_id' - use 'job_id' or 'agent_id' per 0366 model"
    )


# ============================================================================
# TEST 2: MEDIUM PRIORITY - Tenant Key in MCP Schemas
# ============================================================================


@pytest.mark.asyncio
async def test_report_progress_schema_requires_tenant_key():
    """
    Test: report_progress MCP schema should require tenant_key

    Issue: Schema defines job_id and progress, but missing tenant_key.
    Without tenant_key, cross-tenant access is possible.

    This test WILL FAIL initially because schema is missing tenant_key.
    """
    from pathlib import Path

    # Read MCP HTTP schema
    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Find report_progress tool definition
    assert '"name": "report_progress"' in content, "report_progress tool not found in schema"

    # Extract tool definition (simplified check)
    # After fix, should contain tenant_key in properties and required array
    start_idx = content.find('"name": "report_progress"')
    end_idx = content.find('{"name":', start_idx + 1)
    tool_def = content[start_idx:end_idx]

    # Assert: tenant_key in properties
    assert '"tenant_key"' in tool_def, "report_progress schema missing 'tenant_key' in properties"

    # Assert: tenant_key in required array (after job_id and progress)
    # This will fail because current schema only requires ["job_id", "progress"]
    assert (
        '"required": ["job_id", "progress", "tenant_key"]' in tool_def
        or '"required": ["job_id", "tenant_key", "progress"]' in tool_def
        or '"required": ["tenant_key", "job_id", "progress"]' in tool_def
    ), "report_progress schema missing 'tenant_key' in required array"


@pytest.mark.asyncio
async def test_complete_job_schema_requires_tenant_key():
    """
    Test: complete_job MCP schema should require tenant_key

    This test WILL FAIL initially because schema is missing tenant_key.
    """
    from pathlib import Path

    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Find complete_job tool definition
    start_idx = content.find('"name": "complete_job"')
    end_idx = content.find('{"name":', start_idx + 1)
    tool_def = content[start_idx:end_idx]

    # Assert: tenant_key in properties
    assert '"tenant_key"' in tool_def, "complete_job schema missing 'tenant_key' in properties"

    # Assert: tenant_key in required array
    assert '"tenant_key"' in tool_def.split('"required":')[1].split("]")[0], (
        "complete_job schema missing 'tenant_key' in required array"
    )


@pytest.mark.asyncio
async def test_report_error_schema_requires_tenant_key():
    """
    Test: report_error MCP schema should require tenant_key

    This test WILL FAIL initially because schema is missing tenant_key.
    """
    from pathlib import Path

    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Find report_error tool definition
    start_idx = content.find('"name": "report_error"')
    end_idx = content.find('{"name":', start_idx + 1)
    tool_def = content[start_idx:end_idx]

    # Assert: tenant_key in properties
    assert '"tenant_key"' in tool_def, "report_error schema missing 'tenant_key' in properties"

    # Assert: tenant_key in required array
    assert '"tenant_key"' in tool_def.split('"required":')[1].split("]")[0], (
        "report_error schema missing 'tenant_key' in required array"
    )


@pytest.mark.asyncio
async def test_send_message_schema_requires_tenant_key():
    """
    Test: send_message MCP schema should require tenant_key

    This test WILL FAIL initially because schema is missing tenant_key.
    """
    from pathlib import Path

    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Find send_message tool definition
    start_idx = content.find('"name": "send_message"')
    end_idx = content.find('{"name":', start_idx + 1)
    tool_def = content[start_idx:end_idx]

    # Assert: tenant_key in properties
    assert '"tenant_key"' in tool_def, "send_message schema missing 'tenant_key' in properties"

    # Assert: tenant_key in required array
    assert '"tenant_key"' in tool_def.split('"required":')[1].split("]")[0], (
        "send_message schema missing 'tenant_key' in required array"
    )


@pytest.mark.asyncio
async def test_receive_messages_schema_requires_tenant_key():
    """
    Test: receive_messages MCP schema should require tenant_key

    This test WILL FAIL initially because schema is missing tenant_key.
    """
    from pathlib import Path

    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Find receive_messages tool definition
    start_idx = content.find('"name": "receive_messages"')
    end_idx = content.find('{"name":', start_idx + 1)
    tool_def = content[start_idx:end_idx]

    # Assert: tenant_key in properties
    assert '"tenant_key"' in tool_def, "receive_messages schema missing 'tenant_key' in properties"

    # Assert: tenant_key in required array
    assert '"tenant_key"' in tool_def.split('"required":')[1].split("]")[0], (
        "receive_messages schema missing 'tenant_key' in required array"
    )


@pytest.mark.asyncio
async def test_list_messages_schema_requires_tenant_key():
    """
    Test: list_messages MCP schema should require tenant_key

    This test WILL FAIL initially because schema is missing tenant_key.
    """
    from pathlib import Path

    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Find list_messages tool definition
    start_idx = content.find('"name": "list_messages"')
    end_idx = content.find('{"name":', start_idx + 1)
    tool_def = content[start_idx:end_idx]

    # Assert: tenant_key in properties
    assert '"tenant_key"' in tool_def, "list_messages schema missing 'tenant_key' in properties"

    # Assert: tenant_key in required array
    assert '"tenant_key"' in tool_def.split('"required":')[1].split("]")[0], (
        "list_messages schema missing 'tenant_key' in required array"
    )


@pytest.mark.asyncio
async def test_gil_handover_schema_requires_tenant_key():
    """
    Test: gil_handover MCP schema should require tenant_key

    This test WILL FAIL initially because schema is missing tenant_key.
    """
    from pathlib import Path

    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Find gil_handover tool definition
    start_idx = content.find('"name": "gil_handover"')
    end_idx = content.find('{"name":', start_idx + 1)
    tool_def = content[start_idx:end_idx]

    # Assert: tenant_key in properties
    assert '"tenant_key"' in tool_def, "gil_handover schema missing 'tenant_key' in properties"

    # Assert: tenant_key in required array
    assert '"tenant_key"' in tool_def.split('"required":')[1].split("]")[0], (
        "gil_handover schema missing 'tenant_key' in required array"
    )


# ============================================================================
# TEST 3: Service-Schema Alignment (Tenant Key Flow)
# ============================================================================


@pytest.mark.asyncio
async def test_tool_accessor_passes_tenant_key_to_report_progress(db_manager):
    """
    Test: ToolAccessor.report_progress should accept and pass tenant_key to service layer

    This test WILL FAIL initially because ToolAccessor may not have tenant_key parameter.
    """
    import inspect

    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    tenant_manager = TenantManager()
    tool_accessor = ToolAccessor(db_manager, tenant_manager)

    # Get method signature
    sig = inspect.signature(tool_accessor.report_progress)
    params = list(sig.parameters.keys())

    # Assert: Should accept tenant_key
    assert "tenant_key" in params, f"ToolAccessor.report_progress should accept 'tenant_key'. Found params: {params}"


@pytest.mark.asyncio
async def test_tool_accessor_passes_tenant_key_to_complete_job(db_manager):
    """
    Test: ToolAccessor.complete_job should accept and pass tenant_key to service layer

    This test WILL FAIL initially because ToolAccessor may not have tenant_key parameter.
    """
    import inspect

    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    tenant_manager = TenantManager()
    tool_accessor = ToolAccessor(db_manager, tenant_manager)

    # Get method signature
    sig = inspect.signature(tool_accessor.complete_job)
    params = list(sig.parameters.keys())

    # Assert: Should accept tenant_key
    assert "tenant_key" in params, f"ToolAccessor.complete_job should accept 'tenant_key'. Found params: {params}"


@pytest.mark.asyncio
async def test_tool_accessor_passes_tenant_key_to_report_error(db_manager):
    """
    Test: ToolAccessor.report_error should accept and pass tenant_key to service layer

    This test WILL FAIL initially because ToolAccessor may not have tenant_key parameter.
    """
    import inspect

    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    tenant_manager = TenantManager()
    tool_accessor = ToolAccessor(db_manager, tenant_manager)

    # Get method signature
    sig = inspect.signature(tool_accessor.report_error)
    params = list(sig.parameters.keys())

    # Assert: Should accept tenant_key
    assert "tenant_key" in params, f"ToolAccessor.report_error should accept 'tenant_key'. Found params: {params}"


# ============================================================================
# TEST 4: Cross-Tenant Security
# ============================================================================


@pytest.mark.asyncio
async def test_report_progress_rejects_cross_tenant_access(multi_tenant_setup, db_manager):
    """
    Test: report_progress should reject cross-tenant access

    Scenario: Tenant A tries to report progress on Tenant B's job
    Expected: Access denied (tenant_key mismatch)

    This test WILL FAIL initially if tenant_key is not enforced in the service layer.
    """
    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    setup = multi_tenant_setup
    tenant_manager = TenantManager()
    tool_accessor = ToolAccessor(db_manager, tenant_manager)

    # Act: Tenant A tries to report progress on Tenant B's job
    result = await tool_accessor.report_progress(
        job_id=setup["job_b"].job_id,  # Tenant B's job
        progress={"percent": 75},
        tenant_key=setup["tenant_a"],  # Tenant A's key (mismatch!)
    )

    # Assert: Access denied
    assert result["status"] == "error", "Cross-tenant report_progress should be rejected"
    assert "tenant" in result.get("error", "").lower() or "not found" in result.get("error", "").lower(), (
        f"Error should mention tenant mismatch. Got: {result.get('error')}"
    )


@pytest.mark.asyncio
async def test_send_message_rejects_cross_tenant_access(multi_tenant_setup, db_session, db_manager, tenant_manager):
    """
    Test: send_message should reject cross-tenant message delivery

    Scenario: Tenant A tries to send message to Tenant B's agent
    Expected: Access denied or message not delivered

    This test WILL FAIL initially if tenant_key is not enforced in MessageService.
    """
    setup = multi_tenant_setup

    msg_service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    # Act: Tenant A tries to send message to Tenant B's agent
    result = await msg_service.send_message(
        to_agents=[setup["exec_b"].agent_id],  # Tenant B's agent
        content="Secret message from Tenant A",
        project_id=setup["project_b"].id,  # Tenant B's project
        from_agent="orchestrator",
        tenant_key=setup["tenant_a"],  # Tenant A's key (mismatch!)
    )

    # Assert: Should fail (either explicit error or message not sent)
    # After fix, service should validate that to_agents belong to tenant_key
    assert result.get("success") is False or result.get("sent_count", 0) == 0, (
        "Cross-tenant send_message should be rejected"
    )


@pytest.mark.asyncio
async def test_receive_messages_rejects_cross_tenant_access(multi_tenant_setup, db_session, db_manager, tenant_manager):
    """
    Test: receive_messages should reject cross-tenant message access

    Scenario:
    1. Send message to Tenant B's agent (using Tenant B's key)
    2. Tenant A tries to receive Tenant B's messages (using Tenant A's key)
    Expected: Tenant A receives no messages

    This test WILL FAIL initially if tenant_key is not enforced in MessageService.
    """
    setup = multi_tenant_setup

    msg_service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    # Arrange: Send message to Tenant B's agent using Tenant B's key
    await msg_service.send_message(
        to_agents=[setup["exec_b"].agent_id],
        content="Secret message for Tenant B",
        project_id=setup["project_b"].id,
        from_agent="orchestrator",
        tenant_key=setup["tenant_b"],  # Correct tenant key
    )

    # Act: Tenant A tries to receive Tenant B's messages
    messages = await msg_service.receive_messages(
        agent_id=setup["exec_b"].agent_id,  # Tenant B's agent
        tenant_key=setup["tenant_a"],  # Tenant A's key (mismatch!)
    )

    # Assert: No messages returned (cross-tenant access blocked)
    assert len(messages) == 0, f"Cross-tenant receive_messages should return no messages. Got {len(messages)} messages."


# ============================================================================
# TEST 5: Tool Signature Consistency Documentation
# ============================================================================


@pytest.mark.asyncio
async def test_all_tenant_scoped_tools_have_tenant_key():
    """
    Test: All tenant-scoped MCP tools should declare tenant_key

    Tenant-scoped tools (operate on tenant data):
    - report_progress
    - complete_job
    - report_error
    - send_message
    - receive_messages
    - list_messages
    - gil_handover
    - get_orchestrator_instructions
    - get_agent_mission
    - orchestrate_project
    - fetch_context

    This is a documentation test that enforces the contract.
    This test WILL FAIL initially for tools missing tenant_key.
    """
    from pathlib import Path

    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    tenant_scoped_tools = [
        "report_progress",
        "complete_job",
        "report_error",
        "send_message",
        "receive_messages",
        "list_messages",
        "gil_handover",
        "get_orchestrator_instructions",
        "get_agent_mission",
        "fetch_context",
    ]

    for tool_name in tenant_scoped_tools:
        # Find tool definition
        start_idx = content.find(f'"name": "{tool_name}"')
        assert start_idx != -1, f"Tool {tool_name} not found in MCP schema"

        end_idx = content.find('{"name":', start_idx + 1)
        if end_idx == -1:
            end_idx = len(content)

        tool_def = content[start_idx:end_idx]

        # Assert: tenant_key in properties
        assert '"tenant_key"' in tool_def, f"Tool {tool_name} missing 'tenant_key' in properties"

        # Assert: tenant_key in required array
        required_section = tool_def.split('"required":')[1].split("]")[0] if '"required":' in tool_def else ""
        assert '"tenant_key"' in required_section, f"Tool {tool_name} missing 'tenant_key' in required array"


@pytest.mark.asyncio
async def test_identity_parameter_consistency():
    """
    Test: Verify identity parameters follow 0366 model consistently

    0366 Identity Model:
    - job_id = AgentJob UUID (work order)
    - agent_id = AgentExecution UUID (executor instance)

    Tools should use:
    - job_id when operating on work orders (complete_job, report_progress)
    - agent_id when targeting executors (receive_messages, send_message)

    This test documents the expected contract.
    This test WILL FAIL initially if any tool uses orchestrator_id.
    """
    from pathlib import Path

    mcp_http_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_http.py")
    content = mcp_http_path.read_text()

    # Tools that should use agent_id (executor-targeted operations)
    agent_id_tools = [
        "receive_messages",
        "send_message",
        "list_messages",
    ]

    # Tools that should use job_id (work order operations)
    job_id_tools = [
        "report_progress",
        "complete_job",
        "report_error",
        "get_orchestrator_instructions",  # Should be job_id, NOT orchestrator_id
        "gil_handover",
    ]

    # Verify agent_id tools
    for tool_name in agent_id_tools:
        start_idx = content.find(f'"name": "{tool_name}"')
        if start_idx == -1:
            continue  # Tool may not exist yet

        end_idx = content.find('{"name":', start_idx + 1)
        if end_idx == -1:
            end_idx = len(content)

        tool_def = content[start_idx:end_idx]

        # Should have agent_id
        assert '"agent_id"' in tool_def, f"Tool {tool_name} should use 'agent_id' (executor identifier)"

    # Verify job_id tools
    for tool_name in job_id_tools:
        start_idx = content.find(f'"name": "{tool_name}"')
        assert start_idx != -1, f"Tool {tool_name} not found in schema"

        end_idx = content.find('{"name":', start_idx + 1)
        if end_idx == -1:
            end_idx = len(content)

        tool_def = content[start_idx:end_idx]

        # Should have job_id
        assert '"job_id"' in tool_def, f"Tool {tool_name} should use 'job_id' (work order identifier)"

        # Should NOT have orchestrator_id
        assert '"orchestrator_id"' not in tool_def, (
            f"Tool {tool_name} should NOT use legacy 'orchestrator_id' - use 'job_id'"
        )


# ============================================================================
# TEST 6: Backward Compatibility Check
# ============================================================================


@pytest.mark.asyncio
async def test_no_tools_rely_on_implicit_tenant_context(db_manager, tenant_manager):
    """
    Test: No tools should rely on implicit TenantManager context for tenant_key

    After 0356, ALL tenant-scoped tools must accept explicit tenant_key parameter.
    Implicit fallback to TenantManager.get_current_tenant() is deprecated.

    This test verifies that all tools explicitly require tenant_key in their signatures.
    This is a DESIGN ENFORCEMENT test to prevent future regressions.
    """
    import inspect

    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    tool_accessor = ToolAccessor(db_manager, tenant_manager)

    # Tools that MUST have explicit tenant_key
    tenant_scoped_methods = [
        "report_progress",
        "complete_job",
        "report_error",
        "get_orchestrator_instructions",
        "get_agent_mission",
    ]

    for method_name in tenant_scoped_methods:
        if not hasattr(tool_accessor, method_name):
            continue  # Method may not exist yet

        method = getattr(tool_accessor, method_name)
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        # Assert: tenant_key is a parameter
        assert "tenant_key" in params, (
            f"ToolAccessor.{method_name} must accept explicit 'tenant_key' (no implicit context). Found params: {params}"
        )
