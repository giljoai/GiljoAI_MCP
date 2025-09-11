"""
Task management API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()

class TaskCreate(BaseModel):
    content: str = Field(..., description="Task content")
    category: Optional[str] = Field(None, description="Task category")
    priority: str = Field("medium", description="Task priority")

class TaskResponse(BaseModel):
    id: str
    content: str
    category: Optional[str]
    priority: str
    status: str
    created_at: datetime

@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    """Create a new task"""
    try:
        from giljo_mcp.tools.task import log_task
        result = await log_task(
            content=task.content,
            category=task.category,
            priority=task.priority
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create task"))
        
        return TaskResponse(
            id=result.get("task_id", ""),
            content=task.content,
            category=task.category,
            priority=task.priority,
            status="pending",
            created_at=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List tasks with optional filters"""
    # This would need implementation in the MCP tools
    # For now, return empty list as placeholder
    return []