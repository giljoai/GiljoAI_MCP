"""
MCP Tools for Serena Optimization Control

Provides MCP tools for managing and monitoring Serena optimization system:
- Get optimization settings and rules
- Update optimization configuration
- Generate token savings reports
- Force agent handoffs due to context limits
"""

import logging
from typing import Any, Dict

from ..database import get_db_manager
from ..optimization import SerenaOptimizer
from ..orchestrator import ProjectOrchestrator


logger = logging.getLogger(__name__)


def register_optimization_tools(mcp, db_manager=None):
    """Register Serena optimization control tools with MCP server"""

    if db_manager is None:
        db_manager = get_db_manager()

    orchestrator = ProjectOrchestrator()

    @mcp.tool()
    async def get_optimization_settings(project_id: str, tenant_key: str) -> Dict[str, Any]:
        """
        Get current optimization settings and rules for a project.

        Args:
            project_id: Project UUID to get settings for
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict containing current optimization rules and settings
        """
        try:
            # Get SerenaOptimizer for tenant
            optimizer = SerenaOptimizer(db_manager, tenant_key)

            # Get current rules
            rules = await optimizer.get_optimization_rules()

            # Format rules for display
            formatted_rules = {}
            for operation_type, rule in rules.items():
                formatted_rules[operation_type.value] = {
                    "max_answer_chars": rule.max_answer_chars,
                    "prefer_symbolic": rule.prefer_symbolic,
                    "guidance": rule.guidance,
                    "context_filter": rule.context_filter,
                }

            return {
                "project_id": project_id,
                "tenant_key": tenant_key,
                "optimization_rules": formatted_rules,
                "total_rules": len(formatted_rules),
                "system_status": "active",
            }

        except Exception as e:
            logger.error(f"Failed to get optimization settings: {e}")
            return {"error": str(e), "project_id": project_id, "system_status": "error"}

    @mcp.tool()
    async def update_optimization_rules(
        project_id: str,
        tenant_key: str,
        operation_type: str,
        max_answer_chars: int,
        prefer_symbolic: bool = True,
        guidance: str = "",
        context_filter: str = None,
    ) -> Dict[str, Any]:
        """
        Update specific optimization rule for a project.

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            operation_type: Type of operation (file_read, symbol_search, etc.)
            max_answer_chars: Maximum character limit for responses
            prefer_symbolic: Whether to prefer symbolic operations
            guidance: Guidance text for the rule
            context_filter: Optional context filter for when to apply rule

        Returns:
            Dict with update status and new rule configuration
        """
        try:
            # Validate operation type
            valid_operations = ["file_read", "symbol_search", "symbol_replace", "pattern_search", "directory_list"]
            if operation_type not in valid_operations:
                return {
                    "error": f"Invalid operation type. Must be one of: {valid_operations}",
                    "project_id": project_id,
                }

            # Update rule in database
            async with db_manager.get_session_async() as session:
                # Check if rule exists
                from sqlalchemy import select

                from ..models import OptimizationRule as OptimizationRuleModel

                result = await session.execute(
                    select(OptimizationRuleModel).where(
                        OptimizationRuleModel.tenant_key == tenant_key,
                        OptimizationRuleModel.operation_type == operation_type,
                    )
                )

                existing_rule = result.scalar_one_or_none()

                if existing_rule:
                    # Update existing rule
                    existing_rule.max_answer_chars = max_answer_chars
                    existing_rule.prefer_symbolic = prefer_symbolic
                    existing_rule.guidance = guidance or existing_rule.guidance
                    existing_rule.context_filter = context_filter
                else:
                    # Create new rule
                    new_rule = OptimizationRuleModel(
                        tenant_key=tenant_key,
                        operation_type=operation_type,
                        max_answer_chars=max_answer_chars,
                        prefer_symbolic=prefer_symbolic,
                        guidance=guidance or f"Optimized rule for {operation_type}",
                        context_filter=context_filter,
                        is_active=True,
                    )
                    session.add(new_rule)

                await session.commit()

                return {
                    "project_id": project_id,
                    "operation_type": operation_type,
                    "updated": True,
                    "rule": {
                        "max_answer_chars": max_answer_chars,
                        "prefer_symbolic": prefer_symbolic,
                        "guidance": guidance,
                        "context_filter": context_filter,
                    },
                }

        except Exception as e:
            logger.error(f"Failed to update optimization rule: {e}")
            return {"error": str(e), "project_id": project_id, "updated": False}

    @mcp.tool()
    async def get_token_savings_report(project_id: str) -> Dict[str, Any]:
        """
        Get comprehensive token savings report for a project.

        Args:
            project_id: Project UUID to generate report for

        Returns:
            Dict with detailed token savings analytics
        """
        try:
            # Get optimization report from orchestrator
            report = await orchestrator.get_optimization_report(project_id)

            # Add summary statistics
            optimization_summary = report.get("optimization_summary", {})
            total_tokens_saved = optimization_summary.get("total_tokens_saved", 0)
            total_operations = optimization_summary.get("total_operations", 0)

            report["analytics"] = {
                "avg_tokens_saved_per_operation": (
                    total_tokens_saved / total_operations if total_operations > 0 else 0
                ),
                "optimization_effectiveness": "high"
                if total_tokens_saved > 10000
                else "medium"
                if total_tokens_saved > 1000
                else "low",
                "recommendation": _get_savings_recommendation(optimization_summary),
            }

            return report

        except Exception as e:
            logger.error(f"Failed to generate token savings report: {e}")
            return {"error": str(e), "project_id": project_id, "report_generated": False}

    @mcp.tool()
    async def estimate_optimization_impact(project_id: str, agent_role: str) -> Dict[str, Any]:
        """
        Estimate optimization impact before spawning an agent.

        Args:
            project_id: Project UUID
            agent_role: Role of agent to estimate impact for

        Returns:
            Dict with estimated optimization benefits
        """
        try:
            # Get impact estimate from orchestrator
            impact = await orchestrator.estimate_optimization_impact(project_id, agent_role)

            return impact

        except Exception as e:
            logger.error(f"Failed to estimate optimization impact: {e}")
            return {"error": str(e), "project_id": project_id, "agent_role": agent_role, "estimate_available": False}

    @mcp.tool()
    async def force_agent_handoff(
        agent_id: str, reason: str = "Manual handoff requested", target_agent_role: str = "orchestrator"
    ) -> Dict[str, Any]:
        """
        Force agent handoff due to context limits or other issues.

        Args:
            agent_id: Agent UUID to hand off from
            reason: Reason for the handoff
            target_agent_role: Role of target agent to hand off to

        Returns:
            Dict with handoff status and details
        """
        try:
            # Get agent details
            async with db_manager.get_session_async() as session:
                from sqlalchemy import select

                from ..models import Agent

                result = await session.execute(select(Agent).where(Agent.id == agent_id))
                agent = result.scalar_one_or_none()

                if not agent:
                    return {"error": f"Agent {agent_id} not found", "handoff_completed": False}

                # Check if handoff is needed
                needs_handoff, auto_reason = await orchestrator.check_handoff_needed(agent_id)

                # Create handoff context
                handoff_context = {
                    "summary": f"Handoff requested: {reason}",
                    "context_used": agent.context_used,
                    "agent_role": agent.role,
                    "forced": True,
                    "reason": reason or auto_reason,
                }

                # Find or create target agent
                target_agents = await session.execute(
                    select(Agent).where(
                        Agent.project_id == agent.project_id,
                        Agent.role == target_agent_role,
                        Agent.status.in_(["active", "idle"]),
                    )
                )
                target_agent = target_agents.scalar_one_or_none()

                if not target_agent:
                    # Spawn new target agent
                    from ..enums import AgentRole

                    target_agent = await orchestrator.spawn_agent(
                        project_id=agent.project_id, role=AgentRole(target_agent_role)
                    )

                # Perform handoff
                handoff_message = await orchestrator.handoff(
                    from_agent_id=agent_id, to_agent_id=target_agent.id, context=handoff_context
                )

                return {
                    "agent_id": agent_id,
                    "target_agent_id": target_agent.id,
                    "target_agent_role": target_agent_role,
                    "handoff_completed": True,
                    "handoff_message_id": handoff_message.id,
                    "reason": reason,
                    "context_used": agent.context_used,
                }

        except Exception as e:
            logger.error(f"Failed to force agent handoff: {e}")
            return {"error": str(e), "agent_id": agent_id, "handoff_completed": False}

    @mcp.tool()
    async def get_optimization_status(tenant_key: str) -> Dict[str, Any]:
        """
        Get overall optimization system status for a tenant.

        Args:
            tenant_key: Tenant key to check status for

        Returns:
            Dict with system status and health metrics
        """
        try:
            # Get optimizer
            optimizer = SerenaOptimizer(db_manager, tenant_key)

            # Get current rules
            rules = await optimizer.get_optimization_rules()

            # Get recent optimization metrics
            async with db_manager.get_session_async() as session:
                from sqlalchemy import func, select

                from ..models import OptimizationMetric

                # Get metrics from last 24 hours
                recent_metrics = await session.execute(
                    select(
                        func.count(OptimizationMetric.id).label("total_operations"),
                        func.sum(OptimizationMetric.tokens_saved).label("total_tokens_saved"),
                        func.avg(OptimizationMetric.tokens_saved).label("avg_tokens_saved"),
                    ).where(
                        OptimizationMetric.tenant_key == tenant_key,
                        OptimizationMetric.created_at >= func.now() - func.make_interval(0, 0, 0, 1),  # 24 hours
                    )
                )

                metrics_row = recent_metrics.first()

                return {
                    "tenant_key": tenant_key,
                    "system_status": "operational",
                    "rules_configured": len(rules),
                    "recent_24h_metrics": {
                        "total_operations": metrics_row.total_operations or 0,
                        "total_tokens_saved": int(metrics_row.total_tokens_saved or 0),
                        "avg_tokens_saved": round(float(metrics_row.avg_tokens_saved or 0), 2),
                    },
                    "optimization_active": True,
                    "last_checked": _get_current_timestamp(),
                }

        except Exception as e:
            logger.error(f"Failed to get optimization status: {e}")
            return {"error": str(e), "tenant_key": tenant_key, "system_status": "error"}


def _get_savings_recommendation(summary: Dict[str, Any]) -> str:
    """Generate recommendation based on savings summary"""

    total_saved = summary.get("total_tokens_saved", 0)
    savings_percent = summary.get("estimated_context_savings_percent", 0)

    if total_saved > 50000 and savings_percent > 70:
        return "Excellent optimization - system performing at target efficiency"
    if total_saved > 10000 and savings_percent > 50:
        return "Good optimization - consider adjusting rules for better performance"
    return "Low optimization - review rules and agent usage patterns"


def _get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
