# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9150: lock the exception hierarchy after removing 7 dead base classes.

Finding BE #27 (SYNTHESIS_ROADMAP.md B-13): seven category/parent exceptions in
``exceptions.py`` were never raised, caught, imported, or referenced anywhere in
the repo (grep-confirmed) — they existed only as base classes for the live
subclasses below. They were deleted and every live child re-parented directly to
``BaseGiljoError``. That re-parent is behavior-preserving: each child keeps its
own ``default_status_code`` and nothing catches the removed parents by name, so
this test locks (a) every surviving exception's HTTP status mapping and
(b) that the removed names stay removed.
"""

from __future__ import annotations

import pytest

from giljo_mcp import exceptions
from giljo_mcp.exceptions import BaseGiljoError


# (class, expected default_status_code) — the observable contract that must not
# drift when the parents were removed.
_EXPECTED_STATUS = {
    "BaseGiljoError": 500,
    "ConfigValidationError": 500,
    "TemplateNotFoundError": 404,
    "OrchestrationError": 500,
    "ProjectStateError": 409,
    "ImplementationNotReadyError": 404,
    "DatabaseError": 500,
    "ValidationError": 400,
    "AuthenticationError": 401,
    "AuthorizationError": 403,
    "ResourceNotFoundError": 404,
    "AlreadyExistsError": 409,
    "RetryExhaustedError": 500,
    "ContextError": 500,
    "GiljoFileNotFoundError": 500,
}

# The 7 dead base classes removed by BE-9150 — must not reappear.
_REMOVED = (
    "ConfigurationError",
    "TemplateError",
    "QueueError",
    "MessageDeliveryError",
    "APIError",
    "ResourceError",
    "FileSystemError",
)


@pytest.mark.parametrize(("name", "expected"), sorted(_EXPECTED_STATUS.items()))
def test_default_status_code_preserved(name: str, expected: str) -> None:
    exc_cls = getattr(exceptions, name)
    assert issubclass(exc_cls, BaseGiljoError)
    assert exc_cls.default_status_code == expected


@pytest.mark.parametrize("name", _REMOVED)
def test_dead_base_class_stays_removed(name: str) -> None:
    assert not hasattr(exceptions, name), (
        f"{name} was removed by BE-9150 (dead base class, never raised/caught); "
        "re-parent new subclasses onto BaseGiljoError instead of reintroducing it."
    )
