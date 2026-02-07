"""
JobCoordinator - Coordinates agent job spawning, dependencies, and aggregation.

Handover 0019: Enables complex agent orchestration patterns including:
- Parallel job spawning
- Sequential job chains (dependencies)
- Result aggregation from child jobs
- Job tree status tracking
- Coordination metrics calculation

Multi-tenant isolation: All operations scoped by tenant_key.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .repositories.agent_job_repository import AgentJobRepository


class JobCoordinator:
    """
    Coordinates agent job lifecycle including spawning, dependencies, and aggregation.

    Provides high-level coordination primitives for complex agent orchestration:
    - spawn_child_jobs: Create multiple child jobs from parent
    - spawn_parallel_jobs: Create independent parallel jobs
    - wait_for_children: Wait for child job completion
    - aggregate_child_results: Collect/merge results from children
    - create_job_chain: Create sequential dependency chain
    - execute_next_in_chain: Execute next job in chain
    - get_job_tree_status: Get recursive job tree status
    - get_coordination_metrics: Calculate coordination metrics
    """

    def __init__(self, db_manager, job_manager, comm_queue):
        """
        Initialize JobCoordinator.

        Args:
            db_manager: DatabaseManager instance for session management
            job_manager: AgentJobManager for job operations
            comm_queue: MessageQueue for notifications
        """
        self.db = db_manager
        self.job_manager = job_manager
        self.comm_queue = comm_queue
        self.job_repo = AgentJobRepository(db_manager)

    async def spawn_child_jobs(
        self,
        tenant_key: str,
        parent_job_id: str,
        child_specs: list[dict[str, Any]],
        send_notifications: bool = False,
        validate_parent: bool = False,
    ) -> dict[str, Any]:
        """
        Spawn multiple child jobs from a parent job.

        Args:
            tenant_key: Tenant key for isolation
            parent_job_id: Parent job ID
            child_specs: List of child job specifications
                Each spec must contain: agent_display_name, mission
                Optional: context_chunks, initial_messages, notify_on_complete
            send_notifications: Whether to send notifications for spawned jobs
            validate_parent: Whether to validate parent job exists

        Returns:
            Dict with:
                success: bool
                job_ids: List[str] - Created job IDs
                count: int - Number of jobs created

        Raises:
            ValueError: If parent validation fails or specs are invalid
        """
        # Validate parent job if requested
        if validate_parent:
            parent_job = await self.job_manager.get_job(tenant_key, parent_job_id)
            if not parent_job:
                raise ValueError(f"Parent job not found: {parent_job_id}")

        # Handle empty specs
        if not child_specs:
            return {"success": True, "job_ids": [], "count": 0}

        # Validate specs
        for spec in child_specs:
            if "agent_display_name" not in spec:
                raise ValueError("Invalid job specification: missing 'agent_display_name'")
            if "mission" not in spec:
                raise ValueError("Invalid job specification: missing 'mission'")

        # Build job batch
        jobs = []
        for spec in child_specs:
            job_data = {
                "tenant_key": tenant_key,
                "agent_display_name": spec["agent_display_name"],
                "mission": spec["mission"],
                "spawned_by": parent_job_id,
                "context_chunks": spec.get("context_chunks", []),
                "initial_messages": spec.get("initial_messages", []),
            }
            jobs.append(job_data)

        # Create jobs in batch
        result = await self.job_manager.create_job_batch(tenant_key=tenant_key, jobs=jobs)

        # Send notifications if requested
        if send_notifications and result.get("job_ids"):
            for job_id in result["job_ids"]:
                await self.comm_queue.send_notification(
                    tenant_key=tenant_key,
                    recipient_job_id=job_id,
                    notification_type="job_spawned",
                    data={"parent_job_id": parent_job_id},
                )

        return {"success": True, "job_ids": result.get("job_ids", []), "count": result.get("count", 0)}

    async def spawn_parallel_jobs(
        self, tenant_key: str, parent_job_id: str, job_specs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Spawn parallel jobs without dependencies.

        Convenience wrapper around spawn_child_jobs for parallel execution.

        Args:
            tenant_key: Tenant key for isolation
            parent_job_id: Parent job ID
            job_specs: List of job specifications (same format as spawn_child_jobs)

        Returns:
            Dict with success, job_ids, count
        """
        return await self.spawn_child_jobs(
            tenant_key=tenant_key, parent_job_id=parent_job_id, child_specs=job_specs, send_notifications=False
        )

    async def wait_for_children(
        self, tenant_key: str, parent_job_id: str, timeout: float = 300.0, poll_interval: float = 1.0
    ) -> dict[str, Any]:
        """
        Wait for all child jobs to complete.

        Polls child job status until all complete or timeout.

        Args:
            tenant_key: Tenant key for isolation
            parent_job_id: Parent job ID whose children to wait for
            timeout: Maximum time to wait in seconds (default 5 minutes)
            poll_interval: Polling interval in seconds (default 1 second)

        Returns:
            Dict with:
                all_complete: bool - All children completed
                completed: int - Number of completed jobs
                failed: int - Number of failed jobs
                active: int - Number of still active jobs
                timed_out: bool - Whether timeout occurred

        Raises:
            ValueError: If timeout is negative
        """
        if timeout < 0:
            raise ValueError("Timeout must be positive")

        start_time = asyncio.get_event_loop().time()
        timed_out = False

        while True:
            # Get current child jobs
            children = await self.job_manager.get_jobs_by_spawner(tenant_key, parent_job_id)

            # Count statuses
            completed = sum(1 for j in children if j.status == "completed")
            failed = sum(1 for j in children if j.status == "failed")
            active = sum(1 for j in children if j.status in ["pending", "active"])

            # Check if all done
            if active == 0:
                return {"all_complete": True, "completed": completed, "failed": failed, "active": 0, "timed_out": False}

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                timed_out = True
                break

            # Wait before polling again
            await asyncio.sleep(poll_interval)

        # Timed out - return current state
        return {
            "all_complete": False,
            "completed": completed,
            "failed": failed,
            "active": active,
            "timed_out": timed_out,
        }

    async def aggregate_child_results(
        self, tenant_key: str, parent_job_id: str, strategy: str = "collect"
    ) -> dict[str, Any]:
        """
        Aggregate results from child jobs.

        Args:
            tenant_key: Tenant key for isolation
            parent_job_id: Parent job ID
            strategy: Aggregation strategy
                - "collect": Collect all results into array
                - "merge": Merge all results into single object

        Returns:
            Dict with:
                strategy: str - Strategy used
                results: List or Dict - Aggregated results
                count: int - Number of children

        Raises:
            ValueError: If strategy is invalid
        """
        valid_strategies = ["collect", "merge"]
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid aggregation strategy: {strategy}. Must be one of {valid_strategies}")

        # Get child jobs
        children = await self.job_manager.get_jobs_by_spawner(tenant_key, parent_job_id)

        if strategy == "collect":
            # Collect all results into array
            results = []
            for child in children:
                results.append(
                    {
                        "job_id": child.job_id,
                        "agent_display_name": child.agent_display_name,
                        "status": child.status,
                        "messages": child.messages or [],
                    }
                )

            return {"strategy": "collect", "results": results, "count": len(children)}

        if strategy == "merge":
            # Merge all messages from all children
            merged_data = []
            for child in children:
                if child.messages:
                    merged_data.extend(child.messages)

            return {"strategy": "merge", "merged_data": merged_data, "count": len(children)}

    async def create_job_chain(
        self, tenant_key: str, parent_job_id: str, chain_specs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Create a sequential job dependency chain.

        Jobs execute in order - each waits for previous to complete.

        Args:
            tenant_key: Tenant key for isolation
            parent_job_id: Parent job ID
            chain_specs: List of job specs in execution order

        Returns:
            Dict with:
                success: bool
                chain_id: str - Unique chain identifier
                job_ids: List[str] - Job IDs in chain order
                chain_length: int
        """
        if not chain_specs:
            return {"success": True, "chain_id": None, "job_ids": [], "chain_length": 0}

        chain_id = f"chain-{uuid4()}"

        # Create all jobs in the chain
        jobs = []
        for i, spec in enumerate(chain_specs):
            job_data = {
                "tenant_key": tenant_key,
                "agent_display_name": spec["agent_display_name"],
                "mission": spec["mission"],
                "spawned_by": parent_job_id,
                "context_chunks": spec.get("context_chunks", []),
                "initial_messages": spec.get("initial_messages", []),
            }
            jobs.append(job_data)

        # Create job batch
        result = await self.job_manager.create_job_batch(tenant_key=tenant_key, jobs=jobs)

        job_ids = result.get("job_ids", [])

        # Add chain metadata to each job
        for i, job_id in enumerate(job_ids):
            next_job_id = job_ids[i + 1] if i < len(job_ids) - 1 else None

            chain_metadata = {
                "type": "chain_metadata",
                "chain_id": chain_id,
                "position": i + 1,
                "total": len(job_ids),
                "next_job_id": next_job_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Add metadata message to job
            job = await self.job_manager.get_job(tenant_key, job_id)
            if job:
                messages = list(job.messages or [])
                messages.append(chain_metadata)
                job.messages = messages

                # Update job (messages are already updated on the job object)

        return {"success": True, "chain_id": chain_id, "job_ids": job_ids, "chain_length": len(job_ids)}

    async def execute_next_in_chain(self, tenant_key: str, current_job_id: str) -> dict[str, Any]:
        """
        Execute the next job in a dependency chain.

        Called when a job completes to trigger next job.

        Args:
            tenant_key: Tenant key for isolation
            current_job_id: Current job that just completed

        Returns:
            Dict with:
                success: bool
                next_job_id: str or None
                chain_complete: bool
        """
        # Get current job
        current_job = await self.job_manager.get_job(tenant_key, current_job_id)
        if not current_job:
            return {"success": False, "error": "Current job not found"}

        # Find chain metadata in messages
        chain_metadata = None
        for message in current_job.messages or []:
            if isinstance(message, dict) and message.get("type") == "chain_metadata":
                chain_metadata = message
                break

        if not chain_metadata:
            return {"success": False, "error": "No chain metadata found"}

        next_job_id = chain_metadata.get("next_job_id")

        if not next_job_id:
            # Chain complete
            return {"success": True, "next_job_id": None, "chain_complete": True}

        # Activate next job
        await self.job_manager.update_job_status(tenant_key=tenant_key, job_id=next_job_id, status="active")

        return {"success": True, "next_job_id": next_job_id, "chain_complete": False}

    async def get_job_tree_status(self, tenant_key: str, root_job_id: str, max_depth: int = 10) -> dict[str, Any]:
        """
        Get recursive job tree status.

        Traverses job hierarchy to collect status of all jobs in tree.

        Args:
            tenant_key: Tenant key for isolation
            root_job_id: Root job ID to start traversal
            max_depth: Maximum depth to traverse (prevents infinite loops)

        Returns:
            Dict with:
                root_job_id: str
                total_jobs: int
                completed: int
                failed: int
                active: int
                pending: int
                tree_depth: int
        """
        # Track visited jobs to prevent cycles
        visited = set()
        status_counts = {"completed": 0, "failed": 0, "active": 0, "pending": 0}

        async def traverse(job_id: str, current_depth: int) -> int:
            """Recursively traverse job tree."""
            if job_id in visited:
                return current_depth

            visited.add(job_id)

            # Get job
            job = await self.job_manager.get_job(tenant_key, job_id)
            if not job:
                return current_depth

            # Count status
            if job.status in status_counts:
                status_counts[job.status] = status_counts[job.status] + 1
            else:
                status_counts[job.status] = 1

            # Check depth limit before traversing children
            if current_depth >= max_depth:
                return current_depth

            # Get children
            children = await self.job_manager.get_jobs_by_spawner(tenant_key, job_id)

            # Traverse children
            max_child_depth = current_depth
            for child in children:
                child_depth = await traverse(child.job_id, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)

            return max_child_depth

        # Start traversal
        tree_depth = await traverse(root_job_id, 0)

        return {
            "root_job_id": root_job_id,
            "total_jobs": len(visited),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "active": status_counts.get("active", 0),
            "pending": status_counts.get("pending", 0),
            "tree_depth": tree_depth,
        }

    async def get_coordination_metrics(self, tenant_key: str, parent_job_id: str) -> dict[str, Any]:
        """
        Calculate coordination metrics for a parent job.

        Args:
            tenant_key: Tenant key for isolation
            parent_job_id: Parent job ID

        Returns:
            Dict with:
                total_children: int
                completed: int
                failed: int
                active: int
                success_rate: float
                avg_completion_time: float or None (seconds)
        """
        # Get child jobs
        children = await self.job_manager.get_jobs_by_spawner(tenant_key, parent_job_id)

        total_children = len(children)

        if total_children == 0:
            return {
                "total_children": 0,
                "completed": 0,
                "failed": 0,
                "active": 0,
                "success_rate": 0.0,
                "avg_completion_time": None,
            }

        # Count statuses
        completed = sum(1 for j in children if j.status == "completed")
        failed = sum(1 for j in children if j.status == "failed")
        active = sum(1 for j in children if j.status in ["pending", "active"])

        # Calculate success rate
        finished = completed + failed
        success_rate = completed / finished if finished > 0 else 0.0

        # Calculate average completion time for completed jobs
        completion_times = []
        for child in children:
            if child.status == "completed" and child.started_at and child.completed_at:
                duration = (child.completed_at - child.started_at).total_seconds()
                completion_times.append(duration)

        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else None

        return {
            "total_children": total_children,
            "completed": completed,
            "failed": failed,
            "active": active,
            "success_rate": success_rate,
            "avg_completion_time": avg_completion_time,
        }
