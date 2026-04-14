# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.

"""Tests for EmailService and get_email_service() factory (SAAS-003)."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from giljo_mcp.saas.email.base import EmailProvider, EmailSendError
from giljo_mcp.saas.email.service import EmailService, get_email_service
from giljo_mcp.saas.email.templates import get_template


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeProvider(EmailProvider):
    """Minimal concrete provider for testing EmailService."""

    def __init__(self) -> None:
        self.send_calls: list[tuple[str, str, str]] = []

    async def send(self, to_email: str, subject: str, html_content: str) -> bool:
        self.send_calls.append((to_email, subject, html_content))
        return True

    async def send_template(self, to_email: str, template_name: str, context: dict) -> bool:
        raise NotImplementedError("Delegate via EmailService, not provider")


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def service(fake_provider: FakeProvider) -> EmailService:
    return EmailService(provider=fake_provider)


# ---------------------------------------------------------------------------
# EmailService.send_template tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_template_calls_provider_with_rendered_content(
    service: EmailService,
    fake_provider: FakeProvider,
) -> None:
    """send_template() should render the template and delegate to provider.send()."""
    context = {
        "user_name": "Patrik",
        "user_email": "patrik@giljo.ai",
        "generated_password": "s3cr3t",
        "login_url": "https://app.giljo.ai/login",
    }
    result = await service.send_template("patrik@giljo.ai", "registration_welcome", context)

    assert result is True
    assert len(fake_provider.send_calls) == 1
    to_email, subject, html_body = fake_provider.send_calls[0]
    assert to_email == "patrik@giljo.ai"
    assert subject == "Welcome to GiljoAI"
    assert "Patrik" in html_body
    assert "patrik@giljo.ai" in html_body
    assert "s3cr3t" in html_body
    assert "https://app.giljo.ai/login" in html_body


@pytest.mark.asyncio
async def test_send_template_raises_for_unknown_template(service: EmailService) -> None:
    """send_template() should raise EmailSendError for nonexistent templates."""
    with pytest.raises(EmailSendError, match="Unknown email template 'nonexistent'"):
        await service.send_template("user@example.com", "nonexistent", {})


@pytest.mark.asyncio
async def test_send_template_propagates_provider_error(service: EmailService) -> None:
    """send_template() should propagate provider failures as-is."""
    service._provider.send = AsyncMock(side_effect=EmailSendError("Network timeout"))

    with pytest.raises(EmailSendError, match="Network timeout"):
        await service.send_template(
            "user@example.com",
            "registration_welcome",
            {
                "user_name": "Test",
                "user_email": "test@example.com",
                "generated_password": "pw",
                "login_url": "https://example.com",
            },
        )


# ---------------------------------------------------------------------------
# EmailService.send_raw tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_raw_delegates_to_provider(
    service: EmailService,
    fake_provider: FakeProvider,
) -> None:
    """send_raw() should pass args directly to provider.send()."""
    result = await service.send_raw("user@example.com", "Test Subject", "<p>Hello</p>")

    assert result is True
    assert len(fake_provider.send_calls) == 1
    assert fake_provider.send_calls[0] == ("user@example.com", "Test Subject", "<p>Hello</p>")


# ---------------------------------------------------------------------------
# get_template() tests
# ---------------------------------------------------------------------------


def test_get_template_returns_correct_template() -> None:
    """get_template() should return the matching EmailTemplate by name."""
    template = get_template("registration_welcome")
    assert template.name == "registration_welcome"
    assert "Welcome" in template.subject


def test_get_template_raises_key_error_for_unknown_name() -> None:
    """get_template() should raise KeyError for unregistered names."""
    with pytest.raises(KeyError, match="Unknown email template 'does_not_exist'"):
        get_template("does_not_exist")


# ---------------------------------------------------------------------------
# get_email_service() factory tests
# ---------------------------------------------------------------------------


def _make_sendgrid_mocks() -> dict[str, ModuleType]:
    """Create mock modules for the sendgrid package."""
    mock_sendgrid = ModuleType("sendgrid")
    mock_helpers = ModuleType("sendgrid.helpers")
    mock_mail = ModuleType("sendgrid.helpers.mail")

    mock_sendgrid.SendGridAPIClient = MagicMock(name="SendGridAPIClient")
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


@patch.dict("os.environ", {"GILJO_MODE": "saas", "SENDGRID_API_KEY": "SG.test"})
def test_get_email_service_returns_service_in_saas_mode() -> None:
    """Factory returns an EmailService when GILJO_MODE=saas."""
    sg_mocks = _make_sendgrid_mocks()
    # Force reimport of sendgrid_provider so it picks up our mocked SDK
    sys.modules.pop("giljo_mcp.saas.email.sendgrid_provider", None)
    with patch.dict(sys.modules, sg_mocks):
        svc = get_email_service()
    assert isinstance(svc, EmailService)


@patch.dict("os.environ", {"GILJO_MODE": "demo", "SENDGRID_API_KEY": "SG.test"})
def test_get_email_service_returns_service_in_demo_mode() -> None:
    """Factory returns an EmailService when GILJO_MODE=demo."""
    sg_mocks = _make_sendgrid_mocks()
    sys.modules.pop("giljo_mcp.saas.email.sendgrid_provider", None)
    with patch.dict(sys.modules, sg_mocks):
        svc = get_email_service()
    assert isinstance(svc, EmailService)


@patch.dict("os.environ", {"GILJO_MODE": ""}, clear=False)
def test_get_email_service_raises_in_ce_mode_empty_string() -> None:
    """Factory raises RuntimeError when GILJO_MODE is empty (CE default)."""
    with pytest.raises(RuntimeError, match="only available in SaaS or Demo mode"):
        get_email_service()


@patch.dict("os.environ", {}, clear=True)
def test_get_email_service_raises_when_giljo_mode_unset() -> None:
    """Factory raises RuntimeError when GILJO_MODE is not set at all."""
    with pytest.raises(RuntimeError, match="only available in SaaS or Demo mode"):
        get_email_service()


@patch.dict("os.environ", {"GILJO_MODE": "ce"})
def test_get_email_service_raises_for_explicit_ce_mode() -> None:
    """Factory raises RuntimeError when GILJO_MODE is explicitly 'ce'."""
    with pytest.raises(RuntimeError, match="only available in SaaS or Demo mode"):
        get_email_service()
