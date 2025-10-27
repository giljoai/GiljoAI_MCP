"""
Comprehensive tests for active product token estimation endpoint.

Tests GET /api/v1/products/active/token-estimate endpoint that calculates
real token usage from active product's config_data based on user's field priority configuration.

Test Coverage:
- Successful token calculation with active product
- Missing config_data fields (graceful handling)
- No active product (404)
- Multi-tenant isolation (critical)
- Token calculation accuracy
- Percentage calculation
- Integration with user field_priority_config
"""

import json
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, User


@pytest_asyncio.fixture
async def test_tenant_key() -> str:
    """Generate test tenant key."""
    return "test_tenant_token_estimate"


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_tenant_key: str) -> User:
    """
    Create test user with field_priority_config.

    Uses default field priorities with 2000 token budget.
    """
    from tests.fixtures.auth_fixtures import UserFactory

    # Default field priority config (matching defaults.py)
    field_priority_config = {
        "version": "1.0",
        "token_budget": 2000,
        "fields": {
            # Priority 1: Critical
            "tech_stack.languages": 1,
            "tech_stack.backend": 1,
            "tech_stack.frontend": 1,
            "architecture.pattern": 1,
            "features.core": 1,
            # Priority 2: High
            "tech_stack.database": 2,
            "architecture.api_style": 2,
            "test_config.strategy": 2,
            # Priority 3: Medium
            "tech_stack.infrastructure": 3,
            "architecture.design_patterns": 3,
            "architecture.notes": 3,
            "test_config.frameworks": 3,
            "test_config.coverage_target": 3,
        }
    }

    user = await UserFactory.create_user(
        session=db_session,
        username="test_token_user",
        tenant_key=test_tenant_key,
        role="developer",
        field_priority_config=field_priority_config
    )

    return user


@pytest_asyncio.fixture
async def test_product_active(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_user: User
) -> Product:
    """
    Create active product with comprehensive config_data.

    Config data includes all prioritized fields with realistic content.
    """
    config_data = {
        "tech_stack": {
            "languages": "Python 3.11+, TypeScript 5.x",  # ~50 chars = ~13 tokens
            "backend": "FastAPI with async/await, SQLAlchemy ORM",  # ~50 chars = ~13 tokens
            "frontend": "Vue 3 Composition API, Vuetify 3, Pinia state management",  # ~70 chars = ~18 tokens
            "database": "PostgreSQL 18 with JSONB for flexible schemas",  # ~55 chars = ~14 tokens
            "infrastructure": "Docker containers, Nginx reverse proxy, systemd services"  # ~75 chars = ~19 tokens
        },
        "architecture": {
            "pattern": "Microservices with event-driven communication via WebSockets",  # ~70 chars = ~18 tokens
            "api_style": "RESTful API with OpenAPI 3.0 documentation, JWT authentication",  # ~75 chars = ~19 tokens
            "design_patterns": "Repository pattern, Factory pattern, Strategy pattern for platform handlers",  # ~95 chars = ~24 tokens
            "notes": "Multi-tenant architecture with strict data isolation. All database queries filtered by tenant_key."  # ~110 chars = ~28 tokens
        },
        "features": {
            "core": "AI agent orchestration, multi-tenant isolation, real-time WebSocket updates, vision document chunking"  # ~115 chars = ~29 tokens
        },
        "test_config": {
            "strategy": "TDD with pytest, 80% coverage target, integration tests for all API endpoints",  # ~90 chars = ~23 tokens
            "frameworks": "pytest, pytest-asyncio, httpx for async testing, factory pattern for test data",  # ~95 chars = ~24 tokens
            "coverage_target": "80% minimum coverage with focus on critical paths and multi-tenant isolation"  # ~95 chars = ~24 tokens
        }
    }

    product = Product(
        id="test_product_active_001",
        tenant_key=test_tenant_key,
        name="Active Test Product",
        description="Product for token estimation testing",
        config_data=config_data,
        is_active=True  # ACTIVE product
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest_asyncio.fixture
async def test_product_inactive(
    db_session: AsyncSession,
    test_tenant_key: str
) -> Product:
    """Create inactive product (should not be counted as active)."""
    product = Product(
        id="test_product_inactive_001",
        tenant_key=test_tenant_key,
        name="Inactive Test Product",
        description="Should not be considered active",
        config_data={"tech_stack": {"languages": "Python"}},
        is_active=False  # INACTIVE
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest_asyncio.fixture
async def other_tenant_product(db_session: AsyncSession) -> Product:
    """Create product for different tenant (multi-tenant isolation test)."""
    product = Product(
        id="other_tenant_product_001",
        tenant_key="other_tenant_key",
        name="Other Tenant Product",
        description="Product from different tenant",
        config_data={"tech_stack": {"languages": "Python"}},
        is_active=True
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest.mark.asyncio
async def test_token_estimate_success(
    api_client: AsyncClient,
    test_user: User,
    test_product_active: Product
):
    """
    Test successful token estimation with active product.

    Validates:
    - Endpoint returns 200
    - All required fields present in response
    - Token calculations are reasonable
    - Percentage calculation is correct
    - Field tokens include all prioritized fields
    """
    # Mock authentication to return test_user
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    try:
        response = await api_client.get("/api/v1/products/active/token-estimate")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Validate response structure
        assert "product_id" in data
        assert "product_name" in data
        assert "field_tokens" in data
        assert "total_field_tokens" in data
        assert "overhead_tokens" in data
        assert "total_tokens" in data
        assert "token_budget" in data
        assert "percentage_used" in data

        # Validate product identification
        assert data["product_id"] == test_product_active.id
        assert data["product_name"] == test_product_active.name

        # Validate token calculations
        assert data["overhead_tokens"] == 500, "Overhead should be 500 tokens"
        assert data["token_budget"] == 2000, "Budget should be 2000 from user config"
        assert data["total_tokens"] > 0, "Total tokens should be positive"
        assert data["total_field_tokens"] > 0, "Field tokens should be positive"

        # Validate total = field_tokens + overhead
        assert data["total_tokens"] == data["total_field_tokens"] + data["overhead_tokens"]

        # Validate percentage calculation
        expected_percentage = round((data["total_tokens"] / data["token_budget"]) * 100, 2)
        assert data["percentage_used"] == expected_percentage

        # Validate field_tokens dict contains expected fields
        assert "tech_stack.languages" in data["field_tokens"]
        assert "tech_stack.backend" in data["field_tokens"]
        assert "tech_stack.frontend" in data["field_tokens"]
        assert "architecture.pattern" in data["field_tokens"]
        assert "features.core" in data["field_tokens"]

        # Validate token calculations (char/4 formula)
        # tech_stack.languages = "Python 3.11+, TypeScript 5.x" = ~50 chars = ~13 tokens
        assert data["field_tokens"]["tech_stack.languages"] > 0

        # All field tokens should be positive integers
        for field, tokens in data["field_tokens"].items():
            assert isinstance(tokens, int), f"Field {field} tokens should be integer"
            assert tokens >= 0, f"Field {field} tokens should be non-negative"

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_token_estimate_no_active_product(
    api_client: AsyncClient,
    test_user: User,
    test_product_inactive: Product
):
    """
    Test token estimation when no active product exists.

    Should return 404 with appropriate error message.
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    try:
        response = await api_client.get("/api/v1/products/active/token-estimate")

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "no active product" in data["detail"].lower()

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_token_estimate_missing_config_fields(
    api_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_tenant_key: str
):
    """
    Test token estimation with missing config_data fields.

    Should handle gracefully by:
    - Returning 0 tokens for missing fields
    - Still calculating total correctly
    - Not raising errors
    """
    # Create product with partial config_data (missing many fields)
    partial_config = {
        "tech_stack": {
            "languages": "Python 3.11+"
            # Missing: backend, frontend, database, infrastructure
        },
        "architecture": {
            "pattern": "Microservices"
            # Missing: api_style, design_patterns, notes
        }
        # Missing: features, test_config
    }

    product = Product(
        id="test_product_partial_config",
        tenant_key=test_tenant_key,
        name="Partial Config Product",
        config_data=partial_config,
        is_active=True
    )

    db_session.add(product)
    await db_session.commit()

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    try:
        response = await api_client.get("/api/v1/products/active/token-estimate")

        assert response.status_code == 200

        data = response.json()

        # Should have tokens for fields that exist
        assert data["field_tokens"]["tech_stack.languages"] > 0
        assert data["field_tokens"]["architecture.pattern"] > 0

        # Missing fields should return 0 tokens (not error)
        assert data["field_tokens"].get("tech_stack.backend", 0) == 0
        assert data["field_tokens"].get("features.core", 0) == 0

        # Total should still be calculated correctly
        assert data["total_tokens"] == data["total_field_tokens"] + data["overhead_tokens"]

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_token_estimate_multi_tenant_isolation(
    api_client: AsyncClient,
    test_user: User,
    other_tenant_product: Product
):
    """
    CRITICAL: Test multi-tenant isolation.

    User should only see their tenant's active product, not other tenants'.
    Even if another tenant has an active product, user should get 404.
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    try:
        # other_tenant_product is active but belongs to different tenant
        response = await api_client.get("/api/v1/products/active/token-estimate")

        # Should return 404 because test_user's tenant has no active product
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "no active product" in data["detail"].lower()

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_token_estimate_calculation_accuracy(
    api_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_tenant_key: str
):
    """
    Test token calculation accuracy using character/4 formula.

    Validates that token calculation matches expected char/4 conversion.
    """
    # Create product with known character counts
    known_config = {
        "tech_stack": {
            "languages": "ABCD",  # 4 chars = 1 token
            "backend": "ABCDEFGH",  # 8 chars = 2 tokens
        },
        "architecture": {
            "pattern": "ABCDEFGHIJKL"  # 12 chars = 3 tokens
        }
    }

    product = Product(
        id="test_product_known_tokens",
        tenant_key=test_tenant_key,
        name="Known Token Product",
        config_data=known_config,
        is_active=True
    )

    db_session.add(product)
    await db_session.commit()

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    try:
        response = await api_client.get("/api/v1/products/active/token-estimate")

        assert response.status_code == 200

        data = response.json()

        # Validate exact token calculations (char / 4, rounded up)
        # "ABCD" = 4 chars = 4/4 = 1 token
        assert data["field_tokens"]["tech_stack.languages"] == 1

        # "ABCDEFGH" = 8 chars = 8/4 = 2 tokens
        assert data["field_tokens"]["tech_stack.backend"] == 2

        # "ABCDEFGHIJKL" = 12 chars = 12/4 = 3 tokens
        assert data["field_tokens"]["architecture.pattern"] == 3

        # Total field tokens = 1 + 2 + 3 = 6
        assert data["total_field_tokens"] == 6

        # Total tokens = 6 + 500 overhead = 506
        assert data["total_tokens"] == 506

        # Percentage = (506 / 2000) * 100 = 25.3%
        assert data["percentage_used"] == 25.3

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_token_estimate_user_without_field_config(
    api_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product_active: Product
):
    """
    Test token estimation for user without field_priority_config.

    Should use default field priorities from defaults.py.
    """
    from tests.fixtures.auth_fixtures import UserFactory

    # Create user without field_priority_config
    user_no_config = await UserFactory.create_user(
        session=db_session,
        username="user_no_config",
        tenant_key=test_tenant_key,
        role="developer",
        field_priority_config=None  # No custom config
    )

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return user_no_config

    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    try:
        response = await api_client.get("/api/v1/products/active/token-estimate")

        assert response.status_code == 200

        data = response.json()

        # Should use default token budget from defaults.py (2000)
        assert data["token_budget"] == 2000

        # Should have field tokens for all default priority fields
        assert "tech_stack.languages" in data["field_tokens"]
        assert "features.core" in data["field_tokens"]

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_token_estimate_empty_config_data(
    api_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_tenant_key: str
):
    """
    Test token estimation with empty config_data.

    Should handle gracefully with all field tokens = 0.
    """
    product = Product(
        id="test_product_empty_config",
        tenant_key=test_tenant_key,
        name="Empty Config Product",
        config_data={},  # Empty config
        is_active=True
    )

    db_session.add(product)
    await db_session.commit()

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    try:
        response = await api_client.get("/api/v1/products/active/token-estimate")

        assert response.status_code == 200

        data = response.json()

        # All field tokens should be 0
        assert data["total_field_tokens"] == 0

        # Total = 0 + 500 overhead = 500
        assert data["total_tokens"] == 500

        # Percentage = (500 / 2000) * 100 = 25.0%
        assert data["percentage_used"] == 25.0

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_token_estimate_percentage_over_100(
    api_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_tenant_key: str
):
    """
    Test token estimation when usage exceeds budget.

    Percentage should be > 100% (not capped).
    """
    # Create product with very large config_data (exceeds 2000 token budget)
    large_content = "A" * 8000  # 8000 chars = 2000 tokens

    large_config = {
        "tech_stack": {
            "languages": large_content,
        }
    }

    product = Product(
        id="test_product_large_config",
        tenant_key=test_tenant_key,
        name="Large Config Product",
        config_data=large_config,
        is_active=True
    )

    db_session.add(product)
    await db_session.commit()

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    try:
        response = await api_client.get("/api/v1/products/active/token-estimate")

        assert response.status_code == 200

        data = response.json()

        # Should exceed budget
        assert data["total_tokens"] > data["token_budget"]

        # Percentage should be > 100%
        assert data["percentage_used"] > 100.0

        # Validate calculation: (total / budget) * 100
        expected_pct = round((data["total_tokens"] / data["token_budget"]) * 100, 2)
        assert data["percentage_used"] == expected_pct

    finally:
        app.dependency_overrides.clear()
