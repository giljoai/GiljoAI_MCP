# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-9174 #34 — secret-bearing query params must not reach access logs.

Lifecycle links (password reset / account deletion / email change) arrive as
GET requests with the plaintext token in ``?token=...``; uvicorn's access log
writes the full request line to captured stdout (Railway log drain in SaaS,
``logs/giljo_mcp.log`` in CE). The redaction filter on the ``uvicorn.access``
logger rewrites the path arg so sensitive param VALUES never hit a sink,
while keeping the param name so the line stays debuggable.

Uvicorn passes the access tuple via ``record.args``:
``(client_addr, method, full_path, http_version, status_code)`` — these tests
emit records shaped exactly like that.
"""

import logging

import pytest

from giljo_mcp.logging import _SensitiveQueryAccessFilter, configure_logging


UVICORN_ACCESS_FORMAT = '%s - "%s %s HTTP/%s" %d'


def _access_record(path: str) -> logging.LogRecord:
    """Build a LogRecord shaped like uvicorn.access emits."""
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=UVICORN_ACCESS_FORMAT,
        args=("127.0.0.1:50000", "GET", path, "1.1", 200),
        exc_info=None,
    )


class TestSensitiveQueryAccessFilter:
    def test_reset_link_token_value_redacted(self):
        record = _access_record("/reset-password?token=plaintext-reset-secret")
        keep = _SensitiveQueryAccessFilter().filter(record)
        line = record.getMessage()
        assert keep is True, "redaction must never DROP the access line"
        assert "plaintext-reset-secret" not in line
        assert '"GET /reset-password?token=[REDACTED] HTTP/1.1" 200' in line

    def test_oauth_callback_code_and_state_redacted(self):
        record = _access_record("/api/auth/social/callback?code=oauth-code-secret&state=csrf-state-val")
        _SensitiveQueryAccessFilter().filter(record)
        line = record.getMessage()
        assert "oauth-code-secret" not in line
        assert "csrf-state-val" not in line
        assert "code=[REDACTED]&state=[REDACTED]" in line

    def test_sensitive_param_mixed_with_benign_params(self):
        record = _access_record("/confirm?email=a@b.example&token=tok-secret&page=2")
        _SensitiveQueryAccessFilter().filter(record)
        line = record.getMessage()
        assert "tok-secret" not in line
        assert "email=a@b.example" in line
        assert "page=2" in line

    def test_param_name_match_is_exact_not_substring(self):
        """``access_token_hint`` or ``statement`` must NOT be redacted — the
        match is on the exact param name, case-insensitive."""
        record = _access_record("/search?statement=select&csrftoken_like=keepme")
        _SensitiveQueryAccessFilter().filter(record)
        line = record.getMessage()
        assert "statement=select" in line
        assert "csrftoken_like=keepme" in line

    def test_benign_query_untouched(self):
        record = _access_record("/api/projects?page=2&sort=name")
        keep = _SensitiveQueryAccessFilter().filter(record)
        assert keep is True
        assert "/api/projects?page=2&sort=name" in record.getMessage()

    def test_path_without_query_untouched(self):
        record = _access_record("/api/health")
        keep = _SensitiveQueryAccessFilter().filter(record)
        assert keep is True
        assert '"GET /api/health HTTP/1.1" 200' in record.getMessage()

    def test_non_access_shaped_record_passes_through(self):
        """A record without the uvicorn access args tuple must pass unharmed."""
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg="plain message, no args",
            args=None,
            exc_info=None,
        )
        assert _SensitiveQueryAccessFilter().filter(record) is True
        assert record.getMessage() == "plain message, no args"


class TestFilterRegisteredOnUvicornAccess:
    def test_configure_logging_attaches_redaction_filter(self):
        """The filter must be live on the ``uvicorn.access`` logger after
        ``configure_logging()`` (auto-runs on package import), so both the CE
        ``uvicorn.run`` path and the SaaS ``uvicorn api.app:app`` path get it
        without any deploy-config change."""
        configure_logging()  # no-op if already configured on import
        access_logger = logging.getLogger("uvicorn.access")
        assert any(isinstance(f, _SensitiveQueryAccessFilter) for f in access_logger.filters)

    @pytest.mark.asyncio
    async def test_end_to_end_reset_request_line_has_no_token_value(self, caplog):
        """WO verify clause: a reset request produces no token value in the
        emitted access-log line."""
        configure_logging()
        logger = logging.getLogger("uvicorn.access")
        with caplog.at_level(logging.INFO, logger="uvicorn.access"):
            logger.info(
                UVICORN_ACCESS_FORMAT,
                "198.51.100.9:44100",
                "GET",
                "/reset-password?token=live-plaintext-token",
                "1.1",
                200,
            )
        assert "live-plaintext-token" not in caplog.text
        assert "token=[REDACTED]" in caplog.text
