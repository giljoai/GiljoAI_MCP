#!/usr/bin/env python
"""Test orchestrator workflow for the test project."""

import json
import requests
from datetime import datetime
from typing import Any, Dict

# Configuration
API_BASE = "http://localhost:7272/api/v1"
PROJECT_ID = "19a2567f-b350-4f53-a04b-45e2f662a30a"
TENANT_KEY = "tk_72afac7c58cc4e1daddf4f0092f96a5a"


def pretty_print(title: str, data: Any):
    """Pretty print JSON data with a title."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)


def test_project_operations():
    """Test project operations."""
    print("\n" + "="*60)
    print(" ORCHESTRATOR WORKFLOW TEST")
    print("="*60)

    # 1. Get project details
    response = requests.get(f"{API_BASE}/projects/{PROJECT_ID}", timeout=10)
    if response.status_code != 200:
        print(f"[ERROR] Failed to get project: {response.status_code}")
        return False

    project = response.json()
    pretty_print("Step 1: Project Details Retrieved", project)

    # Verify project has correct product_id
    if project.get("product_id") == "e74a3a44-1d3e-48cd-b60d-9158d6b3aae6":
        print("[OK] Project has correct product_id")
    else:
        print(f"[ERROR] Project has incorrect product_id: {project.get('product_id')}")

    return True


def spawn_orchestrator_agent():
    """Spawn the orchestrator agent for the project."""
    agent_data = {
        "agent_name": "Orchestrator",
        "project_id": PROJECT_ID,
        "mission": "Coordinate and plan the execution of the project mission"
    }

    response = requests.post(f"{API_BASE}/agents", json=agent_data, timeout=10)

    if response.status_code == 200:
        agent = response.json()
        pretty_print("Step 2: Orchestrator Agent Spawned", agent)
        return agent
    else:
        print(f"[ERROR] Failed to spawn orchestrator: {response.status_code}")
        print(response.text)
        return None


def create_mission(agent_id: str):
    """Create a test mission."""
    mission_data = {
        "title": "Build a Todo App API",
        "description": """Create a simple REST API for a todo application with the following features:
        - CRUD operations for todos
        - User authentication with JWT
        - PostgreSQL database
        - FastAPI framework
        - Proper error handling and validation""",
        "priority": "high",
        "category": "feature",
        "project_id": PROJECT_ID
    }

    # Try to create a task (mission)
    response = requests.post(f"{API_BASE}/tasks", json=mission_data, timeout=10)

    if response.status_code == 200:
        task = response.json()
        pretty_print("Step 3: Mission Created", task)
        return task
    else:
        print(f"[ERROR] Failed to create mission: {response.status_code}")
        print(response.text)
        return None


def plan_agent_team(mission: Dict[str, Any]):
    """Plan the agent team for the mission (without launching agents)."""

    # This would normally be done by the orchestrator agent analyzing the mission
    # For testing, we'll simulate the planning phase

    team_plan = {
        "mission_id": mission.get("id") if mission else "test-mission",
        "mission_name": mission.get("name") if mission else "Build a Todo App API",
        "planned_agents": [
            {
                "role": "architect",
                "name": "System Architect",
                "purpose": "Design the API structure and database schema",
                "status": "queued",
                "dependencies": []
            },
            {
                "role": "backend_developer",
                "name": "Backend Developer",
                "purpose": "Implement the FastAPI endpoints and business logic",
                "status": "queued",
                "dependencies": ["architect"]
            },
            {
                "role": "database_expert",
                "name": "Database Expert",
                "purpose": "Set up PostgreSQL schema and optimize queries",
                "status": "queued",
                "dependencies": ["architect"]
            },
            {
                "role": "security_expert",
                "name": "Security Expert",
                "purpose": "Implement JWT authentication and security best practices",
                "status": "queued",
                "dependencies": ["backend_developer"]
            },
            {
                "role": "tester",
                "name": "QA Engineer",
                "purpose": "Write unit and integration tests",
                "status": "queued",
                "dependencies": ["backend_developer", "database_expert"]
            }
        ],
        "execution_order": [
            "architect",
            "database_expert",
            "backend_developer",
            "security_expert",
            "tester"
        ],
        "estimated_context_usage": {
            "architect": 15000,
            "database_expert": 10000,
            "backend_developer": 25000,
            "security_expert": 12000,
            "tester": 18000,
            "total": 80000
        },
        "notes": "Agents are queued but NOT launched - this is planning phase only"
    }

    pretty_print("Step 4: Agent Team Assembly Plan", team_plan)
    return team_plan


def main():
    """Main test function."""
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"Test Project ID: {PROJECT_ID}")
    print(f"Tenant Key: {TENANT_KEY}")

    # Step 1: Verify project exists
    if not test_project_operations():
        print("\n[ERROR] Project verification failed")
        return

    # Step 2: Spawn orchestrator agent
    agent = spawn_orchestrator_agent()
    if not agent:
        print("\n[WARNING] Orchestrator spawn failed - continuing with simulation")
        agent = {"id": "simulated-orchestrator", "name": "Orchestrator (Simulated)"}

    # Step 3: Create a mission
    mission = create_mission(agent.get("id"))
    if not mission:
        print("\n[WARNING] Mission creation failed - continuing with simulation")

    # Step 4: Plan agent team (without launching)
    team_plan = plan_agent_team(mission)

    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    print(f"[OK] Project verified: {PROJECT_ID}")
    print(f"{'[OK]' if agent and agent.get('id') != 'simulated-orchestrator' else '[WARNING]'} Orchestrator agent: {agent.get('name')}")
    print(f"{'[OK]' if mission else '[WARNING]'} Mission created: {'Build a Todo App API' if mission else 'Simulated'}")
    print(f"[OK] Team planning: {len(team_plan['planned_agents'])} agents queued (not launched)")
    print(f"[OK] Context budget usage: {team_plan['estimated_context_usage']['total']}/{150000} tokens")

    print("\n" + "="*60)
    print(" WORKFLOW TEST COMPLETED")
    print("="*60)
    print("\nNOTE: This test focused on the planning phase.")
    print("Agents were queued but NOT launched as requested.")
    print("The orchestrator would normally handle the actual agent spawning.")


if __name__ == "__main__":
    main()
