# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Mission Planner for GiljoAI MCP.

Provides toggle-based context instructions for orchestrator agents.
The orchestrator calls fetch_context() on-demand using these instructions,
avoiding inline context bloat (Handover 0350b).
"""

import logging

from .database import DatabaseManager
from .models import Product, Project

logger = logging.getLogger(__name__)


class MissionPlanner:
    """
    Build fetch instructions that guide orchestrator agents to fetch context on-demand.

    The only active entry point is _build_fetch_instructions(), called by
    OrchestrationService.get_orchestrator_instructions().
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize MissionPlanner.

        Args:
            db_manager: Database manager instance for data access
        """
        self.db_manager = db_manager

    def _build_fetch_instructions(
        self,
        product: "Product",
        project: "Project",
        field_toggles: dict,
        depth_config: dict,
    ) -> list[dict]:
        """
        Build fetch instructions for context tools based on user toggles (Handover 0350b).

        Each instruction includes: tool name, params, framing text.
        Toggled-off categories are excluded. Toggled-on categories produce
        a fetch instruction with depth params where applicable.

        Args:
            product: Product model with metadata
            project: Project model with metadata
            field_toggles: Dict mapping field names to toggle state (bool).
                          True = included, False = excluded.
            depth_config: Dict mapping field names to depth levels.
                         Controls HOW MUCH detail to fetch for each field.

        Returns:
            List of instruction dicts, each with field, tool, params, framing keys.
        """
        instructions = []

        tool_configs = {
            "product_core": {
                "tool": "fetch_context",
                "category": "product_core",
                "framing": "Product name, description, and core features. Essential foundation for all work.",
            },
            "vision_documents": {
                "tool": "fetch_context",
                "category": "vision_documents",
                "framing": "Product vision and strategic direction. Use pagination for large documents.",
                "supports_pagination": True,
                "depth_aware": True,
            },
            "tech_stack": {
                "tool": "fetch_context",
                "category": "tech_stack",
                "framing": "Programming languages, frameworks, and databases. Critical for implementation decisions.",
            },
            "architecture": {
                "tool": "fetch_context",
                "category": "architecture",
                "framing": "System architecture patterns, API style, and design principles.",
            },
            "testing": {
                "tool": "fetch_context",
                "category": "testing",
                "framing": "Quality standards, testing strategy, and frameworks.",
            },
            "memory_360": {
                "tool": "fetch_context",
                "category": "memory_360",
                "framing": "Historical project outcomes and cumulative product knowledge.",
                "depth_aware": True,
            },
            "git_history": {
                "tool": "fetch_context",
                "category": "git_history",
                "framing": "Recent git commits aggregated across projects.",
                "depth_aware": True,
            },
            "agent_templates": {
                "tool": "fetch_context",
                "category": "agent_templates",
                "framing": "Available agent templates for spawning specialized agents.",
                "depth_aware": True,
            },
        }

        inlined_fields = {"project_description"}

        for field, enabled in field_toggles.items():
            if not enabled:
                continue

            if field in inlined_fields:
                continue

            config = tool_configs.get(field)
            if not config:
                logger.warning(f"No fetch tool config for field: {field}")
                continue

            instruction = {
                "field": field,
                "tool": config["tool"],
                "params": {
                    "category": config["category"],
                    "product_id": str(product.id),
                    "tenant_key": product.tenant_key,
                },
                "framing": config["framing"],
            }

            if config.get("supports_pagination"):
                instruction["supports_pagination"] = True

            if config.get("depth_aware"):
                if field == "vision_documents":
                    vision_depth = depth_config.get("vision_documents", "light")
                    instruction["params"]["depth"] = vision_depth

                    vision_framing = {
                        "light": "33% summarized vision document (single response).",
                        "medium": "66% summarized vision document (single response).",
                        "full": "Complete vision document (paginated, call until has_more=false).",
                    }
                    instruction["framing"] = vision_framing.get(vision_depth, vision_framing["light"])

                    if vision_depth == "full":
                        instruction["params"]["offset"] = 0
                        instruction["supports_pagination"] = True
                    else:
                        instruction.pop("supports_pagination", None)
                elif field == "memory_360":
                    instruction["params"]["limit"] = depth_config.get("memory_360", 5)
                elif field == "git_history":
                    instruction["params"]["limit"] = depth_config.get("git_history", 20)
                elif field == "agent_templates":
                    agent_depth = depth_config.get("agent_templates", "type_only")
                    if agent_depth == "type_only":
                        continue  # Already inline - no fetch needed
                    instruction["params"]["depth"] = agent_depth
                    instruction["framing"] = "Full agent templates with complete prompts for spawning."

            instructions.append(instruction)

        return instructions
