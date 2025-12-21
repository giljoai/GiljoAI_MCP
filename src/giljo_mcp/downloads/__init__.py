"""
Downloads package - Token management for secure file downloads.

This package provides the TokenManager class for generating and validating
one-time download tokens for slash commands and agent templates.
"""

from .token_manager import TokenManager

__all__ = ["TokenManager"]
