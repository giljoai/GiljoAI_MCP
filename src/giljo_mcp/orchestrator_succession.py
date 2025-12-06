"""
Orchestrator Succession Manager for GiljoAI MCP Server.

Handover 0080: Manages orchestrator succession lifecycle for unlimited project duration.

Responsibilities:
- Context threshold detection (90% trigger point)
- Successor orchestrator creation with instance numbering
- Handover summary generation with compression (<10K tokens target)
- State transfer between orchestrator instances
- Multi-tenant isolation enforcement

Valid succession reasons:
- context_limit: Context usage >= 90% of budget
- manual: User-requested handover
- phase_transition: Project phase change
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from .models import MCPAgentJob


logger = logging.getLogger(__name__)


# ============================================================================
# Context Monitoring Utilities
# ============================================================================


def calculate_context_usage(orchestrator: MCPAgentJob) -> tuple[int, int]:
    """
    Calculate context window usage for an orchestrator.

    For now: Returns (context_used, context_budget) from job record.
    Future: Integrate with actual LLM token counting via API.

    Args:
        orchestrator: MCPAgentJob instance (must be orchestrator type)

    Returns:
        Tuple of (context_used, context_budget) in tokens

    Example:
        >>> used, budget = calculate_context_usage(orchestrator)
        >>> percentage = (used / budget) * 100
        >>> print(f"Context usage: {percentage:.1f}%")
    """
    return (orchestrator.context_used, orchestrator.context_budget)


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
        orchestrator: MCPAgentJob,
        manual_request: bool = False,
    ) -> bool:
        """
        Check if orchestrator should trigger succession.

        Triggers when:
        - Context usage >= 90% of context budget
        - OR manual handover requested (manual_request=True)

        Args:
            orchestrator: MCPAgentJob instance to check
            manual_request: True if manual succession requested

        Returns:
            True if succession should be triggered, False otherwise

        Example:
            >>> if manager.should_trigger_succession(orchestrator):
            >>>     print("Succession threshold reached!")
        """
        # Manual request always triggers
        if manual_request:
            return True

        # Calculate context usage percentage
        used, budget = calculate_context_usage(orchestrator)

        # Avoid division by zero
        if budget == 0:
            logger.warning(f"Orchestrator {orchestrator.job_id} has zero context budget")
            return False

        usage_percentage = used / budget

        # Trigger if >= 90% threshold
        return usage_percentage >= self.CONTEXT_THRESHOLD

    def create_successor(
        self,
        orchestrator: MCPAgentJob,
        reason: str,
    ) -> MCPAgentJob:
        """
        Create successor orchestrator for handover.

        Creates new MCPAgentJob with:
        - Incremented instance_number
        - Fresh context window (context_used = 0)
        - Status = 'waiting' (for manual launch)
        - Same tenant_key and project_id
        - Linkage via spawned_by field
        - Preserved execution_mode from parent (Handover 0247 Gap 4)

        Args:
            orchestrator: Parent orchestrator job
            reason: Succession reason ('context_limit', 'manual', 'phase_transition')

        Returns:
            New MCPAgentJob instance (successor)

        Raises:
            ValueError: If reason is invalid

        Example:
            >>> successor = manager.create_successor(orchestrator, "context_limit")
            >>> print(f"Created successor instance {successor.instance_number}")
        """
        # Validate reason
        if reason not in self.VALID_REASONS:
            raise ValueError(f"Invalid succession reason: {reason}. Must be one of: {', '.join(self.VALID_REASONS)}")

        # Verify tenant isolation
        if orchestrator.tenant_key != self.tenant_key:
            raise ValueError(
                f"Tenant mismatch: orchestrator belongs to {orchestrator.tenant_key}, "
                f"manager initialized for {self.tenant_key}"
            )

        # Generate handover mission
        handover_mission = self._generate_handover_mission(orchestrator)

        # Handover 0247 Gap 4: Preserve execution_mode from parent orchestrator
        # Extract execution_mode from parent's job_metadata (default: "multi-terminal")
        parent_metadata = orchestrator.job_metadata or {}
        execution_mode = parent_metadata.get("execution_mode", "multi-terminal")
        
        # Build successor metadata preserving execution_mode and other critical fields
        successor_metadata = {
            "execution_mode": execution_mode,
            "predecessor_id": orchestrator.job_id,
            "succession_reason": reason,
            "field_priorities": parent_metadata.get("field_priorities", {}),
            "depth_config": parent_metadata.get("depth_config", {}),
            "user_id": parent_metadata.get("user_id"),
            "tool": parent_metadata.get("tool", "universal"),
            "created_via": "orchestrator_succession"
        }

        # Create successor job
        successor = MCPAgentJob(
            tenant_key=self.tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission=handover_mission,
            status="waiting",  # Manual launch required
            instance_number=orchestrator.instance_number + 1,
            spawned_by=orchestrator.job_id,
            project_id=orchestrator.project_id,
            context_used=0,  # Fresh context window
            context_budget=orchestrator.context_budget,  # Same budget
            context_chunks=[],  # Will be populated from handover summary
            messages=[],  # Fresh message queue
            job_metadata=successor_metadata,  # Handover 0247 Gap 4: Preserve metadata
        )

        # Add to session and commit
        self.db_session.add(successor)
        self.db_session.commit()
        self.db_session.refresh(successor)

        logger.info(
            f"Created successor orchestrator {successor.job_id} "
            f"(instance {successor.instance_number}) for {orchestrator.job_id}, "
            f"reason: {reason}, execution_mode: {execution_mode}"
        )

        return successor

    def generate_handover_summary(self, orchestrator: MCPAgentJob) -> dict[str, Any]:
        """
        Generate compressed handover summary for successor.

        Compression strategy:
        - Extract only actionable state
        - Reference context chunks (not full text)
        - Summarize completed work (not replay)
        - Highlight pending decisions only
        - Target: <10K tokens for handover

        Returns dict with:
        - project_status: Overall progress percentage
        - active_agents: List of active sub-agents
        - completed_phases: Summary of completed work
        - pending_decisions: Open questions requiring attention
        - critical_context_refs: Context chunk IDs to load
        - message_count: Number of messages in history
        - unresolved_blockers: Current blocking issues
        - next_steps: Recommended next actions

        Args:
            orchestrator: Orchestrator job to summarize

        Returns:
            Compressed handover summary dict

        Example:
            >>> summary = manager.generate_handover_summary(orchestrator)
            >>> print(f"Project status: {summary['project_status']}")
            >>> print(f"Messages: {summary['message_count']}")
        """
        # Extract messages for analysis
        messages = orchestrator.messages or []
        message_count = len(messages)

        # Extract context chunk references
        critical_context_refs = orchestrator.context_chunks or []

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
            "critical_context_refs": critical_context_refs,
            "message_count": message_count,
            "unresolved_blockers": unresolved_blockers,
            "next_steps": next_steps,
            "instance_number": orchestrator.instance_number,
            "context_usage": {
                "used": orchestrator.context_used,
                "budget": orchestrator.context_budget,
                "percentage": round(
                    (orchestrator.context_used / orchestrator.context_budget * 100)
                    if orchestrator.context_budget > 0
                    else 0,
                    2,
                ),
            },
        }

        # Log summary size (rough token estimate)
        summary_str = json.dumps(summary)
        estimated_tokens = len(summary_str) / 4  # Rough approximation

        logger.info(
            f"Generated handover summary for {orchestrator.job_id}: "
            f"~{estimated_tokens:.0f} tokens, {message_count} messages"
        )

        return summary

    def complete_handover(
        self,
        orchestrator: MCPAgentJob,
        successor: MCPAgentJob,
        handover_summary: dict[str, Any],
        reason: str = "context_limit",
    ) -> None:
        """
        Complete handover from orchestrator to successor.

        Updates orchestrator job:
        - Status → 'complete'
        - handover_to → successor.job_id
        - handover_summary → compressed summary
        - handover_context_refs → context chunk IDs
        - succession_reason → reason code
        - completed_at → current timestamp

        Args:
            orchestrator: Parent orchestrator job
            successor: Successor orchestrator job
            handover_summary: Generated handover summary
            reason: Succession reason (default: 'context_limit')

        Raises:
            ValueError: If reason is invalid

        Example:
            >>> manager.complete_handover(orchestrator, successor, summary, "manual")
            >>> print(f"Handover complete: {orchestrator.job_id} → {successor.job_id}")
        """
        # Validate reason
        if reason not in self.VALID_REASONS:
            raise ValueError(f"Invalid succession reason: {reason}. Must be one of: {', '.join(self.VALID_REASONS)}")

        # Update orchestrator job
        orchestrator.status = "complete"
        orchestrator.handover_to = successor.job_id
        orchestrator.handover_summary = handover_summary
        orchestrator.handover_context_refs = handover_summary.get("critical_context_refs", [])
        orchestrator.succession_reason = reason
        orchestrator.completed_at = datetime.now(timezone.utc)

        # Commit changes
        self.db_session.commit()
        self.db_session.refresh(orchestrator)

        logger.info(
            f"Completed handover: {orchestrator.job_id} (instance {orchestrator.instance_number}) "
            f"→ {successor.job_id} (instance {successor.instance_number}), "
            f"reason: {reason}"
        )

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _generate_handover_mission(self, orchestrator: MCPAgentJob) -> str:
        """
        Generate mission text for successor orchestrator.

        Args:
            orchestrator: Parent orchestrator job

        Returns:
            Mission string for successor
        """
        return (
            f"Continue orchestration from instance {orchestrator.instance_number}.\n\n"
            f"Previous orchestrator reached context capacity. "
            f"Review handover summary and continue project coordination.\n\n"
            f"Original mission:\n{orchestrator.mission}"
        )

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
