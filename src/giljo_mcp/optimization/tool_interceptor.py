"""
Tool Interceptor - Middleware for optimizing Serena MCP tool calls

Provides real-time interception and optimization of MCP tool calls
to enforce token efficiency and optimization rules.
"""

import logging
from typing import Any

from .serena_optimizer import OperationType, SerenaOptimizer


logger = logging.getLogger(__name__)


class SerenaToolInterceptor:
    """
    Middleware to intercept and optimize Serena MCP tool calls in real-time.

    This class acts as a middleware layer that sits between agent missions
    and actual MCP tool execution, applying optimization rules automatically.
    """

    def __init__(self, optimizer: SerenaOptimizer):
        self.optimizer = optimizer
        self._operation_mapping = self._create_operation_mapping()

    def _create_operation_mapping(self) -> dict[str, OperationType]:
        """Create mapping from MCP tool names to operation types"""
        return {
            # Serena MCP tools mapping
            "mcp__serena__read_file": OperationType.FILE_READ,
            "mcp__serena__find_symbol": OperationType.SYMBOL_SEARCH,
            "mcp__serena__get_symbols_overview": OperationType.SYMBOL_SEARCH,
            "mcp__serena__find_referencing_symbols": OperationType.SYMBOL_SEARCH,
            "mcp__serena__replace_symbol_body": OperationType.SYMBOL_REPLACE,
            "mcp__serena__replace_regex": OperationType.SYMBOL_REPLACE,
            "mcp__serena__search_for_pattern": OperationType.PATTERN_SEARCH,
            "mcp__serena__list_dir": OperationType.DIRECTORY_LIST,
            # Add more mappings as needed
        }

    async def intercept_tool_call(
        self, agent_id: str, tool_name: str, params: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Intercept MCP tool call and apply optimizations.

        Args:
            agent_id: ID of the agent making the call
            tool_name: Name of the MCP tool being called
            params: Original parameters for the tool call

        Returns:
            Tuple of (optimized_params, metadata)
            - optimized_params: Modified parameters with optimizations applied
            - metadata: Information about optimizations applied
        """

        # Only intercept Serena MCP tools
        if not self._is_serena_tool(tool_name):
            return params, {"intercepted": False, "reason": "not_serena_tool"}

        # Get operation type
        operation_type = self._operation_mapping.get(tool_name)
        if not operation_type:
            logger.warning(f"Unknown Serena tool: {tool_name}")
            return params, {"intercepted": False, "reason": "unknown_tool"}

        # Apply optimizations
        optimized_params = await self._apply_optimizations(agent_id, tool_name, operation_type, params)

        # Track the optimization
        metadata = {
            "intercepted": True,
            "operation_type": operation_type.value,
            "optimizations_applied": self._get_applied_optimizations(params, optimized_params),
        }

        if optimized_params != params:
            logger.info(f"Agent {agent_id}: Optimized {tool_name} call")
            logger.debug(f"Original params: {params}")
            logger.debug(f"Optimized params: {optimized_params}")

        return optimized_params, metadata

    def _is_serena_tool(self, tool_name: str) -> bool:
        """Check if tool is a Serena MCP tool"""
        return tool_name.startswith("mcp__serena__")

    async def _apply_optimizations(
        self, agent_id: str, tool_name: str, operation_type: OperationType, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply optimization rules to tool parameters"""

        # Get optimization rules
        rules = await self.optimizer.get_optimization_rules()
        rule = rules.get(operation_type)

        if not rule:
            return params

        # Apply rule-based optimizations
        optimized_params = params.copy()

        # Apply max_answer_chars limit
        if "max_answer_chars" not in optimized_params and rule.max_answer_chars > 0:
            optimized_params["max_answer_chars"] = rule.max_answer_chars

        # Apply operation-specific optimizations
        if operation_type == OperationType.FILE_READ:
            optimized_params = self._optimize_file_read(optimized_params, rule)
        elif operation_type == OperationType.SYMBOL_SEARCH:
            optimized_params = self._optimize_symbol_search(optimized_params, rule)
        elif operation_type == OperationType.PATTERN_SEARCH:
            optimized_params = self._optimize_pattern_search(optimized_params, rule)
        elif operation_type == OperationType.DIRECTORY_LIST:
            optimized_params = self._optimize_directory_list(optimized_params, rule)
        elif operation_type == OperationType.SYMBOL_REPLACE:
            optimized_params = self._optimize_symbol_replace(optimized_params, rule)

        return optimized_params

    def _optimize_file_read(self, params: dict[str, Any], rule) -> dict[str, Any]:
        """Apply file_read specific optimizations"""

        # Warn about potentially large files
        relative_path = params.get("relative_path", "")
        if self._file_likely_large(relative_path):
            logger.warning(
                f"Reading potentially large file: {relative_path}. "
                f"Consider using find_symbol() or get_symbols_overview() instead."
            )

        # Add reading limits if not specified
        # For very large files, suggest chunked reading
        if "start_line" not in params and "end_line" not in params and self._file_likely_very_large(relative_path):
            logger.info(f"Large file detected: {relative_path}. Adding read limits.")
            params["end_line"] = 200  # Limit to first 200 lines

        return params

    def _optimize_symbol_search(self, params: dict[str, Any], rule) -> dict[str, Any]:
        """Apply symbol_search specific optimizations"""

        # Default to not including body unless explicitly requested
        if "include_body" not in params:
            params["include_body"] = False

        # Start with shallow depth
        if "depth" not in params:
            params["depth"] = 0

        # Use substring matching for discovery phases
        if "substring_matching" not in params and not params.get("name_path", "").startswith("/"):
            params["substring_matching"] = True

        return params

    def _optimize_pattern_search(self, params: dict[str, Any], rule) -> dict[str, Any]:
        """Apply pattern_search specific optimizations"""

        # Restrict to code files by default
        if "restrict_search_to_code_files" not in params:
            params["restrict_search_to_code_files"] = True

        # Limit context lines to reduce output
        if "context_lines_before" not in params:
            params["context_lines_before"] = 1

        if "context_lines_after" not in params:
            params["context_lines_after"] = 1

        return params

    def _optimize_directory_list(self, params: dict[str, Any], rule) -> dict[str, Any]:
        """Apply directory_list specific optimizations"""

        # Default to non-recursive unless needed
        if "recursive" not in params:
            params["recursive"] = False

        # Skip ignored files by default
        if "skip_ignored_files" not in params:
            params["skip_ignored_files"] = True

        return params

    def _optimize_symbol_replace(self, params: dict[str, Any], rule) -> dict[str, Any]:
        """Apply symbol_replace specific optimizations"""

        # Add safety limits for replacement operations
        if "max_answer_chars" not in params:
            params["max_answer_chars"] = rule.max_answer_chars

        return params

    def _file_likely_large(self, relative_path: str) -> bool:
        """Heuristic to determine if file is likely large"""
        large_file_indicators = [
            ".min.",
            "bundle.",
            ".lock",
            "package-lock.json",
            "yarn.lock",
            ".log",
            "requirements.txt",
            ".md",
        ]

        path_lower = relative_path.lower()
        return any(indicator in path_lower for indicator in large_file_indicators)

    def _file_likely_very_large(self, relative_path: str) -> bool:
        """Heuristic to determine if file is likely very large (>1000 lines)"""
        very_large_indicators = [
            ".min.js",
            ".min.css",
            "bundle.js",
            "bundle.css",
            "package-lock.json",
            "yarn.lock",
            ".sql",
            "migration",
        ]

        path_lower = relative_path.lower()
        return any(indicator in path_lower for indicator in very_large_indicators)

    def _get_applied_optimizations(self, original: dict[str, Any], optimized: dict[str, Any]) -> list[str]:
        """Get list of optimizations that were applied"""

        optimizations = []

        # Check for added parameters
        for key, value in optimized.items():
            if key not in original:
                optimizations.append(f"added_{key}={value}")
            elif original[key] != value:
                optimizations.append(f"modified_{key}: {original[key]} -> {value}")

        return optimizations

    async def record_tool_execution(
        self, agent_id: str, tool_name: str, params: dict[str, Any], result: Any, metadata: dict[str, Any]
    ):
        """Record tool execution for analytics and optimization tracking"""

        if not metadata.get("intercepted", False):
            return

        operation_type = OperationType(metadata["operation_type"])

        # Calculate sizes for token tracking
        params_size = len(str(params))
        result_size = len(str(result)) if result else 0

        # Record the optimization operation
        await self.optimizer.record_operation(
            agent_id=agent_id,
            operation_type=operation_type,
            params_size=params_size,
            result_size=result_size,
            optimized=True,
        )

        logger.debug(f"Recorded optimization for {tool_name}: {result_size} chars")


class MissionOptimizationInjector:
    """
    Utility to inject optimization rules directly into agent missions.

    This is used as an alternative to runtime interception - rules are
    injected at mission creation time for better performance.
    """

    def __init__(self, optimizer: SerenaOptimizer):
        self.optimizer = optimizer

    async def inject_optimization_rules(self, agent_role: str, mission: str, context_data: dict[str, Any]) -> str:
        """
        Inject optimization rules directly into agent mission text.

        Args:
            agent_role: Role of the agent (implementer, researcher, etc.)
            mission: Original mission text
            context_data: Project context for rule customization

        Returns:
            Mission text with optimization rules injected
        """

        # Get optimization augmentation
        augmentation = await self.optimizer.create_optimization_augmentation(agent_role, context_data)

        # Inject the rules into the mission
        optimized_mission = self._inject_augmentation(mission, augmentation)

        logger.info(f"Injected optimization rules for {agent_role} agent")
        logger.debug(f"Augmentation content length: {len(augmentation['content'])} chars")

        return optimized_mission

    def _inject_augmentation(self, mission: str, augmentation: dict[str, Any]) -> str:
        """Inject augmentation content into mission"""

        if augmentation["type"] != "inject":
            return mission

        target_section = augmentation["target"]
        content = augmentation["content"]

        # Find target section in mission
        if target_section in mission:
            # Insert after the target section
            insertion_point = mission.find(target_section) + len(target_section)
            return mission[:insertion_point] + "\n\n" + content + "\n\n" + mission[insertion_point:]
        # Append to end if target section not found
        return mission + "\n\n" + content

    async def estimate_optimization_impact(self, agent_role: str, context_data: dict[str, Any]) -> dict[str, Any]:
        """
        Estimate the context-efficiency impact of optimization rules.

        Returns:
            Dictionary with estimated savings percentages and impacts
        """

        # Get rules that would be applied
        rules = await self.optimizer.get_optimization_rules()
        adjusted_rules = self.optimizer.adjust_rules_for_context(rules, context_data)

        # Calculate estimated impact
        estimated_impact = {
            "file_read_reduction": "70-90%",  # Based on symbolic operation enforcement
            "search_efficiency": "50-80%",  # Based on max_answer_chars limits
            "overall_token_savings": "60-90%",  # Combined optimization effect
            "rules_applied": len(adjusted_rules),
            "context_adjustments": self._count_context_adjustments(rules, adjusted_rules),
        }

        return estimated_impact

    def _count_context_adjustments(self, original_rules: dict, adjusted_rules: dict) -> int:
        """Count how many rules were adjusted based on context"""

        adjustments = 0
        for operation_type, original_rule in original_rules.items():
            adjusted_rule = adjusted_rules.get(operation_type)
            if adjusted_rule and adjusted_rule.max_answer_chars != original_rule.max_answer_chars:
                adjustments += 1

        return adjustments
