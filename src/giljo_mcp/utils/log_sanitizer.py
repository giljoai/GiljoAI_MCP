# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Log sanitization utility to prevent log injection attacks (CWE-117).

Strips newlines and control characters from values before they are
interpolated into log messages. Also provides token masking to prevent
credential exposure in log output.
"""

import re


_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize(value: str) -> str:
    """Remove control characters (newlines, tabs, etc.) from a log value."""
    if not isinstance(value, str):
        return str(value)
    return _CONTROL_CHARS.sub("", value)


def mask_token(token: str) -> str:
    """Mask a token/secret for safe log output, showing only the first 8 chars.

    Returns the first 8 characters followed by '...' so the token can be
    correlated in logs without exposing the full credential.

    Args:
        token: The token string to mask.

    Returns:
        Masked string, e.g. 'a1b2c3d4...' or the original if <= 8 chars.
    """
    if not isinstance(token, str):
        return str(token)
    if len(token) <= 8:
        return token
    return token[:8] + "..."
