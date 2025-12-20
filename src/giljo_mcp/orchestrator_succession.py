"""
Orchestrator Succession Manager for GiljoAI MCP Server.

Handover 0080: Manages orchestrator succession lifecycle for unlimited project duration.
Handover 0366b: Updated to use dual-model architecture (AgentJob + AgentExecution).

Responsibilities:
- Context threshold detection (90% trigger point)
- Successor EXECUTION creation (not new job) with instance numbering
- Handover summary generation with compression (<10K tokens target)
- State transfer between execution instances
- Multi-tenant isolation enforcement

Valid succession reasons:
- context_limit: Context usage >= 90% of budget
- manual: User-requested handover
- phase_transition: Project phase change

Key Change (0366b):
- Succession creates new AgentExecution on SAME job (job_id persists)
- Mission stored in AgentJob (not duplicated in executions)
- Handover summary stored in AgentExecution (execution-specific state)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select

# Handover 0366b: Import dual-model architecture
from .models.agent_identity import AgentJob, AgentExecution
# Keep MCPAgentJob for backward compatibility during migration
from .models import MCPAgentJob


logger = logging.getLogger(__name__)


# ============================================================================
# Context Monitoring Utilities
# ============================================================================


def calculate_context_usage(execution: AgentExecution) -> tuple[int, int]:
    """
    Calculate context window usage for an agent execution.

    Handover 0366b: Now uses AgentExecution (context tracking is executor-specific).

    For now: Returns (context_used, context_budget) from execution record.
    Future: Integrate with actual LLM token counting via API.

    Args:
        execution: AgentExecution instance (executor context tracking)

    Returns:
        Tuple of (context_used, context_budget) in tokens

    Example:
        >>> used, budget = calculate_context_usage(execution)
        >>> percentage = (used / budget) * 100
        >>> print(f"Context usage: {percentage:.1f}%")
    """
    return (execution.context_used, execution.context_budget)


# ============================================================================
# Orchestrator Succession Manager
# ============================================================================


class OrchestratorSuccessionManager:
    """
    Manages orchestrator succession lifecycle with multi-tenant isolation.

    Handles:
    - Context threshold detection
    - Successor creation with instance numbering
    - Handover summary generation and compression
    - State transfer between instances
    - Multi-tenant isolation enforcement

    Usage:
        >>> with db_manager.get_session() as session:
        >>>     manager = OrchestratorSuccessionManager(session, tenant_key)
        >>>
        >>>     # Check if succession needed
        >>>     if manager.should_trigger_succession(orchestrator):
        >>>         # Create successor
        >>>         successor = manager.create_successor(orchestrator, "context_limit")
        >>>
        >>>         # Generate handover summary
        >>>         summary = manager.generate_handover_summary(orchestrator)
        >>>
        >>>         # Complete handover
        >>>         manager.complete_handover(orchestrator, successor, summary)
    """

    # Context usage threshold for automatic succession (90%)
    CONTEXT_THRESHOLD = 0.90

    # Valid succession reasons
    VALID_REASONS = {"context_limit", "manual", "phase_transition"}

    def __init__(self, db_session: Session, tenant_key: str):
        """
        Initialize OrchestratorSuccessionManager.

        Args:
            db_session: SQLAlchemy session for database operations
            tenant_key: Tenant key for multi-tenant isolation
        """
        self.db_session = db_session
        self.tenant_key = tenant_key

    def should_trigger_succession(
        self,
        execution: AgentExecution,
        manual_request: bool = False,
    ) -> bool:
        """
        Check if execution should trigger succession.

        Handover 0366b: Now checks AgentExecution (context is executor-specific).

        Triggers when:
        - Context usage >= 90% of context budget
        - OR manual handover requested (manual_request=True)

        Args:
            execution: AgentExecution instance to check
            manual_request: True if manual succession requested

        Returns:
            True if succession should be triggered, False otherwise

        Example:
            >>> if manager.should_trigger_succession(execution):
            >>>     print("Succession threshold reached!")
        """
        # Manual request always triggers
        if manual_request:
            return True

        # Calculate context usage percentage
        used, budget = calculate_context_usage(execution)

        # Avoid division by zero
        if budget == 0:
            logger.warning(f"Execution {execution.agent_id} has zero context budget")
            return False

        usage_percentage = used / budget

        # Trigger if >= 90% threshold
        return usage_percentage >= self.CONTEXT_THRESHOLD

    async def create_successor(
        self,
        current_execution: AgentExecution,
        reason: str,
    ) -> AgentExecution:
        """
        Create successor execution for handover.

        Handover 0366b: Creates new AgentExecution on SAME job (not new job).

        Creates new AgentExecution with:
        - SAME job_id (work order persists)
        - NEW agent_id (new executor)
        - Incremented instance_number
        - Fresh context window (context_used = 0)
        - Status = 'waiting' (for manual launch)
        - Linkage via spawned_by/succeeded_by fields

        Args:
            current_execution: Current execution to hand over from
            reason: Succession reason ('context_limit', 'manual', 'phase_transition')

        Returns:
            New AgentExecution instance (successor)

        Raises:
            ValueError: If reason is invalid

        Example:
            >>> successor = await manager.create_successor(current_execution, "context_limit")
            >>> print(f"Created successor instance {successor.instance_number}")
        """
        # Validate reason
        if reason not in self.VALID_REASONS:
            raise ValueError(f"Invalid succession reason: {reason}. Must be one of: {', '.join(self.VALID_REASONS)}")

        # Verify tenant isolation
        if current_execution.tenant_key != self.tenant_key:
            raise ValueError(
                f"Tenant mismatch: execution belongs to {current_execution.tenant_key}, "
                f"manager initialized for {self.tenant_key}"
            )

        # Get parent job (via relationship or query)
        if hasattr(current_execution, 'job') and current_execution.job is not None:
            job = current_execution.job
        else:
            # Load job if not already loaded
            result = await self.db_session.execute(
                select(AgentJob).where(AgentJob.job_id == current_execution.job_id)
            )
            job = result.scalar_one()

        # Create NEW execution on SAME job
        successor_execution = AgentExecution(
            agent_id=str(uuid4()),  # New executor ID
            job_id=job.job_id,  # SAME work order
            tenant_key=self.tenant_key,
            agent_type=current_execution.agent_type,
            instance_number=current_execution.instance_number + 1,
            status="waiting",  # Manual launch required
            spawned_by=current_execution.agent_id,  # Points to agent, not job
            context_used=0,  # Fresh context window
            context_budget=current_execution.context_budget,  # Same budget
            tool_type=current_execution.tool_type,  # Preserve tool assignment
        )

        # Update current execution succession chain
        current_execution.succeeded_by = successor_execution.agent_id
        current_execution.succession_reason = reason
        current_execution.status = "complete"  # Mark current as complete
        current_execution.completed_at = datetime.now(timezone.utc)

        # Add to session and commit
        self.db_session.add(successor_execution)
        await self.db_session.commit()
        await self.db_session.refresh(successor_execution)

        logger.info(
            f"Created successor execution {successor_execution.agent_id} "
            f"(instance {successor_execution.instance_number}) for {current_execution.agent_id}, "
            f"job_id: {job.job_id}, reason: {reason}"
        )

        return successor_execution

    def generate_handover_summary(self, execution: AgentExecution) -> dict[str, Any]:
        """
        Generate compressed handover summary for successor.

        Handover 0366b: Now generates summary from AgentExecution (execution-specific state).

        Compression strategy:
        - Extract only actionable state
        - Summarize completed work (not replay)
        - Highlight pending decisions only
        - Target: <10K tokens for handover

        Returns dict with:
        - project_status: Overall progress percentage
        - active_agents: List of active sub-agents
        - completed_phases: Summary of completed work
        - pending_decisions: Open questions requiring attention
        - message_count: Number of messages in history
        - unresolved_blockers: Current blocking issues
        - next_steps: Recommended next actions

        Args:
            execution: AgentExecution to summarize

        Returns:
            Compressed handover summary dict

        Example:
            >>> summary = manager.generate_handover_summary(execution)
            >>> print(f"Project status: {summary['project_status']}")
            >>> print(f"Messages: {summary['message_count']}")
        """
        # Extract messages for analysis
        messages = execution.messages or []
        message_count = len(messages)

        # Analyze message history for project status
        # (Simple implementation - can be enhanced with NLP)
        project_status = self._estimate_project_status(messages)
        active_agents = self._extract_active_agents(messages)
        completed_phases = self._extract_completed_phases(messages)
        pending_decisions = self._extract_pending_decisions(messages)
        unresolved_blockers = self._extract_blockers(messages)
        next_steps = self._generate_next_steps(messages)

        # Build compressed summary
        summary = {
            "project_status": project_status,
            "active_agents": active_agents,
            "completed_phases": completed_phases,
            "pending_decisions": pending_decisions,
            "message_count": message_count,
            "unresolved_blockers": unresolved_blockers,
            "next_steps": next_steps,
            "instance_number": execution.instance_number,
            "context_usage": {
                "used": execution.context_used,
                "budget": execution.context_budget,
                "percentage": round(
                    (execution.context_used / execution.context_budget * 100)
                    if execution.context_budget > 0
                    else 0,
                    2,
                ),
            },
        }

        # Log summary size (rough token estimate)
        summary_str = json.dumps(summary)
        estimated_tokens = len(summary_str) / 4  # Rough approximation

        logger.info(
            f"Generated handover summary for execution {execution.agent_id}: "
            f"~{estimated_tokens:.0f} tokens, {message_count} messages"
        )

        return summary

    async def complete_handover(
        self,
        current_execution: AgentExecution,
        successor_execution: AgentExecution,
        handover_summary: dict[str, Any],
        reason: str = "context_limit",
    ) -> None:
        """
        Complete handover from current execution to successor.

        Handover 0366b: Stores handover summary in AgentExecution (execution-specific state).

        Updates current execution:
        - Status → 'complete'
        - succeeded_by → successor.agent_id
        - handover_summary → compressed summary (JSONB field)
        - succession_reason → reason code
        - completed_at → current timestamp

        Args:
            current_execution: Current execution handing over
            successor_execution: Successor execution taking over
            handover_summary: Generated handover summary
            reason: Succession reason (default: 'context_limit')

        Raises:
            ValueError: If reason is invalid

        Example:
            >>> await manager.complete_handover(current_exec, successor_exec, summary, "manual")
            >>> print(f"Handover complete: {current_exec.agent_id} → {successor_exec.agent_id}")
        """
        # Validate reason
        if reason not in self.VALID_REASONS:
            raise ValueError(f"Invalid succession reason: {reason}. Must be one of: {', '.join(self.VALID_REASONS)}")

        # Update current execution
        current_execution.status = "complete"
        current_execution.succeeded_by = successor_execution.agent_id
        current_execution.handover_summary = handover_summary
        current_execution.succession_reason = reason
        current_execution.completed_at = datetime.now(timezone.utc)

        # Commit changes
        await self.db_session.commit()
        await self.db_session.refresh(current_execution)

        logger.info(
            f"Completed handover: {current_execution.agent_id} (instance {current_execution.instance_number}) "
            f"→ {successor_execution.agent_id} (instance {successor_execution.instance_number}), "
            f"job_id: {current_execution.job_id}, reason: {reason}"
        )

    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    # Note: _generate_handover_mission() removed (Handover 0366b)
    # Mission is stored in AgentJob and shared by all executions (no regeneration needed)

    def _estimate_project_status(self, messages: list[dict]) -> str:
        """
        Estimate project completion status from messages.

        Simple heuristic implementation - can be enhanced with NLP.

        Args:
            messages: List of message dicts

        Returns:
            Status string (e.g., "60% complete", "early phase", "in progress")
        """
        if not messages:
            return "0% complete - project starting"

        # Look for status messages
        status_messages = [msg for msg in messages if msg.get("type") in ["status", "progress"]]

        if status_messages:
            # Try to extract percentage from latest status
            latest = status_messages[-1]
            content = latest.get("content", "")

            # Simple percentage extraction
            if "%" in content:
                try:
                    # Extract first percentage found
                    import re

                    match = re.search(r"(\d+)%", content)
                    if match:
                        return f"{match.group(1)}% complete"
                except Exception:
                    pass

        # Fallback: estimate based on message count
        message_count = len(messages)
        if message_count < 10:
            return "Early phase"
        if message_count < 50:
            return "In progress"
        return "Advanced phase"

    def _extract_active_agents(self, messages: list[dict]) -> list[dict]:
        """
        Extract active sub-agents from message history.

        Args:
            messages: List of message dicts

        Returns:
            List of active agent dicts
        """
        # Look for agent-related messages
        agent_messages = [msg for msg in messages if msg.get("type") in ["agent_spawn", "agent_status", "agent_update"]]

        # Extract unique agents (simplified - can be enhanced)
        active_agents = []
        seen_agents = set()

        for msg in reversed(agent_messages):  # Latest first
            if "agent_id" in msg and msg["agent_id"] not in seen_agents:
                seen_agents.add(msg["agent_id"])
                active_agents.append(
                    {
                        "job_id": msg.get("agent_id"),
                        "type": msg.get("agent_type", "unknown"),
                        "status": msg.get("status", "unknown"),
                    }
                )

        return active_agents

    def _extract_completed_phases(self, messages: list[dict]) -> list[str]:
        """
        Extract completed project phases from messages.

        Args:
            messages: List of message dicts

        Returns:
            List of completed phase names
        """
        completed = []

        # Look for completion messages
        for msg in messages:
            msg_type = msg.get("type", "")
            content = msg.get("content", "").lower()

            if msg_type == "phase_complete" or "complete" in content:
                # Extract phase name (simplified)
                phase_name = msg.get("phase", "unknown phase")
                if phase_name not in completed:
                    completed.append(phase_name)

        return completed

    def _extract_pending_decisions(self, messages: list[dict]) -> list[str]:
        """
        Extract pending decisions from messages.

        Args:
            messages: List of message dicts

        Returns:
            List of pending decision strings
        """
        pending = []

        # Look for decision/question messages
        for msg in messages:
            msg_type = msg.get("type", "")
            content = msg.get("content", "")

            if msg_type in ["decision", "question", "pending"] or "?" in content:
                if content and content not in pending:
                    pending.append(content)

        return pending[:10]  # Limit to top 10 most recent

    def _extract_blockers(self, messages: list[dict]) -> list[str]:
        """
        Extract unresolved blockers from messages.

        Args:
            messages: List of message dicts

        Returns:
            List of blocker strings
        """
        blockers = []

        # Look for blocker messages
        for msg in messages:
            msg_type = msg.get("type", "")

            if msg_type == "blocker":
                content = msg.get("content", "")
                if content and content not in blockers:
                    blockers.append(content)

        return blockers

    def _generate_next_steps(self, messages: list[dict]) -> str:
        """
        Generate recommended next steps from message history.

        Args:
            messages: List of message dicts

        Returns:
            Next steps string
        """
        if not messages:
            return "Review project vision and begin initial planning"

        # Look for latest planning/status messages
        recent_messages = messages[-10:]  # Last 10 messages

        # Extract next steps from messages
        for msg in reversed(recent_messages):
            if msg.get("type") in ["next_steps", "plan", "action"]:
                return msg.get("content", "Continue with current workflow")

        # Default fallback
        return "Continue with current workflow and agent coordination"
