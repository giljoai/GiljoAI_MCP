# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.

"""SEC-6098: charset/length validation of repo_owner/repo_name in _fetch_github_commits.

The function interpolates repo_owner/repo_name into the GitHub API URL path. Without
validation a malformed/injection-ish config value (path traversal, query/host
injection) could reach the request. These tests exercise the function boundary --
the exact layer the bug lived -- proving each invalid class is REJECTED with a
422-style ValueError (not a swallowed None, not a downstream 500) while the valid
happy path still fetches and parses commits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from giljo_mcp.tools._memory_helpers import _fetch_github_commits, _validate_github_segment


CREATED = datetime(2026, 1, 1, tzinfo=UTC)
COMPLETED = datetime(2026, 1, 2, tzinfo=UTC)

# Each value is a distinct invalid class the basic charset must reject.
INVALID_SEGMENTS = [
    "owner/repo",  # path separator -> extra URL path segments
    "..",  # path traversal token
    ".",  # single-dot collapses a URL path segment
    "...",  # all-dots
    "a..b",  # embedded traversal
    "repo?ref=x",  # query injection
    "repo#frag",  # fragment injection
    "user@host",  # userinfo/host injection
    "repo name",  # whitespace
    "repo%2e",  # percent-encoding
    "a" * 101,  # exceeds length cap
    "café",  # non-ASCII
]

VALID_SEGMENTS = ["octocat", "GiljoAI", "my-repo", "my_repo", "repo.js", "v1.0.0-rc1", "a" * 100]


@pytest.mark.parametrize("bad", INVALID_SEGMENTS)
def test_validate_github_segment_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        _validate_github_segment(bad, "repo_name")


@pytest.mark.parametrize("good", VALID_SEGMENTS)
def test_validate_github_segment_accepts_valid(good: str) -> None:
    # Should not raise.
    _validate_github_segment(good, "repo_name")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", INVALID_SEGMENTS)
async def test_fetch_rejects_invalid_owner(bad: str) -> None:
    """Invalid repo_owner is rejected at the boundary, not swallowed into None."""
    with pytest.raises(ValueError):
        await _fetch_github_commits("valid-repo", bad, None, CREATED, COMPLETED)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", INVALID_SEGMENTS)
async def test_fetch_rejects_invalid_repo(bad: str) -> None:
    """Invalid repo_name is rejected at the boundary, not swallowed into None."""
    with pytest.raises(ValueError):
        await _fetch_github_commits(bad, "valid-owner", None, CREATED, COMPLETED)


@pytest.mark.asyncio
async def test_fetch_returns_none_when_not_configured() -> None:
    """Missing repo details remain a graceful skip (None), distinct from invalid input."""
    assert await _fetch_github_commits(None, "owner", None, CREATED, COMPLETED) is None
    assert await _fetch_github_commits("repo", None, None, CREATED, COMPLETED) is None


@pytest.mark.asyncio
async def test_fetch_valid_input_still_fetches_commits() -> None:
    """Load-bearing happy path: a valid owner/repo passes validation and parses commits."""
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = [
        {
            "sha": "abc123",
            "commit": {"message": "init", "author": {"name": "Dev", "date": "2026-01-01"}},
            "html_url": "https://x/c",
        }
    ]
    fake_client = MagicMock()
    fake_client.get = AsyncMock(return_value=fake_resp)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=fake_client):
        commits = await _fetch_github_commits("repo.js", "octocat", "tok", CREATED, COMPLETED)

    assert commits is not None
    assert len(commits) == 1
    assert commits[0]["sha"] == "abc123"
    # The URL must contain exactly the validated owner/repo, nothing injected.
    called_url = fake_client.get.call_args[0][0]
    assert called_url == "https://api.github.com/repos/octocat/repo.js/commits"
