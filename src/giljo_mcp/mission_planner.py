"""
Mission Planner for GiljoAI Agent Orchestration MCP Server.

Provides framing-based context instructions for orchestrator agents.
The orchestrator calls fetch_context() on-demand using these instructions,
avoiding inline context bloat (Handover 0350b).
"""

import logging

from .database import DatabaseManager
from .models import Product, Project


logger = logging.getLogger(__name__)


class MissionPlanner:
    """
    Build framing instructions that guide orchestrator agents to fetch context on-demand.

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

    def _get_tier_framing(self, tier: str, base_framing: str) -> str:
        """
        Add tier-specific prefix to framing text (Handover 0350b).

        Args:
            tier: Tier name ('critical', 'important', 'reference')
            base_framing: Base description of the field

        Returns:
            Framing text with appropriate prefix (REQUIRED/RECOMMENDED/OPTIONAL)
        """
        prefixes = {
            "critical": "REQUIRED: ",
            "important": "RECOMMENDED: ",
            "reference": "OPTIONAL: ",
        }
        prefix = prefixes.get(tier, "")

        # Don't duplicate prefix if already present
        if base_framing.startswith(prefix):
            return base_framing
        return prefix + base_framing

    def _build_fetch_instructions(
        self,
        product: "Product",
        project: "Project",
        field_priorities: dict,
        depth_config: dict,
    ) -> dict:
        """
        Build framing instructions for context fetch tools (Handover 0350b).

        Maps user's field priorities to tier-based fetch instructions.
        Each instruction includes: tool name, params, framing text, token estimate.

        This method is the core of the framing-based architecture that replaces
        inline context (~4-8K tokens) with fetch pointers (~500 tokens).

        Args:
            product: Product model with metadata
            project: Project model with metadata
            field_priorities: Dict mapping field names to priority (1-4)
                             1=CRITICAL, 2=IMPORTANT, 3=REFERENCE, 4=EXCLUDED
            depth_config: Dict mapping field names to depth levels
                         Controls HOW MUCH detail to fetch for each field

        Returns:
            {
                "critical": [{"field": "product_core", "tool": "fetch_context", ...}],
                "important": [...],
                "reference": [...]
            }
        """
        instructions = {"critical": [], "important": [], "reference": []}
        tier_map = {1: "critical", 2: "important", 3: "reference"}

        # Tool configuration mapping - defines how each field maps to fetch_context
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

        # Fields that are already inlined in the response (no fetch needed)
        inlined_fields = {"project_description"}

        # Iterate through field priorities and build instructions
        for field, priority in field_priorities.items():
            if priority >= 4:  # Excluded
                continue

            # Skip fields that are already inlined in the response
            if field in inlined_fields:
                continue

            config = tool_configs.get(field)
            if not config:
                logger.warning(f"No fetch tool config for field: {field}")
                continue

            tier = tier_map.get(priority, "reference")

            # Build instruction entry
            instruction = {
                "field": field,
                "tool": config["tool"],
                "params": {
                    "category": config["category"],
                    "product_id": str(product.id),
                    "tenant_key": product.tenant_key,
                },
                "framing": self._get_tier_framing(tier, config["framing"]),
            }

            # Add pagination support flag if applicable
            if config.get("supports_pagination"):
                instruction["supports_pagination"] = True

            # Add depth-specific params if applicable
            if config.get("depth_aware"):
                if field == "vision_documents":
                    # Vision docs use depth for summary level (light/medium/full)
                    # Handover 0352: light=33% summary, medium=66% summary, full=paginated chunks
                    vision_depth = depth_config.get("vision_documents", "light")
                    instruction["params"]["depth"] = vision_depth

                    # Update framing based on depth
                    vision_framing = {
                        "light": "33% summarized vision document (single response).",
                        "medium": "66% summarized vision document (single response).",
                        "full": "Complete vision document (paginated, call until has_more=false).",
                    }
                    base_framing = vision_framing.get(vision_depth, vision_framing["light"])
                    instruction["framing"] = self._get_tier_framing(tier, base_framing)

                    # Only add pagination params for full depth
                    if vision_depth == "full":
                        instruction["params"]["offset"] = 0
                        instruction["supports_pagination"] = True
                    else:
                        # Remove pagination flag for light/medium (single response)
                        instruction.pop("supports_pagination", None)
                elif field == "memory_360":
                    instruction["params"]["limit"] = depth_config.get("memory_360", 5)
                elif field == "git_history":
                    instruction["params"]["limit"] = depth_config.get("git_history", 20)
                elif field == "agent_templates":
                    agent_depth = depth_config.get("agent_templates", "type_only")
                    # Handover 0351: Skip fetch for type_only (already inline in response)
                    # Only include fetch instruction when full templates needed
                    if agent_depth == "type_only":
                        continue  # Already inline - no fetch needed
                    instruction["params"]["depth"] = agent_depth
                    instruction["framing"] = self._get_tier_framing(
                        tier, "Full agent templates with complete prompts for spawning."
                    )

            instructions[tier].append(instruction)

        return instructions
