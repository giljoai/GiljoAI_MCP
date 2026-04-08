# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Downloads package - Token management for secure file downloads.

This package provides the TokenManager class for generating and validating
one-time download tokens for slash commands and agent templates.
"""

from .token_manager import TokenManager


__all__ = ["TokenManager"]
