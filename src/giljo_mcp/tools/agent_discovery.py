# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Dynamic agent discovery tool for orchestrators.

Provides on-demand access to available agent templates without
embedding them in prompts (saves 142 tokens per orchestrator instance).

Handover 0246c: Dynamic Agent Discovery & Token Reduction

Key Features:
- On-demand agent template discovery
- Multi-tenant isolation enforcement
- Version tracking with metadata
- Graceful handling of missing version fields
- Professional error handling with fallback messages
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.templates import AgentTemplate


logger = logging.getLogger(__name__)

# Constants for response formatting
MAX_DESCRIPTION_LENGTH = 200
DEFAULT_VERSION = "unknown"
DEFAULT_ROLE = "Specialized Agent"


def _format_agent_info(template: AgentTemplate, depth: str = "full") -> dict[str, Any]:
    """
    Format agent template into discovery response format.

    Args:
        template: AgentTemplate database model instance
        depth: Detail level - "basic" (name/role/version) or "full" (includes description)

    Returns:
        dict with formatted agent information

    Note:
        Handles missing fields gracefully with sensible defaults.

    Handover 0283: Added depth parameter for context depth configuration.
    Handover 0421: Added staleness detection fields (may_be_stale, last_exported_at, updated_at).
    """
    # Handle missing version gracefully
    version = template.version or DEFAULT_VERSION

    # Base information (always included)
    agent_info = {
        "name": template.name,
        "role": template.role or DEFAULT_ROLE,
        "version_tag": version,
    }

    # Add staleness detection fields (Handover 0421 - always included)
    agent_info.update(
        {
            "may_be_stale": template.may_be_stale,
            "last_exported_at": template.last_exported_at.isoformat() if template.last_exported_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }
    )

    # Add additional fields based on depth level
    if depth == "full":
        # Truncate description if too long
        description = ""
        if template.description:
            description = (
                template.description[:MAX_DESCRIPTION_LENGTH]
                if len(template.description) > MAX_DESCRIPTION_LENGTH
                else template.description
            )

        agent_info.update(
            {
                "description": description,
                "expected_filename": f"{template.name}_{version}.md",
                "created_at": template.created_at.isoformat() if template.created_at else None,
            }
        )

    return agent_info


async def get_available_agents(session: AsyncSession, tenant_key: str, depth: str = "full") -> dict[str, Any]:
    """
    Get available agent templates with version metadata.

    Used by orchestrators to discover available agents without
    requiring embedded templates in prompts.

    Args:
        session: Database session
        tenant_key: Tenant isolation key
        depth: Detail level - "basic" (name/role/version only, ~50 tokens) or
               "full" (includes description, ~1.2k tokens). Default: "full"

    Returns:
        dict with agents list and version metadata

    Example Response (depth="full", with staleness):
        {
            "success": True,
            "data": {
                "agents": [
                    {
                        "name": "implementer",
                        "role": "Code Implementation Specialist",
                        "description": "...",
                        "version_tag": "1.2.0",
                        "may_be_stale": true,
                        "last_exported_at": "2025-12-20T10:00:00Z",
                        "updated_at": "2025-12-28T15:00:00Z",
                        "expected_filename": "implementer_1.2.0.md",
                        "created_at": "2025-11-24T12:00:00"
                    }
                ],
                "count": 5,
                "fetched_at": "2025-11-24T12:30:00",
                "note": "Templates fetched dynamically (full depth)",
                "staleness_warning": {
                    "has_stale_agents": true,
                    "stale_count": 1,
                    "stale_agents": ["implementer"],
                    "action_required": "Some agent templates may be outdated. Run /gil_get_agents to sync, or continue anyway?",
                    "options": ["Run /gil_get_agents", "Continue anyway", "Abort staging"]
                }
            }
        }

    Example Response (depth="basic"):
        {
            "success": True,
            "data": {
                "agents": [
                    {
                        "name": "implementer",
                        "role": "Code Implementation Specialist",
                        "version_tag": "1.2.0"
                    }
                ],
                "count": 5,
                "fetched_at": "2025-11-24T12:30:00",
                "note": "Templates fetched dynamically (basic depth)"
            }
        }

    Handover 0283: Added depth parameter for context depth configuration.
    Handover 0421: Added staleness detection with warning structure.
    """
    try:
        # Input validation
        if not tenant_key or not isinstance(tenant_key, str):
            logger.warning("Invalid tenant_key provided to get_available_agents")
            return {
                "success": True,
                "data": {
                    "agents": [],
                    "count": 0,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "note": "Invalid tenant key - no agents available",
                },
            }

        logger.info("Fetching available agents", extra={"tenant_key": tenant_key, "depth": depth})

        # Fetch active templates for this tenant
        stmt = (
            select(AgentTemplate)
            .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active))
            .order_by(AgentTemplate.created_at)
        )

        result = await session.execute(stmt)
        templates = result.scalars().all()

        # Format response with version metadata (apply depth filtering)
        agents = [_format_agent_info(template, depth=depth) for template in templates]

        # ═══════════════════════════════════════════════════════════════════════
        # Handover 0421: Add staleness warning structure
        # ═══════════════════════════════════════════════════════════════════════
        stale_agents = [agent["name"] for agent in agents if agent.get("may_be_stale", False)]
        staleness_warning = None

        if stale_agents:
            staleness_warning = {
                "has_stale_agents": True,
                "stale_count": len(stale_agents),
                "stale_agents": stale_agents,
                "action_required": (
                    "Some agent templates have been modified since last export. "
                    "Local .claude/agents/ files may be outdated. "
                    "Run /gil_get_agents to sync, or continue anyway?"
                ),
                "options": [
                    "Run /gil_get_agents",
                    "Continue anyway (risk using stale templates)",
                    "Abort staging",
                ],
            }
            logger.warning(
                f"Staleness detected: {len(stale_agents)} stale agent(s) found",
                extra={"tenant_key": tenant_key, "stale_agents": stale_agents},
            )
        # ═══════════════════════════════════════════════════════════════════════

        logger.info(
            f"Found {len(agents)} available agents (depth={depth})",
            extra={"tenant_key": tenant_key, "count": len(agents), "depth": depth},
        )

        response_data = {
            "agents": agents,
            "count": len(agents),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "note": f"Templates fetched dynamically ({depth} depth)",
        }

        # Add staleness warning only if stale agents detected (Handover 0421)
        if staleness_warning:
            response_data["staleness_warning"] = staleness_warning

        return {
            "success": True,
            "data": response_data,
        }

    except Exception:  # Broad catch: tool boundary, logs and re-raises
        logger.exception("Failed to fetch available agents", extra={"tenant_key": tenant_key})
        return {
            "success": False,
            "error": "Database error occurred while fetching agents",
            "fallback": "Unable to discover agents. Check server connectivity.",
        }
