# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Console output helpers for the startup entry point (BE-9060 split).

Extracted verbatim from startup.py. Imported by startup.py AFTER its
venv-relaunch guard has run, so the third-party colorama import here is safe
(never reached from a fresh shell before the relaunch).
"""

import sys

from colorama import Fore, Style


# TSK-9123: legacy Windows console codepages (cp437/cp1252) can't encode
# these common Unicode punctuation marks; printed raw they render as literal
# '?' glyphs. Swap in ASCII-safe equivalents when the console can't render them.
# Built via chr() (not literal glyphs) so ruff (RUF001) doesn't flag ambiguous
# unicode in source, and so `ruff format` can't silently re-introduce them.
_ASCII_FALLBACKS = {
    chr(0x2014): "-",  # em dash
    chr(0x2013): "-",  # en dash
    chr(0x2192): "->",  # rightwards arrow
    chr(0x2190): "<-",  # leftwards arrow
    chr(0x2018): "'",  # left single quote
    chr(0x2019): "'",  # right single quote
    chr(0x201C): '"',  # left double quote
    chr(0x201D): '"',  # right double quote
    chr(0x2026): "...",  # ellipsis
    chr(0x2713): "OK",  # check mark
    chr(0x2717): "X",  # cross mark
    chr(0x2022): "*",  # bullet
}


def _safe(text: str) -> str:
    """Return text encodable on the current console codepage, ASCII-safe."""
    encoding = sys.stdout.encoding or "utf-8"
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        for glyph, fallback in _ASCII_FALLBACKS.items():
            text = text.replace(glyph, fallback)
        text = text.encode(encoding, errors="replace").decode(encoding)
    return text


def print_header(text: str) -> None:
    """Print a styled section header."""
    text = _safe(text)
    separator = "=" * 70
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}  {text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} {_safe(text)}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {_safe(text)}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} {_safe(text)}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {_safe(text)}")
