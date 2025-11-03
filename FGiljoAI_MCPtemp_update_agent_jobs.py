"""
Temporary script to update agent_jobs.py with production-grade WebSocket dependency injection.
Handover 0086B Task 3.1
"""

with open('api/endpoints/agent_jobs.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add new imports after line 34 (after AsyncSession import)
old_import_line = "from sqlalchemy.ext.asyncio import AsyncSession"
new_imports = """from sqlalchemy.ext.asyncio import AsyncSession

# Handover 0086B: Production-grade WebSocket dependency injection
from api.dependencies.websocket import get_websocket_dependency, WebSocketDependency
from api.events.schemas import EventFactory"""

content = content.replace(old_import_line, new_imports)

# 2. Replace the create_job function's signature and WebSocket section
old_function_start = """@router.post("/", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_request: JobCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> JobCreateResponse:"""

new_function_start = """@router.post("/", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_request: JobCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency)
) -> JobCreateResponse:"""

content = content.replace(old_function_start, new_function_start)

# 3. Replace the WebSocket emission section (lines 204-241)
old_websocket_code = """    # Emit WebSocket event for real-time UI update (Handover 0086)
    try:
        from api.app import state

        websocket_manager = getattr(state, "websocket_manager", None)
        if websocket_manager:
            # Serialize agent data
            agent_data = {
                "job_id": str(job.job_id),
                "agent_type": job.agent_type,
                "status": "waiting",
                "priority": 5,  # Default priority
                "created_at": job.created_at.isoformat() if job.created_at else datetime.now(timezone.utc).isoformat(),
            }

            # Broadcast to tenant-specific clients only (multi-tenant isolation)
            for client_id, ws in websocket_manager.active_connections.items():
                auth_context = websocket_manager.auth_contexts.get(client_id, {})
                if auth_context.get("tenant_key") == current_user.tenant_key:
                    try:
                        await ws.send_json(
                            {
                                "type": "agent:created",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "schema_version": "1.0",
                                "data": {
                                    "project_id": getattr(job, "project_id", None),
                                    "tenant_key": current_user.tenant_key,
                                    "agent": agent_data,
                                },
                            }
                        )
                    except Exception:
                        # Client disconnected or error sending - continue
                        pass
    except Exception as ws_error:
        logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")
        # Non-critical - continue without WebSocket broadcast"""

new_websocket_code = """    # Emit WebSocket event for real-time UI update (Handover 0086B Task 3.1)
    # Production-grade implementation with dependency injection
    try:
        # Serialize agent data
        agent_data = {
            "job_id": str(job.job_id),
            "agent_type": job.agent_type,
            "status": "waiting",
            "priority": 5,  # Default priority
            "created_at": job.created_at.isoformat() if job.created_at else datetime.now(timezone.utc).isoformat(),
        }

        # Use EventFactory for standardized event format
        project_id = getattr(job, "project_id", None)
        if project_id:
            project_id = str(project_id)

        # Broadcast via dependency injection
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="agent:created",
            data={
                "project_id": project_id,
                "tenant_key": current_user.tenant_key,
                "agent": agent_data,
            }
        )

        logger.info(
            f"Agent creation broadcasted to {sent_count} clients",
            extra={
                "job_id": str(job.job_id),
                "agent_type": job.agent_type,
                "tenant_key": current_user.tenant_key,
                "sent_count": sent_count
            }
        )
    except Exception as e:
        logger.error(
            f"Failed to broadcast agent creation: {e}",
            extra={
                "job_id": str(job.job_id),
                "agent_type": job.agent_type,
                "tenant_key": current_user.tenant_key
            },
            exc_info=True
        )
        # Non-critical - continue without WebSocket broadcast"""

content = content.replace(old_websocket_code, new_websocket_code)

# Write the updated content
with open('api/endpoints/agent_jobs.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Task 3.1 complete: agent_jobs.py updated with production-grade WebSocket dependency injection")
