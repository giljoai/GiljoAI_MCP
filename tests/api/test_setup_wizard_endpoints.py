"""
API tests for setup wizard endpoints (Handover 0855a).

Tests:
- SetupStateUpdate Pydantic model validation
- PATCH /auth/me/setup-state endpoint
- GET /auth/api-keys/active endpoint
- GET /auth/me returns setup wizard fields

Test Strategy (TDD):
1. Write tests that expect setup wizard integration (RED phase)
2. Update endpoints to pass tests (GREEN phase)
3. Verify all tests pass (REFACTOR phase)
"""

import pytest
from pydantic import ValidationError

from api.endpoints.auth import SetupStateUpdate


# ---------------------------------------------------------------------------
# Pydantic model validation tests (no API client needed)
# ---------------------------------------------------------------------------


class TestSetupStateUpdateValidation:
    """Validate SetupStateUpdate Pydantic model constraints."""

    def test_valid_all_fields(self):
        """All fields provided with valid values."""
        update = SetupStateUpdate(
            setup_selected_tools=["claude_code", "cursor"],
            setup_step_completed=3,
            setup_complete=True,
        )
        assert update.setup_selected_tools == ["claude_code", "cursor"]
        assert update.setup_step_completed == 3
        assert update.setup_complete is True

    def test_valid_partial_step_only(self):
        """Only setup_step_completed provided."""
        update = SetupStateUpdate(setup_step_completed=2)
        assert update.setup_step_completed == 2
        assert update.setup_selected_tools is None
        assert update.setup_complete is None

    def test_valid_empty_tools_list(self):
        """Empty tools list is acceptable."""
        update = SetupStateUpdate(setup_selected_tools=[])
        assert update.setup_selected_tools == []

    def test_valid_step_zero(self):
        """Step 0 (minimum) is valid."""
        update = SetupStateUpdate(setup_step_completed=0)
        assert update.setup_step_completed == 0

    def test_valid_step_four(self):
        """Step 4 (maximum) is valid."""
        update = SetupStateUpdate(setup_step_completed=4)
        assert update.setup_step_completed == 4

    def test_valid_all_none(self):
        """All fields None (no-op update) is valid."""
        update = SetupStateUpdate()
        assert update.setup_selected_tools is None
        assert update.setup_step_completed is None
        assert update.setup_complete is None

    def test_rejects_step_five(self):
        """Step 5 exceeds maximum of 4."""
        with pytest.raises(ValidationError) as exc_info:
            SetupStateUpdate(setup_step_completed=5)
        assert "less than or equal to 4" in str(exc_info.value)

    def test_rejects_negative_step(self):
        """Negative step values are invalid."""
        with pytest.raises(ValidationError) as exc_info:
            SetupStateUpdate(setup_step_completed=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_step_large_value(self):
        """Large step value exceeds maximum."""
        with pytest.raises(ValidationError):
            SetupStateUpdate(setup_step_completed=100)


# ---------------------------------------------------------------------------
# API endpoint tests (require api_client and auth fixtures)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_setup_state_full_update(api_client, auth_headers):
    """PATCH /auth/me/setup-state with all fields updates setup wizard state."""
    response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={
            "setup_step_completed": 2,
            "setup_selected_tools": ["claude_code"],
            "setup_complete": False,
        },
    )
    if response.status_code == 401:
        pytest.skip("No authenticated session available in test environment")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["setup_step_completed"] == 2
    assert data["setup_selected_tools"] == ["claude_code"]
    assert data["setup_complete"] is False


@pytest.mark.asyncio
async def test_patch_setup_state_partial_step_only(api_client, auth_headers):
    """PATCH /auth/me/setup-state with only step updates just that field."""
    response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"setup_step_completed": 3},
    )
    if response.status_code == 401:
        pytest.skip("No authenticated session available in test environment")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["setup_step_completed"] == 3


@pytest.mark.asyncio
async def test_patch_setup_state_complete_flag(api_client, auth_headers):
    """PATCH /auth/me/setup-state marking setup as complete."""
    response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"setup_complete": True, "setup_step_completed": 4},
    )
    if response.status_code == 401:
        pytest.skip("No authenticated session available in test environment")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["setup_complete"] is True
    assert data["setup_step_completed"] == 4


@pytest.mark.asyncio
async def test_patch_setup_state_invalid_step_rejected(api_client, auth_headers):
    """PATCH /auth/me/setup-state with step=5 returns 422 validation error."""
    response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"setup_step_completed": 5},
    )
    if response.status_code == 401:
        pytest.skip("No authenticated session available in test environment")
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_patch_setup_state_unauthenticated(api_client):
    """PATCH /auth/me/setup-state without auth returns 401."""
    response = await api_client.patch(
        "/api/auth/me/setup-state",
        json={"setup_step_completed": 1},
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_get_active_api_keys_empty(api_client, auth_headers):
    """GET /auth/api-keys/active returns empty list when no keys exist."""
    response = await api_client.get(
        "/api/auth/api-keys/active",
        headers=auth_headers,
    )
    if response.status_code == 401:
        pytest.skip("No authenticated session available in test environment")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_active_api_keys_unauthenticated(api_client):
    """GET /auth/api-keys/active without auth returns 401."""
    response = await api_client.get("/api/auth/api-keys/active")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_get_me_includes_setup_fields(api_client, auth_headers):
    """GET /auth/me response includes setup wizard fields with defaults."""
    response = await api_client.get(
        "/api/auth/me",
        headers=auth_headers,
    )
    if response.status_code == 401:
        pytest.skip("No authenticated session available in test environment")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert "setup_complete" in data, "Response should include setup_complete field"
    assert "setup_selected_tools" in data, "Response should include setup_selected_tools field"
    assert "setup_step_completed" in data, "Response should include setup_step_completed field"

    # Defaults for a freshly created test user
    assert data["setup_complete"] is False, "Default setup_complete should be False"
    assert data["setup_step_completed"] == 0, "Default setup_step_completed should be 0"


@pytest.mark.asyncio
async def test_setup_state_roundtrip(api_client, auth_headers):
    """PATCH setup state then GET /me confirms persisted values."""
    # Set state
    patch_response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={
            "setup_step_completed": 2,
            "setup_selected_tools": ["claude_code", "windsurf"],
            "setup_complete": False,
        },
    )
    if patch_response.status_code == 401:
        pytest.skip("No authenticated session available in test environment")
    assert patch_response.status_code == 200

    # Read back via /me
    me_response = await api_client.get("/api/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    data = me_response.json()
    assert data["setup_step_completed"] == 2
    assert data["setup_selected_tools"] == ["claude_code", "windsurf"]
    assert data["setup_complete"] is False
