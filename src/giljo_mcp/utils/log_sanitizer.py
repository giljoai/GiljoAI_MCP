# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Log sanitization utility to prevent log injection attacks (CWE-117).

Strips newlines and control characters from values before they are
interpolated into log messages.
"""

import re


_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize(value: str) -> str:
    """Remove control characters (newlines, tabs, etc.) from a log value."""
    if not isinstance(value, str):
        return str(value)
    return _CONTROL_CHARS.sub("", value)
