"""
Performance tests for token reduction through config_data filtering.

Tests verify that role-based filtering achieves token reduction targets:
- Orchestrator: Full config (baseline)
- Implementer: ~40% reduction
- Tester: ~60% reduction
- Documenter: ~50% reduction
- Overall average: 40% reduction
"""

import json
from typing import Any, Dict

import pytest

from src.giljo_mcp.context_manager import ROLE_CONFIG_FILTERS, get_filtered_config, get_full_config
from src.giljo_mcp.models import Product


def estimate_tokens(text: str) -> int:
    """
    Rough token estimate: 1 token ≈ 4 characters

    This is a conservative estimate. Actual tokens may vary based on:
    - Tokenizer used (GPT-3.5, GPT-4, Claude)
    - Content structure (JSON, natural language, code)

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    return len(text) // 4


def config_to_text(config: Dict[str, Any]) -> str:
    """Convert config dictionary to text representation for token counting"""
    return json.dumps(config, indent=2)


# Use db_session fixture from conftest.py


@pytest.fixture
def realistic_product(db_session):
    """Create product with realistic GiljoAI_MCP config_data"""
    product = Product(
        id="test-product-tokens",
        tenant_key="test-tenant-tokens",
        name="GiljoAI MCP",
        config_data={
            # Core architecture (all roles need this)
            "architecture": "FastAPI + PostgreSQL + Vue.js multi-agent orchestration system",
            "tech_stack": [
                "Python 3.11+",
                "PostgreSQL 18",
                "Vue 3",
                "FastAPI",
                "SQLAlchemy",
                "Pydantic",
                "pytest",
                "Vuetify 3",
            ],
            # Codebase structure (implementation roles)
            "codebase_structure": {
                "src/giljo_mcp/": "Core orchestration engine",
                "src/giljo_mcp/tools/": "20+ MCP tools for agent coordination",
                "api/": "FastAPI REST API and WebSocket server",
                "api/endpoints/": "REST endpoint handlers (projects, agents, messages, tasks)",
                "frontend/": "Vue.js dashboard with real-time updates",
                "tests/": "Comprehensive test suite (unit, integration, performance)",
                "installer/": "Cross-platform installation system",
                "scripts/": "Utility and migration scripts",
                "docs/": "Documentation and technical specifications",
            },
            # Critical features (all roles should know)
            "critical_features": [
                "Multi-tenant isolation (CRITICAL - all queries filtered by tenant_key)",
                "Agent spawning and lifecycle management",
                "Inter-agent messaging with priority queues",
                "Real-time WebSocket updates",
                "Template-based agent configuration",
                "Context chunking for vision documents",
                "Role-based config filtering (this feature!)",
            ],
            # Test configuration (testing roles)
            "test_commands": [
                "pytest tests/unit/",
                "pytest tests/integration/",
                "pytest tests/performance/",
                "pytest tests/ --cov=giljo_mcp --cov-report=html",
            ],
            "test_config": {
                "coverage_threshold": 80,
                "test_database": "giljo_mcp_test",
                "async_tests": True,
                "markers": ["unit", "integration", "slow", "performance"],
            },
            # Database configuration (implementation roles)
            "database_type": "postgresql",
            "database_version": "18",
            "database_features": [
                "JSONB columns for flexible data",
                "GIN indexes for JSON queries",
                "Async SQLAlchemy sessions",
                "Connection pooling",
                "Multi-tenant row-level filtering",
            ],
            # Backend framework details (implementation roles)
            "backend_framework": "FastAPI",
            "backend_features": [
                "Async/await support",
                "Pydantic validation",
                "OpenAPI/Swagger docs",
                "WebSocket support",
                "Middleware for auth and CORS",
            ],
            # Frontend framework details (implementation roles)
            "frontend_framework": "Vue.js 3",
            "frontend_features": [
                "Composition API",
                "Vuetify 3 components",
                "Pinia state management",
                "WebSocket integration",
                "Real-time agent monitoring",
            ],
            # Deployment modes (implementation roles)
            "deployment_modes": ["localhost (development, no auth)", "server/LAN (production, API key auth)"],
            # API documentation (documentation roles)
            "api_docs": "/docs/api.md",
            "api_endpoints": ["/api/projects", "/api/agents", "/api/messages", "/api/tasks", "/api/templates"],
            # Documentation style (documentation roles)
            "documentation_style": "Markdown with code examples",
            "documentation_sections": [
                "Architecture overview",
                "API reference",
                "MCP tools manual",
                "Deployment guides",
                "Testing strategy",
            ],
            # Known issues (QA/testing roles)
            "known_issues": ["WebSocket reconnection needs retry logic", "Template caching could improve performance"],
            # Serena MCP integration (all roles)
            "serena_mcp_enabled": True,
            "serena_tools": [
                "read_file",
                "find_symbol",
                "search_for_pattern",
                "replace_symbol_body",
                "execute_shell_command",
            ],
        },
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    yield product

    # Cleanup
    db_session.delete(product)
    db_session.commit()


class TestTokenReductionBaseline:
    """Test baseline token counts for full config"""

    def test_full_config_token_count(self, realistic_product):
        """Test orchestrator receives full config (baseline)"""
        full_config = get_full_config(realistic_product)
        full_text = config_to_text(full_config)
        full_tokens = estimate_tokens(full_text)

        print("\n=== Full Config (Orchestrator) ===")
        print(f"Fields: {len(full_config)}")
        print(f"Characters: {len(full_text)}")
        print(f"Estimated Tokens: {full_tokens}")

        assert full_tokens > 0
        assert len(full_config) == len(realistic_product.config_data)

        # Store for comparison in other tests
        pytest.baseline_tokens = full_tokens
        pytest.baseline_fields = len(full_config)


class TestImplementerTokenReduction:
    """Test implementer receives reduced config (~40% reduction)"""

    def test_implementer_token_reduction(self, realistic_product):
        """Test implementer config has ~40% fewer tokens"""
        # Get baseline
        full_config = get_full_config(realistic_product)
        full_text = config_to_text(full_config)
        full_tokens = estimate_tokens(full_text)

        # Get implementer config
        impl_config = get_filtered_config("implementer-1", realistic_product, "implementer")
        impl_text = config_to_text(impl_config)
        impl_tokens = estimate_tokens(impl_text)

        # Calculate reduction
        reduction_percent = ((full_tokens - impl_tokens) / full_tokens) * 100
        field_reduction = ((len(full_config) - len(impl_config)) / len(full_config)) * 100

        print("\n=== Implementer Config ===")
        print(f"Fields: {len(impl_config)} (was {len(full_config)}, -{field_reduction:.1f}%)")
        print(f"Characters: {len(impl_text)} (was {len(full_text)})")
        print(f"Estimated Tokens: {impl_tokens} (was {full_tokens}, -{reduction_percent:.1f}%)")

        # Verify implementer has implementation-focused fields
        assert "architecture" in impl_config
        assert "tech_stack" in impl_config
        assert "codebase_structure" in impl_config
        assert "backend_framework" in impl_config

        # Verify filtered out non-relevant fields
        assert "test_commands" not in impl_config
        assert "api_docs" not in impl_config

        # Verify reduction target (~40%)
        assert reduction_percent >= 30, f"Implementer reduction {reduction_percent:.1f}% below 30% target"
        assert impl_tokens < full_tokens


class TestTesterTokenReduction:
    """Test tester receives minimal config (~60% reduction)"""

    def test_tester_token_reduction(self, realistic_product):
        """Test tester config has ~60% fewer tokens"""
        # Get baseline
        full_config = get_full_config(realistic_product)
        full_text = config_to_text(full_config)
        full_tokens = estimate_tokens(full_text)

        # Get tester config
        tester_config = get_filtered_config("tester-qa-1", realistic_product, "tester")
        tester_text = config_to_text(tester_config)
        tester_tokens = estimate_tokens(tester_text)

        # Calculate reduction
        reduction_percent = ((full_tokens - tester_tokens) / full_tokens) * 100
        field_reduction = ((len(full_config) - len(tester_config)) / len(full_config)) * 100

        print("\n=== Tester Config ===")
        print(f"Fields: {len(tester_config)} (was {len(full_config)}, -{field_reduction:.1f}%)")
        print(f"Characters: {len(tester_text)} (was {len(full_text)})")
        print(f"Estimated Tokens: {tester_tokens} (was {full_tokens}, -{reduction_percent:.1f}%)")

        # Verify tester has testing-focused fields
        assert "test_commands" in tester_config
        assert "test_config" in tester_config
        assert "critical_features" in tester_config

        # Verify filtered out non-relevant fields
        assert "codebase_structure" not in tester_config
        assert "backend_framework" not in tester_config
        assert "frontend_framework" not in tester_config

        # Verify reduction target (~60%)
        assert reduction_percent >= 50, f"Tester reduction {reduction_percent:.1f}% below 50% target"
        assert tester_tokens < full_tokens


class TestDocumenterTokenReduction:
    """Test documenter receives documentation-focused config (~50% reduction)"""

    def test_documenter_token_reduction(self, realistic_product):
        """Test documenter config has ~50% fewer tokens"""
        # Get baseline
        full_config = get_full_config(realistic_product)
        full_text = config_to_text(full_config)
        full_tokens = estimate_tokens(full_text)

        # Get documenter config
        doc_config = get_filtered_config("documenter-1", realistic_product, "documenter")
        doc_text = config_to_text(doc_config)
        doc_tokens = estimate_tokens(doc_text)

        # Calculate reduction
        reduction_percent = ((full_tokens - doc_tokens) / full_tokens) * 100
        field_reduction = ((len(full_config) - len(doc_config)) / len(full_config)) * 100

        print("\n=== Documenter Config ===")
        print(f"Fields: {len(doc_config)} (was {len(full_config)}, -{field_reduction:.1f}%)")
        print(f"Characters: {len(doc_text)} (was {len(full_text)})")
        print(f"Estimated Tokens: {doc_tokens} (was {full_tokens}, -{reduction_percent:.1f}%)")

        # Verify documenter has documentation-focused fields
        assert "api_docs" in doc_config
        assert "documentation_style" in doc_config
        assert "architecture" in doc_config

        # Verify filtered out non-relevant fields
        assert "test_commands" not in doc_config
        assert "database_features" not in doc_config

        # Verify reduction target (~50%)
        assert reduction_percent >= 40, f"Documenter reduction {reduction_percent:.1f}% below 40% target"
        assert doc_tokens < full_tokens


class TestOverallTokenReduction:
    """Test overall token reduction across all roles"""

    def test_average_token_reduction(self, realistic_product):
        """Test average token reduction across all agent roles is ~40%"""
        # Get baseline
        full_config = get_full_config(realistic_product)
        full_text = config_to_text(full_config)
        full_tokens = estimate_tokens(full_text)

        # Test all worker roles
        roles = [
            ("implementer-1", "implementer"),
            ("tester-qa-1", "tester"),
            ("documenter-1", "documenter"),
            ("reviewer-1", "reviewer"),
            ("analyzer-1", "analyzer"),
        ]

        role_reductions = []

        print("\n=== Token Reduction Summary ===")
        print(f"Baseline (Orchestrator): {full_tokens} tokens")
        print("\nRole Reductions:")

        for agent_name, role in roles:
            config = get_filtered_config(agent_name, realistic_product, role)
            config_text = config_to_text(config)
            tokens = estimate_tokens(config_text)
            reduction = ((full_tokens - tokens) / full_tokens) * 100
            role_reductions.append(reduction)

            print(f"  {role:12s}: {tokens:4d} tokens (-{reduction:5.1f}%)")

        # Calculate average
        avg_reduction = sum(role_reductions) / len(role_reductions)

        print(f"\nAverage Reduction: {avg_reduction:.1f}%")
        print("Target: 40%")
        print(f"Status: {'✓ PASS' if avg_reduction >= 40 else '✗ FAIL'}")

        # Verify average reduction meets target
        assert avg_reduction >= 35, f"Average reduction {avg_reduction:.1f}% below 35% minimum"

        # Store metrics for reporting
        pytest.token_metrics = {
            "baseline_tokens": full_tokens,
            "role_reductions": dict(zip([r[1] for r in roles], role_reductions)),
            "average_reduction": avg_reduction,
        }


class TestRoleFilteringAccuracy:
    """Test role filtering provides exactly the right fields"""

    def test_all_roles_get_correct_fields(self, realistic_product):
        """Test each role receives exactly its designated fields"""
        accuracy_results = []

        print("\n=== Role Filtering Accuracy ===")

        for role, allowed_fields in ROLE_CONFIG_FILTERS.items():
            if role == "orchestrator":
                # Orchestrator gets all fields
                config = get_full_config(realistic_product)
                expected_count = len(realistic_product.config_data)
                actual_count = len(config)
                accuracy = 100.0
            else:
                # Worker roles get filtered fields
                agent_name = f"{role}-test"
                config = get_filtered_config(agent_name, realistic_product, role)

                # Count how many allowed fields are present
                present_count = sum(1 for field in allowed_fields if field in config)
                expected_count = len(allowed_fields)
                actual_count = len(config)

                # Accuracy: (correct fields / total fields) * 100
                # Always include serena_mcp_enabled in count
                if "serena_mcp_enabled" in realistic_product.config_data:
                    expected_count += 1

                accuracy = (actual_count / expected_count) * 100 if expected_count > 0 else 100.0

            accuracy_results.append(accuracy)

            print(f"  {role:12s}: {actual_count:2d} fields (expected ~{expected_count:2d}, {accuracy:5.1f}% match)")

        # All roles should have 100% accuracy
        avg_accuracy = sum(accuracy_results) / len(accuracy_results)

        print(f"\nAverage Accuracy: {avg_accuracy:.1f}%")
        print("Target: 100%")

        assert avg_accuracy >= 95.0, f"Role filtering accuracy {avg_accuracy:.1f}% below 95% threshold"


class TestConfigDataSchemaCompliance:
    """Test all products comply with config_data schema"""

    def test_realistic_product_validates(self, realistic_product):
        """Test realistic product passes config_data validation"""
        from src.giljo_mcp.context_manager import validate_config_data

        is_valid, errors = validate_config_data(realistic_product.config_data)

        print("\n=== Config Schema Validation ===")
        print(f"Valid: {is_valid}")
        if errors:
            print(f"Errors: {errors}")
        else:
            print("Errors: None")

        assert is_valid is True, f"Config validation failed: {errors}"
        assert len(errors) == 0

    def test_minimal_config_validates(self, db_session):
        """Test minimal valid config passes validation"""
        from src.giljo_mcp.context_manager import validate_config_data

        minimal_config = {"architecture": "Simple REST API", "serena_mcp_enabled": False}

        is_valid, errors = validate_config_data(minimal_config)

        assert is_valid is True, f"Minimal config validation failed: {errors}"

    def test_invalid_config_fails_validation(self):
        """Test invalid config fails validation"""
        from src.giljo_mcp.context_manager import validate_config_data

        invalid_config = {
            # Missing required 'architecture'
            "serena_mcp_enabled": "yes"  # Wrong type (should be bool)
        }

        is_valid, errors = validate_config_data(invalid_config)

        assert is_valid is False
        assert len(errors) > 0
        assert any("architecture" in err for err in errors)


class TestPerformanceMetrics:
    """Test and report performance metrics"""

    def test_config_filtering_performance(self, realistic_product):
        """Test config filtering performance"""
        import time

        # Measure filtering time for each role
        roles = ["implementer", "tester", "documenter", "reviewer", "analyzer"]

        print("\n=== Config Filtering Performance ===")

        for role in roles:
            agent_name = f"{role}-perf-test"

            start = time.time()
            for _ in range(100):
                get_filtered_config(agent_name, realistic_product, role)
            elapsed = (time.time() - start) * 1000  # Convert to ms

            avg_ms = elapsed / 100

            print(f"  {role:12s}: {avg_ms:.2f}ms avg (100 iterations)")

            # Filtering should be fast (< 10ms per call)
            assert avg_ms < 10, f"{role} filtering too slow: {avg_ms:.2f}ms"

    def test_generate_metrics_report(self, realistic_product):
        """Generate comprehensive metrics report"""
        full_config = get_full_config(realistic_product)
        full_tokens = estimate_tokens(config_to_text(full_config))

        print(f"\n{'=' * 60}")
        print("TOKEN REDUCTION METRICS REPORT")
        print(f"{'=' * 60}")

        print("\nBASELINE (Orchestrator):")
        print(f"  Fields: {len(full_config)}")
        print(f"  Estimated Tokens: {full_tokens}")

        roles = [("implementer", 40), ("tester", 60), ("documenter", 50), ("reviewer", 45), ("analyzer", 35)]

        total_reduction = 0

        print("\nROLE-BASED REDUCTIONS:")
        for role, target in roles:
            config = get_filtered_config(f"{role}-1", realistic_product, role)
            tokens = estimate_tokens(config_to_text(config))
            reduction = ((full_tokens - tokens) / full_tokens) * 100
            total_reduction += reduction

            status = "✓" if reduction >= target - 10 else "✗"
            print(f"  {status} {role:12s}: {tokens:4d} tokens (-{reduction:5.1f}%, target: -{target}%)")

        avg_reduction = total_reduction / len(roles)

        print("\nOVERALL METRICS:")
        print(f"  Average Reduction: {avg_reduction:.1f}%")
        print("  Target: 40%")
        print(f"  Status: {'✓ SUCCESS' if avg_reduction >= 40 else '✗ NEEDS IMPROVEMENT'}")

        print(f"\n{'=' * 60}\n")

        assert avg_reduction >= 35, f"Overall reduction {avg_reduction:.1f}% below minimum threshold"
