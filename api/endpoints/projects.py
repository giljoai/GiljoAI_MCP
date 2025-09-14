"""
Project management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

router = APIRouter()

# Pydantic models for request/response
class ProjectCreate(BaseModel):
    name: str = Field(..., description="Project name")
    mission: str = Field(..., description="Project mission statement")
    agents: Optional[List[str]] = Field(None, description="Initial agent list")

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    mission: Optional[str] = None
    status: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    mission: str
    status: str
    created_at: datetime
    updated_at: datetime
    context_budget: int
    context_used: int
    agent_count: int
    message_count: int

@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    from api.app import state
    
    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Create project in database
        project_id = str(uuid.uuid4())
        
        # Use the tool accessor
        result = await state.api_state.tool_accessor.create_project(
            name=project.name,
            mission=project.mission,
            agents=project.agents
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create project"))
        
        response = ProjectResponse(
            id=result["project_id"],
            name=project.name,
            mission=project.mission,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            context_budget=150000,
            context_used=0,
            agent_count=0,
            message_count=0
        )
        
        # Broadcast project creation
        if state.api_state.websocket_manager:
            await state.api_state.websocket_manager.broadcast_project_update(
                project_id=result["project_id"],
                update_type="created",
                project_data={
                    "name": project.name,
                    "mission": project.mission,
                    "status": "active",
                    "context_budget": 150000,
                    "context_used": 0
                }
            )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip")
):
    """List all projects"""
    from api.app import state
    
    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        result = await state.api_state.tool_accessor.list_projects(status=status)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to list projects"))
        
        projects = []
        for proj in result.get("projects", [])[offset:offset+limit]:
            projects.append(ProjectResponse(
                id=proj["id"],
                name=proj["name"],
                mission=proj["mission"],
                status=proj["status"],
                created_at=datetime.fromisoformat(proj["created_at"]),
                updated_at=datetime.fromisoformat(proj.get("updated_at", proj["created_at"])),
                context_budget=proj.get("context_budget", 150000),
                context_used=proj.get("context_used", 0),
                agent_count=proj.get("agent_count", 0),
                message_count=proj.get("message_count", 0)
            ))
        
        return projects
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project details"""
    from api.app import state
    
    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        result = await state.api_state.tool_accessor.project_status(project_id=project_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Project not found")
        
        proj = result["project"]
        return ProjectResponse(
            id=proj["id"],
            name=proj["name"],
            mission=proj["mission"],
            status=proj["status"],
            created_at=datetime.fromisoformat(proj["created_at"]),
            updated_at=datetime.fromisoformat(proj.get("updated_at", proj["created_at"])),
            context_budget=proj.get("context_budget", 150000),
            context_used=proj.get("context_used", 0),
            agent_count=len(result.get("agents", [])),
            message_count=result.get("pending_messages", 0)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, update: ProjectUpdate):
    """Update project details"""
    from api.app import state
    
    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Update mission if provided
        if update.mission:
            result = await state.api_state.tool_accessor.update_project_mission(
                project_id=project_id,
                mission=update.mission
            )
            
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error", "Failed to update project"))
        
        # Get updated project
        return await get_project(project_id)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{project_id}")
async def close_project(project_id: str, summary: str = Query(..., description="Closing summary")):
    """Close a project"""
    from api.app import state
    
    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        result = await state.api_state.tool_accessor.close_project(
            project_id=project_id,
            summary=summary
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to close project"))
        
        # Broadcast project closure
        if state.api_state.websocket_manager:
            await state.api_state.websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type="closed",
                project_data={
                    "status": "closed",
                    "summary": summary
                }
            )
        
        return {"success": True, "message": "Project closed successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))