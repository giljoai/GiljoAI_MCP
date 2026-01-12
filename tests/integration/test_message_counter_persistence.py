"""
Integration test for message counter persistence across page refresh.

Handover 0294 - Database Expert Agent

Tests that message counters persist in the database and can be recomputed
on page refresh by loading agent data with JSONB message arrays.
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.auth import User


@pytest.mark.asyncio
async def test_message_counters_persist_after_page_refresh(async_db_session: AsyncSession):
    """
    Test that message counters are correctly computed from database after page refresh.

    Scenario:
    1. Create project with agents
    2. Send messages (stored in AgentExecution.messages JSONB)
    3. Simulate page refresh by re-querying agents
    4. Verify counters are correctly computed from JSONB data

    EXPECTED TO FAIL INITIALLY - This test documents the desired behavior.
    """
    # ============================================================================
    # Setup: Create test data
    # ============================================================================
    tenant_key = "test_tenant_294"

    # Create user
    user = User(
        id="user-294",
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        tenant_key=tenant_key,
        role="admin"
    )
    async_db_session.add(user)

    # Create product
    product = Product(
        id="product-294",
        name="Test Product",
        description="Test product for counter persistence",
        tenant_key=tenant_key,
        created_by="user-294"
    )
    async_db_session.add(product)

    # Create project
    project = Project(
        id="project-294",
        name="Test Project",
        description="Test project for counter persistence",
        product_id="product-294",
        tenant_key=tenant_key,
        created_by="user-294"
    )
    async_db_session.add(project)

    # Create orchestrator agent (sender)
    orchestrator = AgentExecution(
        job_id="orchestrator-294",
        tenant_key=tenant_key,
        project_id="project-294",
        agent_display_name="orchestrator",
        agent_name="Orchestrator",
        mission="Orchestrate the project",
        status="working",
        tool_type="claude-code",
        messages=[]  # Start empty
    )
    async_db_session.add(orchestrator)

    # Create recipient agents
    implementer = AgentExecution(
        job_id="implementer-294",
        tenant_key=tenant_key,
        project_id="project-294",
        agent_display_name="implementer",
        agent_name="Backend Implementer",
        mission="Implement backend features",
        status="waiting",
        tool_type="claude-code",
        messages=[]
    )
    async_db_session.add(implementer)

    tester = AgentExecution(
        job_id="tester-294",
        tenant_key=tenant_key,
        project_id="project-294",
        agent_display_name="tester",
        agent_name="Integration Tester",
        mission="Run integration tests",
        status="waiting",
        tool_type="claude-code",
        messages=[]
    )
    async_db_session.add(tester)

    await async_db_session.commit()

    # ============================================================================
    # Action 1: Send messages (simulating message_service.send_message())
    # ============================================================================
    now = datetime.now(timezone.utc).isoformat()

    # Orchestrator sends 2 messages
    orchestrator.messages = [
        {
            "id": "msg-1",
            "from": "orchestrator",
            "to": "implementer-294",
            "direction": "outbound",
            "status": "sent",
            "text": "Please implement the feature",
            "priority": "high",
            "timestamp": now
        },
        {
            "id": "msg-2",
            "from": "orchestrator",
            "to": "tester-294",
            "direction": "outbound",
            "status": "sent",
            "text": "Please test the feature",
            "priority": "normal",
            "timestamp": now
        }
    ]

    # Implementer receives 1 message (waiting to read)
    implementer.messages = [
        {
            "id": "msg-1",
            "from": "orchestrator",
            "to": "implementer-294",
            "direction": "inbound",
            "status": "pending",  # UNREAD
            "text": "Please implement the feature",
            "priority": "high",
            "timestamp": now
        }
    ]

    # Tester receives 1 message and acknowledges it
    tester.messages = [
        {
            "id": "msg-2",
            "from": "orchestrator",
            "to": "tester-294",
            "direction": "inbound",
            "status": "acknowledged",  # READ
            "text": "Please test the feature",
            "priority": "normal",
            "timestamp": now
        }
    ]

    await async_db_session.commit()

    # ============================================================================
    # Action 2: Simulate page refresh - re-query agents from database
    # ============================================================================
    await async_db_session.expire_all()  # Clear session cache

    result = await async_db_session.execute(
        select(AgentExecution)
        .where(AgentExecution.project_id == "project-294")
        .where(AgentExecution.tenant_key == tenant_key)
        .order_by(AgentExecution.agent_display_name)
    )
    refreshed_agents = result.scalars().all()

    # ============================================================================
    # Assertions: Verify counters can be computed from JSONB data
    # ============================================================================

    # Helper function (mimics frontend logic)
    def compute_counters(agent: AgentExecution):
        messages = agent.messages or []
        sent = sum(1 for m in messages if m.get("direction") == "outbound")
        waiting = sum(1 for m in messages if m.get("status") == "pending")
        acknowledged = sum(1 for m in messages if m.get("status") == "acknowledged")
        return {"sent": sent, "waiting": waiting, "acknowledged": acknowledged}

    # Find agents
    orch = next(a for a in refreshed_agents if a.agent_display_name == "orchestrator")
    impl = next(a for a in refreshed_agents if a.agent_display_name == "implementer")
    test = next(a for a in refreshed_agents if a.agent_display_name == "tester")

    # Verify orchestrator counters
    orch_counters = compute_counters(orch)
    assert orch_counters["sent"] == 2, f"Orchestrator should have 2 sent messages, got {orch_counters['sent']}"
    assert orch_counters["waiting"] == 0, f"Orchestrator should have 0 waiting messages, got {orch_counters['waiting']}"
    assert orch_counters["acknowledged"] == 0, f"Orchestrator should have 0 acknowledged messages, got {orch_counters['acknowledged']}"

    # Verify implementer counters
    impl_counters = compute_counters(impl)
    assert impl_counters["sent"] == 0, f"Implementer should have 0 sent messages, got {impl_counters['sent']}"
    assert impl_counters["waiting"] == 1, f"Implementer should have 1 waiting message, got {impl_counters['waiting']}"
    assert impl_counters["acknowledged"] == 0, f"Implementer should have 0 acknowledged messages, got {impl_counters['acknowledged']}"

    # Verify tester counters
    test_counters = compute_counters(test)
    assert test_counters["sent"] == 0, f"Tester should have 0 sent messages, got {test_counters['sent']}"
    assert test_counters["waiting"] == 0, f"Tester should have 0 waiting messages, got {test_counters['waiting']}"
    assert test_counters["acknowledged"] == 1, f"Tester should have 1 acknowledged message, got {test_counters['acknowledged']}"


@pytest.mark.asyncio
async def test_table_view_endpoint_computes_message_counters(async_db_session: AsyncSession):
    """
    Test that table_view endpoint correctly computes message counters from JSONB.

    This verifies the backend logic that powers the /table-view API endpoint
    which is used by the frontend to populate agent data.
    """
    # ============================================================================
    # Setup: Create test data
    # ============================================================================
    tenant_key = "test_tenant_294_tv"

    # Create user
    user = User(
        id="user-294-tv",
        username="testuser_tv",
        email="test_tv@example.com",
        hashed_password="hashed",
        tenant_key=tenant_key,
        role="admin"
    )
    async_db_session.add(user)

    # Create product
    product = Product(
        id="product-294-tv",
        name="Test Product TV",
        description="Test product for table view",
        tenant_key=tenant_key,
        created_by="user-294-tv"
    )
    async_db_session.add(product)

    # Create project
    project = Project(
        id="project-294-tv",
        name="Test Project TV",
        description="Test project for table view",
        product_id="product-294-tv",
        tenant_key=tenant_key,
        created_by="user-294-tv"
    )
    async_db_session.add(project)

    # Create agent with messages
    now = datetime.now(timezone.utc).isoformat()
    agent = AgentExecution(
        job_id="agent-294-tv",
        tenant_key=tenant_key,
        project_id="project-294-tv",
        agent_display_name="implementer",
        agent_name="Test Implementer",
        mission="Test mission",
        status="working",
        tool_type="claude-code",
        messages=[
            {"id": "msg-1", "status": "pending", "direction": "inbound", "timestamp": now},
            {"id": "msg-2", "status": "pending", "direction": "inbound", "timestamp": now},
            {"id": "msg-3", "status": "acknowledged", "direction": "inbound", "timestamp": now},
            {"id": "msg-4", "status": "sent", "direction": "outbound", "timestamp": now},
        ]
    )
    async_db_session.add(agent)

    await async_db_session.commit()

    # ============================================================================
    # Action: Query agent and compute counters (mimics table_view endpoint)
    # ============================================================================
    result = await async_db_session.execute(
        select(AgentExecution)
        .where(AgentExecution.project_id == "project-294-tv")
        .where(AgentExecution.tenant_key == tenant_key)
    )
    agents = result.scalars().all()

    assert len(agents) == 1, "Should have 1 agent"

    agent = agents[0]

    # Compute counters (mimics table_view.py lines 194-200)
    unread_count = 0
    acknowledged_count = 0
    total_messages = len(agent.messages) if agent.messages else 0

    if agent.messages:
        for msg in agent.messages:
            if msg.get("status") == "pending":
                unread_count += 1
            elif msg.get("status") == "acknowledged":
                acknowledged_count += 1

    # ============================================================================
    # Assertions: Verify counters match expected values
    # ============================================================================
    assert total_messages == 4, f"Should have 4 total messages, got {total_messages}"
    assert unread_count == 2, f"Should have 2 unread messages, got {unread_count}"
    assert acknowledged_count == 1, f"Should have 1 acknowledged message, got {acknowledged_count}"


@pytest.mark.asyncio
async def test_jsonb_query_filtering_for_unread_messages(async_db_session: AsyncSession):
    """
    Test JSONB path query filtering for agents with unread messages.

    This tests the database-level JSONB query capability used in table_view
    endpoint for filtering agents with unread messages (has_unread filter).
    """
    from sqlalchemy import func, and_

    tenant_key = "test_tenant_294_jsonb"

    # Create user
    user = User(
        id="user-294-jsonb",
        username="testuser_jsonb",
        email="test_jsonb@example.com",
        hashed_password="hashed",
        tenant_key=tenant_key,
        role="admin"
    )
    async_db_session.add(user)

    # Create product
    product = Product(
        id="product-294-jsonb",
        name="Test Product JSONB",
        description="Test product for JSONB queries",
        tenant_key=tenant_key,
        created_by="user-294-jsonb"
    )
    async_db_session.add(product)

    # Create project
    project = Project(
        id="project-294-jsonb",
        name="Test Project JSONB",
        description="Test project for JSONB queries",
        product_id="product-294-jsonb",
        tenant_key=tenant_key,
        created_by="user-294-jsonb"
    )
    async_db_session.add(project)

    now = datetime.now(timezone.utc).isoformat()

    # Agent 1: Has unread messages
    agent_with_unread = AgentExecution(
        job_id="agent-with-unread",
        tenant_key=tenant_key,
        project_id="project-294-jsonb",
        agent_display_name="implementer",
        agent_name="Agent With Unread",
        mission="Test mission",
        status="working",
        tool_type="claude-code",
        messages=[
            {"id": "msg-1", "status": "pending", "direction": "inbound", "timestamp": now},
            {"id": "msg-2", "status": "acknowledged", "direction": "inbound", "timestamp": now},
        ]
    )
    async_db_session.add(agent_with_unread)

    # Agent 2: All messages acknowledged
    agent_all_read = AgentExecution(
        job_id="agent-all-read",
        tenant_key=tenant_key,
        project_id="project-294-jsonb",
        agent_display_name="tester",
        agent_name="Agent All Read",
        mission="Test mission",
        status="working",
        tool_type="claude-code",
        messages=[
            {"id": "msg-3", "status": "acknowledged", "direction": "inbound", "timestamp": now},
            {"id": "msg-4", "status": "acknowledged", "direction": "inbound", "timestamp": now},
        ]
    )
    async_db_session.add(agent_all_read)

    # Agent 3: No messages
    agent_no_messages = AgentExecution(
        job_id="agent-no-messages",
        tenant_key=tenant_key,
        project_id="project-294-jsonb",
        agent_display_name="documenter",
        agent_name="Agent No Messages",
        mission="Test mission",
        status="working",
        tool_type="claude-code",
        messages=[]
    )
    async_db_session.add(agent_no_messages)

    await async_db_session.commit()

    # ============================================================================
    # Test JSONB path query (from table_view.py line 145-150)
    # ============================================================================
    query = select(AgentExecution).where(
        and_(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.project_id == "project-294-jsonb",
            func.jsonb_path_exists(
                AgentExecution.messages,
                '$[*] ? (@.status == "pending")'
            )
        )
    )

    result = await async_db_session.execute(query)
    agents_with_unread = result.scalars().all()

    # ============================================================================
    # Assertions: Only agent with pending messages should match
    # ============================================================================
    assert len(agents_with_unread) == 1, f"Should find 1 agent with unread messages, found {len(agents_with_unread)}"
    assert agents_with_unread[0].job_id == "agent-with-unread", "Should find the agent with unread messages"
