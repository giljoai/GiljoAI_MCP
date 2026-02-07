"""
Validation rules for agent templates.

Each rule implements a specific validation check:
- CRITICAL_001: MCP Tools Presence
- CRITICAL_002: Placeholder Verification
- CRITICAL_003: Injection Detection
- WARNING_001: Tool Usage Best Practices

Rules are executed in order by TemplateValidator.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationError:
    """Represents a validation error or warning."""

    rule_id: str
    severity: str  # "critical", "warning", "info"
    message: str
    remediation: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for API responses."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "remediation": self.remediation,
        }


class ValidationRule(ABC):
    """Base class for all validation rules."""

    rule_id: str
    name: str
    severity: str

    @abstractmethod
    def validate(self, content: str, agent_display_name: str) -> Optional[ValidationError]:
        """
        Validate template content.

        Args:
            content: Full template text to validate
            agent_display_name: Type of agent (orchestrator, implementer, etc.)

        Returns:
            ValidationError if rule fails, None if passes
        """


class MCPToolsPresenceRule(ValidationRule):
    """
    CRITICAL_001: Verify required MCP tools are present in template.

    All agent templates must reference core MCP tools for job lifecycle:
    - acknowledge_job: Acknowledge job assignment
    - report_progress: Report incremental progress
    - complete_job: Mark job as completed
    - send_message: Send messages to other agents
    - receive_messages: Receive messages from other agents
    """

    rule_id = "CRITICAL_001_MCP_TOOLS"
    name = "MCP Tools Presence Check"
    severity = "critical"

    REQUIRED_TOOLS = ["acknowledge_job", "report_progress", "complete_job", "send_message", "receive_messages"]

    def validate(self, content: str, agent_display_name: str) -> Optional[ValidationError]:
        """Check all required MCP tools are mentioned in template."""
        missing_tools = []

        for tool in self.REQUIRED_TOOLS:
            if tool not in content:
                missing_tools.append(tool)

        if missing_tools:
            return ValidationError(
                rule_id=self.rule_id,
                severity=self.severity,
                message=f"Missing required MCP tools: {', '.join(missing_tools)}",
                remediation="Restore missing tools from system_instructions or reset template to defaults",
            )

        return None


class PlaceholderVerificationRule(ValidationRule):
    """
    CRITICAL_002: Verify required placeholders are present.

    Templates must include these placeholders for runtime substitution:
    - {agent_id}: Unique agent identifier
    - {tenant_key}: Multi-tenant isolation key
    - {job_id}: Job assignment identifier

    Optional but recommended:
    - {mission}: Agent mission statement
    - {available_tools}: List of available tools
    """

    rule_id = "CRITICAL_002_PLACEHOLDERS"
    name = "Placeholder Verification"
    severity = "critical"

    REQUIRED_PLACEHOLDERS = ["agent_id", "tenant_key", "job_id"]

    def validate(self, content: str, agent_display_name: str) -> Optional[ValidationError]:
        """Check required placeholders are present and well-formed."""
        missing_placeholders = []

        # Check for required placeholders
        for placeholder in self.REQUIRED_PLACEHOLDERS:
            pattern = r"\{" + placeholder + r"\}"
            if not re.search(pattern, content):
                missing_placeholders.append(f"{{{placeholder}}}")

        if missing_placeholders:
            return ValidationError(
                rule_id=self.rule_id,
                severity=self.severity,
                message=f"Missing required placeholders: {', '.join(missing_placeholders)}",
                remediation="Add required placeholders to template for runtime substitution",
            )

        # Check for malformed placeholders (optional warning)
        malformed_patterns = [
            r"[^{]{[\w_]+}[^}]",  # Missing closing brace
            r"\{\{[\w_]+\}\}",  # Double braces (might be intentional in some contexts)
        ]

        for pattern in malformed_patterns:
            if re.search(pattern, content):
                # Note: Not returning error for malformed placeholders in this version
                # Could be enhanced to detect more edge cases
                pass

        return None


class InjectionDetectionRule(ValidationRule):
    """
    CRITICAL_003: Detect potential injection attacks.

    Scans for common injection patterns:
    - SQL injection (DROP, UNION, etc.)
    - Command injection (&&, |, ;, backticks)
    - Script injection (<script>, onerror, etc.)

    Smart enough to ignore code examples in proper context (code blocks).
    """

    rule_id = "CRITICAL_003_INJECTION"
    name = "Injection Detection"
    severity = "critical"

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"';\s*DROP\s+TABLE",
        r"'\s*OR\s+'\d'\s*=\s*'\d",
        r"'\s*UNION\s+SELECT",
        r"--\s*$",
        r"admin'--",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"&&\s*rm\s+-rf",
        r"\|\s*cat\s+/etc/passwd",
        r";\s*whoami",
        r"`[^`]+`(?!``)",  # Backticks not in code blocks
        r"\$\([^)]+\)",
    ]

    # Script injection patterns
    SCRIPT_INJECTION_PATTERNS = [r"<script[^>]*>", r"onerror\s*=", r"javascript:", r"<iframe[^>]*>"]

    def validate(self, content: str, agent_display_name: str) -> Optional[ValidationError]:
        """Detect injection patterns in template content."""
        # Remove code blocks to avoid false positives
        content_without_code_blocks = self._remove_code_blocks(content)

        detected_patterns = []

        # Check SQL injection
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, content_without_code_blocks, re.IGNORECASE | re.MULTILINE):
                detected_patterns.append(f"SQL injection pattern: {pattern}")

        # Check command injection
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, content_without_code_blocks):
                detected_patterns.append(f"Command injection pattern: {pattern}")

        # Check script injection
        for pattern in self.SCRIPT_INJECTION_PATTERNS:
            if re.search(pattern, content_without_code_blocks, re.IGNORECASE):
                detected_patterns.append(f"Script injection pattern: {pattern}")

        if detected_patterns:
            return ValidationError(
                rule_id=self.rule_id,
                severity=self.severity,
                message=f"Potential injection attack detected: {detected_patterns[0]}",
                remediation="Remove malicious content or reset template to system defaults",
            )

        return None

    def _remove_code_blocks(self, content: str) -> str:
        """
        Remove code blocks to avoid false positives on examples.

        Removes:
        - Triple backtick code blocks (```...```)
        - Inline code blocks (`...`)
        """
        # Remove triple backtick blocks
        content = re.sub(r"```[\s\S]*?```", "", content)

        # Remove inline code
        content = re.sub(r"`[^`]+`", "", content)

        return content


class ToolUsageBestPracticesRule(ValidationRule):
    """
    WARNING_001: Check tool usage best practices.

    Non-critical warnings for recommended practices:
    - Error handling mentions (report_error)
    - Progress reporting frequency guidance
    - Message acknowledgment best practices
    """

    rule_id = "WARNING_001_BEST_PRACTICES"
    name = "Tool Usage Best Practices"
    severity = "warning"

    BEST_PRACTICE_KEYWORDS = ["error", "report_error", "handle errors", "gracefully"]

    def validate(self, content: str, agent_display_name: str) -> Optional[ValidationError]:
        """Check for best practice mentions."""
        # Check if error handling is mentioned
        error_handling_mentioned = any(keyword in content.lower() for keyword in self.BEST_PRACTICE_KEYWORDS)

        if not error_handling_mentioned:
            return ValidationError(
                rule_id=self.rule_id,
                severity=self.severity,
                message="Template does not mention error handling best practices",
                remediation="Consider adding guidance on using report_error() and handling failures gracefully",
            )

        return None
