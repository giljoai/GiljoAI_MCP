#!/usr/bin/env python3
"""
Test core API functionality after tenant key fix
"""
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from src.giljo_mcp.api.app import app


def test_projects_flow():
    """Test complete projects workflow"""
    client = TestClient(app)

    # 1. Create project
    print("1. Creating project...")
    project_data = {
        "name": "API Test Project",
        "mission": "Test complete API functionality",
        "agents": ["orchestrator", "developer"]
    }

    response = client.post("/api/v1/projects/", json=project_data)
    assert response.status_code == 200, f"Create failed: {response.text}"

    project_result = response.json()
    project_id = project_result["project_id"]
    tenant_key = project_result["tenant_key"]
    print(f"   Created project {project_id} with tenant {tenant_key}")

    # 2. List projects
    print("2. Listing projects...")
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200, f"List failed: {response.text}"
    projects = response.json()
    print(f"   Found {len(projects)} projects")

    # 3. Get specific project
    print("3. Getting project details...")
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200, f"Get failed: {response.text}"
    project_details = response.json()
    print(f"   Project status: {project_details['status']}")

    # 4. Update project mission
    print("4. Updating project mission...")
    update_data = {"mission": "Updated mission for testing"}
    response = client.patch(f"/api/v1/projects/{project_id}", json=update_data)
    assert response.status_code == 200, f"Update failed: {response.text}"
    print("   Mission updated successfully")

    # 5. Switch to project
    print("5. Switching to project...")
    response = client.post(f"/api/v1/projects/{project_id}/switch")
    assert response.status_code == 200, f"Switch failed: {response.text}"
    print("   Switched to project successfully")

    return project_id

def test_agents_flow(project_id):
    """Test agents workflow"""
    client = TestClient(app)

    print("6. Testing agents endpoints...")

    # Create agent
    agent_data = {
        "agent_name": "test_agent",
        "mission": "Test agent mission",
        "project_id": project_id
    }

    response = client.post("/api/v1/agents/", json=agent_data)
    assert response.status_code == 200, f"Agent create failed: {response.text}"
    print("   Agent created successfully")

    # List agents
    response = client.get("/api/v1/agents/")
    assert response.status_code == 200, f"Agent list failed: {response.text}"
    agents = response.json()
    print(f"   Found {len(agents)} agents")

def test_messages_flow(project_id):
    """Test messages workflow"""
    client = TestClient(app)

    print("7. Testing messages endpoints...")

    # Send message
    message_data = {
        "to_agents": ["test_agent"],
        "content": "Test message",
        "project_id": project_id,
        "message_type": "direct"
    }

    response = client.post("/api/v1/messages/send", json=message_data)
    assert response.status_code == 200, f"Message send failed: {response.text}"
    print("   Message sent successfully")

def main():
    """Run core functionality tests"""
    print("Testing Core API Functionality")
    print("=" * 50)

    try:
        project_id = test_projects_flow()
        test_agents_flow(project_id)
        test_messages_flow(project_id)

        print("=" * 50)
        print("SUCCESS: All core functionality tests passed")
        return True

    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
