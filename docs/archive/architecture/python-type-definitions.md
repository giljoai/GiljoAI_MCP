# Python Type Definitions - Unified Agent State Architecture

## JobStatus Enum

**Location:** `src/giljo_mcp/types/job_status.py`

```python
from enum import Enum
from typing import Set

class JobStatus(str, Enum):
    """Agent job status states (ADR-0108)."""
    
    # Active States
    WAITING = "waiting"
    PREPARING = "preparing"
    WORKING = "working"
    REVIEW = "review"
    BLOCKED = "blocked"
    
    # Terminal States
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DECOMMISSIONED = "decommissioned"
    
    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal."""
        return self in {
            JobStatus.COMPLETE, JobStatus.FAILED,
            JobStatus.CANCELLED, JobStatus.DECOMMISSIONED
        }
    
    @property
    def is_active(self) -> bool:
        """Check if status is active."""
        return not self.is_terminal
    
    def can_transition_to(self, new_status: 'JobStatus') -> bool:
        """Check if transition is valid."""
        return new_status in VALID_TRANSITIONS.get(self, set())

# Valid state transitions
VALID_TRANSITIONS: dict[JobStatus, Set[JobStatus]] = {
    JobStatus.WAITING: {
        JobStatus.PREPARING, JobStatus.FAILED, JobStatus.CANCELLED
    },
    JobStatus.PREPARING: {
        JobStatus.WORKING, JobStatus.FAILED, JobStatus.CANCELLED
    },
    JobStatus.WORKING: {
        JobStatus.REVIEW, JobStatus.COMPLETE, JobStatus.FAILED,
        JobStatus.BLOCKED, JobStatus.CANCELLED
    },
    JobStatus.REVIEW: {
        JobStatus.COMPLETE, JobStatus.WORKING, JobStatus.FAILED
    },
    JobStatus.BLOCKED: {
        JobStatus.WORKING, JobStatus.CANCELLED, JobStatus.FAILED
    },
    # Terminal states
    JobStatus.COMPLETE: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
    JobStatus.DECOMMISSIONED: set()
}
```

## Pydantic Models

**Location:** `api/schemas/agent_jobs.py`

```python
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from src.giljo_mcp.types.job_status import JobStatus

class StateTransitionRequest(BaseModel):
    """Request to transition job to new status."""
    new_status: JobStatus
    reason: str = Field(..., min_length=1, max_length=500)
    metadata: Optional[Dict[str, Any]] = None

class StateTransitionResponse(BaseModel):
    """Response from state transition."""
    job_id: str
    old_status: JobStatus
    new_status: JobStatus
    timestamp: datetime
    success: bool
    message: Optional[str] = None

class JobCancellationRequest(BaseModel):
    """Request to cancel a job."""
    reason: str = Field(..., min_length=1, max_length=500)

class JobCancellationResponse(BaseModel):
    """Response from job cancellation."""
    job_id: str
    status: JobStatus
    message: str
    cancelled_at: datetime

class DecommissionRequest(BaseModel):
    """Request to decommission an agent."""
    reason: str = Field(..., min_length=1, max_length=500)

class DecommissionResponse(BaseModel):
    """Response from agent decommission."""
    job_id: str
    status: JobStatus
    message: str
    decommissioned_at: datetime

class VersionConflictError(BaseModel):
    """Error response for optimistic locking conflicts."""
    error: str = "Version conflict"
    job_id: str
    expected_version: int
    actual_version: int
    message: str = "Job modified by another process. Refresh and retry."
```

## WebSocket Event Models

**Location:** `api/schemas/websocket_events.py`

```python
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel
from src.giljo_mcp.types.job_status import JobStatus

class JobStatusChangedEvent(BaseModel):
    """WebSocket event for job status changes."""
    event: Literal["job:status_changed"] = "job:status_changed"
    data: dict

class JobStatusChangedData(BaseModel):
    """Data payload for job:status_changed event."""
    job_id: str
    agent_type: str
    agent_name: Optional[str]
    old_status: JobStatus
    new_status: JobStatus
    timestamp: datetime
    reason: Optional[str]
    triggered_by: str
    trigger_source: Literal["user_action", "agent_action", "health_monitor", "system"]
    is_terminal: bool
    metadata: Optional[Dict[str, Any]] = None

class JobMessageBlockedEvent(BaseModel):
    """WebSocket event for blocked messages."""
    event: Literal["job:message_blocked"] = "job:message_blocked"
    data: dict

class JobMessageBlockedData(BaseModel):
    """Data payload for job:message_blocked event."""
    job_id: str
    agent_type: str
    agent_status: JobStatus
    message_id: str
    from_agent: str
    blocked_reason: str
    timestamp: datetime
    suggested_action: str
```
