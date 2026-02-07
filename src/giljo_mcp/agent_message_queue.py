"""
INTERNAL/LEGACY: Agent Message Queue System

WARNING: This module is INTERNAL. The primary messaging implementation is MessageService.
This queue abstraction is retained for:
- Legacy orchestrator code compatibility
- JSONB counter persistence (Job.messages field)
- Internal debugging and testing

New code should use MessageService directly, not this queue.

See Handover 0295 for the canonical messaging contract.
See Handover 0298 for cleanup decisions.
See Handover 0334 for HTTP-only MCP consolidation.

Original Purpose (Handover 0120):
Provides ACID-compliant, priority-based message queue with intelligent routing.
Consolidates AgentCommunicationQueue functionality with advanced features.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select, update

from .database import DatabaseManager

# Import from centralized exceptions
from .exceptions import ConsistencyError, QueueException
from .models import Message
from .models.agent_identity import AgentExecution, AgentJob
from .tenant import TenantManager


logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels with weights"""

    CRITICAL = 1000
    HIGH = 100
    NORMAL = 10
    LOW = 1


class AgentMessageQueue:
    """
    High-performance message queue manager with priority routing and ACID guarantees.

    Handover 0120: Consolidated from AgentCommunicationQueue and MessageQueue.
    Provides both compatibility layer methods and advanced features.
    """

    def __init__(self, db_manager: DatabaseManager, tenant_manager: Optional[TenantManager] = None):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._routing_engine = RoutingEngine()
        self._monitor = QueueMonitor()
        self._dead_letter_queue = DeadLetterQueue(db_manager)
        self._stuck_detector = StuckMessageDetector(db_manager)
        self._durability_manager = DurabilityManager(db_manager)
        self._isolation_manager = IsolationManager()

        # Configuration
        self._batch_size = 10
        self._max_retries = 3
        self._default_timeout = 300  # 5 minutes

        # Priority weights
        self.priority_weights = {
            "critical": MessagePriority.CRITICAL.value,
            "high": MessagePriority.HIGH.value,
            "normal": MessagePriority.NORMAL.value,
            "low": MessagePriority.LOW.value,
        }

        logger.info("AgentMessageQueue initialized")

    async def enqueue(self, message: Message) -> str:
        """
        Add message to queue with transaction and monitoring.

        Args:
            message: Message to enqueue

        Returns:
            Message ID
        """
        try:
            # Write-ahead logging for durability
            await self._durability_manager.persist_with_wal(message)

            # Record metrics
            await self._monitor.record_enqueue(message)

            logger.info(f"Enqueued message {message.id} with priority {message.priority}")
            return str(message.id)

        except Exception as e:
            logger.exception(f"Failed to enqueue message: {e}")
            raise QueueException(f"Enqueue failed: {e}") from e

    async def dequeue(self, agent_name: str, batch_size: Optional[int] = None) -> list[Message]:
        """
        Retrieve messages for agent based on priority and routing rules.

        Args:
            agent_name: Name of the agent requesting messages
            batch_size: Number of messages to retrieve (default: self._batch_size)

        Returns:
            List of messages for the agent
        """
        if batch_size is None:
            batch_size = self._batch_size

        async with self.db_manager.get_session_async() as session:
            try:
                # Start transaction
                await session.begin()

                # Get messages for this agent ordered by priority
                # Using FOR UPDATE to lock rows
                stmt = (
                    select(Message)
                    .where(
                        and_(
                            Message.status == "pending",
                            Message.to_agents.contains([agent_name]),
                        )
                    )
                    .order_by(Message.priority.desc(), Message.created_at)
                    .limit(batch_size)
                    .with_for_update()
                )

                result = await session.execute(stmt)
                messages = result.scalars().all()

                # Update status to processing
                for message in messages:
                    message.status = "processing"
                    message.meta_data = message.meta_data or {}
                    message.meta_data["processing_started_at"] = datetime.now(timezone.utc).isoformat()
                    message.meta_data["processing_agent"] = agent_name

                    # Record dequeue metrics
                    await self._monitor.record_dequeue(message, agent_name)

                # Commit transaction
                await session.commit()

                logger.info(f"Dequeued {len(messages)} messages for agent {agent_name}")
                return messages

            except Exception as e:
                await session.rollback()
                logger.exception(f"Failed to dequeue messages: {e}")
                raise QueueException(f"Dequeue failed: {e}") from e

    async def process_message(self, message_id: str, agent_name: str) -> bool:
        """
        Mark message as being processed by an agent.

        Args:
            message_id: ID of the message
            agent_name: Name of the processing agent

        Returns:
            True if successful
        """
        async with self.db_manager.get_session_async() as session:
            try:
                await session.begin()

                # Get and lock the message
                stmt = select(Message).where(Message.id == message_id).with_for_update()
                result = await session.execute(stmt)
                message = result.scalar_one_or_none()

                if not message:
                    raise QueueException(f"Message {message_id} not found")

                # Validate state transition
                if message.status not in ["pending", "acknowledged"]:
                    raise ConsistencyError(f"Invalid state transition from {message.status}")

                # Update message
                message.status = "processing"
                message.meta_data = message.meta_data or {}
                message.meta_data["processing_started_at"] = datetime.now(timezone.utc).isoformat()
                message.meta_data["processing_agent"] = agent_name

                # Record processing time
                await self._monitor.record_processing_start(message_id, agent_name)

                await session.commit()
                return True

            except Exception as e:
                await session.rollback()
                logger.exception(f"Failed to process message: {e}")
                return False

    async def detect_stuck_messages(self, timeout_seconds: Optional[int] = None) -> list[Message]:
        """
        Find messages that have been processing too long.

        Args:
            timeout_seconds: Timeout threshold (default: self._default_timeout)

        Returns:
            List of stuck messages
        """
        if timeout_seconds is None:
            timeout_seconds = self._default_timeout

        return await self._stuck_detector.detect_stuck_messages(timeout_seconds)

    async def retry_message(self, message_id: str, reason: str = "") -> bool:
        """
        Retry a failed message with exponential backoff.

        Args:
            message_id: ID of the message to retry
            reason: Reason for retry

        Returns:
            True if message was retried, False if moved to DLQ
        """
        async with self.db_manager.get_session_async() as session:
            try:
                await session.begin()

                # Get the message
                stmt = select(Message).where(Message.id == message_id).with_for_update()
                result = await session.execute(stmt)
                message = result.scalar_one_or_none()

                if not message:
                    return False

                # Check retry count
                message.meta_data = message.meta_data or {}
                retry_count = message.meta_data.get("retry_count", 0)

                if retry_count >= self._max_retries:
                    # Move to DLQ
                    await self._dead_letter_queue.add_message(message, f"Max retries exceeded: {reason}")
                    await session.commit()
                    return False

                # Calculate backoff
                backoff_seconds = (2**retry_count) * 60  # Exponential backoff
                retry_after = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)

                # Update message for retry
                message.status = "pending"
                message.meta_data["retry_count"] = retry_count + 1
                message.meta_data["retry_reason"] = reason
                message.meta_data["retry_after"] = retry_after.isoformat()
                message.meta_data["last_retry_at"] = datetime.now(timezone.utc).isoformat()

                await session.commit()

                logger.info(f"Message {message_id} scheduled for retry #{retry_count + 1}")
                return True

            except Exception as e:
                await session.rollback()
                logger.exception(f"Failed to retry message: {e}")
                return False

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive queue statistics.

        Returns:
            Dictionary of queue metrics
        """
        stats = await self._monitor.get_statistics()

        # Add stuck message count
        stuck_messages = await self.detect_stuck_messages()
        stats["stuck_count"] = len(stuck_messages)

        # Add DLQ size
        stats["dlq_count"] = await self._dead_letter_queue.get_size()

        return stats

    async def recover_from_crash(self):
        """
        Recover queue state after a crash.
        """
        logger.info("Starting crash recovery...")

        async with self.db_manager.get_session_async() as session:
            try:
                await session.begin()

                # Reset all 'processing' messages to 'pending'
                stmt = (
                    update(Message)
                    .where(Message.status == "processing")
                    .values(
                        status="pending",
                        meta_data=func.json_set(Message.meta_data, "$.recovered_from_crash", True),
                    )
                )
                result = await session.execute(stmt)
                recovered_count = result.rowcount

                await session.commit()

                logger.info(f"Recovered {recovered_count} messages from processing state")

                # Recover from WAL
                await self._durability_manager.recover_from_crash()

                # Rebuild metrics
                await self._monitor.rebuild_metrics()

                logger.info("Crash recovery completed")

            except Exception as e:
                await session.rollback()
                logger.exception(f"Crash recovery failed: {e}")
                raise QueueException(f"Recovery failed: {e}") from e

    async def checkpoint(self):
        """
        Create a recovery checkpoint.
        """
        await self._durability_manager.checkpoint()
        await self._monitor.persist_metrics()
        logger.info("Checkpoint created")

    # ==================================================================================
    # COMPATIBILITY LAYER - AgentCommunicationQueue API
    # ==================================================================================
    # The following methods provide backward compatibility with AgentCommunicationQueue
    # to enable gradual migration of existing code. These methods:
    # - Accept same parameters as AgentCommunicationQueue
    # - Return dict responses {"status": "success"/"error", ...} instead of raising exceptions
    # - Link messages to jobs via project_id
    # - Map integer priorities (0, 1, 2) to string priorities ("low", "normal", "high")
    # ==================================================================================

    async def send_message(
        self,
        session: Any,  # AsyncSession
        job_id: str,
        tenant_key: str,
        from_agent: str,
        to_agent: Optional[str],
        message_type: str,
        content: str,
        priority: int = 1,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Send a message (AgentCommunicationQueue compatibility).

        Args:
            session: Database session (AsyncSession)
            job_id: Job ID to send message to
            tenant_key: Tenant key for isolation
            from_agent: Agent sending the message
            to_agent: Agent receiving the message (None for broadcast)
            message_type: Type of message (task, info, error, etc.)
            content: Message content
            priority: Message priority (0=low, 1=normal, 2=high)
            metadata: Optional metadata dict

        Returns:
            Dict with status and message_id or error:
            - Success: {"status": "success", "message_id": str}
            - Error: {"status": "error", "error": str}
        """
        try:
            # Validate priority
            if priority not in [0, 1, 2]:
                return {"status": "error", "error": "Priority must be 0 (low), 1 (normal), or 2 (high)"}

            # Validate content
            if not content or not content.strip():
                return {"status": "error", "error": "Message content cannot be empty"}

            # Map integer priority to string
            priority_map = {0: "low", 1: "normal", 2: "high"}
            priority_str = priority_map[priority]

            # Retrieve job to get project_id
            result = await session.execute(select(AgentJob).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Create Message object
            message = Message(
                tenant_key=tenant_key,
                project_id=job.project_id,
                to_agents=[to_agent] if to_agent else [],  # List for consistency
                message_type=message_type,
                content=content,
                priority=priority_str,
                status="pending",
                meta_data=metadata or {},
            )

            # Add metadata to track compatibility layer usage
            message.meta_data["_compat_layer"] = True
            message.meta_data["_job_id"] = job_id
            message.meta_data["_from_agent"] = from_agent

            # Add to session
            session.add(message)
            await session.commit()

            # Record metrics
            await self._monitor.record_enqueue(message)

            logger.info(
                f"[Compat] Sent message {message.id} from {from_agent} to {to_agent or 'broadcast'} "
                f"(job={job_id}, priority={priority_str})"
            )

            return {"status": "success", "message_id": str(message.id)}

        except Exception as e:
            logger.exception(f"[Compat] Failed to send message: {e}")
            return {"status": "error", "error": str(e)}

    async def send_message_batch(
        self, session: Any, job_id: str, tenant_key: str, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Send multiple messages (AgentCommunicationQueue compatibility).

        Args:
            session: Database session
            job_id: Job ID to send messages to
            tenant_key: Tenant key for isolation
            messages: List of message dicts with keys:
                - from_agent: str
                - to_agent: Optional[str]
                - type: str
                - content: str
                - priority: int (0-2)
                - metadata: Optional[dict]

        Returns:
            Dict with status and sent_count or error:
            - Success: {"status": "success", "sent_count": int}
            - Error: {"status": "error", "error": str}
        """
        try:
            # Retrieve job
            result = await session.execute(select(AgentJob).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Priority mapping
            priority_map = {0: "low", 1: "normal", 2: "high"}

            # Create and add all messages
            sent_count = 0
            for msg_data in messages:
                priority_int = msg_data.get("priority", 1)
                priority_str = priority_map.get(priority_int, "normal")

                message = Message(
                    tenant_key=tenant_key,
                    project_id=job.project_id,
                    to_agents=[msg_data.get("to_agent")] if msg_data.get("to_agent") else [],
                    message_type=msg_data.get("type", "direct"),
                    content=msg_data.get("content", ""),
                    priority=priority_str,
                    status="pending",
                    meta_data=msg_data.get("metadata", {}),
                )

                # Add metadata
                message.meta_data["_compat_layer"] = True
                message.meta_data["_job_id"] = job_id

                session.add(message)
                sent_count += 1

                # Record metrics
                await self._monitor.record_enqueue(message)

            await session.commit()

            logger.info(f"[Compat] Sent batch of {sent_count} messages for job {job_id}")

            return {"status": "success", "sent_count": sent_count}

        except Exception as e:
            logger.exception(f"[Compat] Failed to send message batch: {e}")
            return {"status": "error", "error": str(e)}

    async def get_messages(
        self,
        session: Any,
        job_id: str,
        tenant_key: str,
        to_agent: Optional[str] = None,
        message_type: Optional[str] = None,
        unread_only: bool = False,
    ) -> dict[str, Any]:
        """
        Retrieve messages (AgentCommunicationQueue compatibility).

        Args:
            session: Database session
            job_id: Job ID to retrieve messages from
            tenant_key: Tenant key for isolation
            to_agent: Filter by recipient agent
            message_type: Filter by message type
            unread_only: Only return unacknowledged messages

        Returns:
            Dict with status and messages list or error:
            - Success: {"status": "success", "messages": list[dict]}
            - Error: {"status": "error", "error": str}
        """
        try:
            # Retrieve job
            result = await session.execute(select(AgentJob).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Build query
            query = select(Message).where(
                and_(
                    Message.tenant_key == tenant_key,
                    Message.project_id == job.project_id,
                )
            )

            # Apply filters
            if to_agent:
                # Include messages directly to this agent OR broadcast messages
                # Broadcasts use to_agents=['all']
                query = query.where(
                    or_(
                        Message.to_agents.contains([to_agent]),  # Direct messages
                        Message.to_agents.contains(["all"]),  # Broadcast messages
                    )
                )

            if message_type:
                query = query.where(Message.message_type == message_type)

            if unread_only:
                query = query.where(Message.status == "pending")

            # Execute query
            result = await session.execute(query.order_by(Message.created_at))
            messages = result.scalars().all()

            # Convert to dict format (AgentCommunicationQueue format)
            messages_list = []
            for msg in messages:
                # Map back to integer priority
                priority_reverse_map = {"low": 0, "normal": 1, "high": 2, "critical": 2}
                priority_int = priority_reverse_map.get(msg.priority, 1)

                # Convert to AgentCommunicationQueue format
                msg_dict = {
                    "id": str(msg.id),
                    "from_agent": msg.meta_data.get("_from_agent", ""),
                    "to_agent": msg.to_agents[0] if msg.to_agents else None,
                    "type": msg.message_type,
                    "content": msg.content,
                    "priority": priority_int,
                    "acknowledged": msg.status in ["acknowledged", "completed"],
                    "acknowledged_at": msg.acknowledged_at.isoformat() if msg.acknowledged_at else None,
                    "acknowledged_by": msg.acknowledged_by[0] if msg.acknowledged_by else None,
                    "timestamp": msg.created_at.isoformat(),
                    "metadata": msg.meta_data or {},
                }

                messages_list.append(msg_dict)

            logger.info(f"[Compat] Retrieved {len(messages_list)} messages for job {job_id}")

            return {"status": "success", "messages": messages_list}

        except Exception as e:
            logger.exception(f"[Compat] Failed to get messages: {e}")
            return {"status": "error", "error": str(e)}

    async def get_unread_count(
        self, session: Any, job_id: str, tenant_key: str, to_agent: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get count of unread messages (AgentCommunicationQueue compatibility).

        Args:
            session: Database session
            job_id: Job ID to count messages from
            tenant_key: Tenant key for isolation
            to_agent: Optional filter by recipient agent

        Returns:
            Dict with status and unread_count or error:
            - Success: {"status": "success", "unread_count": int}
            - Error: {"status": "error", "error": str}
        """
        try:
            # Retrieve job
            result = await session.execute(select(AgentJob).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Build query
            query = (
                select(func.count())
                .select_from(Message)
                .where(
                    and_(
                        Message.tenant_key == tenant_key,
                        Message.project_id == job.project_id,
                        Message.status == "pending",
                    )
                )
            )

            # Apply filter
            if to_agent:
                query = query.where(Message.to_agents.contains([to_agent]))

            # Execute query
            result = await session.execute(query)
            unread_count = result.scalar() or 0

            logger.info(f"[Compat] Unread count for job {job_id}: {unread_count}")

            return {"status": "success", "unread_count": unread_count}

        except Exception as e:
            logger.exception(f"[Compat] Failed to get unread count: {e}")
            return {"status": "error", "error": str(e)}

    async def acknowledge_all_messages(
        self, session: Any, job_id: str, tenant_key: str, agent_id: str, to_agent: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Acknowledge all unread messages (AgentCommunicationQueue compatibility).

        Args:
            session: Database session
            job_id: Job ID containing messages
            tenant_key: Tenant key for isolation
            agent_id: Agent acknowledging messages
            to_agent: Optional filter by recipient agent

        Returns:
            Dict with status and acknowledged_count or error:
            - Success: {"status": "success", "acknowledged_count": int}
            - Error: {"status": "error", "error": str}
        """
        try:
            # Retrieve job
            result = await session.execute(select(AgentJob).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Build query
            query = select(Message).where(
                and_(
                    Message.tenant_key == tenant_key,
                    Message.project_id == job.project_id,
                    Message.status == "pending",
                )
            )

            # Apply filter
            if to_agent:
                query = query.where(Message.to_agents.contains([to_agent]))

            # Get messages
            result = await session.execute(query)
            messages = result.scalars().all()

            # Acknowledge all
            acknowledged_count = 0
            now = datetime.now(timezone.utc)

            for message in messages:
                message.status = "acknowledged"
                message.acknowledged_at = now
                if not message.acknowledged_by:
                    message.acknowledged_by = []
                if agent_id not in message.acknowledged_by:
                    message.acknowledged_by.append(agent_id)
                acknowledged_count += 1

            await session.commit()

            logger.info(f"[Compat] Acknowledged {acknowledged_count} messages for agent {agent_id}")

            return {"status": "success", "acknowledged_count": acknowledged_count}

        except Exception as e:
            logger.exception(f"[Compat] Failed to acknowledge all messages: {e}")
            return {"status": "error", "error": str(e)}

    # ==================================================================================
    # END COMPATIBILITY LAYER
    # ==================================================================================


class RoutingEngine:
    """
    Intelligent message routing with capability matching and load balancing.
    """

    def __init__(self):
        self._routing_rules: list[RoutingRule] = []
        self._agent_capabilities: dict[str, list[str]] = {}
        self._agent_load: dict[str, int] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._response_times: dict[str, list[float]] = {}

        # Initialize default routing rules
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Set up default routing rules"""
        # Critical messages go to orchestrator
        self._routing_rules.append(PriorityRoutingRule("critical", ["orchestrator"]))

        # Broadcast messages go to all agents
        self._routing_rules.append(TypeRoutingRule("broadcast", ["*"]))

    async def route_message(self, message: Message, available_agents: list[AgentExecution]) -> list[str]:
        """
        Determine optimal agent(s) for message delivery.

        Args:
            message: Message to route
            available_agents: List of available agent executions

        Returns:
            List of agent names in priority order
        """
        candidates = []

        # Step 1: Apply routing rules
        for rule in self._routing_rules:
            if rule.matches(message):
                rule_agents = rule.get_agents()
                if "*" in rule_agents:
                    # Wildcard - all agents
                    candidates.extend([a.agent_name for a in available_agents])
                else:
                    candidates.extend(rule_agents)

        # Step 2: Filter by agent capabilities
        if not candidates:
            # No specific rules, check capabilities
            for agent in available_agents:
                if self._can_handle(agent, message):
                    candidates.append(agent.agent_name)

        # Step 3: Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for agent_name in candidates:
            if agent_name not in seen:
                seen.add(agent_name)
                unique_candidates.append(agent_name)

        # Step 4: Sort by load and performance
        sorted_agents = sorted(
            unique_candidates,
            key=lambda name: self._calculate_agent_score(name, message),
        )

        # Step 5: Check circuit breakers
        healthy_agents = [agent_name for agent_name in sorted_agents if not self._is_circuit_open(agent_name)]

        return healthy_agents

    def _can_handle(self, agent: AgentExecution, message: Message) -> bool:
        """Check if agent can handle message type"""
        agent_capabilities = self._agent_capabilities.get(agent.agent_name, [])

        # Default capability matching
        if message.message_type in agent_capabilities:
            return True

        # Check if agent is in to_agents list
        return agent.agent_name in (message.to_agents or [])

    def _calculate_agent_score(self, agent_name: str, message: Message) -> float:
        """
        Calculate agent score for load balancing.
        Lower score = better candidate.
        """
        score = 0.0

        # Current load (number of pending messages)
        score += self._agent_load.get(agent_name, 0) * 10

        # Average response time
        if agent_name in self._response_times:
            times = self._response_times[agent_name]
            if times:
                avg_time = sum(times[-10:]) / min(len(times), 10)  # Last 10 messages
                score += avg_time

        # Affinity bonus for similar message types
        if self._has_affinity(agent_name, message.message_type):
            score -= 50

        return score

    def _has_affinity(self, agent_name: str, message_type: str) -> bool:
        """Check if agent has handled similar messages recently"""
        # This would check recent message history
        # For now, return False as placeholder
        return False

    def _is_circuit_open(self, agent_name: str) -> bool:
        """Check if circuit breaker is open for agent"""
        if agent_name not in self._circuit_breakers:
            self._circuit_breakers[agent_name] = CircuitBreaker(agent_name)

        return self._circuit_breakers[agent_name].is_open()

    def update_agent_load(self, agent_name: str, delta: int):
        """Update agent load tracking"""
        self._agent_load[agent_name] = self._agent_load.get(agent_name, 0) + delta

    def record_response_time(self, agent_name: str, response_time: float):
        """Record agent response time for load balancing"""
        if agent_name not in self._response_times:
            self._response_times[agent_name] = []

        self._response_times[agent_name].append(response_time)

        # Keep only last 100 entries
        if len(self._response_times[agent_name]) > 100:
            self._response_times[agent_name] = self._response_times[agent_name][-100:]


class RoutingRule:
    """Base class for routing rules"""

    def matches(self, message: Message) -> bool:
        """Check if rule applies to message"""
        raise NotImplementedError

    def get_agents(self) -> list[str]:
        """Get target agents for this rule"""
        raise NotImplementedError


class PriorityRoutingRule(RoutingRule):
    """Route based on message priority"""

    def __init__(self, priority: str, agents: list[str]):
        self.priority = priority
        self.agents = agents

    def matches(self, message: Message) -> bool:
        return message.priority == self.priority

    def get_agents(self) -> list[str]:
        return self.agents


class TypeRoutingRule(RoutingRule):
    """Route based on message type"""

    def __init__(self, message_type: str, agents: list[str]):
        self.message_type = message_type
        self.agents = agents

    def matches(self, message: Message) -> bool:
        return message.message_type == self.message_type

    def get_agents(self) -> list[str]:
        return self.agents


class ContentRoutingRule(RoutingRule):
    """Route based on message content patterns"""

    def __init__(self, pattern: str, agents: list[str]):
        self.pattern = re.compile(pattern)
        self.agents = agents

    def matches(self, message: Message) -> bool:
        return bool(self.pattern.search(message.content))

    def get_agents(self) -> list[str]:
        return self.agents


class CircuitBreaker:
    """Circuit breaker for agent failure protection"""

    def __init__(self, agent_name: str, failure_threshold: int = 5, timeout: int = 60):
        self.agent_name = agent_name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def is_open(self) -> bool:
        """Check if circuit is open (agent unavailable)"""
        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed > self.timeout:
                    self.state = "half-open"
                    return False
            return True
        return False

    def record_success(self):
        """Record successful operation"""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0

    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened for agent {self.agent_name}")


class QueueMonitor:
    """Real-time monitoring of queue health and performance"""

    def __init__(self):
        self._metrics = {
            "queue_depth": {},  # Per priority level
            "processing_time": {},  # Per agent
            "throughput": {"messages_per_minute": 0},
            "latency": {},  # Time from enqueue to dequeue
            "error_rate": 0,
            "stuck_messages": 0,
            "dlq_size": 0,
        }
        self._latency_samples: list[float] = []
        self._throughput_window: list[tuple[datetime, int]] = []
        self._processing_starts: dict[str, datetime] = {}

    async def record_enqueue(self, message: Message):
        """Record message enqueue event"""
        priority = message.priority
        self._metrics["queue_depth"][priority] = self._metrics["queue_depth"].get(priority, 0) + 1

        # Update throughput
        now = datetime.now(timezone.utc)
        self._throughput_window.append((now, 1))
        self._cleanup_throughput_window()

    async def record_dequeue(self, message: Message, agent_name: str):
        """Record message dequeue event"""
        # Calculate latency
        latency = (datetime.now(timezone.utc) - message.created_at).total_seconds()
        self._latency_samples.append(latency)

        # Keep only last 1000 samples
        if len(self._latency_samples) > 1000:
            self._latency_samples = self._latency_samples[-1000:]

        # Update queue depth
        priority = message.priority
        if priority in self._metrics["queue_depth"]:
            self._metrics["queue_depth"][priority] -= 1

    async def record_processing_start(self, message_id: str, agent_name: str):
        """Record when processing starts"""
        self._processing_starts[message_id] = datetime.now(timezone.utc)

    async def record_processing_end(self, message_id: str, agent_name: str, success: bool):
        """Record when processing ends"""
        if message_id in self._processing_starts:
            start_time = self._processing_starts[message_id]
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            if agent_name not in self._metrics["processing_time"]:
                self._metrics["processing_time"][agent_name] = []

            self._metrics["processing_time"][agent_name].append(processing_time)

            # Keep only last 100 samples per agent
            if len(self._metrics["processing_time"][agent_name]) > 100:
                self._metrics["processing_time"][agent_name] = self._metrics["processing_time"][agent_name][-100:]

            del self._processing_starts[message_id]

        if not success:
            self._metrics["error_rate"] += 1

    def _cleanup_throughput_window(self):
        """Remove old entries from throughput window"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
        self._throughput_window = [(t, c) for t, c in self._throughput_window if t > cutoff]

    def _calculate_throughput(self) -> float:
        """Calculate messages per minute"""
        self._cleanup_throughput_window()
        return sum(c for _, c in self._throughput_window)

    def _calculate_latency_percentiles(self) -> dict[str, float]:
        """Calculate latency percentiles"""
        if not self._latency_samples:
            return {"p50": 0, "p95": 0, "p99": 0}

        sorted_samples = sorted(self._latency_samples)
        n = len(sorted_samples)

        return {
            "p50": sorted_samples[int(n * 0.5)],
            "p95": sorted_samples[int(n * 0.95)],
            "p99": sorted_samples[int(n * 0.99)],
        }

    async def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics"""
        self._metrics["throughput"]["messages_per_minute"] = self._calculate_throughput()
        self._metrics["latency"] = self._calculate_latency_percentiles()

        # Calculate average processing times
        avg_processing = {}
        for agent, times in self._metrics["processing_time"].items():
            if times:
                avg_processing[agent] = sum(times) / len(times)

        self._metrics["avg_processing_time"] = avg_processing

        return self._metrics.copy()

    async def rebuild_metrics(self):
        """Rebuild metrics from database after crash"""
        # This would scan the database and rebuild metric
        logger.info("Rebuilding metrics from database...")
        self._metrics = {
            "queue_depth": {},
            "processing_time": {},
            "throughput": {"messages_per_minute": 0},
            "latency": {},
            "error_rate": 0,
            "stuck_messages": 0,
            "dlq_size": 0,
        }

    async def persist_metrics(self):
        """Save metrics for recovery"""
        # This would save metrics to database or file
        logger.info("Persisting metrics...")


class StuckMessageDetector:
    """Detect and handle stuck messages"""

    def __init__(self, db_manager: DatabaseManager, timeout_seconds: int = 300):
        self.db_manager = db_manager
        self.timeout_seconds = timeout_seconds

    async def detect_stuck_messages(self, timeout_seconds: Optional[int] = None) -> list[Message]:
        """Find messages that have been processing too long"""
        if timeout_seconds is None:
            timeout_seconds = self.timeout_seconds

        async with self.db_manager.get_session_async() as session:
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)

            # Check messages with processing_started_at in meta_data
            stmt = select(Message).where(
                and_(
                    Message.status.in_(["processing", "acknowledged"]),
                    Message.created_at < cutoff_time,
                )
            )

            result = await session.execute(stmt)
            messages = result.scalars().all()

            # Filter by actual processing time
            stuck = []
            for msg in messages:
                if msg.meta_data and "processing_started_at" in msg.meta_data:
                    started = datetime.fromisoformat(msg.meta_data["processing_started_at"])
                    if (datetime.now(timezone.utc) - started).total_seconds() > timeout_seconds:
                        stuck.append(msg)
                elif (datetime.now(timezone.utc) - msg.created_at).total_seconds() > timeout_seconds:
                    stuck.append(msg)

            return stuck


class DeadLetterQueue:
    """Handle messages that cannot be processed"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def add_message(self, message: Message, reason: str):
        """Move message to DLQ with reason"""
        async with self.db_manager.get_session_async() as session:
            try:
                await session.begin()

                # Update message status
                message.status = "dead_letter"
                message.meta_data = message.meta_data or {}
                message.meta_data["dlq_reason"] = reason
                message.meta_data["dlq_timestamp"] = datetime.now(timezone.utc).isoformat()

                session.add(message)
                await session.commit()

                logger.error(f"Message {message.id} moved to DLQ: {reason}")

            except Exception as e:
                await session.rollback()
                logger.exception(f"Failed to move message to DLQ: {e}")

    async def get_size(self) -> int:
        """Get number of messages in DLQ"""
        async with self.db_manager.get_session_async() as session:
            stmt = select(func.count()).select_from(Message).where(Message.status == "dead_letter")
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def reprocess_message(self, message_id: str) -> bool:
        """Attempt to reprocess a DLQ message"""
        async with self.db_manager.get_session_async() as session:
            try:
                await session.begin()

                stmt = select(Message).where(Message.id == message_id).with_for_update()
                result = await session.execute(stmt)
                message = result.scalar_one_or_none()

                if message and message.status == "dead_letter":
                    # Reset for reprocessing
                    message.status = "pending"
                    message.meta_data = message.meta_data or {}
                    message.meta_data["reprocessed_from_dlq"] = True
                    message.meta_data["retry_count"] = 0

                    await session.commit()
                    logger.info(f"Message {message_id} reprocessed from DLQ")
                    return True

            except Exception as e:
                await session.rollback()
                logger.exception(f"Failed to reprocess DLQ message: {e}")

        return False


class DurabilityManager:
    """Ensure message durability and crash recovery"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._wal_entries: list[dict[str, Any]] = []

    async def persist_with_wal(self, message: Message):
        """Write-ahead logging for crash recovery"""
        # Record WAL entry
        wal_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "enqueue",
            "message_id": str(message.id),
            "committed": False,
        }
        self._wal_entries.append(wal_entry)

        # Persist to database
        async with self.db_manager.get_session_async() as session:
            session.add(message)
            await session.commit()

        # Mark as committed
        wal_entry["committed"] = True

    async def recover_from_crash(self):
        """Recover from uncommitted WAL entries"""
        uncommitted = [e for e in self._wal_entries if not e["committed"]]

        for entry in uncommitted:
            logger.info(f"Recovering uncommitted operation: {entry['operation']} for message {entry['message_id']}")
            # In a real implementation, this would replay the operation

    async def checkpoint(self):
        """Create a recovery checkpoint"""
        # Clear committed WAL entries
        self._wal_entries = [e for e in self._wal_entries if not e["committed"]]
        logger.info("Checkpoint created")


class IsolationManager:
    """Ensure proper isolation between concurrent operations"""

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}
        self._agent_locks: dict[str, asyncio.Lock] = {}

    def with_message_lock(self, message_id: str):
        """Get or create a lock for a message"""
        if message_id not in self._locks:
            self._locks[message_id] = asyncio.Lock()
        return self._locks[message_id]

    def with_agent_lock(self, agent_name: str):
        """Get or create a lock for an agent"""
        if agent_name not in self._agent_locks:
            self._agent_locks[agent_name] = asyncio.Lock()
        return self._agent_locks[agent_name]
