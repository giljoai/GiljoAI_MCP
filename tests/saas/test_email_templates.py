# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.

"""Tests for email template registry and content validation (SAAS-003).

Validates that all 5 templates:
- Are registered in the template registry
- Have correct placeholder fields
- Render valid HTML structure
- Contain expected dynamic parts in subjects
"""

from __future__ import annotations

import pytest

from giljo_mcp.saas.email.templates import (
    EMAIL_VERIFICATION,
    PASSWORD_RESET,
    REGISTRATION_WELCOME,
    TRIAL_EXPIRED,
    TRIAL_EXPIRY_WARNING,
    EmailTemplate,
    get_template,
)


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

ALL_TEMPLATE_NAMES = [
    "registration_welcome",
    "email_verification",
    "password_reset",
    "trial_expiry_warning",
    "trial_expired",
]


@pytest.mark.parametrize("template_name", ALL_TEMPLATE_NAMES)
def test_template_is_registered(template_name: str) -> None:
    """Every defined template should be accessible via get_template()."""
    template = get_template(template_name)
    assert isinstance(template, EmailTemplate)
    assert template.name == template_name


def test_registry_contains_exactly_five_templates() -> None:
    """Registry should have exactly 5 templates -- no more, no less."""
    count = 0
    for name in ALL_TEMPLATE_NAMES:
        get_template(name)
        count += 1
    assert count == 5


# ---------------------------------------------------------------------------
# Placeholder validation -- each template renders without KeyError
# ---------------------------------------------------------------------------


TEMPLATE_CONTEXTS = {
    "registration_welcome": {
        "user_name": "Patrik",
        "user_email": "patrik@giljo.ai",
        "generated_password": "s3cr3t",
        "login_url": "https://app.giljo.ai/login",
    },
    "email_verification": {
        "user_name": "Patrik",
        "verification_url": "https://app.giljo.ai/verify/abc123",
    },
    "password_reset": {
        "user_name": "Patrik",
        "reset_url": "https://app.giljo.ai/reset/xyz789",
    },
    "trial_expiry_warning": {
        "user_name": "Patrik",
        "days_remaining": "7",
        "upgrade_url": "https://app.giljo.ai/upgrade",
    },
    "trial_expired": {
        "user_name": "Patrik",
        "upgrade_url": "https://app.giljo.ai/upgrade",
    },
}


@pytest.mark.parametrize("template_name", ALL_TEMPLATE_NAMES)
def test_template_renders_without_missing_placeholders(template_name: str) -> None:
    """Rendering subject and body with expected context should not raise KeyError."""
    template = get_template(template_name)
    context = TEMPLATE_CONTEXTS[template_name]

    subject = template.subject.format(**context)
    html_body = template.html_body.format(**context)

    assert len(subject) > 0
    assert len(html_body) > 0


@pytest.mark.parametrize("template_name", ALL_TEMPLATE_NAMES)
def test_template_body_contains_user_name_after_rendering(template_name: str) -> None:
    """Every template body should include the user_name after rendering."""
    template = get_template(template_name)
    context = TEMPLATE_CONTEXTS[template_name]
    html_body = template.html_body.format(**context)

    assert "Patrik" in html_body


# ---------------------------------------------------------------------------
# HTML structure validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template_name", ALL_TEMPLATE_NAMES)
def test_template_html_has_doctype_and_closing_tags(template_name: str) -> None:
    """Templates should produce well-structured HTML with opening/closing tags."""
    template = get_template(template_name)
    context = TEMPLATE_CONTEXTS[template_name]
    html = template.html_body.format(**context)

    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    assert "</body>" in html
    assert "<head>" in html


@pytest.mark.parametrize("template_name", ALL_TEMPLATE_NAMES)
def test_template_includes_giljoai_branding(template_name: str) -> None:
    """Every template should include GiljoAI branding in the wrapper."""
    template = get_template(template_name)
    assert "GiljoAI" in template.html_body


# ---------------------------------------------------------------------------
# Subject line tests
# ---------------------------------------------------------------------------


def test_registration_welcome_subject_is_static() -> None:
    """Registration welcome has a fixed subject."""
    assert REGISTRATION_WELCOME.subject == "Welcome to GiljoAI"


def test_email_verification_subject_is_static() -> None:
    """Email verification has a fixed subject."""
    assert EMAIL_VERIFICATION.subject == "Verify your email"


def test_password_reset_subject_is_static() -> None:
    """Password reset has a fixed subject."""
    assert PASSWORD_RESET.subject == "Reset your password"


def test_trial_expiry_warning_subject_contains_days_placeholder() -> None:
    """Trial expiry warning subject should include {days_remaining}."""
    rendered = TRIAL_EXPIRY_WARNING.subject.format(days_remaining="3")
    assert "3 days" in rendered


def test_trial_expired_subject_is_static() -> None:
    """Trial expired has a fixed subject."""
    assert TRIAL_EXPIRED.subject == "Your GiljoAI trial has expired"


# ---------------------------------------------------------------------------
# EmailTemplate dataclass tests
# ---------------------------------------------------------------------------


def test_email_template_is_frozen() -> None:
    """EmailTemplate instances should be immutable (frozen dataclass)."""
    with pytest.raises(AttributeError):
        REGISTRATION_WELCOME.name = "changed"
