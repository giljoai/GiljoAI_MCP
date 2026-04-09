# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Platform handler auto-detection factory.

Automatically detects the current platform and returns the appropriate handler.
Uses Strategy pattern to isolate all OS-specific code.

Usage:
    from installer.platforms import get_platform_handler

    handler = get_platform_handler()
    python_path = handler.get_venv_python(venv_dir)
"""

import platform
from typing import Type

from .base import PlatformHandler
from .linux import LinuxPlatformHandler
from .macos import MacOSPlatformHandler
from .windows import WindowsPlatformHandler

# Platform mapping
_PLATFORM_HANDLERS: dict[str, Type[PlatformHandler]] = {
    "Windows": WindowsPlatformHandler,
    "Linux": LinuxPlatformHandler,
    "Darwin": MacOSPlatformHandler,  # macOS reports as 'Darwin'
}


def get_platform_handler() -> PlatformHandler:
    """
    Auto-detect platform and return appropriate handler.

    Detects platform using platform.system() and returns the corresponding
    handler implementation.

    Returns:
        Platform-specific handler instance

    Raises:
        RuntimeError: If platform is not supported

    Examples:
        >>> handler = get_platform_handler()
        >>> handler.platform_name
        'Windows'  # or 'Linux', 'macOS'
    """
    system = platform.system()

    handler_class = _PLATFORM_HANDLERS.get(system)

    if handler_class is None:
        supported = ", ".join(_PLATFORM_HANDLERS.keys())
        raise RuntimeError(f"Unsupported platform: {system}. Supported platforms: {supported}")

    return handler_class()


# Public API
__all__ = [
    "PlatformHandler",
    "WindowsPlatformHandler",
    "LinuxPlatformHandler",
    "MacOSPlatformHandler",
    "get_platform_handler",
]
