"""
Task management API endpoints with product isolation
"""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


router = APIRouter()


class TaskCreate(BaseModel):
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    category: Optional[str] = Field(None, description="Task category")
    priority: str = Field("medium", description="Task priority")
    product_id: Optional[str] = Field(None, description="Product ID for isolation")
    project_id: Optional[str] = Field(None, description="Associated project ID")


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    category: Optional[str]
    priority: str
    status: str
    product_id: Optional[str]
    project_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    """Create a new task with product isolation"""
    try:
        from giljo_mcp.api_helpers import create_task_for_api

        result = await create_task_for_api(
            title=task.title,
            description=task.description,
            category=task.category,
            priority=task.priority,
            product_id=task.product_id,
            project_id=task.project_id,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create task"))  # noqa: TRY301

        return TaskResponse(
            id=result.get("task_id", ""),
            title=task.title,
            description=task.description,
            category=task.category,
            priority=task.priority,
            status="pending",
            product_id=task.product_id,
            project_id=task.project_id,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of tasks to return"),
):
    """List tasks with product isolation and optional filters"""
    try:
        from giljo_mcp.api_helpers import list_tasks_for_api

        result = await list_tasks_for_api(
            product_id=product_id,
            project_id=project_id,
            status=status,
            priority=priority,
            category=category,
            limit=limit,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to list tasks"))  # noqa: TRY301

        tasks = []
        for task_data in result.get("tasks", []):
            tasks.append(
                TaskResponse(
                    id=task_data["id"],
                    title=task_data["title"],
                    description=task_data["description"],
                    category=task_data["category"],
                    priority=task_data["priority"],
                    status=task_data["status"],
                    product_id=task_data["product_id"],
                    project_id=task_data["project_id"],
                    created_at=(
                        datetime.fromisoformat(task_data["created_at"])
                        if task_data["created_at"]
                        else datetime.now(timezone.utc)
                    ),
                    started_at=datetime.fromisoformat(task_data["started_at"]) if task_data["started_at"] else None,
                    completed_at=(
                        datetime.fromisoformat(task_data["completed_at"]) if task_data["completed_at"] else None
                    ),
                )
            )

        return tasks  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_task_summary(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
) -> dict[str, Any]:
    """Get task summary grouped by product"""
    try:
        from giljo_mcp.api_helpers import get_product_task_summary_for_api

        result = await get_product_task_summary_for_api(product_id=product_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to get task summary"))

        return result  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
