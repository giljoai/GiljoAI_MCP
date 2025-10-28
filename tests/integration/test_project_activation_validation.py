#!/usr/bin/env python3
"""
Integration tests for Project Activation Validation (Handover 0050 Phase 4)
Tests that projects can only be activated when parent product is active

This test suite validates the backend implementation of Phase 4.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.app import create_app
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class ProjectActivationValidationTests:
    """
    Integration test suite for Handover 0050 Phase 4
    Validates project activation against parent product status
    """

    def __init__(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.db_manager = None
        self.passed = 0
        self.failed = 0
        self.tenant_key = "tk_test_phase4_validation"

    async def setup(self):
        """Initialize test environment"""
        print(f"\n{Colors.CYAN}Setting up test environment...{Colors.RESET}")

        # Initialize test database
        self.db_manager = DatabaseManager(
            PostgreSQLTestHelper.get_test_db_url(async_driver=False),
            is_async=True
        )
        await self.db_manager.create_tables_async()

        # Store in app state
        self.app.state.api_state.db_manager = self.db_manager

        # Create test data
        await self.create_test_data()

        print(f"{Colors.GREEN}Test environment ready{Colors.RESET}\n")

    async def create_test_data(self):
        """Create test products and projects"""
        async with self.db_manager.get_session_async() as session:
            # Create active product
            self.active_product = Product(
                name="Active Product",
                description="Product with is_active=True",
                tenant_key=self.tenant_key,
                is_active=True
            )
            session.add(self.active_product)
            await session.flush()

            # Create inactive product
            self.inactive_product = Product(
                name="Inactive Product",
                description="Product with is_active=False",
                tenant_key=self.tenant_key,
                is_active=False
            )
            session.add(self.inactive_product)
            await session.flush()

            # Create project under active product (inactive status)
            self.project_active_parent = Project(
                name="Project Under Active Product",
                mission="Test project with active parent",
                tenant_key=self.tenant_key,
                product_id=self.active_product.id,
                status="inactive"
            )
            session.add(self.project_active_parent)

            # Create project under inactive product (inactive status)
            self.project_inactive_parent = Project(
                name="Project Under Inactive Product",
                mission="Test project with inactive parent",
                tenant_key=self.tenant_key,
                product_id=self.inactive_product.id,
                status="inactive"
            )
            session.add(self.project_inactive_parent)

            # Create orphan project (no parent product)
            self.project_orphan = Project(
                name="Orphan Project",
                mission="Test project without parent",
                tenant_key=self.tenant_key,
                product_id=None,
                status="inactive"
            )
            session.add(self.project_orphan)

            await session.commit()

    async def teardown(self):
        """Clean up test environment"""
        if self.db_manager:
            await self.db_manager.close_async()

    def test_result(self, test_name: str, passed: bool, details: str = ""):
        """Record and print test result"""
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {status} {test_name}")
        if details:
            print(f"       {Colors.YELLOW}{details}{Colors.RESET}")

        if passed:
            self.passed += 1
        else:
            self.failed += 1

    async def run_all_tests(self):
        """Run all test cases"""
        print(f"\n{Colors.BOLD}Running Handover 0050 Phase 4 Integration Tests{Colors.RESET}")
        print("=" * 70)

        # Test 1: Activate project with active parent product
        await self.test_activate_with_active_parent()

        # Test 2: Fail to activate project with inactive parent product
        await self.test_fail_activate_with_inactive_parent()

        # Test 3: Activate orphan project (no parent)
        await self.test_activate_orphan_project()

        # Test 4: Update other fields doesn't trigger validation
        await self.test_update_non_status_fields()

        # Test 5: Error message clarity
        await self.test_error_message_clarity()

        # Print summary
        self.print_summary()

    async def test_activate_with_active_parent(self):
        """Test: Project can be activated when parent product is active"""
        print(f"\n{Colors.BLUE}Test 1: Activate Project with Active Parent Product{Colors.RESET}")

        response = self.client.patch(
            f"/api/projects/{self.project_active_parent.id}",
            json={"status": "active"},
            headers={"X-Tenant-Key": self.tenant_key}
        )

        passed = response.status_code == 200
        details = f"Status Code: {response.status_code}"

        if passed:
            data = response.json()
            if data.get("status") == "active":
                details += " | Project status: active"
            else:
                passed = False
                details += f" | ERROR: Expected status 'active', got '{data.get('status')}'"

        self.test_result(
            "Activate project with active parent product",
            passed,
            details
        )

    async def test_fail_activate_with_inactive_parent(self):
        """Test: Project cannot be activated when parent product is inactive"""
        print(f"\n{Colors.BLUE}Test 2: Fail to Activate Project with Inactive Parent{Colors.RESET}")

        response = self.client.patch(
            f"/api/projects/{self.project_inactive_parent.id}",
            json={"status": "active"},
            headers={"X-Tenant-Key": self.tenant_key}
        )

        passed = response.status_code == 400
        details = f"Status Code: {response.status_code}"

        if response.status_code == 400:
            data = response.json()
            error_msg = data.get("detail", "")
            if "not active" in error_msg.lower():
                details += " | Error message mentions 'not active'"
            else:
                passed = False
                details += f" | ERROR: Expected 'not active' in error, got: {error_msg}"
        else:
            passed = False
            details += " | ERROR: Expected 400 Bad Request"

        self.test_result(
            "Cannot activate project with inactive parent",
            passed,
            details
        )

    async def test_activate_orphan_project(self):
        """Test: Orphan project (no parent) can be activated"""
        print(f"\n{Colors.BLUE}Test 3: Activate Orphan Project (No Parent){Colors.RESET}")

        response = self.client.patch(
            f"/api/projects/{self.project_orphan.id}",
            json={"status": "active"},
            headers={"X-Tenant-Key": self.tenant_key}
        )

        passed = response.status_code == 200
        details = f"Status Code: {response.status_code}"

        if passed:
            data = response.json()
            if data.get("status") == "active":
                details += " | Orphan project activated successfully"
            else:
                passed = False
                details += f" | ERROR: Expected status 'active', got '{data.get('status')}'"

        self.test_result(
            "Activate orphan project without parent",
            passed,
            details
        )

    async def test_update_non_status_fields(self):
        """Test: Updating non-status fields doesn't trigger validation"""
        print(f"\n{Colors.BLUE}Test 4: Update Project Name (No Validation){Colors.RESET}")

        response = self.client.patch(
            f"/api/projects/{self.project_inactive_parent.id}",
            json={"name": "Updated Project Name"},
            headers={"X-Tenant-Key": self.tenant_key}
        )

        passed = response.status_code == 200
        details = f"Status Code: {response.status_code}"

        if passed:
            data = response.json()
            if data.get("name") == "Updated Project Name":
                details += " | Name updated successfully (validation bypassed)"
            else:
                passed = False
                details += f" | ERROR: Name not updated correctly"

        self.test_result(
            "Update project name without status validation",
            passed,
            details
        )

    async def test_error_message_clarity(self):
        """Test: Error messages are clear and actionable"""
        print(f"\n{Colors.BLUE}Test 5: Error Message Clarity{Colors.RESET}")

        response = self.client.patch(
            f"/api/projects/{self.project_inactive_parent.id}",
            json={"status": "active"},
            headers={"X-Tenant-Key": self.tenant_key}
        )

        passed = True
        details = ""

        if response.status_code == 400:
            data = response.json()
            error_msg = data.get("detail", "")

            checks = {
                "Mentions product name": "Inactive Product" in error_msg,
                "Explains reason": "not active" in error_msg.lower(),
                "Provides solution": "activate the product" in error_msg.lower()
            }

            for check_name, check_result in checks.items():
                if check_result:
                    details += f"{check_name}: ✓ | "
                else:
                    passed = False
                    details += f"{check_name}: ✗ | "

            details += f"\nError: {error_msg}"
        else:
            passed = False
            details = f"Expected 400, got {response.status_code}"

        self.test_result(
            "Error message is clear and actionable",
            passed,
            details
        )

    def print_summary(self):
        """Print test execution summary"""
        print("\n" + "=" * 70)
        print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
        print("=" * 70)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.RESET}")

        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}ALL TESTS PASSED!{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}SOME TESTS FAILED{Colors.RESET}")

        print("=" * 70 + "\n")


async def main():
    """Main test execution"""
    test_suite = ProjectActivationValidationTests()

    try:
        await test_suite.setup()
        await test_suite.run_all_tests()
    finally:
        await test_suite.teardown()


if __name__ == "__main__":
    asyncio.run(main())
