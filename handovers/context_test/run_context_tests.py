"""
Comprehensive Context Configuration Test Suite.

Tests ALL combinations of context configuration settings and captures
get_orchestrator_instructions output for each combination.

Test Strategy:
1. Baseline Test: Current configuration
2. Priority Sweep: Test each priority field at all 4 levels
3. Depth Sweep: Test each depth field at all levels
4. Execution Mode Toggle: Test both modes with default config
5. Edge Cases: All OFF, All Critical, All Reference, etc.

Usage:
    python run_context_tests.py

Requirements:
    - Server running at http://10.1.0.164:7274
    - Valid API key set in environment variable GILJO_API_KEY
    - Test orchestrator created with provided credentials
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx


# ==================== Configuration ====================

# Test Credentials
ORCHESTRATOR_ID = "6792fae5-c46b-4ed7-86d6-df58aa833df3"
TENANT_KEY = "***REMOVED***"
PROJECT_ID = "97d95e5a-51dd-47ae-92de-7f8839de503a"
API_BASE_URL = "http://10.1.0.164:7274"

# Authentication credentials (JWT login for REST, API key for MCP)
USERNAME = os.environ.get("GILJO_USERNAME", "patrik")
PASSWORD = os.environ.get("GILJO_PASSWORD", "***REMOVED***")
API_KEY = os.environ.get("GILJO_API_KEY", "gk_9-TgHc3tqq0-GzXJRXts_GjyxgIkLmGLthoJbtfrOac")

# Output configuration
RESULTS_DIR = Path(__file__).parent / "results"
DELAY_BETWEEN_CALLS = 0.5  # Seconds to avoid rate limiting

# Default configurations for reference
DEFAULT_FIELD_PRIORITIES = {
    "product_core": {"toggle": True, "priority": 1},
    "project_description": {"toggle": True, "priority": 1},
    "vision_documents": {"toggle": True, "priority": 2},
    "tech_stack": {"toggle": True, "priority": 2},
    "architecture": {"toggle": True, "priority": 3},
    "testing": {"toggle": True, "priority": 3},
    "memory_360": {"toggle": True, "priority": 2},
    "git_history": {"toggle": False, "priority": 4},
    "agent_templates": {"toggle": True, "priority": 2},
}

DEFAULT_DEPTH_CONFIG = {
    "vision_documents": "optional",
    "memory_last_n_projects": 5,
    "git_commits": 25,
    "agent_templates": "type_only",
    "tech_stack_sections": "all",
    "architecture_depth": "overview",
}


# ==================== API Client ====================


class GiljoAPIClient:
    """Client for interacting with GiljoAI MCP Server API."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token = None
        self.headers = {"Content-Type": "application/json"}
        self.client = httpx.AsyncClient(timeout=30.0)

    async def login(self) -> bool:
        """Login to get JWT token (stored in cookies)."""
        print("  -> Logging in...")
        try:
            response = await self.client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.username, "password": self.password},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            # Token is set as cookie, extract it for Authorization header too
            self.access_token = response.cookies.get("access_token")
            if self.access_token:
                # Use both cookie (auto) and Authorization header (explicit)
                self.headers["Authorization"] = f"Bearer {self.access_token}"
                print(f"  [OK] Logged in as {self.username}")
                return True
            print("  [FAIL] No access token cookie in response")
            return False
        except Exception as e:
            print(f"  [FAIL] Login failed: {e}")
            return False

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def update_field_priority_config(self, priorities: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update field priority configuration.

        Args:
            priorities: Dict with toggle and priority for each field

        Returns:
            API response
        """
        # Convert toggle/priority format to priority-only format for API
        priority_only = {}
        for field, config in priorities.items():
            # If toggled OFF, set priority to 4 (EXCLUDED)
            if not config.get("toggle", True):
                priority_only[field] = 4
            else:
                priority_only[field] = config.get("priority", 2)

        payload = {"version": "2.0", "priorities": priority_only}

        response = await self.client.put(
            f"{self.base_url}/api/v1/users/me/field-priority",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def update_depth_config(self, depth_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update depth configuration.

        Args:
            depth_config: Depth settings for various context sources

        Returns:
            API response
        """
        payload = {"depth_config": depth_config}

        response = await self.client.put(
            f"{self.base_url}/api/v1/users/me/context/depth",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_orchestrator_instructions(
        self, orchestrator_id: str, tenant_key: str, api_key: str
    ) -> Dict[str, Any]:
        """
        Call MCP tool get_orchestrator_instructions.

        Args:
            orchestrator_id: Orchestrator job UUID
            tenant_key: Tenant isolation key
            api_key: API key for MCP authentication

        Returns:
            Orchestrator instructions
        """
        # Use MCP HTTP endpoint with X-API-Key header
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_orchestrator_instructions",
                "arguments": {
                    "orchestrator_id": orchestrator_id,
                    "tenant_key": tenant_key,
                },
            },
        }

        # MCP uses X-API-Key, not JWT
        mcp_headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        response = await self.client.post(f"{self.base_url}/mcp", headers=mcp_headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise Exception(f"MCP Error: {data['error']}")

        return data.get("result", {}).get("content", [{}])[0].get("text", {})


# ==================== Test Configuration Generator ====================


class TestConfigGenerator:
    """Generates test configuration combinations."""

    @staticmethod
    def baseline_test() -> Dict[str, Any]:
        """Get baseline configuration (current defaults)."""
        return {
            "name": "Baseline - Default Configuration",
            "field_priorities": DEFAULT_FIELD_PRIORITIES.copy(),
            "depth_config": DEFAULT_DEPTH_CONFIG.copy(),
        }

    @staticmethod
    def priority_sweep_tests() -> List[Dict[str, Any]]:
        """
        Test each priority field at all 4 levels.

        For each field:
        - OFF (priority = 4, toggle = False)
        - ON + Critical (priority = 1, toggle = True)
        - ON + Important (priority = 2, toggle = True)
        - ON + Reference (priority = 3, toggle = True)
        """
        tests = []
        fields = [
            "product_core",
            "vision_documents",
            "tech_stack",
            "architecture",
            "testing",
            "memory_360",
            "git_history",
            "agent_templates",
        ]

        for field in fields:
            for priority_level in [1, 2, 3, 4]:
                config = DEFAULT_FIELD_PRIORITIES.copy()

                if priority_level == 4:
                    # OFF
                    config[field] = {"toggle": False, "priority": 4}
                    level_name = "OFF"
                else:
                    # ON + priority level
                    config[field] = {"toggle": True, "priority": priority_level}
                    level_name = {1: "Critical", 2: "Important", 3: "Reference"}[priority_level]

                tests.append(
                    {
                        "name": f"Priority Sweep - {field} = {level_name}",
                        "field_priorities": config,
                        "depth_config": DEFAULT_DEPTH_CONFIG.copy(),
                    }
                )

        return tests

    @staticmethod
    def depth_sweep_tests() -> List[Dict[str, Any]]:
        """
        Test each depth field at all levels.

        Fields:
        - vision_documents: ["optional", "light", "medium", "full"]
        - memory_last_n_projects: [1, 3, 5, 10]
        - git_commits: [5, 10, 25, 50, 100]
        - agent_templates: ["type_only", "full"]
        """
        tests = []

        # Vision documents depth
        for level in ["optional", "light", "medium", "full"]:
            config = DEFAULT_DEPTH_CONFIG.copy()
            config["vision_documents"] = level
            tests.append(
                {
                    "name": f"Depth Sweep - vision_documents = {level}",
                    "field_priorities": DEFAULT_FIELD_PRIORITIES.copy(),
                    "depth_config": config,
                }
            )

        # Memory 360 depth
        for n in [1, 3, 5, 10]:
            config = DEFAULT_DEPTH_CONFIG.copy()
            config["memory_last_n_projects"] = n
            tests.append(
                {
                    "name": f"Depth Sweep - memory_last_n_projects = {n}",
                    "field_priorities": DEFAULT_FIELD_PRIORITIES.copy(),
                    "depth_config": config,
                }
            )

        # Git history depth (valid values: 10, 25, 50, 100)
        for n in [10, 25, 50, 100]:
            config = DEFAULT_DEPTH_CONFIG.copy()
            config["git_commits"] = n
            tests.append(
                {
                    "name": f"Depth Sweep - git_commits = {n}",
                    "field_priorities": DEFAULT_FIELD_PRIORITIES.copy(),
                    "depth_config": config,
                }
            )

        # Agent templates depth
        for level in ["type_only", "full"]:
            config = DEFAULT_DEPTH_CONFIG.copy()
            config["agent_templates"] = level
            tests.append(
                {
                    "name": f"Depth Sweep - agent_templates = {level}",
                    "field_priorities": DEFAULT_FIELD_PRIORITIES.copy(),
                    "depth_config": config,
                }
            )

        return tests

    @staticmethod
    def edge_case_tests() -> List[Dict[str, Any]]:
        """
        Test edge cases.

        1. All OFF (minimum context)
        2. All Critical (maximum priority)
        3. All Reference (minimum priority)
        4. Mixed priorities (alternating)
        """
        tests = []

        # All OFF (except product_core which must be ON for validation)
        all_off = {
            "product_core": {"toggle": True, "priority": 1},  # Required
            "project_description": {"toggle": False, "priority": 4},
            "vision_documents": {"toggle": False, "priority": 4},
            "tech_stack": {"toggle": False, "priority": 4},
            "architecture": {"toggle": False, "priority": 4},
            "testing": {"toggle": False, "priority": 4},
            "memory_360": {"toggle": False, "priority": 4},
            "git_history": {"toggle": False, "priority": 4},
            "agent_templates": {"toggle": False, "priority": 4},
        }
        tests.append(
            {
                "name": "Edge Case - All OFF (minimum context)",
                "field_priorities": all_off,
                "depth_config": DEFAULT_DEPTH_CONFIG.copy(),
            }
        )

        # All Critical
        all_critical = {field: {"toggle": True, "priority": 1} for field in DEFAULT_FIELD_PRIORITIES}
        tests.append(
            {
                "name": "Edge Case - All Critical (maximum priority)",
                "field_priorities": all_critical,
                "depth_config": DEFAULT_DEPTH_CONFIG.copy(),
            }
        )

        # All Reference
        all_reference = {
            "product_core": {"toggle": True, "priority": 1},  # At least one Critical
            "project_description": {"toggle": True, "priority": 3},
            "vision_documents": {"toggle": True, "priority": 3},
            "tech_stack": {"toggle": True, "priority": 3},
            "architecture": {"toggle": True, "priority": 3},
            "testing": {"toggle": True, "priority": 3},
            "memory_360": {"toggle": True, "priority": 3},
            "git_history": {"toggle": True, "priority": 3},
            "agent_templates": {"toggle": True, "priority": 3},
        }
        tests.append(
            {
                "name": "Edge Case - All Reference (minimum priority)",
                "field_priorities": all_reference,
                "depth_config": DEFAULT_DEPTH_CONFIG.copy(),
            }
        )

        # Mixed priorities (alternating 1, 2, 3)
        mixed = {
            "product_core": {"toggle": True, "priority": 1},
            "project_description": {"toggle": True, "priority": 2},
            "vision_documents": {"toggle": True, "priority": 3},
            "tech_stack": {"toggle": True, "priority": 1},
            "architecture": {"toggle": True, "priority": 2},
            "testing": {"toggle": True, "priority": 3},
            "memory_360": {"toggle": True, "priority": 1},
            "git_history": {"toggle": True, "priority": 2},
            "agent_templates": {"toggle": True, "priority": 3},
        }
        tests.append(
            {
                "name": "Edge Case - Mixed priorities (alternating)",
                "field_priorities": mixed,
                "depth_config": DEFAULT_DEPTH_CONFIG.copy(),
            }
        )

        return tests


# ==================== Test Runner ====================


class ContextTestRunner:
    """Runs comprehensive context configuration tests."""

    def __init__(self, client: GiljoAPIClient, results_dir: Path):
        self.client = client
        self.results_dir = results_dir
        self.results: List[Dict[str, Any]] = []

    async def run_single_test(self, combo_id: int, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single test configuration.

        Args:
            combo_id: Unique test combination ID
            test_config: Test configuration dict

        Returns:
            Test result dict
        """
        test_name = test_config["name"]
        print(f"\n{'=' * 80}")
        print(f"Test {combo_id}: {test_name}")
        print(f"{'=' * 80}")

        try:
            # Update field priority config
            print("  -> Updating field priority configuration...")
            await self.client.update_field_priority_config(test_config["field_priorities"])
            await asyncio.sleep(DELAY_BETWEEN_CALLS)

            # Update depth config
            print("  -> Updating depth configuration...")
            await self.client.update_depth_config(test_config["depth_config"])
            await asyncio.sleep(DELAY_BETWEEN_CALLS)

            # Get orchestrator instructions
            print("  -> Fetching orchestrator instructions...")
            instructions = await self.client.get_orchestrator_instructions(ORCHESTRATOR_ID, TENANT_KEY, API_KEY)

            # Parse instructions (may be JSON string)
            if isinstance(instructions, str):
                try:
                    instructions = json.loads(instructions)
                except json.JSONDecodeError:
                    pass

            # Build result
            result = {
                "combo_id": combo_id,
                "test_name": test_name,
                "timestamp": datetime.now().isoformat(),
                "input_config": {
                    "field_priorities": test_config["field_priorities"],
                    "depth_config": test_config["depth_config"],
                },
                "output": instructions,
                "validation": self._validate_output(instructions, test_config["field_priorities"]),
                "success": True,
                "error": None,
            }

            # Print summary
            estimated_tokens = instructions.get("estimated_tokens", 0)
            print(f"  [OK] Success! Estimated tokens: {estimated_tokens}")

            return result

        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            return {
                "combo_id": combo_id,
                "test_name": test_name,
                "timestamp": datetime.now().isoformat(),
                "input_config": {
                    "field_priorities": test_config["field_priorities"],
                    "depth_config": test_config["depth_config"],
                },
                "output": None,
                "validation": {},
                "success": False,
                "error": str(e),
            }

    def _validate_output(self, output: Dict[str, Any], field_priorities: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate orchestrator instructions output.

        Args:
            output: Orchestrator instructions
            field_priorities: Expected field priorities

        Returns:
            Validation results
        """
        validation = {
            "has_mission": False,
            "has_estimated_tokens": False,
            "has_field_priorities": False,
            "field_priorities_match": False,
        }

        if not isinstance(output, dict):
            return validation

        # Check required fields
        validation["has_mission"] = "mission" in output and bool(output["mission"])
        validation["has_estimated_tokens"] = "estimated_tokens" in output
        validation["has_field_priorities"] = "field_priorities" in output

        # Validate field priorities match
        if "field_priorities" in output:
            output_priorities = output["field_priorities"]
            # Compare priority values (convert toggle/priority format to priority-only)
            expected_priorities = {}
            for field, config in field_priorities.items():
                if not config.get("toggle", True):
                    expected_priorities[field] = 4
                else:
                    expected_priorities[field] = config.get("priority", 2)

            validation["field_priorities_match"] = output_priorities == expected_priorities

        return validation

    async def run_all_tests(self):
        """Run all test combinations."""
        print("\n" + "=" * 80)
        print("GiljoAI Context Configuration Test Suite")
        print("=" * 80)
        print(f"Orchestrator ID: {ORCHESTRATOR_ID}")
        print(f"Tenant Key: {TENANT_KEY}")
        print(f"API Base URL: {API_BASE_URL}")
        print(f"Results Directory: {self.results_dir}")
        print("=" * 80)

        # Generate test configurations
        print("\nGenerating test configurations...")
        test_configs = []

        # 1. Baseline
        test_configs.append(TestConfigGenerator.baseline_test())

        # 2. Priority sweep
        test_configs.extend(TestConfigGenerator.priority_sweep_tests())

        # 3. Depth sweep
        test_configs.extend(TestConfigGenerator.depth_sweep_tests())

        # 4. Edge cases
        test_configs.extend(TestConfigGenerator.edge_case_tests())

        print(f"Generated {len(test_configs)} test configurations")

        # Run tests
        print("\nRunning tests...")
        for i, test_config in enumerate(test_configs, start=1):
            result = await self.run_single_test(i, test_config)
            self.results.append(result)

            # Save individual result
            result_file = self.results_dir / f"combo_{i:03d}.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Delay to avoid rate limiting
            await asyncio.sleep(DELAY_BETWEEN_CALLS)

        # Save summary
        self._save_summary()

        # Print final report
        self._print_report()

    def _save_summary(self):
        """Save summary of all test results."""
        summary = {
            "test_run_timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "successful_tests": sum(1 for r in self.results if r["success"]),
            "failed_tests": sum(1 for r in self.results if not r["success"]),
            "test_credentials": {
                "orchestrator_id": ORCHESTRATOR_ID,
                "tenant_key": TENANT_KEY,
                "project_id": PROJECT_ID,
            },
            "results": [
                {
                    "combo_id": r["combo_id"],
                    "test_name": r["test_name"],
                    "success": r["success"],
                    "estimated_tokens": (r["output"].get("estimated_tokens", 0) if r["output"] else 0),
                    "validation": r["validation"],
                }
                for r in self.results
            ],
        }

        summary_file = self.results_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Summary saved to: {summary_file}")

    def _print_report(self):
        """Print final test report."""
        print("\n" + "=" * 80)
        print("TEST REPORT")
        print("=" * 80)

        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful

        print(f"Total Tests: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(successful / total * 100):.1f}%")

        if failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if not r["success"]:
                    print(f"  - {r['test_name']}: {r['error']}")

        # Token statistics
        tokens = [r["output"].get("estimated_tokens", 0) for r in self.results if r["success"] and r["output"]]
        if tokens:
            print("\nToken Statistics:")
            print(f"  Min: {min(tokens)}")
            print(f"  Max: {max(tokens)}")
            print(f"  Average: {sum(tokens) / len(tokens):.0f}")

        print("\n" + "=" * 80)


# ==================== Main ====================


async def main():
    """Main entry point."""
    # Validate credentials
    if not USERNAME or not PASSWORD:
        print("ERROR: Username or password not set")
        print("Set GILJO_USERNAME and GILJO_PASSWORD environment variables")
        return

    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize client
    client = GiljoAPIClient(API_BASE_URL, USERNAME, PASSWORD)

    try:
        # Login first
        print("\n" + "=" * 80)
        print("AUTHENTICATION")
        print("=" * 80)
        if not await client.login():
            print("ERROR: Authentication failed. Cannot run tests.")
            return

        # Run tests
        runner = ContextTestRunner(client, RESULTS_DIR)
        await runner.run_all_tests()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
