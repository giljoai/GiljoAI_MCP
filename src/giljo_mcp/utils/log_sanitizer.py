# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Log sanitization utility to prevent log injection attacks (CWE-117).

Strips newlines and control characters from values before they are
interpolated into log messages. Also provides token masking to prevent
credential exposure in log output.
"""

import re


_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize(value: str) -> str:
    """Remove control characters (newlines, tabs, etc.) from a log value."""
    text = value if isinstance(value, str) else str(value)
    # CodeQL models only literal str.replace() chains as CWE-117 barriers
    # (not re.sub), so newlines are stripped explicitly before the regex
    # pass. Every return path must flow through this chain -- do not
    # re-add a str(value) early-return above it.
    text = text.replace("\r\n", "").replace("\r", "").replace("\n", "")
    return _CONTROL_CHARS.sub("", text)


def mask_token(token: str) -> str:
    """Mask a token/secret for safe log output, showing only the first 8 chars.

    Returns the first 8 characters followed by '...' so the token can be
    correlated in logs without exposing the full credential. The masked
    form is passed through sanitize() before returning: tokens are
    user-supplied (URL path segments), and both the short-token
    passthrough and the raw slice would otherwise carry newlines and
    control characters straight into the log line (CWE-117). Masking
    happens on the RAW token first so at most 8 raw characters are ever
    exposed; sanitizing first would let control chars widen the window.

    Args:
        token: The token string to mask.

    Returns:
        Masked, control-char-free string, e.g. 'a1b2c3d4...', or the
        sanitized original if <= 8 chars.
    """
    if not isinstance(token, str):
        token = str(token)
    if len(token) > 8:
        token = token[:8] + "..."
    return sanitize(token)
