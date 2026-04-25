# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Smoke tests for ``giljo_mcp.services.memory_entry_write_validator``.

The exhaustive acceptance suite for INF-WriteShape lives in
``tests/unit/test_inf_writeshape_memory_caps.py``. This file exists so
the CI guardrail (Guardrail 2: new service = new test) sees a test file
matching the service module name; it doubles as a sanity check that the
public surface (``validate_memory_entry_write``,
``MemoryEntryWriteSchema``, ``MemoryEntryWriteValidationError``) imports
cleanly and short-circuits the obvious cases.
"""

from __future__ import annotations

import pytest

from giljo_mcp.services.memory_entry_write_validator import (
    MEMORY_SUMMARY_MAX,
    MemoryEntryWriteSchema,
    MemoryEntryWriteValidationError,
    validate_memory_entry_write,
)


def test_public_surface_importable():
    assert MEMORY_SUMMARY_MAX == 500
    assert issubclass(MemoryEntryWriteSchema, object)
    assert issubclass(MemoryEntryWriteValidationError, Exception)


def test_validator_accepts_minimal_valid_payload():
    schema = validate_memory_entry_write(
        {
            "summary": "Headline summary.",
            "key_outcomes": ["A"],
            "decisions_made": ["D"],
            "deliverables": [],
            "tags": ["bug-fix"],
        }
    )
    assert schema.summary == "Headline summary."


def test_validator_rejects_oversize_summary_with_structured_error():
    with pytest.raises(MemoryEntryWriteValidationError) as exc_info:
        validate_memory_entry_write(
            {
                "summary": "x" * 600,
                "key_outcomes": [],
                "decisions_made": [],
                "deliverables": [],
                "tags": [],
            }
        )
    err = exc_info.value
    assert err.error == "validation_failed"
    assert err.field == "summary"
    assert err.actual_size == 600
    assert err.max_size == 500


def test_validator_rejects_unknown_tag():
    with pytest.raises(MemoryEntryWriteValidationError) as exc_info:
        validate_memory_entry_write(
            {
                "summary": "ok",
                "key_outcomes": [],
                "decisions_made": [],
                "deliverables": [],
                "tags": ["NOT a slug!"],
            }
        )
    assert exc_info.value.field == "tags"
