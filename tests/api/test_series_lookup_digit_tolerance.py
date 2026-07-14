# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression: serial-lookup endpoints tolerate grandfathered 5-digit serials.

The prod minting bug (soft-deleted ``9999`` inflating ``max+1`` to ``10000``)
left projects with 5-digit ``series_number``. The availability-check endpoints
``GET /api/v1/projects/check-series`` and ``/used-subseries`` validated
``series_number`` with ``Query(le=9999)``, so every lookup on such a project
returned **422**, spamming the frontend console.

These are read-only availability checks, not assignment, so the bound is widened
to 6 digits (decision D: lookups tolerate grandfathered outliers). This test
pins the boundary layer where the 422 actually surfaced.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["check-series", "used-subseries"])
async def test_five_digit_serial_lookup_is_not_422(api_client: AsyncClient, auth_headers: dict, path: str) -> None:
    """A 5-digit ``series_number`` must NOT be rejected with 422."""
    resp = await api_client.get(
        f"/api/v1/projects/{path}",
        params={"series_number": 10000},
        headers=auth_headers,
    )
    # The lookup may return 200 (no such serial → available / empty) but it must
    # never 422 on a number that can legitimately exist in the data.
    assert resp.status_code != 422, resp.text
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["check-series", "used-subseries"])
async def test_six_digit_upper_bound_still_enforced(api_client: AsyncClient, auth_headers: dict, path: str) -> None:
    """The widened bound still rejects genuinely out-of-range input (> 999999)."""
    resp = await api_client.get(
        f"/api/v1/projects/{path}",
        params={"series_number": 1000000},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["check-series", "used-subseries"])
async def test_zero_lower_bound_still_enforced(api_client: AsyncClient, auth_headers: dict, path: str) -> None:
    """``series_number`` must still be >= 1."""
    resp = await api_client.get(
        f"/api/v1/projects/{path}",
        params={"series_number": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text
