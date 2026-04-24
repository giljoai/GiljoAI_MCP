# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
Upload guard helpers (SEC-0001 Phase 2).

Two pure helpers used by both vision-document upload endpoints:

- ``sanitize_upload_filename(raw)`` -- strict filename sanitizer that rejects
  path traversal, absolute paths, null bytes, control chars, Unicode bidi /
  RTL overrides, leading dots, Windows-reserved chars and device names, and
  anything whose UTF-8 byte length exceeds 255 bytes after NFC normalization.
- ``enforce_text_content(content)`` / ``is_text_content(content)`` --
  byte-sniff that rejects any payload containing binary C0 control bytes in
  the first ``SNIFF_BYTES`` bytes, then requires a strict UTF-8 decode of the
  whole payload.

Both helpers raise subclasses of ``ValueError`` on rejection so endpoints
can catch them and convert to structured 4xx responses with machine-readable
``error_code`` values.

Authoritative behavior spec is covered by ``tests/security/test_upload_guard.py``
and the analyzer handover ``handovers/SEC-0001_upload_analysis.md`` (sections
2 and 3).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Extension allowlist shared with both endpoints and frontend.
#: ``.markdown`` is retained for backward compatibility with existing uploaders
#: (analyzer §9.2 item 7).
TEXT_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md", ".markdown"})

#: Byte-sniff window size. 8 KB is enough to catch every common binary magic
#: header and cheap to scan.
SNIFF_BYTES: int = 8192

#: Maximum filename length in bytes after NFC normalization.
#: ext4 = 255 bytes; NTFS = 255 UTF-16 units; 255 bytes is safe on both.
MAX_FILENAME_BYTES: int = 255


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class UploadFilenameError(ValueError):
    """Raised when a filename cannot be made safe for disk storage."""


class UploadContentError(ValueError):
    """Raised when uploaded content fails the text byte-sniff."""


class UploadSizeError(ValueError):
    """Raised when an upload exceeds the configured size cap."""


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

# Unicode bidi / RTL override and embedding codepoints. These are a known
# spoof vector in filenames (e.g. "exploit<U+202E>cod.txt.exe" renders as
# "exploitexe.txt" in most viewers). Stored as \u escape sequences so ruff
# PLE2502 (control chars in source) stays happy.
_BIDI_CHARS: frozenset[str] = frozenset(
    {
        "\u202a",  # LEFT-TO-RIGHT EMBEDDING
        "\u202b",  # RIGHT-TO-LEFT EMBEDDING
        "\u202c",  # POP DIRECTIONAL FORMATTING
        "\u202d",  # LEFT-TO-RIGHT OVERRIDE
        "\u202e",  # RIGHT-TO-LEFT OVERRIDE
        "\u2066",  # LEFT-TO-RIGHT ISOLATE
        "\u2067",  # RIGHT-TO-LEFT ISOLATE
        "\u2068",  # FIRST STRONG ISOLATE
        "\u2069",  # POP DIRECTIONAL ISOLATE
        "\u200e",  # LEFT-TO-RIGHT MARK
        "\u200f",  # RIGHT-TO-LEFT MARK
        "\u061c",  # ARABIC LETTER MARK
    }
)

# Windows-reserved device names, matched case-insensitively against the stem.
_WINDOWS_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$", re.IGNORECASE)

# Windows absolute path: "C:\..." or "C:/..." (any drive letter).
_WIN_ABS_PATH = re.compile(r"^[A-Za-z]:[\\/]")

# Characters forbidden on Windows NTFS / SMB shares. Reject everywhere for
# cross-platform safety.
_FORBIDDEN_CHARS: frozenset[str] = frozenset('<>:"|?*')


def _has_control_char(value: str) -> bool:
    """Return True if ``value`` contains any ASCII C0 control char or DEL.

    The check uses explicit ordinal comparison so it works on arbitrary
    Unicode without pulling in the full ``unicodedata`` category of every
    codepoint.
    """
    for ch in value:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            return True
    return False


def sanitize_upload_filename(raw: str | None) -> str:
    """Return a filesystem-safe basename, or raise ``UploadFilenameError``.

    Behavior (analyzer handover §2):
    - Strips leading/trailing whitespace; NFC-normalizes.
    - Rejects empty/whitespace-only names.
    - Rejects path separators (``/``, ``\\``), NUL, ``..`` substrings.
    - Rejects absolute paths (POSIX ``/...`` and Windows ``C:\\...``).
    - Rejects ASCII control chars (``[0x00, 0x20)`` and ``0x7F``).
    - Rejects Unicode bidi / RTL / LTR override codepoints.
    - Rejects Windows-forbidden chars (``< > : " | ? *``).
    - Rejects leading dot (POSIX hidden file, ``.``, ``..``).
    - Rejects ``> 255`` UTF-8 bytes after normalization.
    - Rejects Windows-reserved device-name stems (CON, PRN, AUX, NUL,
      COM1-9, LPT1-9, case-insensitive).
    - Takes ``PurePosixPath(name).name`` as the final return to strip any
      residual directory parts (defense-in-depth; the separator check above
      would already have rejected them).
    """
    if raw is None or not raw or not raw.strip():
        raise UploadFilenameError("filename is empty")

    stripped = raw.strip()
    normalized = unicodedata.normalize("NFC", stripped)

    if _has_control_char(normalized):
        raise UploadFilenameError("filename contains control characters")

    if any(ch in _BIDI_CHARS for ch in normalized):
        raise UploadFilenameError("filename contains bidi/RTL override characters")

    if "/" in normalized or "\\" in normalized or "\x00" in normalized:
        raise UploadFilenameError("filename contains path separators")

    if ".." in normalized:
        raise UploadFilenameError("filename contains path traversal")

    if normalized.startswith("/") or _WIN_ABS_PATH.match(normalized):
        raise UploadFilenameError("filename is an absolute path")

    if any(ch in _FORBIDDEN_CHARS for ch in normalized):
        raise UploadFilenameError("filename contains forbidden characters")

    if normalized.startswith("."):
        raise UploadFilenameError("filename starts with a dot")

    if len(normalized.encode("utf-8")) > MAX_FILENAME_BYTES:
        raise UploadFilenameError("filename exceeds 255 bytes")

    stem = normalized.rsplit(".", 1)[0] if "." in normalized else normalized
    if _WINDOWS_RESERVED.match(stem):
        raise UploadFilenameError("filename uses a reserved device name")

    # Defense-in-depth: take basename of the sanitized name. Because the
    # separator check above rejected any path separators, this is an identity
    # operation on any accepted input -- but it guards against a future change
    # that might relax the separator rule.
    return PurePosixPath(normalized).name


# ---------------------------------------------------------------------------
# Byte-sniff / text-content enforcement
# ---------------------------------------------------------------------------

# Binary C0 bytes. Everything in [0x00, 0x20) is a control char; we tolerate
# only ``\t`` (0x09), ``\n`` (0x0A), and ``\r`` (0x0D) because those are the
# three whitespace controls legal in TXT/MD. We deliberately reject ``\v``
# (0x0B) and ``\f`` (0x0C) because they are rare in modern plaintext and
# their presence is a strong binary signal.
_BINARY_BYTES: frozenset[int] = frozenset(set(range(0x09)) | {0x0B, 0x0C} | set(range(0x0E, 0x20)))


def is_text_content(content: bytes, *, sniff_bytes: int = SNIFF_BYTES) -> bool:
    """Return True if ``content`` looks like plain UTF-8 text.

    Algorithm:
    1. Inspect up to the first ``sniff_bytes`` bytes. If any byte is in the
       ``_BINARY_BYTES`` set, return False.
    2. Attempt a strict UTF-8 decode of the WHOLE payload. If it fails,
       return False.

    Tolerated C0 bytes: ``\\t`` (0x09), ``\\n`` (0x0A), ``\\r`` (0x0D).
    Everything else in ``[0x00, 0x20)`` causes rejection, as does ``0xFF``
    / ``0xFE`` sequences typical of UTF-16 (because UTF-16 LE BOM ``0xFF
    0xFE`` starts with 0xFF which is never a valid UTF-8 lead byte).
    """
    window = content[:sniff_bytes]
    for byte in window:
        if byte in _BINARY_BYTES:
            return False

    try:
        content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return False

    return True


def enforce_text_content(content: bytes, *, sniff_bytes: int = SNIFF_BYTES) -> None:
    """Raise ``UploadContentError`` unless ``content`` passes ``is_text_content``.

    Used at the HTTP endpoint boundary to convert byte-sniff failures into
    structured 415 responses with ``error_code="UPLOAD_CONTENT_NOT_TEXT"``.
    """
    if not is_text_content(content, sniff_bytes=sniff_bytes):
        raise UploadContentError("uploaded content does not look like plain UTF-8 text")
