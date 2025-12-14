"""
YAML Context Builder Utility Class.

Builds structured YAML context with priority framing for orchestrator prompts.
Implements 3-tier priority system:
- CRITICAL: Always inline, always read
- IMPORTANT: Inline but condensed with fetch_details pointer
- REFERENCE: Summary only with fetch_tool pointer

Token estimate: 1 token ≈ 4 characters
"""

from typing import Any

import yaml


class YAMLContextBuilder:
    """Builds structured YAML context with priority framing."""

    def __init__(self) -> None:
        """Initialize builder with empty priority lists and content dictionaries."""
        self.critical_fields: list[str] = []
        self.important_fields: list[str] = []
        self.reference_fields: list[str] = []
        self.critical_content: dict[str, Any] = {}
        self.important_content: dict[str, Any] = {}
        self.reference_content: dict[str, Any] = {}

    def add_critical(self, field_name: str) -> None:
        """
        Add field to CRITICAL priority tier.

        Args:
            field_name: Name of the field to mark as critical
        """
        if field_name not in self.critical_fields:
            self.critical_fields.append(field_name)

    def add_important(self, field_name: str) -> None:
        """
        Add field to IMPORTANT priority tier.

        Args:
            field_name: Name of the field to mark as important
        """
        if field_name not in self.important_fields:
            self.important_fields.append(field_name)

    def add_reference(self, field_name: str) -> None:
        """
        Add field to REFERENCE priority tier.

        Args:
            field_name: Name of the field to mark as reference
        """
        if field_name not in self.reference_fields:
            self.reference_fields.append(field_name)

    def add_critical_content(self, field_name: str, content: Any) -> None:
        """
        Add full inline content for CRITICAL field.

        Args:
            field_name: Name of the critical field
            content: Full nested content to include inline
        """
        self.critical_content[field_name] = content

    def add_important_content(self, field_name: str, content: Any) -> None:
        """
        Add condensed content for IMPORTANT field.

        Should include fetch_details pointer for full content retrieval.

        Args:
            field_name: Name of the important field
            content: Condensed content with fetch_details pointer
        """
        self.important_content[field_name] = content

    def add_reference_content(self, field_name: str, content: Any) -> None:
        """
        Add summary-only content for REFERENCE field.

        Should include summary and fetch_tool pointer.

        Args:
            field_name: Name of the reference field
            content: Summary and fetch_tool pointer
        """
        self.reference_content[field_name] = content

    def to_yaml(self) -> str:
        """
        Generate structured YAML output with priority framing.

        Returns:
            YAML string with visual section headers and prioritized content
        """
        lines = []

        # Priority map section
        lines.append("# " + "=" * 67)
        lines.append("# CONTEXT PRIORITY MAP - Read this first")
        lines.append("# " + "=" * 67)

        # Build priorities structure
        priorities = {}
        if self.critical_fields:
            priorities["CRITICAL"] = self.critical_fields
        if self.important_fields:
            priorities["IMPORTANT"] = self.important_fields
        if self.reference_fields:
            priorities["REFERENCE"] = self.reference_fields

        priority_yaml = yaml.dump({"priorities": priorities}, default_flow_style=False, sort_keys=False)
        lines.append(priority_yaml.rstrip())

        # CRITICAL section
        if self.critical_content:
            lines.append("")
            lines.append("# " + "=" * 67)
            lines.append("# CRITICAL (Priority 1) - Always inline, always read")
            lines.append("# " + "=" * 67)
            critical_yaml = yaml.dump(self.critical_content, default_flow_style=False, sort_keys=False)
            lines.append(critical_yaml.rstrip())

        # IMPORTANT section
        if self.important_content:
            lines.append("")
            lines.append("# " + "=" * 67)
            lines.append("# IMPORTANT (Priority 2) - Inline but condensed")
            lines.append("# " + "=" * 67)
            important_yaml = yaml.dump(self.important_content, default_flow_style=False, sort_keys=False)
            lines.append(important_yaml.rstrip())

        # REFERENCE section
        if self.reference_content:
            lines.append("")
            lines.append("# " + "=" * 67)
            lines.append("# REFERENCE (Priority 3) - Summary only, fetch on-demand")
            lines.append("# " + "=" * 67)
            reference_yaml = yaml.dump(self.reference_content, default_flow_style=False, sort_keys=False)
            lines.append(reference_yaml.rstrip())

        return "\n".join(lines)

    def estimate_tokens(self) -> int:
        """
        Estimate token count using 1 token ≈ 4 characters formula.

        Returns:
            Estimated token count for generated YAML
        """
        yaml_output = self.to_yaml()
        return len(yaml_output) // 4
