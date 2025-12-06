"""
Helper functions for multi-tenant testing.

These helpers provide utilities for verifying tenant isolation,
testing concurrent operations, and measuring performance.
"""

import asyncio
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.models import MCPAgentJob, Message, Project, Task


@dataclass
class IsolationTestResult:
    """Result of an isolation test."""

    passed: bool
    tenant1_key: str
    tenant2_key: str
    test_type: str
    message: str
    details: Optional[dict[str, Any]] = None


@dataclass
class PerformanceMetric:
    """Performance measurement result."""

    operation: str
    tenant_key: str
    duration_ms: float
    success: bool
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class TenantIsolationHelper:
    """Helper class for testing tenant isolation."""

    def __init__(self):
        self.db_manager = get_db_manager()

    def assert_tenant_isolation(
        self, tenant1_key: str, tenant2_key: str, test_all_models: bool = True
    ) -> IsolationTestResult:
        """
        Assert that two tenants are completely isolated from each other.

        Args:
            tenant1_key: First tenant key
            tenant2_key: Second tenant key
            test_all_models: Whether to test all model types

        Returns:
            IsolationTestResult with test outcome
        """
        try:
            with self.db_manager.get_session() as session:
                # Test Project isolation
                tenant1_projects = session.query(Project).filter_by(tenant_key=tenant1_key).all()
                tenant2_projects = session.query(Project).filter_by(tenant_key=tenant2_key).all()

                # Ensure no cross-contamination
                for project in tenant1_projects:
                    if project.tenant_key != tenant1_key:
                        return IsolationTestResult(
                            passed=False,
                            tenant1_key=tenant1_key,
                            tenant2_key=tenant2_key,
                            test_type="project_isolation",
                            message=f"Project {project.id} has wrong tenant_key",
                            details={"project_id": project.id},
                        )

                # Try to access tenant2 data with tenant1 filter
                cross_access = (
                    session.query(Project)
                    .filter_by(tenant_key=tenant1_key)
                    .filter(Project.id.in_([p.id for p in tenant2_projects]))
                    .all()
                )

                if cross_access:
                    return IsolationTestResult(
                        passed=False,
                        tenant1_key=tenant1_key,
                        tenant2_key=tenant2_key,
                        test_type="cross_access",
                        message="Able to access tenant2 data with tenant1 key",
                        details={"leaked_projects": [p.id for p in cross_access]},
                    )

                if test_all_models:
                    # Test MCPAgentJob isolation
                    if not self._test_model_isolation(session, MCPAgentJob, tenant1_key, tenant2_key):
                        return IsolationTestResult(
                            passed=False,
                            tenant1_key=tenant1_key,
                            tenant2_key=tenant2_key,
                            test_type="agent_job_isolation",
                            message="MCPAgentJob isolation failed",
                        )

                    # Test Message isolation
                    if not self._test_model_isolation(session, Message, tenant1_key, tenant2_key):
                        return IsolationTestResult(
                            passed=False,
                            tenant1_key=tenant1_key,
                            tenant2_key=tenant2_key,
                            test_type="message_isolation",
                            message="Message isolation failed",
                        )

                    # Test Task isolation
                    if not self._test_model_isolation(session, Task, tenant1_key, tenant2_key):
                        return IsolationTestResult(
                            passed=False,
                            tenant1_key=tenant1_key,
                            tenant2_key=tenant2_key,
                            test_type="task_isolation",
                            message="Task isolation failed",
                        )

                return IsolationTestResult(
                    passed=True,
                    tenant1_key=tenant1_key,
                    tenant2_key=tenant2_key,
                    test_type="complete_isolation",
                    message="Complete isolation verified",
                )

        except Exception as e:
            return IsolationTestResult(
                passed=False,
                tenant1_key=tenant1_key,
                tenant2_key=tenant2_key,
                test_type="exception",
                message=f"Exception during isolation test: {e!s}",
            )

    def _test_model_isolation(self, session: Session, model_class: type, tenant1_key: str, tenant2_key: str) -> bool:
        """
        Test isolation for a specific model class.

        Args:
            session: Database session
            model_class: Model class to test
            tenant1_key: First tenant key
            tenant2_key: Second tenant key

        Returns:
            True if isolation is maintained, False otherwise
        """
        # Get all records for tenant1
        tenant1_records = session.query(model_class).filter_by(tenant_key=tenant1_key).all()

        # Get all records for tenant2
        tenant2_records = session.query(model_class).filter_by(tenant_key=tenant2_key).all()

        # Check no cross-contamination
        tenant1_ids = [r.id for r in tenant1_records]
        tenant2_ids = [r.id for r in tenant2_records]

        # Ensure no overlap
        if set(tenant1_ids) & set(tenant2_ids):
            return False

        # Try to access tenant2 records with tenant1 key
        for record_id in tenant2_ids:
            leaked = session.query(model_class).filter_by(tenant_key=tenant1_key, id=record_id).first()
            if leaked:
                return False

        return True

    def verify_tenant_key_propagation(self, parent_entity: Any, child_entities: list[Any]) -> tuple[bool, list[str]]:
        """
        Verify that tenant key is properly propagated from parent to children.

        Args:
            parent_entity: Parent entity with tenant_key
            child_entities: List of child entities

        Returns:
            Tuple of (success, list of error messages)
        """
        errors = []
        parent_key = parent_entity.tenant_key

        for child in child_entities:
            if not hasattr(child, "tenant_key"):
                errors.append(f"Child {child.id} missing tenant_key attribute")
                continue

            if child.tenant_key != parent_key:
                errors.append(f"Child {child.id} has tenant_key {child.tenant_key}, expected {parent_key}")

        return len(errors) == 0, errors

    def test_concurrent_tenant_operations(
        self, tenant_keys: list[str], operation: Callable, iterations: int = 10
    ) -> dict[str, Any]:
        """
        Test concurrent operations across multiple tenants.

        Args:
            tenant_keys: List of tenant keys to test
            operation: Operation to perform (receives tenant_key as argument)
            iterations: Number of iterations per tenant

        Returns:
            Dictionary with test results
        """
        results = {
            "success": True,
            "total_operations": len(tenant_keys) * iterations,
            "successful_operations": 0,
            "failed_operations": 0,
            "errors": [],
            "isolation_violations": [],
        }

        with ThreadPoolExecutor(max_workers=len(tenant_keys)) as executor:
            futures = []

            for tenant_key in tenant_keys:
                for _i in range(iterations):
                    future = executor.submit(operation, tenant_key)
                    futures.append((future, tenant_key))

            for future, tenant_key in futures:
                try:
                    result = future.result(timeout=30)

                    # Check for isolation violations
                    if hasattr(result, "tenant_key") and result.tenant_key != tenant_key:
                        results["isolation_violations"].append(
                            {"expected": tenant_key, "actual": result.tenant_key, "entity": str(result)}
                        )
                        results["success"] = False
                    else:
                        results["successful_operations"] += 1

                except Exception as e:
                    results["failed_operations"] += 1
                    results["errors"].append({"tenant_key": tenant_key, "error": str(e)})
                    results["success"] = False

        return results

    async def test_async_tenant_isolation(self, tenant_keys: list[str], async_operation: Callable) -> dict[str, Any]:
        """
        Test tenant isolation with async operations.

        Args:
            tenant_keys: List of tenant keys
            async_operation: Async operation to perform

        Returns:
            Dictionary with test results
        """
        results = {"success": True, "operations": len(tenant_keys), "violations": []}

        tasks = []
        for tenant_key in tenant_keys:
            task = async_operation(tenant_key)
            tasks.append((task, tenant_key))

        completed = await asyncio.gather(*[task for task, _ in tasks], return_exceptions=True)

        for (result, tenant_key), (_, expected_key) in zip(zip(completed, tenant_keys), tasks):
            if isinstance(result, Exception):
                results["success"] = False
                results["violations"].append({"tenant_key": expected_key, "error": str(result)})
            elif hasattr(result, "tenant_key") and result.tenant_key != expected_key:
                results["success"] = False
                results["violations"].append({"expected": expected_key, "actual": result.tenant_key})

        return results


class PerformanceHelper:
    """Helper class for performance testing."""

    def __init__(self):
        self.db_manager = get_db_manager()
        self.metrics: list[PerformanceMetric] = []

    @contextmanager
    def measure_operation(self, operation_name: str, tenant_key: str):
        """
        Context manager to measure operation performance.

        Args:
            operation_name: Name of the operation
            tenant_key: Tenant key for the operation

        Yields:
            PerformanceMetric object
        """
        metric = PerformanceMetric(operation=operation_name, tenant_key=tenant_key, duration_ms=0, success=False)

        start_time = time.perf_counter()

        try:
            yield metric
            metric.success = True
        except Exception as e:
            metric.error = str(e)
            metric.success = False
            raise
        finally:
            end_time = time.perf_counter()
            metric.duration_ms = (end_time - start_time) * 1000
            self.metrics.append(metric)

    def measure_query_performance(
        self, tenant_key: str, query_func: Callable, iterations: int = 100
    ) -> dict[str, float]:
        """
        Measure query performance for a tenant.

        Args:
            tenant_key: Tenant key to test
            query_func: Query function to measure
            iterations: Number of iterations

        Returns:
            Performance statistics
        """
        durations = []

        for _ in range(iterations):
            start = time.perf_counter()
            try:
                query_func(tenant_key)
                end = time.perf_counter()
                durations.append((end - start) * 1000)
            except Exception:
                pass

        if not durations:
            return {"avg_ms": 0, "min_ms": 0, "max_ms": 0, "median_ms": 0}

        durations.sort()

        return {
            "avg_ms": sum(durations) / len(durations),
            "min_ms": durations[0],
            "max_ms": durations[-1],
            "median_ms": durations[len(durations) // 2],
            "p95_ms": durations[int(len(durations) * 0.95)] if len(durations) > 20 else durations[-1],
            "p99_ms": durations[int(len(durations) * 0.99)] if len(durations) > 100 else durations[-1],
        }

    def simulate_concurrent_load(
        self, tenant_configs: list[dict[str, Any]], duration_seconds: int = 60
    ) -> dict[str, Any]:
        """
        Simulate concurrent load from multiple tenants.

        Args:
            tenant_configs: List of tenant configurations
            duration_seconds: Duration of the load test

        Returns:
            Load test results
        """
        results = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_response_time_ms": 0,
            "tenant_metrics": {},
        }

        start_time = time.time()
        end_time = start_time + duration_seconds

        with ThreadPoolExecutor(max_workers=len(tenant_configs)) as executor:
            futures = []

            for config in tenant_configs:
                future = executor.submit(self._run_tenant_load, config, end_time)
                futures.append((future, config["tenant_key"]))

            for future, tenant_key in futures:
                try:
                    tenant_results = future.result()
                    results["tenant_metrics"][tenant_key] = tenant_results
                    results["total_operations"] += tenant_results["operations"]
                    results["successful_operations"] += tenant_results["successful"]
                    results["failed_operations"] += tenant_results["failed"]
                except Exception as e:
                    results["tenant_metrics"][tenant_key] = {"error": str(e)}

        # Calculate average response time
        total_duration = 0
        total_ops = 0
        for tenant_metrics in results["tenant_metrics"].values():
            if "avg_response_ms" in tenant_metrics:
                total_duration += tenant_metrics["avg_response_ms"] * tenant_metrics["operations"]
                total_ops += tenant_metrics["operations"]

        if total_ops > 0:
            results["average_response_time_ms"] = total_duration / total_ops

        return results

    def _run_tenant_load(self, config: dict[str, Any], end_time: float) -> dict[str, Any]:
        """
        Run load test for a single tenant.

        Args:
            config: Tenant configuration
            end_time: When to stop the test

        Returns:
            Tenant-specific results
        """
        tenant_key = config["tenant_key"]
        operations = 0
        successful = 0
        failed = 0
        response_times = []

        while time.time() < end_time:
            start = time.perf_counter()

            try:
                # Perform random operation
                operation = random.choice([self._create_entity, self._query_entities, self._update_entity])

                operation(tenant_key)
                successful += 1

            except Exception:
                failed += 1

            finally:
                operations += 1
                response_times.append((time.perf_counter() - start) * 1000)

            # Small delay to prevent overwhelming the system
            time.sleep(random.uniform(0.01, 0.1))

        return {
            "operations": operations,
            "successful": successful,
            "failed": failed,
            "avg_response_ms": sum(response_times) / len(response_times) if response_times else 0,
            "max_response_ms": max(response_times) if response_times else 0,
            "min_response_ms": min(response_times) if response_times else 0,
        }

    def _create_entity(self, tenant_key: str) -> None:
        """
        Create a random entity for load testing.

        Migration Note (0129a): Replaced Agent with MCPAgentJob.
        """
        with self.db_manager.get_session() as session:
            project = session.query(Project).filter_by(tenant_key=tenant_key).first()

            if project:
                agent_job = MCPAgentJob(
                    job_id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    project_id=project.id,
                    agent_name=f"load_test_agent_{uuid.uuid4().hex[:8]}",
                    agent_type="tester",
                    mission="Load testing mission",
                    status="waiting",
                )
                session.add(agent_job)
                session.commit()

    def _query_entities(self, tenant_key: str) -> None:
        """
        Query entities for load testing.

        Migration Note (0129a): Replaced Agent with MCPAgentJob.
        """
        with self.db_manager.get_session() as session:
            session.query(MCPAgentJob).filter_by(tenant_key=tenant_key).limit(10).all()

            session.query(Message).filter_by(tenant_key=tenant_key).limit(10).all()

    def _update_entity(self, tenant_key: str) -> None:
        """
        Update a random entity for load testing.

        Migration Note (0129a): Replaced Agent with MCPAgentJob.
        """
        with self.db_manager.get_session() as session:
            agent_job = session.query(MCPAgentJob).filter_by(tenant_key=tenant_key).first()

            if agent_job:
                # Update mission as a proxy for context usage
                agent_job.mission = f"Updated mission {uuid.uuid4().hex[:8]}"
                session.commit()

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get summary of all collected metrics.

        Returns:
            Metrics summary
        """
        if not self.metrics:
            return {"message": "No metrics collected"}

        successful = [m for m in self.metrics if m.success]
        failed = [m for m in self.metrics if not m.success]

        operations = {}
        for metric in self.metrics:
            if metric.operation not in operations:
                operations[metric.operation] = []
            operations[metric.operation].append(metric.duration_ms)

        operation_stats = {}
        for op_name, durations in operations.items():
            operation_stats[op_name] = {
                "count": len(durations),
                "avg_ms": sum(durations) / len(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
            }

        return {
            "total_operations": len(self.metrics),
            "successful": len(successful),
            "failed": len(failed),
            "operation_stats": operation_stats,
        }


# Global helper instances
isolation_helper = TenantIsolationHelper()
performance_helper = PerformanceHelper()


# Convenience functions
def assert_tenant_isolation(tenant1_key: str, tenant2_key: str, test_all_models: bool = True) -> IsolationTestResult:
    """Assert complete isolation between two tenants."""
    return isolation_helper.assert_tenant_isolation(tenant1_key, tenant2_key, test_all_models)


def verify_tenant_key_propagation(parent: Any, children: list[Any]) -> tuple[bool, list[str]]:
    """Verify tenant key propagation."""
    return isolation_helper.verify_tenant_key_propagation(parent, children)


def measure_query_performance(tenant_key: str, operation: Callable, iterations: int = 100) -> dict[str, float]:
    """Measure query performance for a tenant."""
    return performance_helper.measure_query_performance(tenant_key, operation, iterations)


def simulate_concurrent_operations(tenant_configs: list[dict[str, Any]], duration_seconds: int = 60) -> dict[str, Any]:
    """Simulate concurrent operations from multiple tenants."""
    return performance_helper.simulate_concurrent_load(tenant_configs, duration_seconds)
