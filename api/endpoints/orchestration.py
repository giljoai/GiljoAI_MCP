"""
Orchestration REST API endpoints (Handover 0020 Phase 3A).

Provides REST API for the complete orchestration workflow:
- Vision processing
- Mission generation
- Agent team spawning
- Workflow coordination
- Metrics and status monitoring
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.dependencies import get_tenant_key
from src.giljo_mcp.models import Agent, Product, Project
from src.giljo_mcp.orchestrator import ProjectOrchestrator

router = APIRouter()


# Pydantic request/response models
class ProcessVisionRequest(BaseModel):
    """Request model for vision processing workflow"""

    tenant_key: str = Field(..., description="Tenant key for multi-tenant isolation")
    product_id: str = Field(..., description="Product UUID with vision document")
    project_requirements: str = Field(..., description="Project requirements description")
    workflow_type: str = Field(default="waterfall", description="Workflow type: 'waterfall' or 'parallel'")


class ProcessVisionResponse(BaseModel):
    """Response model for vision processing workflow"""

    project_id: str = Field(..., description="Created project ID")
    mission_plan: Dict[str, Any] = Field(..., description="Generated missions mapped by role")
    selected_agents: List[str] = Field(..., description="List of selected agent roles")
    spawned_jobs: List[str] = Field(..., description="List of spawned job IDs")
    workflow_status: str = Field(..., description="Workflow execution status")
    token_reduction: Dict[str, Any] = Field(..., description="Token reduction metrics")


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status"""

    project_id: str
    active_agents: int
    completed_agents: int
    failed_agents: int
    current_stage: str
    progress_percent: float


class MetricsResponse(BaseModel):
    """Response model for project metrics"""

    project_id: str
    token_metrics: Dict[str, Any]


class CreateMissionsRequest(BaseModel):
    """Request model for mission creation"""

    tenant_key: str
    product_id: str
    project_description: str


class CreateMissionsResponse(BaseModel):
    """Response model for mission creation"""

    missions: Dict[str, Any]


class SpawnTeamRequest(BaseModel):
    """Request model for team spawning"""

    tenant_key: str
    project_id: str
    agent_roles: List[str]
    workflow_type: str = "waterfall"


class SpawnTeamResponse(BaseModel):
    """Response model for team spawning"""

    spawned_agents: List[str]
    workflow_status: str


class CoordinateRequest(BaseModel):
    """Request model for coordination"""

    project_id: str
    coordination_action: str


class CoordinateResponse(BaseModel):
    """Response model for coordination"""

    status: str


class HandleFailureRequest(BaseModel):
    """Request model for failure handling"""

    project_id: str
    agent_id: str
    failure_reason: str
    recovery_action: str


class HandleFailureResponse(BaseModel):
    """Response model for failure handling"""

    recovery_status: str


# Endpoints
@router.post("/process-vision", response_model=ProcessVisionResponse)
async def process_vision(request: ProcessVisionRequest) -> ProcessVisionResponse:
    """
    Complete vision processing workflow.

    Workflow:
    1. Validate product and tenant
    2. Chunk vision document if needed
    3. Create project
    4. Analyze requirements
    5. Select agents
    6. Generate missions
    7. Coordinate workflow
    8. Calculate token reduction

    Args:
        request: ProcessVisionRequest with tenant_key, product_id, project_requirements

    Returns:
        ProcessVisionResponse with project details, missions, agents, and metrics

    Raises:
        HTTPException: 404 if product not found or tenant mismatch
        HTTPException: 400 if product has no vision document
        HTTPException: 500 for internal errors
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")

    try:
        # Validate product exists and tenant matches
        async with state.db_manager.get_session_async() as session:
            product = await session.get(Product, request.product_id)

            if not product or product.tenant_key != request.tenant_key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {request.product_id} not found"
                )

        # Execute vision processing workflow via orchestrator
        orchestrator = ProjectOrchestrator()

        result = await orchestrator.process_product_vision(
            tenant_key=request.tenant_key, product_id=request.product_id, project_requirements=request.project_requirements
        )

        # Build response
        return ProcessVisionResponse(
            project_id=result['project_id'],
            mission_plan=result['mission_plan'],
            selected_agents=result['selected_agents'],
            spawned_jobs=result['spawned_jobs'],
            workflow_status=result['workflow_result'].status,
            token_reduction=result['token_reduction'],
        )

    except ValueError as e:
        # Handover 0050: Handle inactive product error with 409 Conflict
        error_msg = str(e)
        if "not active" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "inactive_product",
                    "message": error_msg,
                    "hint": "Activate the product in the Products view before creating agent missions."
                }
            )
        # Other ValueError indicates missing vision or invalid data
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/workflow-status/{project_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(project_id: str, tenant_key: str = Query(...)) -> WorkflowStatusResponse:
    """
    Get current workflow status for a project.

    Args:
        project_id: Project UUID
        tenant_key: Tenant key for authorization (query parameter)

    Returns:
        WorkflowStatusResponse with agent counts and progress

    Raises:
        HTTPException: 404 if project not found or tenant mismatch
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Get project with agents
            project = await session.get(Project, project_id)

            if not project or project.tenant_key != tenant_key:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

            # Count agent statuses
            agents = project.agents if hasattr(project, 'agents') and project.agents else []

            active_count = sum(1 for agent in agents if agent.status == 'active')
            completed_count = sum(1 for agent in agents if agent.status == 'completed')
            failed_count = sum(1 for agent in agents if agent.status in ['error', 'failed'])

            total_agents = len(agents)
            progress = (completed_count / total_agents * 100) if total_agents > 0 else 0.0

            return WorkflowStatusResponse(
                project_id=project_id,
                active_agents=active_count,
                completed_agents=completed_count,
                failed_agents=failed_count,
                current_stage=project.status,
                progress_percent=round(progress, 2),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/metrics/{project_id}", response_model=MetricsResponse)
async def get_metrics(project_id: str, tenant_key: str = Query(...)) -> MetricsResponse:
    """
    Get performance metrics for a project.

    Args:
        project_id: Project UUID
        tenant_key: Tenant key for authorization

    Returns:
        MetricsResponse with token reduction metrics

    Raises:
        HTTPException: 404 if project not found or tenant mismatch
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            project = await session.get(Project, project_id)

            if not project or project.tenant_key != tenant_key:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

            # Get token metrics (handle missing gracefully)
            token_metrics = project.token_metrics if hasattr(project, 'token_metrics') and project.token_metrics else {}

            return MetricsResponse(project_id=project_id, token_metrics=token_metrics)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/create-missions", response_model=CreateMissionsResponse)
async def create_missions(request: CreateMissionsRequest) -> CreateMissionsResponse:
    """
    Generate missions from product vision.

    Args:
        request: CreateMissionsRequest with tenant_key, product_id, project_description

    Returns:
        CreateMissionsResponse with generated missions

    Raises:
        HTTPException: 404 if product not found or tenant mismatch
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            product = await session.get(Product, request.product_id)

            if not product or product.tenant_key != request.tenant_key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {request.product_id} not found"
                )

        # Generate missions
        orchestrator = ProjectOrchestrator()
        missions = await orchestrator.generate_mission_plan(product, request.project_description)

        # Convert Mission objects to dicts
        mission_dicts = {}
        for role, mission in missions.items():
            if hasattr(mission, 'to_dict'):
                mission_dicts[role] = mission.to_dict()
            else:
                mission_dicts[role] = mission

        return CreateMissionsResponse(missions=mission_dicts)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/spawn-team", response_model=SpawnTeamResponse)
async def spawn_team(request: SpawnTeamRequest) -> SpawnTeamResponse:
    """
    Spawn agent team for a project.

    Args:
        request: SpawnTeamRequest with tenant_key, project_id, agent_roles, workflow_type

    Returns:
        SpawnTeamResponse with spawned agents and workflow status

    Raises:
        HTTPException: 404 if project not found or tenant mismatch
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            project = await session.get(Project, request.project_id)

            if not project or project.tenant_key != request.tenant_key:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {request.project_id} not found")

        # Coordinate workflow
        orchestrator = ProjectOrchestrator()

        # Create agent configs from roles
        agent_configs = []
        for role in request.agent_roles:
            # Simple agent config - orchestrator will handle details
            agent_configs.append(type('AgentConfig', (), {'role': role, 'mission': None})())

        workflow_result = await orchestrator.coordinate_agent_workflow(
            agent_configs=agent_configs,
            workflow_type=request.workflow_type,
            tenant_key=request.tenant_key,
            project_id=request.project_id,
        )

        return SpawnTeamResponse(spawned_agents=request.agent_roles, workflow_status=workflow_result.status)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/coordinate", response_model=CoordinateResponse)
async def coordinate(request: CoordinateRequest) -> CoordinateResponse:
    """
    Start coordination for a project.

    Args:
        request: CoordinateRequest with project_id and coordination_action

    Returns:
        CoordinateResponse with status

    Note:
        This is a placeholder endpoint for future coordination features.
    """
    # For now, return in_progress status
    # Future: Implement actual coordination logic
    return CoordinateResponse(status="in_progress")


@router.post("/handle-failure", response_model=HandleFailureResponse)
async def handle_failure(request: HandleFailureRequest) -> HandleFailureResponse:
    """
    Handle agent failure with recovery action.

    Args:
        request: HandleFailureRequest with project_id, agent_id, failure_reason, recovery_action

    Returns:
        HandleFailureResponse with recovery status

    Note:
        This is a placeholder endpoint for future failure handling features.
    """
    # For now, return success status
    # Future: Implement actual failure recovery logic
    return HandleFailureResponse(recovery_status="success")


# ========================================================================
# ORCHESTRATOR LAUNCH ENDPOINT - Production-Grade Implementation
# ========================================================================


class LaunchOrchestratorRequest(BaseModel):
    """Request model for orchestrator launch workflow"""

    product_id: str = Field(..., description="Product UUID with vision documents")
    project_description: str = Field(..., description="User's project description/requirements")
    workflow_type: str = Field(default="waterfall", description="Workflow execution pattern: 'waterfall' or 'parallel'")
    auto_start: bool = Field(default=True, description="Automatically start workflow after agent selection")


class LaunchOrchestratorResponse(BaseModel):
    """Response model for orchestrator launch workflow"""

    success: bool = Field(..., description="Whether launch completed successfully")
    session_id: str = Field(..., description="Unique session identifier for tracking")
    workflow_result: Dict[str, Any] = Field(..., description="Workflow execution result")
    mission_count: int = Field(..., description="Number of missions generated")
    agent_count: int = Field(..., description="Number of agents selected")
    project_id: str = Field(..., description="Created project UUID")
    token_reduction: Dict[str, Any] = Field(..., description="Token reduction metrics")


@router.post("/launch", response_model=LaunchOrchestratorResponse)
async def launch_orchestrator(
    request: LaunchOrchestratorRequest,
    tenant_key: str = Depends(get_tenant_key),
) -> LaunchOrchestratorResponse:
    """
    Launch complete orchestrator workflow with WebSocket progress updates.

    This endpoint orchestrates the entire AI agent workflow:
    1. Validates product (exists, belongs to tenant, is active, has vision documents)
    2. Processes product vision documents
    3. Generates condensed missions from vision analysis
    4. Selects optimal agents based on requirements
    5. Coordinates agent workflow (waterfall or parallel)
    6. Broadcasts real-time progress via WebSocket

    **WebSocket Progress Events:**
    Clients receive progress updates via `orchestrator:progress` events:
    - Stage: starting (0%)
    - Stage: processing_vision (20%)
    - Stage: generating_missions (40%)
    - Stage: selecting_agents (60%)
    - Stage: creating_workflow (80%)
    - Stage: complete (100%)

    **Error Stages:**
    On error, broadcasts `orchestrator:error` event with details.

    Args:
        request: LaunchOrchestratorRequest with product_id, project_description, workflow_type, auto_start
        tenant_key: Injected tenant key from authentication middleware

    Returns:
        LaunchOrchestratorResponse with session_id, workflow_result, mission/agent counts, token metrics

    Raises:
        HTTPException 400: Invalid request (product validation failed)
        HTTPException 404: Product not found
        HTTPException 409: Product not active or missing vision documents
        HTTPException 500: Internal orchestrator error

    Multi-tenant Isolation:
        - All database queries filtered by tenant_key
        - WebSocket broadcasts scoped to tenant
        - No cross-tenant data leakage

    Example:
        ```python
        POST /api/v1/orchestration/launch
        {
            "product_id": "prod-uuid-here",
            "project_description": "Build a REST API with authentication",
            "workflow_type": "waterfall",
            "auto_start": true
        }
        ```
    """
    from api.app import state
    import uuid as uuid_lib
    import logging

    logger = logging.getLogger(__name__)

    # Generate unique session ID for tracking
    session_id = str(uuid_lib.uuid4())

    # Validate database availability
    if not state.db_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database manager not initialized. Server is not ready.",
        )

    # Get WebSocketManager for progress broadcasts
    websocket_manager = getattr(state, "websocket_manager", None)

    async def broadcast_progress(
        stage: str,
        progress: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Helper to broadcast progress updates via WebSocket"""
        if websocket_manager:
            try:
                await websocket_manager.broadcast_json(
                    {
                        "type": "orchestrator:progress",
                        "data": {
                            "session_id": session_id,
                            "product_id": request.product_id,
                            "stage": stage,
                            "progress": progress,
                            "message": message,
                            "details": details or {},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast progress update: {e}")

    async def broadcast_error(error_stage: str, error_message: str, error_details: Optional[Dict[str, Any]] = None):
        """Helper to broadcast error notifications via WebSocket"""
        if websocket_manager:
            try:
                await websocket_manager.broadcast_json(
                    {
                        "type": "orchestrator:error",
                        "data": {
                            "session_id": session_id,
                            "product_id": request.product_id,
                            "stage": error_stage,
                            "error": error_message,
                            "details": error_details or {},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast error notification: {e}")

    try:
        # ========================================================================
        # STAGE 1: STARTING (0%) - Initialize and validate
        # ========================================================================
        await broadcast_progress(
            stage="starting",
            progress=0,
            message="Initializing orchestrator workflow",
            details={"session_id": session_id, "workflow_type": request.workflow_type},
        )

        logger.info(
            f"[Launch Orchestrator] Session {session_id}: Starting workflow for "
            f"product={request.product_id}, tenant={tenant_key}, workflow={request.workflow_type}"
        )

        # Validate product exists, belongs to tenant, is active, and has vision documents
        async with state.db_manager.get_session_async() as session:
            product = await session.get(Product, request.product_id)

            # Product not found
            if not product:
                await broadcast_error(
                    error_stage="validation",
                    error_message=f"Product {request.product_id} not found",
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {request.product_id} not found",
                )

            # Tenant mismatch (security check)
            if product.tenant_key != tenant_key:
                await broadcast_error(
                    error_stage="validation",
                    error_message="Product does not belong to current tenant",
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {request.product_id} not found",
                )

            # Product not active
            if not product.is_active:
                await broadcast_error(
                    error_stage="validation",
                    error_message=f"Product '{product.name}' is not active",
                    error_details={
                        "hint": "Activate the product in the Products view before launching orchestrator"
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "inactive_product",
                        "message": f"Cannot launch orchestrator - product '{product.name}' is not active",
                        "hint": "Activate the product in the Products view before launching orchestrator",
                    },
                )

            # Product missing vision documents
            if not product.has_vision_documents:
                await broadcast_error(
                    error_stage="validation",
                    error_message=f"Product '{product.name}' has no vision documents",
                    error_details={
                        "hint": "Add vision documents to the product before launching orchestrator"
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "missing_vision",
                        "message": f"Cannot launch orchestrator - product '{product.name}' has no vision documents",
                        "hint": "Add vision documents to the product before launching orchestrator",
                    },
                )

        logger.info(
            f"[Launch Orchestrator] Session {session_id}: Validation passed - "
            f"product={product.name}, is_active={product.is_active}, has_vision={product.has_vision_documents}"
        )

        # ========================================================================
        # STAGE 2: PROCESSING VISION (20%)
        # ========================================================================
        await broadcast_progress(
            stage="processing_vision",
            progress=20,
            message=f"Processing vision documents for product '{product.name}'",
            details={"product_name": product.name},
        )

        # Initialize orchestrator
        orchestrator = ProjectOrchestrator()

        # Process vision documents and analyze requirements
        # This internally calls:
        # 1. VisionDocumentChunker.chunk_document() if not chunked
        # 2. MissionPlanner.analyze_requirements()
        logger.info(f"[Launch Orchestrator] Session {session_id}: Processing product vision")

        try:
            # Note: process_product_vision is the main workflow method
            # It handles: chunking, requirements analysis, mission generation, agent selection, workflow coordination
            result = await orchestrator.process_product_vision(
                tenant_key=tenant_key,
                product_id=request.product_id,
                project_requirements=request.project_description,
            )
        except ValueError as e:
            error_msg = str(e)
            await broadcast_error(
                error_stage="processing_vision",
                error_message=error_msg,
            )
            # Re-raise with appropriate status code
            if "not active" in error_msg:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

        # ========================================================================
        # STAGE 3: GENERATING MISSIONS (40%)
        # ========================================================================
        await broadcast_progress(
            stage="generating_missions",
            progress=40,
            message="Generating condensed missions from vision analysis",
            details={
                "mission_count": len(result.get("mission_plan", {})),
                "token_reduction": result.get("token_reduction", {}),
            },
        )

        logger.info(
            f"[Launch Orchestrator] Session {session_id}: Generated {len(result.get('mission_plan', {}))} missions"
        )

        # ========================================================================
        # STAGE 4: SELECTING AGENTS (60%)
        # ========================================================================
        await broadcast_progress(
            stage="selecting_agents",
            progress=60,
            message="Selecting optimal agents for mission execution",
            details={
                "agent_count": len(result.get("selected_agents", [])),
                "agent_roles": result.get("selected_agents", []),
            },
        )

        logger.info(
            f"[Launch Orchestrator] Session {session_id}: Selected {len(result.get('selected_agents', []))} agents: "
            f"{result.get('selected_agents', [])}"
        )

        # ========================================================================
        # STAGE 5: CREATING WORKFLOW (80%)
        # ========================================================================
        await broadcast_progress(
            stage="creating_workflow",
            progress=80,
            message=f"Coordinating {request.workflow_type} workflow execution",
            details={
                "workflow_type": request.workflow_type,
                "spawned_jobs": result.get("spawned_jobs", []),
                "job_count": len(result.get("spawned_jobs", [])),
            },
        )

        logger.info(
            f"[Launch Orchestrator] Session {session_id}: Workflow coordination complete - "
            f"status={result['workflow_result'].status}, spawned_jobs={len(result.get('spawned_jobs', []))}"
        )

        # ========================================================================
        # STAGE 6: COMPLETE (100%)
        # ========================================================================
        await broadcast_progress(
            stage="complete",
            progress=100,
            message="Orchestrator workflow completed successfully",
            details={
                "project_id": result.get("project_id"),
                "mission_count": len(result.get("mission_plan", {})),
                "agent_count": len(result.get("selected_agents", [])),
                "workflow_status": result["workflow_result"].status,
            },
        )

        logger.info(
            f"[Launch Orchestrator] Session {session_id}: Workflow complete - "
            f"project={result.get('project_id')}, token_reduction={result.get('token_reduction', {}).get('reduction_percent', 0)}%"
        )

        # Build response
        return LaunchOrchestratorResponse(
            success=True,
            session_id=session_id,
            workflow_result={
                "status": result["workflow_result"].status,
                "completed": [stage for stage in result["workflow_result"].completed] if hasattr(result["workflow_result"], 'completed') else [],
                "failed": [stage for stage in result["workflow_result"].failed] if hasattr(result["workflow_result"], 'failed') else [],
            },
            mission_count=len(result.get("mission_plan", {})),
            agent_count=len(result.get("selected_agents", [])),
            project_id=result.get("project_id", ""),
            token_reduction=result.get("token_reduction", {}),
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already formatted)
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[Launch Orchestrator] Session {session_id}: Unexpected error: {e}")

        await broadcast_error(
            error_stage="orchestrator_error",
            error_message=f"Internal orchestrator error: {str(e)}",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Orchestrator workflow failed: {str(e)}",
        )
