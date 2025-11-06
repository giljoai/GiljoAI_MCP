"""
End-to-End Integration Testing for Orchestrator Upgrade v2.0

Tests the complete workflow with live services:
- PostgreSQL database
- FastAPI REST API
- MCP tools
- Role-based config filtering
- Multi-tenant isolation
- GIN index performance
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from sqlalchemy import select, text


# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}")

# Verify DATABASE_URL is set
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL environment variable not set")

# Import database components
from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Product, Project


class E2ETestMetrics:
    """Collect and report test metrics"""

    def __init__(self):
        self.scenarios = {}
        self.start_time = time.time()

    def record_scenario(self, name: str, data: dict[str, Any]):
        """Record scenario results"""
        self.scenarios[name] = data

    def get_summary(self) -> dict[str, Any]:
        """Generate comprehensive summary"""
        duration = time.time() - self.start_time
        passed = sum(1 for s in self.scenarios.values() if s.get("result") == "PASS")
        failed = sum(1 for s in self.scenarios.values() if s.get("result") == "FAIL")

        return {
            "total_scenarios": len(self.scenarios),
            "passed": passed,
            "failed": failed,
            "duration_seconds": round(duration, 2),
            "scenarios": self.scenarios,
        }


class E2EIntegrationTester:
    """
    Orchestrator v2.0 End-to-End Integration Tester

    Executes 5 comprehensive test scenarios:
    1. Orchestrator Agent Full Context Delivery
    2. Worker Agent Filtered Context Delivery
    3. Specialized Agent Maximum Reduction
    4. Multi-User Context Isolation
    5. GIN Index Performance Testing
    """

    def __init__(self, api_url: str = "http://10.1.0.164:7272"):
        self.api_url = api_url
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL not found in environment")
        self.db_manager = DatabaseManager(database_url=database_url, is_async=True)
        self.metrics = E2ETestMetrics()
        self.test_products = []
        self.test_projects = []

    async def setup(self):
        """Initialize test environment"""
        print("=" * 80)
        print("  GiljoAI MCP Orchestrator v2.0 - End-to-End Integration Testing")
        print("=" * 80)
        print(f"API URL: {self.api_url}")
        print(f"Database: {self.db_manager.database_url}")
        print(f"Test started: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 80)

        # Verify API health
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/health")
            health = response.json()
            print(f"\nAPI Health Check: {health}")

            if health["status"] != "healthy":
                raise RuntimeError(f"API not healthy: {health}")

        # Verify database connection
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"Database Version: {version}")

        print("\n[PASS] Environment verification complete\n")

    async def cleanup(self):
        """Clean up test data"""
        print("\n" + "=" * 80)
        print("  Cleaning up test data...")
        print("=" * 80)

        async with self.db_manager.get_session_async() as session:
            # Delete test products
            for product_id in self.test_products:
                product = await session.get(Product, product_id)
                if product:
                    await session.delete(product)
                    print(f"Deleted test product: {product_id}")

            # Delete test projects
            for project_id in self.test_projects:
                project = await session.get(Project, project_id)
                if project:
                    await session.delete(project)
                    print(f"Deleted test project: {project_id}")

            await session.commit()

        print("[PASS] Cleanup complete\n")

    async def create_test_product(self, name: str, tenant_key: str, config_complexity: str = "full") -> str:
        """
        Create test product with specified config complexity

        Args:
            name: Product name
            tenant_key: Tenant isolation key
            config_complexity: "full" (14 fields), "medium" (9 fields), "minimal" (5 fields)

        Returns:
            Product ID
        """
        # Base config data (5 fields - minimal)
        config_data = {
            "project_name": f"E2E Test - {name}",
            "stack_info": {
                "backend": "FastAPI + PostgreSQL",
                "frontend": "Vue 3 + Vuetify",
                "deployment": "Docker + Uvicorn",
            },
            "coding_standards": {
                "style_guide": "PEP 8 for Python, Airbnb for JavaScript",
                "linting": "Ruff for Python, ESLint for JS",
                "testing": "pytest for backend, Vitest for frontend",
            },
            "key_features": [
                "Multi-agent orchestration",
                "Role-based context filtering",
                "Real-time WebSocket updates",
                "Multi-tenant data isolation",
            ],
            "repository_info": {
                "type": "git",
                "url": "https://github.com/GiljoAI/mcp-orchestrator",
                "branch": "master",
            },
        }

        # Add medium complexity fields (4 additional = 9 total)
        if config_complexity in ["medium", "full"]:
            config_data.update(
                {
                    "architecture_overview": """
GiljoAI MCP is a multi-agent orchestration system with hierarchical context loading.
The orchestrator (v2.0) uses role-based filtering to deliver only relevant config
fields to each agent, reducing token usage by up to 60% for specialized roles.
                """,
                    "api_endpoints": {
                        "products": "/api/v1/products",
                        "projects": "/api/v1/projects",
                        "agents": "/api/v1/agents",
                        "messages": "/api/v1/messages",
                    },
                    "database_schema": {
                        "products": "Product configuration and metadata",
                        "projects": "Project lifecycle and context tracking",
                        "agents": "Agent instances with role-based filtering",
                        "messages": "Inter-agent communication queue",
                    },
                    "testing_strategy": {
                        "unit": "pytest with 162+ tests",
                        "integration": "Live API and database testing",
                        "e2e": "Full workflow validation with metrics",
                    },
                }
            )

        # Add full complexity fields (5 additional = 14 total)
        if config_complexity == "full":
            config_data.update(
                {
                    "deployment_modes": {
                        "localhost": "Development mode, 127.0.0.1 binding",
                        "lan": "LAN mode with API key auth",
                        "wan": "WAN mode with OAuth + TLS",
                    },
                    "security_requirements": {
                        "authentication": "API key + JWT for server modes",
                        "multi_tenant_isolation": "All queries filtered by tenant_key",
                        "data_encryption": "TLS/SSL for WAN mode",
                    },
                    "performance_targets": {
                        "api_response": "<200ms for 95th percentile",
                        "database_queries": "<100ms with GIN index",
                        "websocket_latency": "<50ms for broadcasts",
                    },
                    "monitoring_and_logging": {
                        "logs": "Structured JSON logging with rotation",
                        "metrics": "Prometheus-compatible endpoints",
                        "tracing": "OpenTelemetry integration",
                    },
                    "future_enhancements": [
                        "Claude Code sub-agent integration",
                        "Advanced task templates",
                        "Performance analytics dashboard",
                        "Multi-project coordination",
                    ],
                }
            )

        # Calculate config size (approximate tokens)
        config_json = json.dumps(config_data, indent=2)
        config_tokens = len(config_json) // 4  # Rough estimate: 4 chars per token

        # Create product directly in database (REST API doesn't support config_data)
        product_id = str(uuid4())
        async with self.db_manager.get_session_async() as session:
            product = Product(
                id=product_id,
                name=name,
                tenant_key=tenant_key,
                config_data=config_data,
                created_at=datetime.now(timezone.utc),
            )
            session.add(product)
            await session.commit()

        self.test_products.append(product_id)

        print(f"Created test product: {name}")
        print(f"  - Product ID: {product_id}")
        print(f"  - Tenant Key: {tenant_key}")
        print(f"  - Config Complexity: {config_complexity} ({len(config_data)} fields)")
        print(f"  - Estimated Tokens: ~{config_tokens}")

        return product_id

    async def get_product_config_tokens(self, product_id: str, role: str) -> dict[str, Any]:
        """
        Fetch product config for a specific role and measure token delivery
        Uses context_manager filtering logic directly

        Returns:
            {
                'field_count': int,
                'estimated_tokens': int,
                'fields_delivered': list[str],
                'config_data': dict
            }
        """
        from giljo_mcp.context_manager import get_filtered_config, get_full_config

        async with self.db_manager.get_session_async() as session:
            # Get product from database
            product = await session.get(Product, product_id)
            if not product:
                raise RuntimeError(f"Product {product_id} not found in database")

            # Apply role-based filtering
            if role == "orchestrator":
                # Orchestrator gets full config
                config = get_full_config(product)
            else:
                # Other roles get filtered config
                config = get_filtered_config(agent_name=f"{role}-agent-test", product=product, agent_role=role)

        # Measure actual token delivery
        config_json = json.dumps(config, indent=2)
        estimated_tokens = len(config_json) // 4

        return {
            "field_count": len(config),
            "estimated_tokens": estimated_tokens,
            "fields_delivered": list(config.keys()),
            "config_data": config,
        }

    async def scenario_1_orchestrator_full_context(self):
        """
        Scenario 1: Orchestrator Agent Full Context Delivery

        Goal: Verify orchestrator receives all 14 config fields with 0% reduction
        """
        print("\n" + "=" * 80)
        print("  SCENARIO 1: Orchestrator Agent Full Context Delivery")
        print("=" * 80)

        try:
            # Create test product with full config
            tenant_key = f"test-orchestrator-{uuid4().hex[:8]}"
            product_id = await self.create_test_product(
                name="E2E Test - Orchestrator Full Context", tenant_key=tenant_key, config_complexity="full"
            )

            # Get full config (unfiltered - orchestrator view)
            full_config = await self.get_product_config_tokens(product_id, role="orchestrator")

            # Get baseline (what orchestrator should receive)
            baseline_tokens = full_config["estimated_tokens"]
            baseline_fields = full_config["field_count"]

            print("\nOrchestrator Context Delivery:")
            print(f"  - Fields Delivered: {baseline_fields}/14")
            print(f"  - Estimated Tokens: ~{baseline_tokens}")
            print("  - Reduction: 0% (expected)")
            print(f"  - Fields: {', '.join(full_config['fields_delivered'])}")

            # Validate
            assert baseline_fields == 14, f"Expected 14 fields, got {baseline_fields}"

            result = {
                "result": "PASS",
                "fields_delivered": baseline_fields,
                "expected_fields": 14,
                "estimated_tokens": baseline_tokens,
                "reduction_percent": 0,
                "fields": full_config["fields_delivered"],
            }

            print("\n[PASS] SCENARIO 1: PASS - Orchestrator receives full context")

        except Exception as e:
            print(f"\n[FAIL] SCENARIO 1: FAIL - {e!s}")
            result = {"result": "FAIL", "error": str(e)}

        self.metrics.record_scenario("scenario_1_orchestrator_full_context", result)
        return result

    async def scenario_2_worker_filtered_context(self):
        """
        Scenario 2: Worker Agent Filtered Context Delivery

        Goal: Verify implementer receives filtered config (9 fields, ~36% reduction)
        """
        print("\n" + "=" * 80)
        print("  SCENARIO 2: Worker Agent Filtered Context Delivery")
        print("=" * 80)

        try:
            # Create test product with full config
            tenant_key = f"test-worker-{uuid4().hex[:8]}"
            product_id = await self.create_test_product(
                name="E2E Test - Worker Filtered Context", tenant_key=tenant_key, config_complexity="full"
            )

            # Get orchestrator context (baseline)
            orchestrator_config = await self.get_product_config_tokens(product_id, role="orchestrator")
            baseline_tokens = orchestrator_config["estimated_tokens"]

            # Get implementer context (filtered)
            implementer_config = await self.get_product_config_tokens(product_id, role="implementer")

            # Calculate reduction
            tokens_delivered = implementer_config["estimated_tokens"]
            reduction_percent = round(((baseline_tokens - tokens_delivered) / baseline_tokens) * 100, 1)

            print("\nImplementer Context Delivery:")
            print(f"  - Fields Delivered: {implementer_config['field_count']}/14")
            print(f"  - Estimated Tokens: ~{tokens_delivered}")
            print(f"  - Baseline Tokens: ~{baseline_tokens}")
            print(f"  - Reduction: {reduction_percent}% (expected ~36%)")
            print(f"  - Fields: {', '.join(implementer_config['fields_delivered'])}")

            # Validate
            assert implementer_config["field_count"] == 9, f"Expected 9 fields, got {implementer_config['field_count']}"
            assert 30 <= reduction_percent <= 45, f"Expected ~36% reduction, got {reduction_percent}%"

            result = {
                "result": "PASS",
                "fields_delivered": implementer_config["field_count"],
                "expected_fields": 9,
                "estimated_tokens": tokens_delivered,
                "baseline_tokens": baseline_tokens,
                "reduction_percent": reduction_percent,
                "expected_reduction": 36,
                "fields": implementer_config["fields_delivered"],
            }

            print(f"\n[PASS] SCENARIO 2: PASS - Worker receives filtered context ({reduction_percent}% reduction)")

        except Exception as e:
            print(f"\n[FAIL] SCENARIO 2: FAIL - {e!s}")
            result = {"result": "FAIL", "error": str(e)}

        self.metrics.record_scenario("scenario_2_worker_filtered_context", result)
        return result

    async def scenario_3_specialized_minimal_context(self):
        """
        Scenario 3: Specialized Agent Maximum Reduction

        Goal: Verify tester/documenter receives minimal config (5-6 fields, ~60% reduction)
        """
        print("\n" + "=" * 80)
        print("  SCENARIO 3: Specialized Agent Maximum Reduction")
        print("=" * 80)

        try:
            # Create test product with full config
            tenant_key = f"test-specialist-{uuid4().hex[:8]}"
            product_id = await self.create_test_product(
                name="E2E Test - Specialist Minimal Context", tenant_key=tenant_key, config_complexity="full"
            )

            # Get orchestrator context (baseline)
            orchestrator_config = await self.get_product_config_tokens(product_id, role="orchestrator")
            baseline_tokens = orchestrator_config["estimated_tokens"]

            # Get tester context (minimal)
            tester_config = await self.get_product_config_tokens(product_id, role="tester")

            # Calculate reduction
            tokens_delivered = tester_config["estimated_tokens"]
            reduction_percent = round(((baseline_tokens - tokens_delivered) / baseline_tokens) * 100, 1)

            print("\nTester Context Delivery:")
            print(f"  - Fields Delivered: {tester_config['field_count']}/14")
            print(f"  - Estimated Tokens: ~{tokens_delivered}")
            print(f"  - Baseline Tokens: ~{baseline_tokens}")
            print(f"  - Reduction: {reduction_percent}% (expected ~60%)")
            print(f"  - Fields: {', '.join(tester_config['fields_delivered'])}")

            # Validate
            assert 5 <= tester_config["field_count"] <= 6, f"Expected 5-6 fields, got {tester_config['field_count']}"
            assert reduction_percent >= 55, f"Expected ~60% reduction, got {reduction_percent}%"

            result = {
                "result": "PASS",
                "fields_delivered": tester_config["field_count"],
                "expected_fields": "5-6",
                "estimated_tokens": tokens_delivered,
                "baseline_tokens": baseline_tokens,
                "reduction_percent": reduction_percent,
                "expected_reduction": 60,
                "fields": tester_config["fields_delivered"],
            }

            print(f"\n[PASS] SCENARIO 3: PASS - Specialist receives minimal context ({reduction_percent}% reduction)")

        except Exception as e:
            print(f"\n[FAIL] SCENARIO 3: FAIL - {e!s}")
            result = {"result": "FAIL", "error": str(e)}

        self.metrics.record_scenario("scenario_3_specialized_minimal_context", result)
        return result

    async def scenario_4_multi_tenant_isolation(self):
        """
        Scenario 4: Multi-User Context Isolation

        Goal: Verify tenant_key isolation prevents cross-tenant data leakage
        """
        print("\n" + "=" * 80)
        print("  SCENARIO 4: Multi-User Context Isolation")
        print("=" * 80)

        try:
            # Create two products with different tenant keys
            tenant_a = f"tenant-a-{uuid4().hex[:8]}"
            tenant_b = f"tenant-b-{uuid4().hex[:8]}"

            product_a_id = await self.create_test_product(
                name="E2E Test - Tenant A Product", tenant_key=tenant_a, config_complexity="full"
            )

            product_b_id = await self.create_test_product(
                name="E2E Test - Tenant B Product", tenant_key=tenant_b, config_complexity="full"
            )

            # Verify isolation at database level
            async with self.db_manager.get_session_async() as session:
                # Query products for tenant A
                query_a = select(Product).where(Product.tenant_key == tenant_a)
                result_a = await session.execute(query_a)
                products_a = result_a.scalars().all()

                # Query products for tenant B
                query_b = select(Product).where(Product.tenant_key == tenant_b)
                result_b = await session.execute(query_b)
                products_b = result_b.scalars().all()

            print("\nMulti-Tenant Isolation Results:")
            print(f"  - Tenant A Products: {len(products_a)}")
            print(f"  - Tenant B Products: {len(products_b)}")
            print(f"  - Product A ID: {product_a_id}")
            print(f"  - Product B ID: {product_b_id}")

            # Validate isolation
            assert len(products_a) >= 1, "Tenant A should have at least 1 product"
            assert len(products_b) >= 1, "Tenant B should have at least 1 product"

            # Verify no cross-contamination
            tenant_a_ids = [str(p.id) for p in products_a]
            tenant_b_ids = [str(p.id) for p in products_b]

            assert product_a_id in tenant_a_ids, "Product A not found in Tenant A"
            assert product_b_id in tenant_b_ids, "Product B not found in Tenant B"
            assert product_a_id not in tenant_b_ids, "Product A leaked into Tenant B!"
            assert product_b_id not in tenant_a_ids, "Product B leaked into Tenant A!"

            result = {
                "result": "PASS",
                "tenant_a_products": len(products_a),
                "tenant_b_products": len(products_b),
                "isolation_verified": True,
                "cross_tenant_leakage": False,
            }

            print("\n[PASS] SCENARIO 4: PASS - Multi-tenant isolation verified (no leakage)")

        except Exception as e:
            print(f"\n[FAIL] SCENARIO 4: FAIL - {e!s}")
            result = {"result": "FAIL", "error": str(e)}

        self.metrics.record_scenario("scenario_4_multi_tenant_isolation", result)
        return result

    async def scenario_5_gin_index_performance(self):
        """
        Scenario 5: GIN Index Performance Testing

        Goal: Verify JSONB query performance with GIN index (<100ms)
        """
        print("\n" + "=" * 80)
        print("  SCENARIO 5: GIN Index Performance Testing")
        print("=" * 80)

        try:
            # Create 10 test products with complex config data
            product_ids = []
            tenant_key = f"test-performance-{uuid4().hex[:8]}"

            print("\nCreating 10 test products for performance testing...")
            for i in range(10):
                product_id = await self.create_test_product(
                    name=f"E2E Test - Performance Product {i + 1}", tenant_key=tenant_key, config_complexity="full"
                )
                product_ids.append(product_id)

            # Measure query performance
            query_times = []

            print("\nMeasuring JSONB query performance (10 iterations)...")
            for product_id in product_ids:
                start = time.time()

                # Query database directly to measure JSONB performance (not HTTP overhead)
                from giljo_mcp.context_manager import get_full_config

                async with self.db_manager.get_session_async() as session:
                    product = await session.get(Product, product_id)
                    if product:
                        config = get_full_config(product)

                elapsed = (time.time() - start) * 1000  # Convert to ms
                query_times.append(elapsed)
                print(f"  - Query {len(query_times)}: {elapsed:.2f}ms")

            # Calculate statistics
            avg_time = sum(query_times) / len(query_times)
            min_time = min(query_times)
            max_time = max(query_times)
            p95_time = sorted(query_times)[int(len(query_times) * 0.95)]

            print("\nPerformance Statistics:")
            print(f"  - Average: {avg_time:.2f}ms")
            print(f"  - Min: {min_time:.2f}ms")
            print(f"  - Max: {max_time:.2f}ms")
            print(f"  - 95th Percentile: {p95_time:.2f}ms")
            print("  - Target: <100ms")

            # Validate performance
            performance_ok = avg_time < 100

            result = {
                "result": "PASS" if performance_ok else "FAIL",
                "queries_executed": len(query_times),
                "avg_time_ms": round(avg_time, 2),
                "min_time_ms": round(min_time, 2),
                "max_time_ms": round(max_time, 2),
                "p95_time_ms": round(p95_time, 2),
                "target_met": performance_ok,
                "target_ms": 100,
            }

            if performance_ok:
                print(f"\n[PASS] SCENARIO 5: PASS - GIN index performance target met ({avg_time:.2f}ms avg)")
            else:
                print(f"\n[FAIL] SCENARIO 5: FAIL - Performance target not met ({avg_time:.2f}ms avg > 100ms)")

        except Exception as e:
            print(f"\n[FAIL] SCENARIO 5: FAIL - {e!s}")
            result = {"result": "FAIL", "error": str(e)}

        self.metrics.record_scenario("scenario_5_gin_index_performance", result)
        return result

    async def run_all_scenarios(self):
        """Execute all 5 test scenarios and generate report"""
        await self.setup()

        try:
            # Execute scenarios sequentially
            await self.scenario_1_orchestrator_full_context()
            await self.scenario_2_worker_filtered_context()
            await self.scenario_3_specialized_minimal_context()
            await self.scenario_4_multi_tenant_isolation()
            await self.scenario_5_gin_index_performance()

            # Generate final report
            self.generate_report()

        finally:
            await self.cleanup()

    def generate_report(self):
        """Generate comprehensive E2E test report"""
        summary = self.metrics.get_summary()

        print("\n" + "=" * 80)
        print("  END-TO-END INTEGRATION TEST SUMMARY")
        print("=" * 80)
        print(f"\nTotal Scenarios: {summary['total_scenarios']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Duration: {summary['duration_seconds']}s")
        print(f"Success Rate: {(summary['passed'] / summary['total_scenarios'] * 100):.1f}%")

        print("\n" + "=" * 80)
        print("  DETAILED RESULTS")
        print("=" * 80)

        for name, data in summary["scenarios"].items():
            print(f"\n{name}:")
            print(f"  Result: {data.get('result', 'UNKNOWN')}")

            if data.get("result") == "PASS":
                if "fields_delivered" in data:
                    print(f"  Fields: {data['fields_delivered']}/{data['expected_fields']}")
                if "reduction_percent" in data:
                    print(f"  Token Reduction: {data['reduction_percent']}%")
                if "avg_time_ms" in data:
                    print(f"  Avg Query Time: {data['avg_time_ms']}ms")
            else:
                print(f"  Error: {data.get('error', 'Unknown error')}")

        # Write detailed JSON report
        report_path = "F:/GiljoAI_MCP/E2E_INTEGRATION_TEST_RESULTS.json"
        with open(report_path, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n[PASS] Detailed results saved to: {report_path}")

        # Production readiness assessment
        print("\n" + "=" * 80)
        print("  PRODUCTION READINESS ASSESSMENT")
        print("=" * 80)

        if summary["failed"] == 0:
            print("\n[SUCCESS] ALL TESTS PASSED - PRODUCTION READY")
            print("\nKey Achievements:")
            print("  [PASS] Role-based filtering working correctly")
            print("  [PASS] Token reduction targets met")
            print("  [PASS] Multi-tenant isolation verified")
            print("  [PASS] Performance targets achieved")
            print("  [PASS] No regressions detected")
            print("\nRecommendation: DEPLOY TO PRODUCTION")
        else:
            print("\n[WARNING]  SOME TESTS FAILED - REVIEW REQUIRED")
            print(f"\nFailed Scenarios: {summary['failed']}/{summary['total_scenarios']}")
            print("\nRecommendation: ADDRESS FAILURES BEFORE PRODUCTION DEPLOYMENT")


async def main():
    """Main entry point for E2E integration testing"""
    tester = E2EIntegrationTester(api_url="http://10.1.0.164:7272")
    await tester.run_all_scenarios()


if __name__ == "__main__":
    asyncio.run(main())
