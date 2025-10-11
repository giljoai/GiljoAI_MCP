"""
GiljoAI MCP CLI Installer Package
Professional CLI-only installation system for localhost and server deployments

**DEPRECATED**: This installer is no longer used.

Use the root installer instead:
    python install.py

The root installer (install.py) uses the SAME table creation method
as the rest of the application:
    DatabaseManager.create_tables_async() -> Base.metadata.create_all()

This folder is kept only for reference. DO NOT USE in production.
"""

__version__ = "2.0.0 (DEPRECATED)"
__all__ = ["install"]

from .install import install
