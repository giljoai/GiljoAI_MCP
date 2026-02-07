"""
System-managed agent role declarations.

Roles listed here are protected by the platform - the Template Manager UI and
template APIs should treat them as immutable, always-on components that cannot
be toggled, exported, or modified by end users.
"""

from __future__ import annotations


SYSTEM_MANAGED_ROLES: set[str] = {"orchestrator"}
