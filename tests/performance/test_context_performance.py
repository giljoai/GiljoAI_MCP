"""
Performance tests for context loading and filtering.

Metrics:
1. Token usage reduction (orchestrator vs workers)
2. Config loading time
3. Filtering performance
4. JSONB query performance with GIN index
"""

import pytest
import time
import json
from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.models import Product
from src.giljo_mcp.context_manager import get_full_config, get_filtered_config


@pytest.fixture
def db_session():
    """Get database session"""
    db = get_db_manager()
    with db.get_session() as session:
        yield session


@pytest.fixture
def large_config_product(db_session):
    """Create product with large config_data (100+ fields)"""
    config_data = {
        "architecture": "Microservices with FastAPI + PostgreSQL + Vue.js + Redis + Docker",
        "serena_mcp_enabled": True,
        "tech_stack": [
            "Python 3.11", "PostgreSQL 18", "Vue 3", "FastAPI", "SQLAlchemy",
            "Alembic", "Docker", "Redis", "Nginx", "Gunicorn"
        ],
        "codebase_structure": {
            "api": "REST API endpoints with WebSocket support",
            "frontend": "Vue 3 SPA with Vuetify and Pinia",
            "src/core": "Core business logic and orchestration",
            "src/models": "SQLAlchemy ORM models",
            "src/services": "Business service layer",
            "src/utils": "Utility functions and helpers",
            "tests/unit": "Unit tests with pytest",
            "tests/integration": "Integration tests",
            "tests/e2e": "End-to-end tests",
            "migrations": "Alembic database migrations",
            "docs": "Comprehensive documentation",
            "scripts": "Automation and deployment scripts",
            "installer": "Cross-platform installer",
            "docker": "Docker configuration files"
        },
        "critical_features": [
            "Multi-tenant isolation with tenant_key",
            "Agent orchestration and coordination",
            "Message queue for inter-agent communication",
            "Vision document chunking (50K+ tokens)",
            "Database-backed template system",
            "Real-time WebSocket updates",
            "API key authentication",
            "Role-based access control",
            "Configuration discovery system",
            "Git integration for version control"
        ],
        "test_commands": [
            "pytest tests/",
            "pytest tests/unit/ --cov=src",
            "pytest tests/integration/ --cov=src --cov-append",
            "pytest tests/e2e/",
            "npm run test",
            "npm run test:unit",
            "npm run test:e2e"
        ],
        "test_config": {
            "coverage_threshold": 80,
            "framework": "pytest",
            "parallel": True,
            "markers": ["slow", "integration", "unit", "e2e"],
            "plugins": ["pytest-asyncio", "pytest-cov", "pytest-mock"],
            "timeout": 300
        },
        "api_docs": "/docs/api_reference.md",
        "documentation_style": "Markdown with mermaid diagrams and code samples",
        "database_type": "postgresql",
        "database_version": "18",
        "database_features": ["JSONB", "GIN indexes", "Full-text search", "Triggers"],
        "frontend_framework": "Vue 3",
        "frontend_version": "3.3",
        "frontend_libraries": ["Vuetify", "Pinia", "Vue Router", "Axios"],
        "backend_framework": "FastAPI",
        "backend_version": "0.104",
        "backend_features": ["Async support", "Dependency injection", "OpenAPI docs"],
        "deployment_modes": ["localhost", "server", "lan", "wan"],
        "deployment_requirements": {
            "python": "3.11+",
            "postgresql": "14+",
            "node": "18+",
            "memory": "2GB+",
            "disk": "10GB+"
        },
        "known_issues": [
            "Performance optimization needed for large vision documents",
            "WebSocket reconnection handling needs improvement",
            "Template caching could be more efficient"
        ],
        "performance_targets": {
            "api_response_time": "< 200ms",
            "websocket_latency": "< 100ms",
            "database_query_time": "< 50ms",
            "agent_spawn_time": "< 1s"
        },
        "security_features": [
            "API key authentication",
            "Tenant isolation",
            "SQL injection prevention",
            "XSS protection",
            "CORS configuration"
        ],
        "monitoring": {
            "logging_level": "INFO",
            "log_format": "JSON",
            "metrics_enabled": True,
            "health_check_endpoint": "/health"
        }
    }

    product = Product(
        id="perf-test-product-large",
        tenant_key="perf-test",
        name="Performance Test Product (Large Config)",
        config_data=config_data
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    yield product

    # Cleanup
    db_session.delete(product)
    db_session.commit()


class TestTokenUsageReduction:
    """Test token usage reduction through filtering"""

    def test_implementer_token_reduction_percentage(self, large_config_product):
        """Test implementer achieves significant token reduction"""
        full_config = get_full_config(large_config_product)
        filtered_config = get_filtered_config("implementer-1", large_config_product)

        # Calculate token estimates
        full_tokens = estimate_tokens(full_config)
        filtered_tokens = estimate_tokens(filtered_config)

        reduction_pct = ((full_tokens - filtered_tokens) / full_tokens) * 100

        print(f"\nImplementer Token Reduction:")
        print(f"  Full config: {full_tokens} tokens")
        print(f"  Filtered config: {filtered_tokens} tokens")
        print(f"  Reduction: {reduction_pct:.1f}%")

        # Target: 40%+ reduction
        assert reduction_pct >= 40, f"Expected 40%+ reduction, got {reduction_pct:.1f}%"

    def test_tester_token_reduction_percentage(self, large_config_product):
        """Test tester achieves significant token reduction"""
        full_config = get_full_config(large_config_product)
        filtered_config = get_filtered_config("tester-qa-1", large_config_product)

        full_tokens = estimate_tokens(full_config)
        filtered_tokens = estimate_tokens(filtered_config)

        reduction_pct = ((full_tokens - filtered_tokens) / full_tokens) * 100

        print(f"\nTester Token Reduction:")
        print(f"  Full config: {full_tokens} tokens")
        print(f"  Filtered config: {filtered_tokens} tokens")
        print(f"  Reduction: {reduction_pct:.1f}%")

        # Testers should have even more reduction (more specialized)
        assert reduction_pct >= 50, f"Expected 50%+ reduction, got {reduction_pct:.1f}%"

    def test_documenter_token_reduction_percentage(self, large_config_product):
        """Test documenter achieves significant token reduction"""
        full_config = get_full_config(large_config_product)
        filtered_config = get_filtered_config("documenter-1", large_config_product)

        full_tokens = estimate_tokens(full_config)
        filtered_tokens = estimate_tokens(filtered_config)

        reduction_pct = ((full_tokens - filtered_tokens) / full_tokens) * 100

        print(f"\nDocumenter Token Reduction:")
        print(f"  Full config: {full_tokens} tokens")
        print(f"  Filtered config: {filtered_tokens} tokens")
        print(f"  Reduction: {reduction_pct:.1f}%")

        assert reduction_pct >= 50, f"Expected 50%+ reduction, got {reduction_pct:.1f}%"

    def test_all_workers_achieve_target_reduction(self, large_config_product):
        """Test all worker roles achieve target token reduction"""
        full_config = get_full_config(large_config_product)
        full_tokens = estimate_tokens(full_config)

        worker_roles = ["implementer", "tester", "documenter", "analyzer", "reviewer"]
        results = []

        for role in worker_roles:
            filtered_config = get_filtered_config(f"{role}-1", large_config_product)
            filtered_tokens = estimate_tokens(filtered_config)
            reduction_pct = ((full_tokens - filtered_tokens) / full_tokens) * 100

            results.append({
                "role": role,
                "full_tokens": full_tokens,
                "filtered_tokens": filtered_tokens,
                "reduction_pct": reduction_pct
            })

        print("\nToken Reduction Summary (All Roles):")
        print(f"{'Role':<15} {'Full':<10} {'Filtered':<10} {'Reduction':<12}")
        print("-" * 50)

        for result in results:
            print(f"{result['role']:<15} {result['full_tokens']:<10} "
                  f"{result['filtered_tokens']:<10} {result['reduction_pct']:<10.1f}%")

            # All workers should have at least 30% reduction
            assert result['reduction_pct'] >= 30, \
                f"{result['role']} only achieved {result['reduction_pct']:.1f}% reduction"


class TestConfigLoadingPerformance:
    """Test config loading performance"""

    def test_get_full_config_performance(self, large_config_product):
        """Test get_full_config() performance"""
        iterations = 100

        start_time = time.time()
        for _ in range(iterations):
            config = get_full_config(large_config_product)
        end_time = time.time()

        avg_time_ms = ((end_time - start_time) / iterations) * 1000

        print(f"\nget_full_config() Performance:")
        print(f"  Average time: {avg_time_ms:.2f}ms")
        print(f"  Iterations: {iterations}")

        # Should be very fast (< 10ms average)
        assert avg_time_ms < 10, f"Expected < 10ms, got {avg_time_ms:.2f}ms"

    def test_get_filtered_config_performance(self, large_config_product):
        """Test get_filtered_config() performance"""
        iterations = 100

        start_time = time.time()
        for _ in range(iterations):
            config = get_filtered_config("implementer-1", large_config_product)
        end_time = time.time()

        avg_time_ms = ((end_time - start_time) / iterations) * 1000

        print(f"\nget_filtered_config() Performance:")
        print(f"  Average time: {avg_time_ms:.2f}ms")
        print(f"  Iterations: {iterations}")

        # Should be fast (< 20ms average)
        assert avg_time_ms < 20, f"Expected < 20ms, got {avg_time_ms:.2f}ms"

    def test_multiple_role_filtering_performance(self, large_config_product):
        """Test filtering for multiple roles sequentially"""
        roles = ["implementer", "tester", "documenter", "analyzer", "reviewer"]
        iterations = 20

        start_time = time.time()
        for _ in range(iterations):
            for role in roles:
                config = get_filtered_config(f"{role}-1", large_config_product)
        end_time = time.time()

        total_calls = iterations * len(roles)
        avg_time_ms = ((end_time - start_time) / total_calls) * 1000

        print(f"\nMultiple Role Filtering Performance:")
        print(f"  Average time per call: {avg_time_ms:.2f}ms")
        print(f"  Total calls: {total_calls}")
        print(f"  Roles tested: {', '.join(roles)}")

        assert avg_time_ms < 20, f"Expected < 20ms average, got {avg_time_ms:.2f}ms"


class TestDatabaseQueryPerformance:
    """Test database query performance with JSONB and GIN index"""

    def test_product_query_with_config_data(self, db_session, large_config_product):
        """Test querying products with config_data is performant"""
        iterations = 50

        start_time = time.time()
        for _ in range(iterations):
            product = db_session.query(Product).filter(
                Product.id == large_config_product.id
            ).first()
            config = product.config_data
        end_time = time.time()

        avg_time_ms = ((end_time - start_time) / iterations) * 1000

        print(f"\nProduct Query with config_data Performance:")
        print(f"  Average time: {avg_time_ms:.2f}ms")
        print(f"  Iterations: {iterations}")

        # Should be fast (< 50ms average)
        assert avg_time_ms < 50, f"Expected < 50ms, got {avg_time_ms:.2f}ms"

    def test_jsonb_field_access_performance(self, large_config_product):
        """Test accessing JSONB fields is performant"""
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            arch = large_config_product.config_data.get("architecture")
            tech_stack = large_config_product.config_data.get("tech_stack")
            features = large_config_product.config_data.get("critical_features")
        end_time = time.time()

        avg_time_us = ((end_time - start_time) / iterations) * 1000000

        print(f"\nJSONB Field Access Performance:")
        print(f"  Average time: {avg_time_us:.2f}µs")
        print(f"  Iterations: {iterations}")

        # Should be very fast (< 100µs average)
        assert avg_time_us < 100, f"Expected < 100µs, got {avg_time_us:.2f}µs"


class TestScalabilityMetrics:
    """Test scalability with large config_data"""

    def test_config_data_size_impact(self, db_session):
        """Test performance impact of different config_data sizes"""
        sizes = [
            ("small", 5),    # 5 fields
            ("medium", 20),  # 20 fields
            ("large", 50),   # 50 fields
        ]

        results = []

        for size_name, field_count in sizes:
            config_data = generate_config_data(field_count)

            product = Product(
                id=f"perf-test-{size_name}",
                tenant_key="perf-test-size",
                name=f"Performance Test ({size_name})",
                config_data=config_data
            )

            db_session.add(product)
            db_session.commit()
            db_session.refresh(product)

            # Measure filtering time
            start_time = time.time()
            for _ in range(100):
                filtered = get_filtered_config("implementer-1", product)
            end_time = time.time()

            avg_time_ms = ((end_time - start_time) / 100) * 1000

            results.append({
                "size": size_name,
                "fields": field_count,
                "avg_time_ms": avg_time_ms
            })

            # Cleanup
            db_session.delete(product)
            db_session.commit()

        print("\nConfig Data Size Impact:")
        print(f"{'Size':<10} {'Fields':<10} {'Avg Time (ms)':<15}")
        print("-" * 35)

        for result in results:
            print(f"{result['size']:<10} {result['fields']:<10} {result['avg_time_ms']:<15.2f}")

        # Performance should scale linearly or better
        # Large should not be more than 3x slower than small
        small_time = next(r['avg_time_ms'] for r in results if r['size'] == 'small')
        large_time = next(r['avg_time_ms'] for r in results if r['size'] == 'large')

        scaling_factor = large_time / small_time
        assert scaling_factor < 3, f"Large config is {scaling_factor:.1f}x slower (should be < 3x)"


# Helper functions

def estimate_tokens(config_dict: dict) -> int:
    """
    Estimate token count for config_data.
    Uses Claude's approximation: 1 token ≈ 4 characters
    """
    config_str = json.dumps(config_dict, indent=2)
    return len(config_str) // 4


def generate_config_data(field_count: int) -> dict:
    """Generate config_data with specified number of fields"""
    config = {
        "architecture": "Test Architecture",
        "serena_mcp_enabled": True
    }

    # Add additional fields to reach target count
    for i in range(field_count - 2):
        config[f"field_{i}"] = f"value_{i}"

    return config
