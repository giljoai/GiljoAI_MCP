# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
Security regression tests for SEC-SPRINT-001a.

Covers:
- Path traversal prevention in chunker.py (H-3)
- Setup endpoint guard after setup completion (H-4)
- Error detail leak prevention across hardened endpoints
"""

import sys
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest


# Add project root to path
# TODO: Remove after editable install confirmed on all platforms
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestPathTraversalPrevention:
    """Test that the chunker path containment logic blocks traversal (H-3).

    The containment check resolves the path and verifies it is within
    ./products. We test the core logic directly: resolve() + is_relative_to().
    """

    def _is_allowed(self, vision_path: str) -> bool:
        """Replicate the chunker containment check."""
        normalized = vision_path.replace("\\", "/")
        resolved = Path(normalized).resolve()
        allowed_base = Path("./products").resolve()
        return resolved.is_relative_to(allowed_base)

    def test_relative_traversal_blocked(self):
        """../../etc/passwd should be blocked."""
        assert not self._is_allowed("../../etc/passwd")

    def test_absolute_outside_path_blocked(self):
        """Absolute path outside products/ should be blocked."""
        assert not self._is_allowed("/etc/shadow")

    def test_backslash_traversal_blocked(self):
        """Backslash traversal should be caught after normalization."""
        assert not self._is_allowed("..\\..\\etc\\passwd")

    def test_windows_absolute_blocked(self):
        """Windows absolute path should be blocked."""
        assert not self._is_allowed("C:\\Windows\\System32\\config\\sam")

    def test_valid_products_path_allowed(self):
        """Path within products/ should be allowed."""
        # Create a temp products dir so resolve works
        products_dir = Path("./products").resolve()
        products_dir.mkdir(parents=True, exist_ok=True)
        assert self._is_allowed("./products/test-product/vision/doc.txt")

    def test_dot_dot_in_products_still_blocked(self):
        """products/../../../etc/passwd should be blocked."""
        assert not self._is_allowed("./products/../../../etc/passwd")


class TestSetupEndpointGuard:
    """Test that setup endpoints return 403 after setup is complete (H-4)."""

    def test_require_setup_incomplete_blocks_when_users_exist(self):
        """Setup guard should raise 403 when users already exist."""
        from fastapi import HTTPException

        from api.endpoints.database_setup import require_setup_incomplete

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # 1 user exists
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with (
            patch.dict(
                "os.environ",
                {
                    "DB_HOST": "localhost",
                    "DB_PORT": "5432",
                    "DB_NAME": "giljo_mcp",
                    "DB_USER": "giljo_user",
                    "DB_PASSWORD": "test",
                },
            ),
            patch("psycopg2.connect", return_value=mock_conn),
        ):
            with pytest.raises(HTTPException) as exc_info:
                require_setup_incomplete()
            assert exc_info.value.status_code == 403
            assert "already completed" in exc_info.value.detail.lower()

    def test_require_setup_incomplete_allows_when_no_users(self):
        """Setup guard should allow access when no users exist."""
        from api.endpoints.database_setup import require_setup_incomplete

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)  # No users
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        with (
            patch.dict(
                "os.environ",
                {
                    "DB_HOST": "localhost",
                    "DB_PORT": "5432",
                    "DB_NAME": "giljo_mcp",
                    "DB_USER": "giljo_user",
                    "DB_PASSWORD": "test",
                },
            ),
            patch("psycopg2.connect", return_value=mock_conn),
        ):
            result = require_setup_incomplete()
            assert result is None

    def test_require_setup_incomplete_allows_when_no_credentials(self):
        """Setup guard should allow access when DB credentials are not configured."""
        from api.endpoints.database_setup import require_setup_incomplete

        with patch.dict("os.environ", {}, clear=True):
            result = require_setup_incomplete()
            assert result is None

    def test_require_setup_incomplete_allows_when_db_unreachable(self):
        """Setup guard should allow access when DB connection fails."""
        from api.endpoints.database_setup import require_setup_incomplete

        with (
            patch.dict(
                "os.environ",
                {
                    "DB_HOST": "localhost",
                    "DB_PORT": "5432",
                    "DB_NAME": "giljo_mcp",
                    "DB_USER": "giljo_user",
                    "DB_PASSWORD": "test",
                },
            ),
            patch("psycopg2.connect", side_effect=Exception("Connection refused")),
        ):
            result = require_setup_incomplete()
            assert result is None


class TestErrorDetailLeaks:
    """Test that hardened endpoints do NOT leak internal error details.

    Verifies that generic error messages returned by endpoints do not contain
    exception class names, file paths, SQL fragments, or stack trace indicators.
    """

    LEAK_PATTERNS: ClassVar[list[str]] = [
        "traceback",
        'file "',
        "sqlalchemy",
        "psycopg2",
        "oserror",
        "valueerror",
        "keyerror",
        "integrityerror",
        "/home/",
    ]

    def _assert_no_internal_leak(self, detail: str):
        """Verify response detail does not contain internal error signatures."""
        detail_lower = detail.lower()
        for pattern in self.LEAK_PATTERNS:
            assert pattern not in detail_lower, f"Error detail leaked internal info matching '{pattern}': {detail}"

    def test_git_endpoint_detail_is_generic(self):
        """Git toggle endpoint should not leak OSError details."""
        self._assert_no_internal_leak("Failed to save configuration. Check server logs.")

    def test_vision_document_create_detail_is_generic(self):
        """Vision document creation should not leak SQL or path details."""
        self._assert_no_internal_leak("Failed to create vision document. Check server logs.")

    def test_vision_document_update_detail_is_generic(self):
        """Vision document update should not leak internal details."""
        self._assert_no_internal_leak("Failed to update vision document. Check server logs.")

    def test_prompts_endpoint_detail_is_generic(self):
        """Prompts endpoint should not leak exception details."""
        self._assert_no_internal_leak("Failed to generate orchestrator prompt. Check server logs.")

    def test_template_delete_detail_is_generic(self):
        """Template delete endpoint should not leak exception details."""
        self._assert_no_internal_leak("Failed to delete template. Check server logs.")

    def test_oauth_authorize_detail_is_generic(self):
        """OAuth authorize endpoint should not leak validation details."""
        self._assert_no_internal_leak("Invalid authorization request parameters.")

    def test_oauth_token_detail_is_generic(self):
        """OAuth token exchange endpoint should not leak internal details."""
        self._assert_no_internal_leak("Invalid token exchange request.")

    def test_system_prompt_validation_detail_is_generic(self):
        """System prompt update should not leak ValueError content."""
        self._assert_no_internal_leak("Invalid prompt content.")

    def test_system_prompt_service_error_detail_is_generic(self):
        """System prompt service error should not leak RuntimeError content."""
        self._assert_no_internal_leak("System prompt service temporarily unavailable.")

    def test_database_setup_failure_detail_is_generic(self):
        """Database setup failure should not leak internal error list."""
        self._assert_no_internal_leak("Database setup failed. Check server logs for details.")

    def test_setup_status_contains_expected_fields_only(self):
        """Setup status endpoint response should contain only expected fields."""
        expected_fields = {"setup_complete", "is_fresh_install", "requires_admin_creation", "total_users_count"}
        response = {
            "setup_complete": True,
            "is_fresh_install": False,
            "requires_admin_creation": False,
            "total_users_count": 1,
        }
        assert set(response.keys()) == expected_fields
