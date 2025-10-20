"""
Orchestration REST API endpoints (Handover 0020 Phase 3A).

Provides REST API for the complete orchestration workflow:
- Vision processing
- Mission generation
- Agent team spawning
- Workflow coordination
- Metrics and status monitoring
"""

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
        # ValueError from orchestrator indicates missing vision or invalid data
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
