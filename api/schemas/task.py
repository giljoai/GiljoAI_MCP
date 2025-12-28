"""
Task API Pydantic schemas for Phase 4: Task-Centric Multi-User Dashboard.

Provides request/response models for:
- Task updates (PATCH /tasks/{id})
- Task conversion to projects (POST /tasks/{id}/convert)
- Task responses with user fields
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    """
    Schema for creating a task (POST /tasks/).

    Product and project are optional to allow unscoped tasks.
    """

    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[str] = Field(
        None, description="Task status: pending, in_progress, completed, blocked, cancelled, converted"
    )
    priority: Optional[str] = Field(None, description="Task priority: low, medium, high, critical")
    category: Optional[str] = Field(None, max_length=100, description="Task category")
    product_id: Optional[str] = Field(None, description="Product ID for isolation")
    project_id: Optional[str] = Field(None, description="Associated project ID")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID for hierarchy")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    estimated_effort: Optional[float] = Field(None, ge=0, description="Estimated effort in hours")
    actual_effort: Optional[float] = Field(None, ge=0, description="Actual effort in hours")

    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    """
    Schema for updating a task (PATCH /tasks/{id}).

    Users can update their own tasks or tasks assigned to them.
    Admins can update any task in their tenant.
    """

    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[str] = Field(
        None, description="Task status: pending, in_progress, completed, blocked, cancelled, converted"
    )
    priority: Optional[str] = Field(None, description="Task priority: low, medium, high, critical")
    category: Optional[str] = Field(None, max_length=100, description="Task category")
    # Handover 0076: Removed assigned_to_user_id field
    estimated_effort: Optional[float] = Field(None, ge=0, description="Estimated effort in hours")
    actual_effort: Optional[float] = Field(None, ge=0, description="Actual effort in hours")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID for hierarchy changes")
    product_id: Optional[str] = Field(None, description="Update product scope")
    project_id: Optional[str] = Field(None, description="Update associated project")

    model_config = ConfigDict(from_attributes=True)


class TaskConversionRequest(BaseModel):
    """
    Schema for task-to-project conversion (POST /tasks/{id}/convert).

    Conversion strategies:
    - single: Convert task + subtasks to one project
    - individual: Convert each subtask to separate project
    - grouped: Group subtasks by category into projects
    """

    project_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Name for new project (defaults to task title)"
    )
    strategy: str = Field("single", description="Conversion strategy: single | individual | grouped")
    include_subtasks: bool = Field(True, description="Include subtasks in conversion")

    model_config = ConfigDict(from_attributes=True)


class ProjectConversionResponse(BaseModel):
    """
    Schema for conversion response after creating project from task.
    """

    project_id: str = Field(..., description="ID of created project")
    project_name: str = Field(..., description="Name of created project")
    original_task_id: str = Field(..., description="ID of original task")
    conversion_strategy: str = Field(..., description="Strategy used for conversion")
    created_at: datetime = Field(..., description="Project creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(BaseModel):
    """
    Enhanced task response with user fields for Phase 4.

    Includes:
    - User ownership (created_by_user_id)
    - User assignment (assigned_to_user_id)
    - Conversion tracking (converted_to_project_id)
    """

    id: str = Field(..., description="Task ID")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    category: Optional[str] = Field(None, description="Task category")
    status: str = Field(..., description="Task status")
    priority: str = Field(..., description="Task priority")
    product_id: Optional[str] = Field(None, description="Product ID for isolation")
    project_id: Optional[str] = Field(
        None, description="Associated project ID (nullable for unassigned tasks - Handover 0072)"
    )

    # Handover 0072/0381: Agent job integration (renamed from agent_job_id)
    job_id: Optional[str] = Field(None, description="Linked agent job ID for execution tracking")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID for subtasks")

    # Phase 4: User fields (Handover 0076: removed assigned_to_user_id)
    created_by_user_id: Optional[str] = Field(None, description="User who created task")
    converted_to_project_id: Optional[str] = Field(None, description="Project ID if task was converted")

    # Timestamps
    created_at: datetime = Field(..., description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    due_date: Optional[datetime] = Field(None, description="Task due date")

    # Effort tracking
    estimated_effort: Optional[float] = Field(None, description="Estimated effort in hours")
    actual_effort: Optional[float] = Field(None, description="Actual effort in hours")

    model_config = ConfigDict(from_attributes=True)


class StatusUpdate(BaseModel):
    """Schema for status-only updates."""

    status: str = Field(..., description="New task status")
