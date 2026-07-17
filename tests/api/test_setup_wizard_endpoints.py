# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

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


class TestTutorialReentryValidation:
    """BE-9201: learning_beat / router_choice model constraints."""

    def test_valid_beat_range(self):
        """Beats 1 and 6 (the rail's boundaries) are both valid."""
        assert SetupStateUpdate(learning_beat=1).learning_beat == 1
        assert SetupStateUpdate(learning_beat=6).learning_beat == 6

    def test_rejects_beat_zero_and_seven(self):
        """The tutorial has exactly 6 rail stops — 0 and 7 are out of range."""
        with pytest.raises(ValidationError):
            SetupStateUpdate(learning_beat=0)
        with pytest.raises(ValidationError):
            SetupStateUpdate(learning_beat=7)

    def test_valid_router_choices(self):
        """All four router doors are accepted."""
        for door in ("A", "B", "C", "D"):
            assert SetupStateUpdate(router_choice=door).router_choice == door

    def test_rejects_unknown_router_choice(self):
        """Anything outside A|B|C|D is rejected at the boundary."""
        with pytest.raises(ValidationError):
            SetupStateUpdate(router_choice="E")
        with pytest.raises(ValidationError):
            SetupStateUpdate(router_choice="a")  # case-sensitive contract

    def test_defaults_are_none(self):
        """Omitted fields stay None — an older frontend never sends them."""
        update = SetupStateUpdate()
        assert update.learning_beat is None
        assert update.router_choice is None


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
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert "setup_complete" in data, "Response should include setup_complete field"
    assert "setup_selected_tools" in data, "Response should include setup_selected_tools field"
    assert "setup_step_completed" in data, "Response should include setup_step_completed field"

    # Defaults for a freshly created test user
    assert data["setup_complete"] is False, "Default setup_complete should be False"
    assert data["setup_step_completed"] == 0, "Default setup_step_completed should be 0"


# ---------------------------------------------------------------------------
# BE-9201: onboarding-tutorial re-entry state (learning_beat + router_choice)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_tutorial_reentry_state_persists_and_echoes(api_client, auth_headers):
    """PATCH learning_beat + router_choice persists both and echoes them back."""
    response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"learning_beat": 3, "router_choice": "D"},
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["learning_beat"] == 3
    assert data["router_choice"] == "D"


@pytest.mark.asyncio
async def test_patch_learning_beat_six_boundary_roundtrips(api_client, auth_headers):
    """A persisted beat=6 (the router stop) survives the roundtrip.

    Documents the range contract for FE re-entry: 6 is a legal stored value
    (the state machine's last rail stop), so a stale beat=6 re-entry reads back
    6 and lands on the router — never a validation error or a crash.
    """
    patch_response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"learning_beat": 6},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["learning_beat"] == 6

    me_response = await api_client.get("/api/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    assert me_response.json()["learning_beat"] == 6


@pytest.mark.asyncio
async def test_patch_tutorial_reentry_rejects_out_of_range(api_client, auth_headers):
    """learning_beat outside 1-6 and router_choice outside A-D both 422."""
    beat_response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"learning_beat": 7},
    )
    assert beat_response.status_code == 422

    door_response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"router_choice": "X"},
    )
    assert door_response.status_code == 422


@pytest.mark.asyncio
async def test_patch_setup_state_tolerates_unknown_fields(api_client, auth_headers):
    """A payload carrying an unknown field is accepted (ignored), not 422'd.

    The forward/backward tolerance contract: an older backend receiving a newer
    frontend's extra fields must not break the whole PATCH.
    """
    response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"learning_beat": 2, "some_future_field": "ignored"},
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["learning_beat"] == 2


@pytest.mark.asyncio
async def test_get_me_includes_tutorial_reentry_fields(api_client, auth_headers):
    """GET /me carries learning_beat + router_choice (NULL for a fresh user)."""
    response = await api_client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "learning_beat" in data
    assert "router_choice" in data


@pytest.mark.asyncio
async def test_tutorial_reentry_roundtrip_via_me(api_client, auth_headers):
    """PATCH tutorial state then GET /me confirms persisted values."""
    patch_response = await api_client.patch(
        "/api/auth/me/setup-state",
        headers=auth_headers,
        json={"learning_beat": 5, "router_choice": "B"},
    )
    assert patch_response.status_code == 200

    me_response = await api_client.get("/api/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    data = me_response.json()
    assert data["learning_beat"] == 5
    assert data["router_choice"] == "B"


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
    assert patch_response.status_code == 200

    # Read back via /me
    me_response = await api_client.get("/api/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    data = me_response.json()
    assert data["setup_step_completed"] == 2
    assert data["setup_selected_tools"] == ["claude_code", "windsurf"]
    assert data["setup_complete"] is False
