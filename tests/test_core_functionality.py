#!/usr/bin/env python3
"""
Test core API functionality after tenant key fix
"""

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from api.app import app


def _create_test_client_with_mock_auth():
    """Helper function to create test client with mocked authentication"""
    from unittest.mock import AsyncMock, MagicMock

    from api.middleware.auth import AuthMiddleware
    from src.giljo_mcp.auth import AuthManager

    # Monkey-patch AuthMiddleware.dispatch to bypass authentication
    original_dispatch = AuthMiddleware.dispatch

    async def mock_dispatch(self, request, call_next):
        # Check if it's a public endpoint first (preserve original behavior)
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # For non-public endpoints, set mock auth state
        request.state.authenticated = True
        request.state.user_id = "test_user"
        request.state.user = None
        request.state.is_auto_login = True
        request.state.tenant_key = "test_tenant_key"
        return await call_next(request)

    AuthMiddleware.dispatch = mock_dispatch

    # Create a mock auth manager for app state
    mock_auth = MagicMock(spec=AuthManager)
    mock_auth.authenticate_request = AsyncMock(
        return_value={
            "authenticated": True,
            "user_id": "test_user",
            "user_obj": None,
            "is_auto_login": True,
            "tenant_key": "test_tenant_key",
        }
    )
    app.state.auth = mock_auth

    return TestClient(app), original_dispatch


def test_projects_flow():
    """Test complete projects workflow"""
    from api.middleware.auth import AuthMiddleware

    client, original_dispatch = _create_test_client_with_mock_auth()

    try:
        # 1. Create project
        project_data = {
            "name": "API Test Project",
            "mission": "Test complete API functionality",
            "agents": ["orchestrator", "developer"],
        }

        response = client.post("/api/v1/projects/", json=project_data)
        assert response.status_code == 200, f"Create failed: {response.text}"

        project_result = response.json()
        project_id = project_result["project_id"]
        project_result["tenant_key"]

        # 2. List projects
        response = client.get("/api/v1/projects/")
        assert response.status_code == 200, f"List failed: {response.text}"
        response.json()

        # 3. Get specific project
        response = client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200, f"Get failed: {response.text}"
        response.json()

        # 4. Update project mission
        update_data = {"mission": "Updated mission for testing"}
        response = client.patch(f"/api/v1/projects/{project_id}", json=update_data)
        assert response.status_code == 200, f"Update failed: {response.text}"

        # 5. Switch to project
        response = client.post(f"/api/v1/projects/{project_id}/switch")
        assert response.status_code == 200, f"Switch failed: {response.text}"

        return project_id
    finally:
        # Restore original dispatch
        AuthMiddleware.dispatch = original_dispatch


def test_agents_flow(project_id):
    """Test agents workflow"""
    from api.middleware.auth import AuthMiddleware

    client, original_dispatch = _create_test_client_with_mock_auth()

    try:
        # Create agent
        agent_data = {"agent_name": "test_agent", "mission": "Test agent mission", "project_id": project_id}

        response = client.post("/api/v1/agents/", json=agent_data)
        assert response.status_code == 200, f"Agent create failed: {response.text}"

        # List agents
        response = client.get("/api/v1/agents/")
        assert response.status_code == 200, f"Agent list failed: {response.text}"
        response.json()
    finally:
        # Restore original dispatch
        AuthMiddleware.dispatch = original_dispatch


def test_messages_flow(project_id):
    """Test messages workflow"""
    from api.middleware.auth import AuthMiddleware

    client, original_dispatch = _create_test_client_with_mock_auth()

    try:
        # Send message
        message_data = {
            "to_agents": ["test_agent"],
            "content": "Test message",
            "project_id": project_id,
            "message_type": "direct",
        }

        response = client.post("/api/v1/messages/send", json=message_data)
        assert response.status_code == 200, f"Message send failed: {response.text}"
    finally:
        # Restore original dispatch
        AuthMiddleware.dispatch = original_dispatch


def main():
    """Run core functionality tests"""

    try:
        project_id = test_projects_flow()
        test_agents_flow(project_id)
        test_messages_flow(project_id)

        return True

    except Exception:
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
