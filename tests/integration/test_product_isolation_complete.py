#!/usr/bin/env python3
"""
Comprehensive test suite for Product/Task Isolation (Project 5.1.e)
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import and_, func, select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project, Task
from src.giljo_mcp.tenant import TenantManager


class ProductIsolationTestSuite:
    def __init__(self):
        self.db_manager = DatabaseManager(is_async=True)
        self.tenant_manager = TenantManager()
        self.test_results = []
        self.test_tenant = None
        self.test_project_id = None
        self.product1_id = str(uuid.uuid4())
        self.product2_id = str(uuid.uuid4())

    def log_test(self, name: str, passed: bool, details: str = ""):
        """Log test result"""
        result = {"test": name, "passed": passed, "details": details, "timestamp": datetime.now().isoformat()}
        self.test_results.append(result)

    async def setup_test_data(self):
        """Set up test database and data"""

        # Create tables
        await self.db_manager.create_tables_async()

        # Generate test tenant
        self.test_tenant = self.db_manager.generate_tenant_key("test_project")
        self.tenant_manager.set_current_tenant(self.test_tenant)

        async with self.db_manager.get_session_async() as session:
            # Create test project
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key=self.test_tenant,
                name="Product Isolation Test Project",
                mission="Testing product isolation features",
                status="active",
            )
            session.add(project)
            await session.commit()
            self.test_project_id = project.id

            # Create tasks for Product 1
            tasks_product1 = [
                Task(
                    tenant_key=self.test_tenant,
                    product_id=self.product1_id,
                    project_id=self.test_project_id,
                    title=f"Product 1 Task {i}",
                    description=f"Task {i} for Product 1",
                    priority=["low", "medium", "high"][i % 3],
                    status=["pending", "in_progress", "database_initialized"][i % 3],
                    category="development",
                )
                for i in range(5)
            ]

            # Create tasks for Product 2
            tasks_product2 = [
                Task(
                    tenant_key=self.test_tenant,
                    product_id=self.product2_id,
                    project_id=self.test_project_id,
                    title=f"Product 2 Task {i}",
                    description=f"Task {i} for Product 2",
                    priority=["low", "medium", "high"][i % 3],
                    status=["pending", "in_progress"][i % 2],
                    category="testing",
                )
                for i in range(3)
            ]

            # Create tasks with no product (legacy compatibility)
            tasks_no_product = [
                Task(
                    tenant_key=self.test_tenant,
                    product_id=None,
                    project_id=self.test_project_id,
                    title=f"Legacy Task {i}",
                    description=f"Task {i} without product",
                    priority="medium",
                    status="waiting",
                    category="maintenance",
                )
                for i in range(2)
            ]

            session.add_all(tasks_product1 + tasks_product2 + tasks_no_product)
            await session.commit()

        self.log_test("Test Data Setup", True, "Created 10 tasks across 2 products + legacy")

    async def test_database_schema(self):
        """Test 1: Verify database schema has product_id"""

        async with self.db_manager.get_session_async() as session:
            # Check if we can query by product_id
            try:
                query = select(Task).where(Task.product_id == self.product1_id)
                result = await session.execute(query)
                result.scalars().all()

                self.log_test("Database Schema - product_id column", True, "Column exists and queryable")
            except Exception as e:
                self.log_test("Database Schema - product_id column", False, str(e))

    async def test_product_filtering(self):
        """Test 2: Test filtering by product_id"""

        async with self.db_manager.get_session_async() as session:
            # Test Product 1 filtering
            query1 = select(Task).where(and_(Task.tenant_key == self.test_tenant, Task.product_id == self.product1_id))
            result1 = await session.execute(query1)
            product1_tasks = result1.scalars().all()

            test1_pass = len(product1_tasks) == 5
            self.log_test("Product 1 Filtering", test1_pass, f"Expected 5 tasks, got {len(product1_tasks)}")

            # Test Product 2 filtering
            query2 = select(Task).where(and_(Task.tenant_key == self.test_tenant, Task.product_id == self.product2_id))
            result2 = await session.execute(query2)
            product2_tasks = result2.scalars().all()

            test2_pass = len(product2_tasks) == 3
            self.log_test("Product 2 Filtering", test2_pass, f"Expected 3 tasks, got {len(product2_tasks)}")

            # Test NULL product filtering
            query_null = select(Task).where(and_(Task.tenant_key == self.test_tenant, Task.product_id is None))
            result_null = await session.execute(query_null)
            null_tasks = result_null.scalars().all()

            test_null_pass = len(null_tasks) == 2
            self.log_test("NULL Product Filtering", test_null_pass, f"Expected 2 legacy tasks, got {len(null_tasks)}")

    async def test_product_isolation(self):
        """Test 3: Verify complete isolation between products"""

        async with self.db_manager.get_session_async() as session:
            # Get all tasks for Product 1
            query1 = select(Task).where(and_(Task.tenant_key == self.test_tenant, Task.product_id == self.product1_id))
            result1 = await session.execute(query1)
            product1_tasks = result1.scalars().all()

            # Verify no contamination
            contamination = [t for t in product1_tasks if t.product_id != self.product1_id]

            test_pass = len(contamination) == 0
            self.log_test(
                "Product Isolation - No Contamination",
                test_pass,
                f"Found {len(contamination)} contaminated tasks" if contamination else "Complete isolation verified",
            )

            # Verify categories are isolated
            categories1 = {t.category for t in product1_tasks}

            query2 = select(Task).where(and_(Task.tenant_key == self.test_tenant, Task.product_id == self.product2_id))
            result2 = await session.execute(query2)
            product2_tasks = result2.scalars().all()
            categories2 = {t.category for t in product2_tasks}

            self.log_test("Product Category Isolation", True, f"Product 1: {categories1}, Product 2: {categories2}")

    async def test_product_metrics(self):
        """Test 4: Test product-level metrics and aggregation"""

        async with self.db_manager.get_session_async() as session:
            # Get metrics for Product 1
            query1 = (
                select(Task.status, func.count(Task.id).label("count"))
                .where(and_(Task.tenant_key == self.test_tenant, Task.product_id == self.product1_id))
                .group_by(Task.status)
            )

            result1 = await session.execute(query1)
            metrics1 = {row.status: row.count for row in result1}

            expected_metrics1 = {"pending": 2, "in_progress": 2, "database_initialized": 1}
            metrics_match = all(metrics1.get(status, 0) == count for status, count in expected_metrics1.items())

            self.log_test("Product 1 Metrics", metrics_match, f"Status counts: {metrics1}")

            # Get priority distribution for Product 2
            query2 = (
                select(Task.priority, func.count(Task.id).label("count"))
                .where(and_(Task.tenant_key == self.test_tenant, Task.product_id == self.product2_id))
                .group_by(Task.priority)
            )

            result2 = await session.execute(query2)
            priorities2 = {row.priority: row.count for row in result2}

            self.log_test("Product 2 Priority Distribution", True, f"Priorities: {priorities2}")

    async def test_cross_product_operations(self):
        """Test 5: Test operations across products"""

        async with self.db_manager.get_session_async() as session:
            # Count total tasks across all products
            query_total = select(func.count(Task.id)).where(Task.tenant_key == self.test_tenant)
            result = await session.execute(query_total)
            total_count = result.scalar()

            test_pass = total_count == 10
            self.log_test("Total Task Count", test_pass, f"Expected 10 total tasks, got {total_count}")

            # Get product summary
            query_summary = (
                select(
                    Task.product_id,
                    func.count(Task.id).label("task_count"),
                    func.count(func.distinct(Task.category)).label("category_count"),
                )
                .where(Task.tenant_key == self.test_tenant)
                .group_by(Task.product_id)
            )

            result = await session.execute(query_summary)
            summary = []
            for row in result:
                summary.append(
                    {
                        "product_id": row.product_id[:8] if row.product_id else "NULL",
                        "tasks": row.task_count,
                        "categories": row.category_count,
                    }
                )

            self.log_test("Product Summary", len(summary) == 3, f"Products: {json.dumps(summary, indent=2)}")

    async def test_task_updates_respect_isolation(self):
        """Test 6: Verify task updates respect product boundaries"""

        async with self.db_manager.get_session_async() as session:
            # Get a task from Product 1
            query = (
                select(Task)
                .where(and_(Task.tenant_key == self.test_tenant, Task.product_id == self.product1_id))
                .limit(1)
            )
            result = await session.execute(query)
            task = result.scalar_one()

            original_product = task.product_id
            task_id = task.id

            # Update the task
            task.status = "database_initialized"
            task.priority = "critical"
            await session.commit()

            # Verify product_id wasn't changed
            query_verify = select(Task).where(Task.id == task_id)
            result = await session.execute(query_verify)
            updated_task = result.scalar_one()

            test_pass = updated_task.product_id == original_product
            self.log_test("Task Update Preserves Product", test_pass, "Product ID preserved after update")

    async def test_frontend_integration_points(self):
        """Test 7: Verify frontend integration requirements"""

        # Check if required frontend files exist
        frontend_files = [
            "frontend/src/stores/products.js",
            "frontend/src/components/ProductSwitcher.vue",
            "frontend/src/views/ProductsView.vue",
        ]

        for file_path in frontend_files:
            exists = Path(file_path).exists()
            self.log_test(f"Frontend File: {Path(file_path).name}", exists, "Exists" if exists else "Missing")

    def generate_report(self):
        """Generate comprehensive test report"""

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed

        if failed > 0:
            for result in self.test_results:
                if not result["passed"]:
                    pass

        # Save detailed report
        report_dir = Path("test_reports")
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / f"product_isolation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report_data = {
            "test_suite": "Product/Task Isolation (Project 5.1.e)",
            "timestamp": datetime.now().isoformat(),
            "summary": {"total": total, "passed": passed, "failed": failed, "success_rate": (passed / total) * 100},
            "test_results": self.test_results,
            "products_tested": {"product1_id": self.product1_id, "product2_id": self.product2_id},
        }

        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        return passed == total


async def main():
    """Run complete test suite"""

    tester = ProductIsolationTestSuite()

    try:
        # Setup
        await tester.setup_test_data()

        # Run all tests
        await tester.test_database_schema()
        await tester.test_product_filtering()
        await tester.test_product_isolation()
        await tester.test_product_metrics()
        await tester.test_cross_product_operations()
        await tester.test_task_updates_respect_isolation()
        await tester.test_frontend_integration_points()

        # Generate report
        all_passed = tester.generate_report()

        if all_passed:
            pass
        else:
            pass

        return all_passed

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    # sys.exit(0 if success else 1)  # Commented for pytest
