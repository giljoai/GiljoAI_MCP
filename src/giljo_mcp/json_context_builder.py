"""
JSON Context Builder for Orchestrator Missions.

Builds structured JSON context with priority framing for orchestrator missions.
Organizes context fields into three priority tiers (critical/important/reference)
to enable efficient token usage and priority-based context management.

Part of the mission response JSON restructuring initiative (Handover 0347a).
Uses only Python stdlib (no PyYAML dependency).
"""

from __future__ import annotations

import json
from typing import Any


class JSONContextBuilder:
    """
    Builds structured JSON context with priority framing for orchestrator missions.

    Organizes context fields into three priority tiers:
    - critical: Always included (e.g., product_core, tech_stack)
    - important: High priority (e.g., architecture, testing)
    - reference: Medium priority (e.g., vision_documents, memory_360)

    Usage:
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {"name": "GiljoAI", ...})
        builder.add_important("architecture")
        builder.add_important_content("architecture", {"patterns": [...]})
        result = builder.build()
        tokens = builder.estimate_tokens()

    Output Structure:
        {
            "priority_map": {
                "critical": ["field1", "field2"],
                "important": ["field3"],
                "reference": ["field4", "field5"]
            },
            "critical": {
                "field1": <content>,
                "field2": <content>
            },
            "important": {
                "field3": <content>
            },
            "reference": {
                "field4": <content>,
                "field5": <content>
            }
        }
    """

    def __init__(self) -> None:
        """Initialize empty builder with three priority tiers."""
        self.critical_fields: list[str] = []
        self.important_fields: list[str] = []
        self.reference_fields: list[str] = []
        self.critical_content: dict[str, Any] = {}
        self.important_content: dict[str, Any] = {}
        self.reference_content: dict[str, Any] = {}

    def _validate_field_name(self, field_name: str | None) -> None:
        """
        Validate that field name is non-empty and not None.

        Args:
            field_name: Name of the field to validate

        Raises:
            ValueError: If field_name is empty or None
        """
        if not field_name:
            raise ValueError("Field name cannot be empty")

    def _check_field_exists(self, field_name: str) -> None:
        """
        Check if field already exists in any tier.

        Args:
            field_name: Name of the field to check

        Raises:
            ValueError: If field already exists in any tier
        """
        all_fields = (
            self.critical_fields +
            self.important_fields +
            self.reference_fields
        )
        if field_name in all_fields:
            raise ValueError(f"Field '{field_name}' already exists in a priority tier")

    def _validate_json_serializable(self, content: Any) -> None:
        """
        Validate that content is JSON-serializable.

        Args:
            content: Content to validate

        Raises:
            TypeError: If content is not JSON-serializable
        """
        try:
            json.dumps(content)
        except (TypeError, ValueError) as e:
            raise TypeError(f"Content is not JSON-serializable: {e}") from e

    def add_critical(self, field_name: str) -> None:
        """
        Add a field to the critical priority tier.

        Critical fields are always included in the mission context and
        represent essential information the agent must know.

        Args:
            field_name: Name of the context field (e.g., "product_core")

        Raises:
            ValueError: If field_name is empty or already exists in any tier
        """
        self._validate_field_name(field_name)
        self._check_field_exists(field_name)
        self.critical_fields.append(field_name)

    def add_important(self, field_name: str) -> None:
        """
        Add a field to the important priority tier.

        Important fields contain high-priority context that should be
        included when token budget allows.

        Args:
            field_name: Name of the context field (e.g., "architecture")

        Raises:
            ValueError: If field_name is empty or already exists in any tier
        """
        self._validate_field_name(field_name)
        self._check_field_exists(field_name)
        self.important_fields.append(field_name)

    def add_reference(self, field_name: str) -> None:
        """
        Add a field to the reference priority tier.

        Reference fields contain supplementary context that can be
        fetched on-demand via MCP tools when needed.

        Args:
            field_name: Name of the context field (e.g., "vision_documents")

        Raises:
            ValueError: If field_name is empty or already exists in any tier
        """
        self._validate_field_name(field_name)
        self._check_field_exists(field_name)
        self.reference_fields.append(field_name)

    def add_critical_content(self, field_name: str, content: Any) -> None:
        """
        Add content for a critical field.

        Args:
            field_name: Name of the field (must be in critical_fields)
            content: Any JSON-serializable content (dict, list, str, int, etc.)

        Raises:
            ValueError: If field_name not in critical_fields
            TypeError: If content is not JSON-serializable
        """
        if field_name not in self.critical_fields:
            raise ValueError(f"Field '{field_name}' not in critical_fields")
        self._validate_json_serializable(content)
        self.critical_content[field_name] = content

    def add_important_content(self, field_name: str, content: Any) -> None:
        """
        Add content for an important field.

        Args:
            field_name: Name of the field (must be in important_fields)
            content: Any JSON-serializable content

        Raises:
            ValueError: If field_name not in important_fields
            TypeError: If content is not JSON-serializable
        """
        if field_name not in self.important_fields:
            raise ValueError(f"Field '{field_name}' not in important_fields")
        self._validate_json_serializable(content)
        self.important_content[field_name] = content

    def add_reference_content(self, field_name: str, content: Any) -> None:
        """
        Add content for a reference field.

        Args:
            field_name: Name of the field (must be in reference_fields)
            content: Any JSON-serializable content

        Raises:
            ValueError: If field_name not in reference_fields
            TypeError: If content is not JSON-serializable
        """
        if field_name not in self.reference_fields:
            raise ValueError(f"Field '{field_name}' not in reference_fields")
        self._validate_json_serializable(content)
        self.reference_content[field_name] = content

    def build(self) -> dict[str, Any]:
        """
        Build the complete JSON structure with priority framing.

        Returns:
            dict: Structured JSON with format:
                {
                    "priority_map": {
                        "critical": ["field1", "field2"],
                        "important": ["field3"],
                        "reference": ["field4", "field5"]
                    },
                    "critical": {
                        "field1": <content>,
                        "field2": <content>
                    },
                    "important": {
                        "field3": <content>
                    },
                    "reference": {
                        "field4": <content>,
                        "field5": <content>
                    }
                }

        Note:
            - Fields without content are omitted from tier dicts
            - priority_map always includes all registered fields
            - Result is always JSON-serializable
        """
        return {
            "priority_map": {
                "critical": list(self.critical_fields),
                "important": list(self.important_fields),
                "reference": list(self.reference_fields)
            },
            "critical": dict(self.critical_content),
            "important": dict(self.important_content),
            "reference": dict(self.reference_content)
        }

    def estimate_tokens(self) -> int:
        """
        Estimate total token count for the built JSON structure.

        Uses approximation: 1 token ~ 4 characters

        Returns:
            int: Estimated token count

        Note:
            - Estimates based on JSON-serialized output
            - Includes all formatting (whitespace, brackets, quotes)
            - Useful for context budget management
        """
        json_str = json.dumps(self.build())
        return len(json_str) // 4
