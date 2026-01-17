"""
WorkflowEngine - Execute multi-agent workflows with different coordination patterns.

Handover 0020 Phase 1D: Enables waterfall (sequential) and parallel workflow execution
with failure recovery, retry logic, and progress monitoring.

Features:
- Waterfall execution: Sequential stages with dependency checking
- Parallel execution: Concurrent independent stages
- Failure recovery: Retry logic and critical/non-critical handling
- Progress monitoring: Stage status tracking and result aggregation
- Multi-tenant isolation: All operations scoped by tenant_key

Integration:
- JobCoordinator (Handover 0019) for multi-agent coordination
- AgentJobManager for job spawning and lifecycle management
- orchestration_types for data structures
"""

import asyncio
import logging
import time
from typing import List

from .services.agent_job_manager import AgentJobManager
from .job_coordinator import JobCoordinator
from .orchestration_types import (
    StageResult,
    WorkflowResult,
    WorkflowStage,
)
from .repositories.agent_job_repository import AgentJobRepository


logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Execute multi-agent workflows with different coordination patterns.

    Supports:
    - Waterfall (sequential) execution with dependencies
    - Parallel execution for independent tasks
    - Failure recovery strategies
    - Progress monitoring

    Integrates with:
    - JobCoordinator (Handover 0019) for multi-agent coordination
    - AgentJobManager for job spawning and lifecycle
    """

    def __init__(self, db_manager):
        """
        Initialize WorkflowEngine.

        Args:
            db_manager: DatabaseManager instance for session management
        """
        self.db = db_manager
        self.job_manager = AgentJobManager(db_manager)
        self.job_coordinator = JobCoordinator(
            db_manager,
            self.job_manager,
            None,  # comm_queue not needed for workflow execution
        )
        self.job_repo = AgentJobRepository(db_manager)

    async def execute_workflow(
        self,
        workflow_type: str,
        stages: List[WorkflowStage],
        tenant_key: str,
        project_id: str,
    ) -> WorkflowResult:
        """
        Execute a multi-agent workflow.

        Args:
            workflow_type: Type of workflow ('waterfall' or 'parallel')
            stages: List of WorkflowStage objects to execute
            tenant_key: Tenant key for multi-tenant isolation
            project_id: Project ID for context

        Returns:
            WorkflowResult with execution results

        Raises:
            ValueError: If workflow_type is invalid
        """
        logger.info(
            f"Starting {workflow_type} workflow with {len(stages)} stages for tenant {tenant_key}, project {project_id}"
        )

        # Validate workflow type
        valid_types = ["waterfall", "parallel"]
        if workflow_type not in valid_types:
            raise ValueError(f"Invalid workflow type: {workflow_type}. Must be one of {valid_types}")

        # Track start time
        start_time = time.time()

        # Execute workflow based on type
        if workflow_type == "waterfall":
            result = await self._execute_waterfall(stages, tenant_key, project_id)
        else:  # parallel
            result = await self._execute_parallel(stages, tenant_key, project_id)

        # Calculate duration
        duration = time.time() - start_time
        result.duration_seconds = duration

        logger.info(
            f"Workflow completed: {result.status}, "
            f"{len(result.completed)} completed, {len(result.failed)} failed, "
            f"duration: {duration:.2f}s"
        )

        return result

    async def _execute_waterfall(
        self,
        stages: List[WorkflowStage],
        tenant_key: str,
        project_id: str,
    ) -> WorkflowResult:
        """
        Execute workflow stages sequentially with dependency checking.

        Waterfall execution:
        1. Execute stages in order
        2. Check dependencies before each stage
        3. Stop on critical failure
        4. Continue on non-critical failure

        Args:
            stages: List of WorkflowStage objects
            tenant_key: Tenant key for isolation
            project_id: Project ID for context

        Returns:
            WorkflowResult with execution status
        """
        completed_stages: List[StageResult] = []
        failed_stages: List[str] = []

        # Handle empty stages
        if not stages:
            return WorkflowResult(
                completed=[],
                failed=[],
                status="completed",
                duration_seconds=0.0,
            )

        # Execute stages sequentially
        for stage in stages:
            # Check dependencies
            if not await self._dependencies_met(stage, completed_stages):
                logger.warning(f"Stage {stage.name} dependencies not met, skipping")
                failed_stages.append(stage.name)
                continue

            # Execute stage with retry logic
            try:
                stage_result = await self._execute_stage_with_retry(stage, tenant_key, project_id)
                completed_stages.append(stage_result)
                logger.info(f"Stage {stage.name} completed successfully")

            except Exception as e:
                logger.error(f"Stage {stage.name} failed: {e}")
                failed_stages.append(stage.name)

                # Handle failure
                await self._handle_stage_failure(stage, e, tenant_key)

                # Stop on critical failure
                if stage.critical:
                    logger.error(f"Critical stage {stage.name} failed, stopping workflow")
                    break
                logger.warning(f"Non-critical stage {stage.name} failed, continuing workflow")

        # Determine overall status
        if not failed_stages:
            status = "completed"
        elif completed_stages:
            status = "partial"
        else:
            status = "failed"

        return WorkflowResult(
            completed=completed_stages,
            failed=failed_stages,
            status=status,
            duration_seconds=0.0,  # Will be set by execute_workflow
        )

    async def _execute_parallel(
        self,
        stages: List[WorkflowStage],
        tenant_key: str,
        project_id: str,
    ) -> WorkflowResult:
        """
        Execute workflow stages in parallel.

        Parallel execution:
        1. Spawn all stages concurrently
        2. Wait for all to complete
        3. Aggregate results
        4. Determine overall status

        Args:
            stages: List of WorkflowStage objects
            tenant_key: Tenant key for isolation
            project_id: Project ID for context

        Returns:
            WorkflowResult with execution status
        """
        # Handle empty stages
        if not stages:
            return WorkflowResult(
                completed=[],
                failed=[],
                status="completed",
                duration_seconds=0.0,
            )

        # Create tasks for all stages
        stage_tasks = []
        for stage in stages:
            task = self._execute_stage_with_retry(stage, tenant_key, project_id)
            stage_tasks.append((stage, task))

        # Execute all stages concurrently and gather results
        completed_stages: List[StageResult] = []
        failed_stages: List[str] = []

        results = await asyncio.gather(
            *[task for _, task in stage_tasks],
            return_exceptions=True,
        )

        # Process results
        for (stage, _), result in zip(stage_tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Stage {stage.name} failed: {result}")
                failed_stages.append(stage.name)
                await self._handle_stage_failure(stage, result, tenant_key)
            else:
                completed_stages.append(result)
                logger.info(f"Stage {stage.name} completed successfully")

        # Determine overall status
        if not failed_stages:
            status = "completed"
        elif completed_stages:
            status = "partial"
        else:
            status = "failed"

        return WorkflowResult(
            completed=completed_stages,
            failed=failed_stages,
            status=status,
            duration_seconds=0.0,  # Will be set by execute_workflow
        )

    async def _execute_stage_with_retry(
        self,
        stage: WorkflowStage,
        tenant_key: str,
        project_id: str,
    ) -> StageResult:
        """
        Execute a stage with retry logic.

        Args:
            stage: WorkflowStage to execute
            tenant_key: Tenant key for isolation
            project_id: Project ID for context

        Returns:
            StageResult with execution results

        Raises:
            Exception: If stage fails after all retries
        """
        last_error = None

        # Try execution with retries
        max_attempts = stage.max_retries + 1  # Initial attempt + retries
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    logger.info(f"Retrying stage {stage.name} (attempt {attempt + 1}/{max_attempts})")
                    stage.retry_count = attempt

                return await self._execute_stage(stage, tenant_key, project_id)

            except Exception as e:
                last_error = e
                if attempt < stage.max_retries:
                    # Exponential backoff
                    delay = 2**attempt
                    logger.warning(f"Stage {stage.name} attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Stage {stage.name} failed after {max_attempts} attempts")

        # All retries exhausted
        raise last_error

    async def _execute_stage(
        self,
        stage: WorkflowStage,
        tenant_key: str,
        project_id: str,
    ) -> StageResult:
        """
        Execute a single workflow stage.

        Execution process:
        1. Spawn agents for the stage
        2. Wait for completion (with timeout)
        3. Aggregate results
        4. Return StageResult

        Args:
            stage: WorkflowStage to execute
            tenant_key: Tenant key for isolation
            project_id: Project ID for context

        Returns:
            StageResult with execution results

        Raises:
            Exception: If stage execution fails
        """
        logger.info(f"Executing stage: {stage.name} with {len(stage.agents)} agents")

        start_time = time.time()
        job_ids: List[str] = []

        # Spawn jobs for all agents in the stage
        for agent_config in stage.agents:
            job_id = await self.job_manager.create_job(
                tenant_key=tenant_key,
                agent_display_name=agent_config.role,
                mission=agent_config.mission.content if agent_config.mission else "",
                spawned_by="workflow_engine",
                context_chunks=(agent_config.context_chunks if agent_config.context_chunks else []),
                initial_messages=[],
            )
            job_ids.append(job_id)
            logger.debug(f"Created job {job_id} for agent {agent_config.role}")

        # Wait for all jobs to complete (using parent_job_id pattern)
        # Note: For workflow engine, we use the stage name as a pseudo parent
        wait_result = await self.job_coordinator.wait_for_children(
            tenant_key=tenant_key,
            parent_job_id="workflow_engine",
            timeout=float(stage.timeout_seconds),
        )

        # Check for timeout
        if wait_result["timed_out"]:
            raise TimeoutError(f"Stage {stage.name} timed out after {stage.timeout_seconds}s")

        # Check for failures
        if wait_result["failed"] > 0:
            raise Exception(f"Stage {stage.name} had {wait_result['failed']} failed jobs")

        # Aggregate results from all jobs
        aggregated = await self.job_coordinator.aggregate_child_results(
            tenant_key=tenant_key,
            parent_job_id="workflow_engine",
            strategy="collect",
        )

        # Calculate duration
        duration = time.time() - start_time

        return StageResult(
            stage_name=stage.name,
            job_ids=job_ids,
            results=aggregated,
            duration=duration,
            status="completed",
        )

    async def _dependencies_met(
        self,
        stage: WorkflowStage,
        completed_stages: List[StageResult],
    ) -> bool:
        """
        Check if stage dependencies are satisfied.

        Args:
            stage: WorkflowStage to check
            completed_stages: List of completed StageResult objects

        Returns:
            bool: True if all dependencies are met
        """
        # No dependencies means ready to execute
        if not stage.depends_on or len(stage.depends_on) == 0:
            return True

        # Check if all dependency stages are completed
        completed_names = {stage_result.stage_name for stage_result in completed_stages}

        for dependency in stage.depends_on:
            if dependency not in completed_names:
                logger.debug(f"Stage {stage.name} waiting for dependency: {dependency}")
                return False

        return True

    async def _handle_stage_failure(
        self,
        stage: WorkflowStage,
        error: Exception,
        tenant_key: str,
    ):
        """
        Handle stage failure with recovery strategies.

        Strategies:
        1. Retry if retries available (handled by _execute_stage_with_retry)
        2. Log failure details
        3. Mark as partial success if non-critical

        Args:
            stage: Failed WorkflowStage
            error: Exception that caused failure
            tenant_key: Tenant key for isolation
        """
        logger.error(
            f"Handling failure for stage {stage.name}: {error}",
            extra={
                "stage_name": stage.name,
                "critical": stage.critical,
                "retry_count": stage.retry_count,
                "max_retries": stage.max_retries,
                "tenant_key": tenant_key,
            },
        )

        # Increment retry count
        stage.retry_count += 1

        # Log strategy
        if not stage.critical:
            logger.warning(f"Non-critical stage {stage.name} failed, workflow will continue")
        else:
            logger.error(f"Critical stage {stage.name} failed, workflow will stop")

        # Future: Send notifications to orchestrator (Phase 3)
        # For now, just log the failure
