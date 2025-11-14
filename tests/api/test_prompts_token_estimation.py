"""
Integration tests for token estimation endpoint.

Tests cover:
- POST /api/prompts/estimate-tokens (estimate mission token usage)

Test scenarios:
- Basic token calculation (mission + agents)
- Token calculation with project description
- Budget threshold calculations (within budget, over budget)
- Authentication enforcement
- Multi-tenant isolation
- Edge cases (empty mission, zero agents, very large mission)
- Invalid input validation
- Utilization percentage calculation

Handover: 0065 - Mission Launch Token Counter & Cancel Button (SCOPED)
"""

import pytest
from httpx import AsyncClient
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import User


# Fixtures


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create test user for testing."""
    from uuid import uuid4
    unique_suffix = uuid4().hex[:8]
    user = User(
        username=f"test_user_{unique_suffix}",
        password_hash=bcrypt.hash("test_password"),
        email=f"user_{unique_suffix}@test.com",
        role="developer",
        tenant_key=f"test_tenant_{unique_suffix}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def second_tenant_user(db_session: AsyncSession):
    """Create test user in different tenant."""
    user = User(
        username="tenant2_user",
        password_hash=bcrypt.hash("test_password"),
        email="tenant2@test.com",
        role="developer",
        tenant_key="test_tenant_2",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def user_token(api_client: AsyncClient, test_user):
    """Get JWT token for test user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": "test_user", "password": "test_password"},
    )
    assert response.status_code == 200

    # Extract token from cookie
    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


@pytest.fixture
async def second_tenant_token(api_client: AsyncClient, second_tenant_user):
    """Get JWT token for second tenant user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": "tenant2_user", "password": "test_password"},
    )
    assert response.status_code == 200

    # Extract token from cookie
    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


# Test Cases


@pytest.mark.asyncio
async def test_estimate_tokens_basic(api_client: AsyncClient, user_token):
    """Test basic token estimation with mission and agents."""
    # Create test request with ~2000 char mission (500 tokens at 4 chars/token)
    mission = "a" * 2000

    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 3,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "mission_tokens" in data
    assert "context_tokens" in data
    assert "agent_overhead" in data
    assert "total_estimate" in data
    assert "budget_available" in data
    assert "within_budget" in data
    assert "utilization_percent" in data

    # Verify calculations
    assert data["mission_tokens"] == 500  # 2000 / 4
    assert data["context_tokens"] == 0  # No project_description
    assert data["agent_overhead"] == 1500  # 3 * 500
    assert data["total_estimate"] == 2000  # 500 + 0 + 1500
    assert data["budget_available"] == 10000
    assert data["within_budget"] is True
    assert data["utilization_percent"] == 20.0  # (2000/10000) * 100


@pytest.mark.asyncio
async def test_estimate_tokens_with_project_description(api_client: AsyncClient, user_token):
    """Test token estimation with project description context."""
    mission = "a" * 1000  # 250 tokens
    project_description = "b" * 2000  # 500 tokens

    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 2,
            "project_description": project_description,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify calculations with context
    assert data["mission_tokens"] == 250  # 1000 / 4
    assert data["context_tokens"] == 500  # 2000 / 4
    assert data["agent_overhead"] == 1000  # 2 * 500
    assert data["total_estimate"] == 1750  # 250 + 500 + 1000
    assert data["within_budget"] is True


@pytest.mark.asyncio
async def test_estimate_tokens_at_budget_threshold(api_client: AsyncClient, user_token):
    """Test token estimation exactly at budget limit."""
    # Create mission that will hit exactly 10,000 token budget
    # Total = mission + context + (agents * 500)
    # 10000 = mission + 0 + (5 * 500)
    # mission = 7500 tokens = 30000 chars
    mission = "a" * 30000

    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 5,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total_estimate"] == 10000
    assert data["within_budget"] is True
    assert data["utilization_percent"] == 100.0


@pytest.mark.asyncio
async def test_estimate_tokens_over_budget(api_client: AsyncClient, user_token):
    """Test token estimation exceeding budget."""
    # Create mission that exceeds budget
    # Total = 50000 chars / 4 + (10 * 500) = 12500 + 5000 = 17500 tokens
    mission = "a" * 50000

    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 10,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total_estimate"] == 17500
    assert data["within_budget"] is False
    assert data["utilization_percent"] == 175.0


@pytest.mark.asyncio
async def test_estimate_tokens_zero_agents(api_client: AsyncClient, user_token):
    """Test token estimation with zero agents."""
    mission = "a" * 4000  # 1000 tokens

    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 0,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["mission_tokens"] == 1000
    assert data["agent_overhead"] == 0
    assert data["total_estimate"] == 1000


@pytest.mark.asyncio
async def test_estimate_tokens_empty_mission(api_client: AsyncClient, user_token):
    """Test token estimation with empty mission."""
    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": "",
            "agent_count": 3,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["mission_tokens"] == 0
    assert data["agent_overhead"] == 1500
    assert data["total_estimate"] == 1500


@pytest.mark.asyncio
async def test_estimate_tokens_very_large_mission(api_client: AsyncClient, user_token):
    """Test token estimation with very large mission (edge case)."""
    # 400,000 chars = 100,000 tokens (way over budget)
    mission = "a" * 400000

    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 1,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["mission_tokens"] == 100000
    assert data["agent_overhead"] == 500
    assert data["total_estimate"] == 100500
    assert data["within_budget"] is False
    assert data["utilization_percent"] == 1005.0


@pytest.mark.asyncio
async def test_estimate_tokens_requires_authentication(api_client: AsyncClient):
    """Test that endpoint requires authentication."""
    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": "test mission",
            "agent_count": 1,
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_estimate_tokens_invalid_token(api_client: AsyncClient):
    """Test that endpoint rejects invalid tokens."""
    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": "test mission",
            "agent_count": 1,
        },
        cookies={"access_token": "invalid_token_xyz"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_estimate_tokens_missing_mission(api_client: AsyncClient, user_token):
    """Test validation - mission field is required."""
    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "agent_count": 1,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_estimate_tokens_missing_agent_count(api_client: AsyncClient, user_token):
    """Test validation - agent_count field is required."""
    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": "test mission",
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_estimate_tokens_negative_agent_count(api_client: AsyncClient, user_token):
    """Test validation - agent_count cannot be negative."""
    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": "test mission",
            "agent_count": -5,
        },
        cookies={"access_token": user_token},
    )

    # Should either reject (422) or treat as 0
    # Accept either response depending on validation rules
    assert response.status_code in [200, 422]

    if response.status_code == 200:
        # If allowed, agent_overhead should be 0 or treated as invalid
        data = response.json()
        assert data["agent_overhead"] >= 0


@pytest.mark.asyncio
async def test_estimate_tokens_multi_tenant_isolation(
    api_client: AsyncClient,
    test_user,
    second_tenant_user,
    user_token,
    second_tenant_token,
):
    """Test that token estimation is tenant-isolated (no cross-tenant data leakage)."""
    # Both tenants can use endpoint independently
    mission = "a" * 4000  # 1000 tokens

    # Tenant 1 estimate
    response1 = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 2,
        },
        cookies={"access_token": user_token},
    )
    assert response1.status_code == 200
    data1 = response1.json()

    # Tenant 2 estimate (same request)
    response2 = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 2,
        },
        cookies={"access_token": second_tenant_token},
    )
    assert response2.status_code == 200
    data2 = response2.json()

    # Both should get identical results (stateless calculation)
    assert data1 == data2
    assert data1["total_estimate"] == 2000  # 1000 + 0 + 1000


@pytest.mark.asyncio
async def test_estimate_tokens_precision(api_client: AsyncClient, user_token):
    """Test utilization percentage precision and rounding."""
    # Create specific values to test rounding
    # Total = 3333 tokens, budget = 10000
    # Utilization = 33.33%
    mission = "a" * 11332  # 2833 tokens

    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 1,  # 500 tokens
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify rounding to 1 decimal place
    assert isinstance(data["utilization_percent"], float)
    assert data["utilization_percent"] == 33.3


@pytest.mark.asyncio
async def test_estimate_tokens_unicode_mission(api_client: AsyncClient, user_token):
    """Test token estimation with unicode characters."""
    # Unicode characters may vary in byte length but we count chars
    mission = "🚀" * 1000  # 1000 unicode chars

    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 1,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Should calculate based on character count
    assert data["mission_tokens"] == 250  # 1000 / 4


@pytest.mark.asyncio
async def test_estimate_tokens_with_none_project_description(api_client: AsyncClient, user_token):
    """Test that None project_description is handled correctly."""
    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": "test mission" * 100,
            "agent_count": 2,
            "project_description": None,
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["context_tokens"] == 0


@pytest.mark.asyncio
async def test_estimate_tokens_with_empty_project_description(api_client: AsyncClient, user_token):
    """Test that empty string project_description results in 0 context tokens."""
    response = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": "test mission" * 100,
            "agent_count": 2,
            "project_description": "",
        },
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["context_tokens"] == 0


@pytest.mark.asyncio
async def test_estimate_tokens_calculation_consistency(api_client: AsyncClient, user_token):
    """Test that calculations are consistent and deterministic."""
    mission = "a" * 8000  # 2000 tokens

    # Make same request twice
    response1 = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 4,
        },
        cookies={"access_token": user_token},
    )

    response2 = await api_client.post(
        "/api/prompts/estimate-tokens",
        json={
            "mission": mission,
            "agent_count": 4,
        },
        cookies={"access_token": user_token},
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    # Results should be identical
    assert response1.json() == response2.json()
