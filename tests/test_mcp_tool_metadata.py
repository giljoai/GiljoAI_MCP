"""
Tests for MCP Tool Metadata Enhancement (Handover 0090 Phase 3)

Tests that all 25 MCP tools have:
1. Enhanced argument descriptions with types and REQUIRED/OPTIONAL markers
2. Usage examples showing 2-3 common patterns
3. Correct array notation in examples (["value"] not "value")
4. Realistic UUID formats in examples

Test-Driven Development: This test suite MUST pass before deployment.
"""

import pytest
from fastapi.testclient import TestClient


class TestMCPToolMetadata:
    """Test suite for enhanced MCP tool metadata"""

    @pytest.fixture
    def client(self):
        """Create test client for API"""
        from api.app import app

        return TestClient(app)

    def test_all_20_tools_present(self, client):
        """Verify all 20 tools are listed in the endpoint"""
        response = client.get("/api/v1/mcp-tools/list")
        assert response.status_code == 200

        data = response.json()
        assert "tools" in data
        assert "total_count" in data

        # Count all tools across categories
        total_tools = sum(len(tools) for tools in data["tools"].values())
        assert total_tools == 20, f"Expected 20 tools, found {total_tools}"

    def test_project_management_tools_have_rich_metadata(self, client):
        """Test project management tools (4 tools) have enhanced metadata"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        project_tools = data["tools"]["project_management"]
        expected_tools = ["list_projects", "get_project", "close_project", "update_project_mission"]

        assert len(project_tools) == 4

        for tool in project_tools:
            assert tool["name"] in expected_tools

            # Verify enhanced arguments with type markers
            assert "arguments" in tool
            for arg_name, arg_desc in tool["arguments"].items():
                # Check for type indicators (string, array, dict, etc.)
                assert any(
                    keyword in arg_desc.lower()
                    for keyword in ["string", "array", "dict", "object", "uuid", "boolean", "integer"]
                ), f"Argument '{arg_name}' missing type indicator: {arg_desc}"

                # Check for REQUIRED/OPTIONAL markers
                assert any(marker in arg_desc for marker in ["REQUIRED", "OPTIONAL"]), (
                    f"Argument '{arg_name}' missing REQUIRED/OPTIONAL marker: {arg_desc}"
                )

            # Verify examples section exists
            assert "examples" in tool, f"Tool '{tool['name']}' missing examples"
            assert isinstance(tool["examples"], list), f"Examples should be a list for '{tool['name']}'"
            assert len(tool["examples"]) >= 2, f"Tool '{tool['name']}' should have at least 2 examples"
            assert len(tool["examples"]) <= 3, f"Tool '{tool['name']}' should have max 3 examples"

            # Verify each example has description and payload
            for example in tool["examples"]:
                assert "description" in example, f"Example missing description in '{tool['name']}'"
                assert "payload" in example, f"Example missing payload in '{tool['name']}'"
                assert isinstance(example["payload"], dict), f"Payload should be dict in '{tool['name']}'"

    def test_message_queue_tools_have_rich_metadata(self, client):
        """Test message queue tools (4 tools) have enhanced metadata"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        message_tools = data["tools"]["message_queue"]
        expected_tools = ["send_message", "receive_messages", "acknowledge_message", "list_messages"]

        assert len(message_tools) == 4

        for tool in message_tools:
            assert tool["name"] in expected_tools
            self._verify_tool_metadata(tool)

    def test_task_management_tools_have_rich_metadata(self, client):
        """Test task management tools (3 tools) have enhanced metadata"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        task_tools = data["tools"]["task_management"]
        expected_tools = ["create_task", "list_tasks", "update_task"]

        assert len(task_tools) == 3

        for tool in task_tools:
            assert tool["name"] in expected_tools
            self._verify_tool_metadata(tool)

    def test_template_management_tools_have_rich_metadata(self, client):
        """Test template management tools (2 tools) have enhanced metadata"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        template_tools = data["tools"]["template_management"]
        expected_tools = ["list_templates"]

        assert len(template_tools) == 1

        for tool in template_tools:
            assert tool["name"] in expected_tools
            self._verify_tool_metadata(tool)

    def test_orchestration_tools_have_rich_metadata(self, client):
        """Test orchestration tools (6 tools) have enhanced metadata"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        orchestration_tools = data["tools"]["orchestration"]
        expected_tools = [
            "health_check",
            "get_orchestrator_instructions",
            "spawn_agent_job",
            "get_agent_mission",
            "get_workflow_status",
        ]

        assert len(orchestration_tools) == 5

        for tool in orchestration_tools:
            assert tool["name"] in expected_tools
            self._verify_tool_metadata(tool)

    def test_agent_coordination_tools_have_rich_metadata(self, client):
        """Test agent coordination tools (5 tools) have enhanced metadata"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        coordination_tools = data["tools"]["agent_coordination"]
        expected_tools = ["get_pending_jobs", "acknowledge_job", "report_progress", "complete_job", "report_error"]

        assert len(coordination_tools) == 5

        for tool in coordination_tools:
            assert tool["name"] in expected_tools
            self._verify_tool_metadata(tool)

    def test_send_message_array_notation_in_examples(self, client):
        """Specific test: send_message must show array notation for to_agents"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        send_message_tool = next(
            (tool for tool in data["tools"]["message_queue"] if tool["name"] == "send_message"), None
        )

        assert send_message_tool is not None

        # Check arguments show array notation
        assert "to_agents" in send_message_tool["arguments"]
        assert "array" in send_message_tool["arguments"]["to_agents"].lower()

        # Check examples use array notation
        for example in send_message_tool["examples"]:
            payload = example["payload"]
            assert "to_agents" in payload
            assert isinstance(payload["to_agents"], list), "to_agents must be a list in examples"

            # Check for special values like ["broadcast"] or ["orchestrator"]
            if "broadcast" in example["description"].lower():
                assert payload["to_agents"] == ["broadcast"], "Broadcast example should use ['broadcast']"

    def test_uuid_format_consistency(self, client):
        """Verify all examples use realistic UUID format"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        # Check all tools across all categories
        for category, tools in data["tools"].items():
            for tool in tools:
                if "examples" not in tool:
                    continue

                for example in tool["examples"]:
                    payload = example["payload"]

                    # Check common UUID fields
                    uuid_fields = ["project_id", "agent_id", "job_id", "orchestrator_id", "task_id", "message_id"]

                    for field in uuid_fields:
                        if field in payload:
                            uuid_value = payload[field]
                            # Should be a string with dashes or underscores (realistic format)
                            assert isinstance(uuid_value, str), (
                                f"UUID field '{field}' should be string in {tool['name']}"
                            )
                            assert len(uuid_value) > 8, f"UUID field '{field}' too short in {tool['name']}"

    def test_priority_values_in_examples(self, client):
        """Verify priority fields use valid values"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        valid_priorities = ["low", "normal", "medium", "high", "critical"]

        for category, tools in data["tools"].items():
            for tool in tools:
                if "examples" not in tool:
                    continue

                for example in tool["examples"]:
                    payload = example["payload"]

                    if "priority" in payload:
                        assert payload["priority"] in valid_priorities, (
                            f"Invalid priority '{payload['priority']}' in {tool['name']}"
                        )

    def test_status_values_in_examples(self, client):
        """Verify status fields use valid values"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        valid_statuses = ["active", "completed", "archived", "pending", "in_progress", "blocked", "silent", "decommissioned", "failed"]

        for category, tools in data["tools"].items():
            for tool in tools:
                if "examples" not in tool:
                    continue

                for example in tool["examples"]:
                    payload = example["payload"]

                    if "status" in payload:
                        assert payload["status"] in valid_statuses, (
                            f"Invalid status '{payload['status']}' in {tool['name']}"
                        )

    def _verify_tool_metadata(self, tool):
        """Helper method to verify tool has complete metadata"""
        # Verify arguments have type and required/optional markers
        assert "arguments" in tool

        for arg_name, arg_desc in tool["arguments"].items():
            # Check for type indicators
            assert any(
                keyword in arg_desc.lower()
                for keyword in ["string", "array", "dict", "object", "uuid", "boolean", "integer"]
            ), f"Argument '{arg_name}' missing type indicator in '{tool['name']}': {arg_desc}"

            # Check for REQUIRED/OPTIONAL markers
            assert any(marker in arg_desc for marker in ["REQUIRED", "OPTIONAL"]), (
                f"Argument '{arg_name}' missing REQUIRED/OPTIONAL marker in '{tool['name']}': {arg_desc}"
            )

        # Verify examples
        assert "examples" in tool, f"Tool '{tool['name']}' missing examples"
        assert isinstance(tool["examples"], list)
        assert 2 <= len(tool["examples"]) <= 3, f"Tool '{tool['name']}' should have 2-3 examples"

        for example in tool["examples"]:
            assert "description" in example
            assert "payload" in example
            assert isinstance(example["payload"], dict)


class TestSpecificToolExamples:
    """Test specific tools for correct parameter usage"""

    @pytest.fixture
    def client(self):
        from api.app import app

        return TestClient(app)

    def test_spawn_agent_job_parameters(self, client):
        """Verify spawn_agent_job shows correct parameters"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        spawn_tool = next((tool for tool in data["tools"]["orchestration"] if tool["name"] == "spawn_agent_job"), None)

        assert spawn_tool is not None

        # Check required parameters
        required_params = ["agent_display_name", "agent_name", "mission", "project_id", "tenant_key"]
        for param in required_params:
            assert param in spawn_tool["arguments"], f"Missing parameter '{param}'"
            assert "REQUIRED" in spawn_tool["arguments"][param], f"Parameter '{param}' should be marked REQUIRED"

        # Verify examples show all required parameters
        for example in spawn_tool["examples"]:
            for param in required_params:
                assert param in example["payload"], f"Example missing required parameter '{param}'"

    def test_get_orchestrator_instructions_parameters(self, client):
        """Verify get_orchestrator_instructions shows correct parameters"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        orch_tool = next(
            (tool for tool in data["tools"]["orchestration"] if tool["name"] == "get_orchestrator_instructions"),
            None,
        )

        assert orch_tool is not None

        # Check required parameters
        assert "orchestrator_id" in orch_tool["arguments"]
        assert "tenant_key" in orch_tool["arguments"]

        # Both should be REQUIRED
        assert "REQUIRED" in orch_tool["arguments"]["orchestrator_id"]
        assert "REQUIRED" in orch_tool["arguments"]["tenant_key"]

    def test_report_progress_parameters(self, client):
        """Verify report_progress shows progress as dict/object"""
        response = client.get("/api/v1/mcp-tools/list")
        data = response.json()

        progress_tool = next(
            (tool for tool in data["tools"]["agent_coordination"] if tool["name"] == "report_progress"), None
        )

        assert progress_tool is not None

        # Check progress parameter shows as object/dict
        assert "progress" in progress_tool["arguments"]
        assert any(keyword in progress_tool["arguments"]["progress"].lower() for keyword in ["object", "dict"]), (
            "Progress should be described as object/dict"
        )

        # Verify examples show progress as dict
        for example in progress_tool["examples"]:
            assert "progress" in example["payload"]
            assert isinstance(example["payload"]["progress"], dict), (
                "Progress should be a dict in examples, not a string"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
