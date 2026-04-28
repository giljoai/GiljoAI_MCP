# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""HO 1028 coverage gap fills for the skills-version drift endpoint.

The existing suite covers the regex-rejection path with a clearly invalid
string ("not-a-version") but not the EMPTY string. The Pydantic regex
``^\\d+(\\.\\d+)*$`` requires at least one digit, so an empty value MUST
still be rejected with 422 — the endpoint must not treat ``""`` as
"version not provided" and silently fall through to the null-installed
branch.
"""

import pytest


ENDPOINT = "/api/notifications/check-skills-version"


@pytest.mark.asyncio
async def test_rejects_empty_string_input(api_client, auth_headers):
    """Empty installed_skills_version -> 422, not silent null fallthrough."""
    resp = await api_client.get(
        ENDPOINT + "?installed_skills_version=",
        headers=auth_headers,
    )
    assert resp.status_code == 422
