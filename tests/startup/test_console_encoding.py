# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for TSK-9123: console glyphs renders as literal '?' on
legacy Windows console codepages (cp437/cp1252) that can't encode common
Unicode punctuation. startup_support/console.py._safe() must fall back to
ASCII-safe equivalents instead of letting the raw character reach print().
"""

from unittest.mock import MagicMock, patch

import pytest

from startup_support.console import _safe


@pytest.mark.parametrize(
    ("encoding", "text", "expected"),
    [
        # cp1252 can encode an em dash directly (byte 0x97) -- no fallback needed.
        ("cp1252", "SSL cert/key files not found — falling back to HTTP", None),
        # cp1252 cannot encode a check mark -- must fall back to ASCII.
        ("cp1252", "✓ all checks passed", "OK all checks passed"),
        # cp437 (legacy OEM console codepage) cannot encode an em dash either.
        (
            "cp437",
            "npm not found in PATH — skipping frontend rebuild",
            "npm not found in PATH - skipping frontend rebuild",
        ),
        # utf-8 (modern terminals) can encode everything -- text passes through unchanged.
        ("utf-8", "→ branch order — saas first ✓", None),
    ],
)
def test_safe_falls_back_on_unencodable_glyphs(encoding, text, expected):
    """_safe() must not let a glyph the console codepage can't render reach print()."""
    with patch("startup_support.console.sys.stdout", MagicMock(encoding=encoding)):
        result = _safe(text)

    if expected is None:
        assert result == text
    else:
        assert result == expected
    # Whatever comes back must actually be encodable on that codepage --
    # this is the property that prevents the '?' glyph regression.
    result.encode(encoding)


def test_safe_defaults_to_utf8_when_stdout_encoding_is_unset():
    """A stream with no .encoding attribute value must not crash _safe()."""
    with patch("startup_support.console.sys.stdout", MagicMock(encoding=None)):
        assert _safe("— fine on utf-8 —") == "— fine on utf-8 —"
