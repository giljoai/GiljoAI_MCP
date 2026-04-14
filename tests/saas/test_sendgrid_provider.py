# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.

"""Tests for SendGridProvider (SAAS-003).

The sendgrid SDK may not be installed in all environments (it is a SaaS-only
dependency). All tests mock the SDK at the module level so they run without
the real package.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from giljo_mcp.saas.email.base import EmailSendError


# ---------------------------------------------------------------------------
# Helpers -- mock the sendgrid SDK so the provider module can be imported
# ---------------------------------------------------------------------------


def _make_sendgrid_mocks() -> dict[str, ModuleType]:
    """Create mock modules for the sendgrid package."""
    mock_sendgrid = ModuleType("sendgrid")
    mock_helpers = ModuleType("sendgrid.helpers")
    mock_mail = ModuleType("sendgrid.helpers.mail")

    mock_client_cls = MagicMock(name="SendGridAPIClient")
    mock_sendgrid.SendGridAPIClient = mock_client_cls

    mock_mail.Content = MagicMock(name="Content")
    mock_mail.Email = MagicMock(name="Email")
    mock_mail.Mail = MagicMock(name="Mail")
    mock_mail.To = MagicMock(name="To")

    mock_sendgrid.helpers = mock_helpers
    mock_helpers.mail = mock_mail

    return {
        "sendgrid": mock_sendgrid,
        "sendgrid.helpers": mock_helpers,
        "sendgrid.helpers.mail": mock_mail,
    }


def _import_provider(sg_mocks: dict[str, ModuleType]):
    """Import (or reimport) SendGridProvider with mocked sendgrid SDK."""
    mod_name = "giljo_mcp.saas.email.sendgrid_provider"
    # Remove cached module so it re-imports with our mocks
    sys.modules.pop(mod_name, None)
    with patch.dict(sys.modules, sg_mocks):
        mod = importlib.import_module(mod_name)
    return mod.SendGridProvider, sg_mocks["sendgrid"].SendGridAPIClient


# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------


@patch.dict("os.environ", {"SENDGRID_API_KEY": "SG.test-key-123"})
def test_sendgrid_provider_initializes_with_api_key() -> None:
    """Provider reads SENDGRID_API_KEY and creates a client."""
    sg_mocks = _make_sendgrid_mocks()
    provider_cls, _ = _import_provider(sg_mocks)

    provider = provider_cls()
    assert provider._from_email == "noreply@giljo.ai"


@patch.dict("os.environ", {"SENDGRID_API_KEY": "SG.key", "SENDGRID_FROM_EMAIL": "custom@giljo.ai"})
def test_sendgrid_provider_reads_custom_from_email() -> None:
    """Provider uses SENDGRID_FROM_EMAIL when set."""
    sg_mocks = _make_sendgrid_mocks()
    provider_cls, _ = _import_provider(sg_mocks)

    provider = provider_cls()
    assert provider._from_email == "custom@giljo.ai"


@patch.dict("os.environ", {}, clear=True)
def test_sendgrid_provider_raises_without_api_key() -> None:
    """Provider raises EmailSendError if SENDGRID_API_KEY is missing."""
    sg_mocks = _make_sendgrid_mocks()
    provider_cls, _ = _import_provider(sg_mocks)

    with pytest.raises(EmailSendError, match="SENDGRID_API_KEY environment variable is not set"):
        provider_cls()


# ---------------------------------------------------------------------------
# send() tests
# ---------------------------------------------------------------------------


@patch.dict("os.environ", {"SENDGRID_API_KEY": "SG.test-key"})
@pytest.mark.asyncio
async def test_send_constructs_correct_mail_and_succeeds() -> None:
    """send() should build a Mail object and return True on 202 response."""
    sg_mocks = _make_sendgrid_mocks()
    provider_cls, _ = _import_provider(sg_mocks)

    provider = provider_cls()

    mock_response = MagicMock()
    mock_response.status_code = 202
    provider._client.send = MagicMock(return_value=mock_response)

    result = await provider.send("user@example.com", "Test Subject", "<p>Hello</p>")

    assert result is True
    provider._client.send.assert_called_once()


@patch.dict("os.environ", {"SENDGRID_API_KEY": "SG.test-key"})
@pytest.mark.asyncio
async def test_send_raises_on_api_exception() -> None:
    """send() should wrap SDK exceptions in EmailSendError."""
    sg_mocks = _make_sendgrid_mocks()
    provider_cls, _ = _import_provider(sg_mocks)

    provider = provider_cls()
    provider._client.send = MagicMock(side_effect=Exception("Connection refused"))

    with pytest.raises(EmailSendError, match="SendGrid API error: Connection refused"):
        await provider.send("user@example.com", "Subject", "<p>Body</p>")


@patch.dict("os.environ", {"SENDGRID_API_KEY": "SG.test-key"})
@pytest.mark.asyncio
async def test_send_raises_on_non_2xx_status() -> None:
    """send() should raise EmailSendError for non-2xx responses."""
    sg_mocks = _make_sendgrid_mocks()
    provider_cls, _ = _import_provider(sg_mocks)

    provider = provider_cls()

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.body = b"Forbidden"
    provider._client.send = MagicMock(return_value=mock_response)

    with pytest.raises(EmailSendError, match="SendGrid returned status 403"):
        await provider.send("user@example.com", "Subject", "<p>Body</p>")


# ---------------------------------------------------------------------------
# send_template() tests
# ---------------------------------------------------------------------------


@patch.dict("os.environ", {"SENDGRID_API_KEY": "SG.test-key"})
@pytest.mark.asyncio
async def test_send_template_renders_and_delegates() -> None:
    """send_template() should render template then call send()."""
    sg_mocks = _make_sendgrid_mocks()
    provider_cls, _ = _import_provider(sg_mocks)

    provider = provider_cls()

    mock_response = MagicMock()
    mock_response.status_code = 202
    provider._client.send = MagicMock(return_value=mock_response)

    result = await provider.send_template(
        "user@example.com",
        "email_verification",
        {"user_name": "Test", "verification_url": "https://giljo.ai/verify/abc"},
    )

    assert result is True
    provider._client.send.assert_called_once()


@patch.dict("os.environ", {"SENDGRID_API_KEY": "SG.test-key"})
@pytest.mark.asyncio
async def test_send_template_raises_for_unknown_template() -> None:
    """send_template() should raise EmailSendError for unknown templates."""
    sg_mocks = _make_sendgrid_mocks()
    provider_cls, _ = _import_provider(sg_mocks)

    provider = provider_cls()

    with pytest.raises(EmailSendError, match="Unknown email template"):
        await provider.send_template("user@example.com", "bogus_template", {})
