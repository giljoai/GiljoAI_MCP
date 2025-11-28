"""
Integration tests for message system schema issues (TDD RED phase)

These tests expose critical backend errors in the message system:
1. Message model schema mismatch (from_agent vs from_agent_id)
2. Message creation validation (to_agents vs to_agent)
3. SQLAlchemy session cleanup race condition

Tests written following strict TDD methodology:
- RED: Write failing test that exposes the bug
- GREEN: Fix code to make test pass
- REFACTOR: Clean up solution

Target: All tests should FAIL initially, then PASS after fixes
"""

import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy import select

from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.message_service import MessageService


class TestMessageSchemaFix:
    """
    Test suite for Error #1: Message model schema mismatch

    ISSUE: MessageService.list_messages() tries to access:
    - msg.from_agent (doesn't exist)
    - msg.to_agent (doesn't exist)
    - msg.type (doesn't exist)

    But Message model has:
    - to_agents (JSON list)
    - message_type (string)
    - meta_data (JSON dict with _from_agent)

    Expected behavior: list_messages should correctly map Message model fields
    """

    @pytest.mark.asyncio
    async def test_list_messages_returns_correct_schema(
        self,
        db_manager,
        tenant_manager
    ):
        """
        RED TEST: This should FAIL because list_messages tries to access
        non-existent fields (from_agent, to_agent, type)

        Expected failure: AttributeError: 'Message' object has no attribute 'from_agent'
        """
        from uuid import uuid4
        from src.giljo_mcp.models.products import Product
        from src.giljo_mcp.models.projects import Project

        # Arrange: Create test data in real database (no transaction)
        async with db_manager.get_session_async() as session:
            # Create product and project
            tenant_key = f"tk_test_{uuid4().hex[:16]}"
            product = Product(
                name=f"Test Product {uuid4().hex[:8]}",
                tenant_key=tenant_key,
                is_active=True,
            )
            session.add(product)
            await session.flush()

            project = Project(
                name=f"Test Project {uuid4().hex[:8]}",
                description="Test project for message schema validation",
                mission="Test mission for schema validation",
                product_id=product.id,
                tenant_key=tenant_key,
                status="active",
            )
            session.add(project)
            await session.flush()

            # Create message with correct schema
            message = Message(
                project_id=project.id,
                tenant_key=tenant_key,
                to_agents=["implementer", "analyzer"],
                content="Test message content",
                message_type="direct",
                priority="high",
                status="pending",
                meta_data={"_from_agent": "orchestrator"},
            )
            session.add(message)
            await session.commit()
            message_id = str(message.id)
            project_id = project.id

        # Act: List messages using MessageService
        service = MessageService(db_manager, tenant_manager)
        result = await service.list_messages(
            project_id=project_id,
            tenant_key=tenant_key,
        )

        # Assert: Should succeed and return correct schema
        assert result["success"] is True, f"Expected success=True, got {result}"
        assert result["count"] == 1, f"Expected 1 message, got {result['count']}"

        msg = result["messages"][0]

        # These assertions will reveal what fields are actually being returned
        assert "id" in msg, "Message should have 'id' field"
        assert msg["id"] == message_id, f"Expected message_id={message_id}, got {msg.get('id')}"

        # Check from_agent field (stored in meta_data._from_agent)
        assert "from_agent" in msg, "Message should have 'from_agent' field"
        assert msg["from_agent"] == "orchestrator", f"Expected from_agent='orchestrator', got {msg.get('from_agent')}"

        # Check to_agents field (JSON list in database)
        assert "to_agents" in msg, "Message should have 'to_agents' field"
        assert msg["to_agents"] == ["implementer", "analyzer"], f"Expected to_agents list, got {msg.get('to_agents')}"

        # Check type field (stored as message_type)
        assert "type" in msg, "Message should have 'type' field"
        assert msg["type"] == "direct", f"Expected type='direct', got {msg.get('type')}"

        # Check other fields
        assert msg["content"] == "Test message content"
        assert msg["status"] == "pending"
        assert msg["priority"] == "high"
        assert "created_at" in msg

    @pytest.mark.asyncio
    async def test_list_messages_with_multiple_messages(
        self,
        db_manager,
        tenant_manager
    ):
        """
        RED TEST: List multiple messages with different from_agent values

        This exposes the schema mismatch when processing multiple messages
        """
        from uuid import uuid4
        from src.giljo_mcp.models.products import Product
        from src.giljo_mcp.models.projects import Project

        # Arrange: Create test data and multiple messages in real database
        async with db_manager.get_session_async() as session:
            # Create product and project
            tenant_key = f"tk_test_{uuid4().hex[:16]}"
            product = Product(
                name=f"Test Product {uuid4().hex[:8]}",
                tenant_key=tenant_key,
                is_active=True,
            )
            session.add(product)
            await session.flush()

            project = Project(
                name=f"Test Project {uuid4().hex[:8]}",
                description="Test project for multiple messages",
                mission="Test mission for multiple messages",
                product_id=product.id,
                tenant_key=tenant_key,
                status="active",
            )
            session.add(project)
            await session.flush()

            # Create multiple messages
            messages = [
                Message(
                    project_id=project.id,
                    tenant_key=tenant_key,
                    to_agents=["implementer"],
                    content="Message 1",
                    message_type="direct",
                    priority="normal",
                    status="pending",
                    meta_data={"_from_agent": "orchestrator"},
                ),
                Message(
                    project_id=project.id,
                    tenant_key=tenant_key,
                    to_agents=["analyzer", "tester"],
                    content="Message 2",
                    message_type="broadcast",
                    priority="high",
                    status="pending",
                    meta_data={"_from_agent": "implementer"},
                ),
                Message(
                    project_id=project.id,
                    tenant_key=tenant_key,
                    to_agents=["orchestrator"],
                    content="Message 3",
                    message_type="direct",
                    priority="low",
                    status="acknowledged",
                    meta_data={"_from_agent": "analyzer"},
                ),
            ]
            session.add_all(messages)
            await session.commit()
            project_id = project.id

        # Act: List all messages
        service = MessageService(db_manager, tenant_manager)
        result = await service.list_messages(
            project_id=project_id,
            tenant_key=tenant_key,
        )

        # Assert: Should return all 3 messages with correct schema
        assert result["success"] is True
        assert result["count"] == 3

        # Verify each message has correct schema
        for msg in result["messages"]:
            assert "from_agent" in msg
            assert "to_agents" in msg
            assert isinstance(msg["to_agents"], list)
            assert "type" in msg
            assert msg["type"] in ["direct", "broadcast"]


class TestMessageCreationValidation:
    """
    Test suite for Error #2: Message creation validation

    ISSUE: API endpoint expects:
    - to_agents (plural, list)
    - content
    - project_id

    But some calls might use:
    - to_agent (singular)
    - message (instead of content)
    - priority

    Expected behavior: API should validate and enforce correct schema
    """

    @pytest.mark.asyncio
    async def test_send_message_api_with_correct_schema(
        self,
        async_client: AsyncClient,
        test_project,
        auth_headers
    ):
        """
        RED TEST: Verify API accepts correct schema (to_agents, content, project_id)

        This should PASS but we include it to verify correct behavior
        """
        # Arrange
        payload = {
            "to_agents": ["implementer", "analyzer"],
            "content": "Test message via API",
            "project_id": test_project.id,
            "message_type": "direct",
            "priority": "high",
        }

        # Act
        response = await async_client.post(
            "/api/messages/",
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["to_agents"] == ["implementer", "analyzer"]
        assert data["content"] == "Test message via API"
        assert data["message_type"] == "direct"
        assert data["priority"] == "high"

    @pytest.mark.asyncio
    async def test_send_message_api_rejects_wrong_schema(
        self,
        async_client: AsyncClient,
        test_project,
        auth_headers
    ):
        """
        RED TEST: Verify API rejects incorrect schema (to_agent singular, message instead of content)

        Expected: 422 validation error
        """
        # Arrange: Wrong schema (singular to_agent, message instead of content)
        wrong_payload = {
            "to_agent": "implementer",  # Wrong: should be to_agents (plural)
            "message": "Test message",   # Wrong: should be content
            "project_id": test_project.id,
            "priority": "normal",
        }

        # Act
        response = await async_client.post(
            "/api/messages/",
            json=wrong_payload,
            headers=auth_headers
        )

        # Assert: Should return 422 validation error
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
        error_detail = response.json()["detail"]

        # Verify error mentions missing required fields
        error_fields = [err["loc"][-1] for err in error_detail]
        assert "to_agents" in error_fields or "content" in error_fields, \
            f"Expected validation error for to_agents or content, got {error_fields}"

    @pytest.mark.asyncio
    async def test_send_message_api_missing_required_fields(
        self,
        async_client: AsyncClient,
        test_project,
        auth_headers
    ):
        """
        RED TEST: Verify API rejects payload missing required fields

        Expected: 422 validation error
        """
        # Arrange: Missing required fields
        incomplete_payload = {
            "priority": "normal",  # Missing to_agents, content, project_id
        }

        # Act
        response = await async_client.post(
            "/api/messages/",
            json=incomplete_payload,
            headers=auth_headers
        )

        # Assert: Should return 422 validation error
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"


class TestSessionCleanup:
    """
    Test suite for Error #3: SQLAlchemy session cleanup race condition

    ISSUE: IllegalStateChangeError: Method 'close()' can't be called here
    Location: database.py:198

    Root cause: Race condition in async session cleanup

    Expected behavior: Sessions should cleanup gracefully without race conditions
    """

    @pytest.mark.asyncio
    async def test_concurrent_message_operations_no_session_error(
        self,
        db_manager,
        tenant_manager,
        test_project,
        test_tenant_key
    ):
        """
        RED TEST: Run concurrent message operations to expose session cleanup race condition

        Expected failure: IllegalStateChangeError during concurrent operations
        """
        import asyncio

        service = MessageService(db_manager, tenant_manager)

        async def create_message(i: int):
            """Create a message (opens and closes a session)"""
            return await service.send_message(
                to_agents=[f"agent-{i}"],
                content=f"Message {i}",
                project_id=test_project.id,
                priority="normal",
            )

        async def list_messages():
            """List messages (opens and closes a session)"""
            return await service.list_messages(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
            )

        # Act: Run 10 concurrent operations (mix of creates and lists)
        tasks = []
        for i in range(5):
            tasks.append(create_message(i))
            tasks.append(list_messages())

        # This should complete without IllegalStateChangeError
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert: No session errors occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Check if it's the specific session error
                if "IllegalStateChangeError" in str(type(result)) or "close()" in str(result):
                    pytest.fail(
                        f"Session cleanup error in task {i}: {type(result).__name__}: {result}"
                    )
                # Other exceptions might be acceptable (e.g., validation errors)
                # but session errors are NOT

        # Verify all create operations succeeded
        create_results = [r for i, r in enumerate(results) if i % 2 == 0]
        for result in create_results:
            if not isinstance(result, Exception):
                assert result.get("success") is True, f"Create operation failed: {result}"

    @pytest.mark.asyncio
    async def test_session_cleanup_after_exception(
        self,
        db_manager,
        tenant_manager,
        test_tenant_key
    ):
        """
        RED TEST: Verify sessions cleanup properly even when exceptions occur

        This tests the session cleanup in error paths
        """
        service = MessageService(db_manager, tenant_manager)

        # Act: Trigger an error (non-existent project)
        result = await service.send_message(
            to_agents=["agent-1"],
            content="Test",
            project_id="nonexistent-project-id",
            priority="normal",
        )

        # Assert: Should fail gracefully without session errors
        assert result["success"] is False
        assert "not found" in result["error"].lower()

        # Verify we can still perform operations (session was cleaned up)
        result2 = await service.list_messages(
            project_id="any-project",
            tenant_key=test_tenant_key,
        )

        # This should work without session errors (even if it returns empty or fails for other reasons)
        assert "success" in result2, "Should return a result dict"
