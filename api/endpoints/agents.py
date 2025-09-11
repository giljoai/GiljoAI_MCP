"""
Agent management API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()

class AgentCreate(BaseModel):
    project_id: str = Field(..., description="Project ID")
    agent_name: str = Field(..., description="Agent name")
    mission: Optional[str] = Field(None, description="Agent mission")

class AgentResponse(BaseModel):
    id: str
    name: str
    project_id: str
    status: str
    mission: Optional[str]
    created_at: datetime
    health: dict

@router.post("/", response_model=AgentResponse)
async def create_agent(agent: AgentCreate):
    """Create or ensure an agent exists"""
    from api.app import state
    
    try:
        result = await state.api_state.tool_accessor.ensure_agent(
            project_id=agent.project_id,
            agent_name=agent.agent_name,
            mission=agent.mission
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create agent"))
        
        return AgentResponse(
            id=result.get("agent_id", agent.agent_name),
            name=agent.agent_name,
            project_id=agent.project_id,
            status="active",
            mission=agent.mission,
            created_at=datetime.utcnow(),
            health={"status": "healthy", "context_used": 0}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_name}/health", response_model=dict)
async def get_agent_health(agent_name: str):
    """Get agent health status"""
    from api.app import state
    
    try:
        result = await state.api_state.tool_accessor.agent_health(agent_name=agent_name)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return result.get("health", {})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_name}/decommission")
async def decommission_agent(
    agent_name: str,
    project_id: str = Query(..., description="Project ID"),
    reason: str = Query("completed", description="Decommission reason")
):
    """Decommission an agent"""
    from api.app import state
    
    try:
        result = await state.api_state.tool_accessor.decommission_agent(
            agent_name=agent_name,
            project_id=project_id,
            reason=reason
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to decommission agent"))
        
        return {"success": True, "message": f"Agent {agent_name} decommissioned"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))