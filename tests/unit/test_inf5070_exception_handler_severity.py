# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-5070: BaseGiljoError exception handler log-severity must follow the
HTTP status class so the Sentry LoggingIntegration's default event_level
(ERROR) does not auto-create Sentry issues for ordinary 4xx client errors.

Background: demo.giljo.ai was flooding Sentry's giljoai-backend project
with one issue per failed login because the global exception handler logged
ALL BaseGiljoError subclasses (including 401 AuthenticationError and 404
NotFoundError) at ERROR level. With public traffic + bot probes that would
burn the 5K/month free-tier quota in days. Fix: 4xx -> WARNING (visible in
journalctl, breadcrumb in Sentry, no issue); 5xx -> ERROR (real alerts).

These tests assert that the log call site picks the right severity for
each status-code class. They do NOT depend on Sentry being installed --
the LoggingIntegration coupling is tested via the before_send filter in
test_inf5063_sentry_init.py.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from api.exception_handlers import register_exception_handlers
from giljo_mcp.exceptions import BaseGiljoError


pytestmark = pytest.mark.informational


class _Boom4xx(BaseGiljoError):
    default_status_code = 401


class _BoomForbidden(BaseGiljoError):
    default_status_code = 403


class _BoomNotFound(BaseGiljoError):
    default_status_code = 404


class _BoomConflict(BaseGiljoError):
    default_status_code = 409


class _BoomUnprocessable(BaseGiljoError):
    default_status_code = 422


class _BoomRateLimit(BaseGiljoError):
    default_status_code = 429


class _Boom5xx(BaseGiljoError):
    default_status_code = 500


class _BoomBadGateway(BaseGiljoError):
    default_status_code = 502


class _BoomServiceUnavailable(BaseGiljoError):
    default_status_code = 503


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    return app


def _make_request() -> MagicMock:
    request = MagicMock()
    request.url.path = "/api/test"
    return request


def _get_handler(app: FastAPI):
    return app.exception_handlers[BaseGiljoError]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc_cls",
    [_Boom4xx, _BoomForbidden, _BoomNotFound, _BoomConflict, _BoomUnprocessable, _BoomRateLimit],
)
async def test_4xx_logged_at_warning(caplog, exc_cls):
    """Every 4xx domain error must log at WARNING -- below Sentry's default
    ERROR event_level. Anonymous probes, invalid credentials, missing
    records, validation failures are not server bugs."""
    app = _build_app()
    handler = _get_handler(app)
    exc = exc_cls("client did something wrong")

    with caplog.at_level(logging.DEBUG, logger="api.exception_handlers"):
        response = await handler(_make_request(), exc)

    # Status code in response unchanged
    assert response.status_code == exc.default_status_code
    # Exactly one log record from the handler
    records = [r for r in caplog.records if r.name == "api.exception_handlers"]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING, (
        f"4xx ({exc.default_status_code}) was logged at {records[0].levelname}, "
        f"expected WARNING -- this would re-flood Sentry"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_cls", [_Boom5xx, _BoomBadGateway, _BoomServiceUnavailable])
async def test_5xx_logged_at_error(caplog, exc_cls):
    """5xx must stay at ERROR -- those are real failures that warrant a
    Sentry issue + alert email."""
    app = _build_app()
    handler = _get_handler(app)
    exc = exc_cls("backend exploded")

    with caplog.at_level(logging.DEBUG, logger="api.exception_handlers"):
        response = await handler(_make_request(), exc)

    assert response.status_code == exc.default_status_code
    records = [r for r in caplog.records if r.name == "api.exception_handlers"]
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR, (
        f"5xx ({exc.default_status_code}) was logged at {records[0].levelname}, "
        f"expected ERROR -- this would suppress real alerts"
    )


@pytest.mark.asyncio
async def test_response_shape_preserved(caplog):
    """The severity change must not alter the JSON response body."""
    app = _build_app()
    handler = _get_handler(app)
    exc = _BoomNotFound("project xyz", context={"id": "xyz"})

    with caplog.at_level(logging.DEBUG, logger="api.exception_handlers"):
        response = await handler(_make_request(), exc)

    import json

    body = json.loads(bytes(response.body).decode())
    assert body["error_code"] == "_BOOMNOTFOUND"
    assert body["message"] == "project xyz"
    assert body["context"] == {"id": "xyz"}
    assert body["status_code"] == 404


@pytest.mark.asyncio
async def test_log_message_carries_error_code(caplog):
    """The log line still contains the error_code so journalctl operators
    can grep for specific failures even when severity is WARNING."""
    app = _build_app()
    handler = _get_handler(app)
    exc = _Boom4xx("invalid password", error_code="AUTHENTICATION_ERROR")

    with caplog.at_level(logging.DEBUG, logger="api.exception_handlers"):
        await handler(_make_request(), exc)

    records = [r for r in caplog.records if r.name == "api.exception_handlers"]
    assert "AUTHENTICATION_ERROR" in records[0].getMessage()
    assert "invalid password" in records[0].getMessage()
