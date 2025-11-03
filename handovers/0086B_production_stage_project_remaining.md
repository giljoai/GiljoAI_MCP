# Handover 0086B: Production-Grade Stage Project - Remaining Work

**Status**: Ready for Implementation
**Priority**: CRITICAL - Commercial Product Core
**Continuation of**: Handover 0086A
**Scope**: Phases 2 (final task), 3, 4, 5, and 6
**Estimated Effort**: 200 hours (8 weeks remaining)
**Quality Target**: 85%+ test coverage, zero band-aids

---

## Executive Summary

**Current State**: Phase 1 (100% complete) and Phase 2 (95% complete) from Handover 0086A are done. We have established production-grade infrastructure patterns including:
- ✅ Standardized data model with `@hybrid_property` for backwards compatibility
- ✅ WebSocket dependency injection system (`api/dependencies/websocket.py`)
- ✅ `broadcast_to_tenant()` method in WebSocketManager
- ✅ Event schema standardization via EventFactory
- ✅ Refactored project.py to use dependency injection
- ✅ User configuration propagation chain (`user_id` parameter added throughout)
- ✅ Field Priority System (4/5 methods implemented in mission_planner.py)
- ✅ WebSocket events updated with `user_config_applied` flag

**Remaining Work**: One critical stub to complete in Phase 2, then complete Phases 3-6 for mission generation enhancement, frontend production-grade quality, comprehensive testing, and documentation.

**Business Impact**:
- ✅ Enables monetization-ready commercial product
- ✅ Achieves **70% token reduction** through proper user configuration
- ✅ Provides real-time UI updates for premium user experience
- ✅ Ensures multi-tenant isolation for enterprise customers

---

## What's Already Done - Quick Reference

For complete implementation details, see **Handover 0086A** (`F:\GiljoAI_MCP\handovers\0086A_production_grade_stage_project.md`).

### Phase 1: Foundation ✅ (100% Complete)
- **Task 1.1**: `@hybrid_property` added to Project model (`src/giljo_mcp/models.py`)
- **Task 1.2**: WebSocket dependency injection created (`api/dependencies/websocket.py`)
- **Task 1.3**: `broadcast_to_tenant()` method added to WebSocketManager (`api/websocket_manager.py`)
- **Task 1.4**: Event schemas standardized (`api/events/schemas.py`)
- **Task 1.5**: Refactored `project.py` to use dependency injection

### Phase 2: Context Management ✅ (95% Complete)
- **Task 2.1**: `user_id` parameter chain added throughout orchestration flow
- **Task 2.2**: Field Priority System implemented with 4/5 methods:
  - ✅ `_get_detail_level(priority: int)` - Maps priority 1-10 to detail levels
  - ✅ `_abbreviate_codebase_summary()` - 50% token reduction
  - ✅ `_minimal_codebase_summary()` - 20% token reduction
  - ✅ `_format_field()` - Helper for field formatting
  - ⚠️ **STUB**: `_build_context_with_priorities()` at line 516 needs full implementation
- **Task 2.3**: WebSocket events include `user_config_applied` flag

---

## Critical Context for Implementers

### 1. Zero Band-Aids Philosophy
**CRITICAL**: All code must be production-grade. No temporary fixes, no "V2" variants, no commented-out code. If you encounter an issue, fix it properly or create a new handover task.

### 2. 70% Token Reduction Goal
The **core business value** of this refactoring is achieving 70% token reduction through intelligent field prioritization. Every implementation decision should optimize for this goal.

**How it works**:
- User sets field priorities (1-10) for each product vision field in My Settings
- Priority 10 = Full detail (100% tokens)
- Priority 6 = Abbreviated (50% tokens)
- Priority 2 = Minimal (20% tokens)
- Priority 0 = Excluded (0% tokens)
- Mission generation respects these priorities when building context

### 3. Multi-Tenant Isolation (Security Critical)
**EVERY** database query, WebSocket broadcast, and API endpoint MUST enforce tenant isolation via `tenant_key`. Zero exceptions.

```python
# ✅ CORRECT
project = db.query(Project).filter_by(
    id=project_id,
    tenant_key=current_user.tenant_key  # ALWAYS include
).first()

# ❌ WRONG - Security vulnerability
project = db.query(Project).filter_by(id=project_id).first()
```

### 4. WebSocket Event Standards
All events MUST use EventFactory from `api/events/schemas.py`:

```python
from api.events.schemas import EventFactory

event_data = EventFactory.project_mission_updated(
    project_id=project.id,
    tenant_key=project.tenant_key,
    mission=mission,
    token_estimate=len(mission) // 4,
    generated_by="orchestrator",
    user_config_applied=bool(user_id),
    field_priorities=field_priorities if user_id else None
)

await ws_dep.broadcast_to_tenant(
    tenant_key=current_user.tenant_key,
    event_type="project:mission_updated",
    data=event_data["data"]
)
```

### 5. Dependency Injection Pattern
**ALWAYS** use FastAPI dependency injection for WebSocket access:

```python
from api.dependencies.websocket import get_websocket_dependency, WebSocketDependency
from fastapi import Depends

@router.post("/endpoint")
async def endpoint(
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency)
):
    sent_count = await ws_dep.broadcast_to_tenant(...)
```

**NEVER** use the old pattern:
```python
# ❌ WRONG - Band-aid pattern from old code
websocket_manager = getattr(state, "websocket_manager", None)
if websocket_manager:
    for client_id, ws in websocket_manager.active_connections.items():
        # ... manual loop
```

### 6. File Locations Reference

**Backend Core**:
- `F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py` - Mission generation with field priorities
- `F:\GiljoAI_MCP\src\giljo_mcp\context_manager.py` - Role-based context filtering
- `F:\GiljoAI_MCP\api\dependencies\websocket.py` - WebSocket dependency injection
- `F:\GiljoAI_MCP\api\events\schemas.py` - Event schema standardization
- `F:\GiljoAI_MCP\api\websocket_manager.py` - WebSocket connection management

**Backend API**:
- `F:\GiljoAI_MCP\api\endpoints\agent_jobs.py` - Agent job management endpoints
- `F:\GiljoAI_MCP\api\endpoints\project.py` - Project endpoints (refactored)
- `F:\GiljoAI_MCP\api\endpoints\orchestration.py` - NEW: Mission regeneration endpoint

**Frontend**:
- `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue` - Stage Project UI
- `F:\GiljoAI_MCP\frontend\src\composables\useWebSocket.js` - WebSocket composable (needs memory leak fix)

**Tests**:
- `F:\GiljoAI_MCP\tests\dependencies\` - Dependency injection tests
- `F:\GiljoAI_MCP\tests\mission_planner\` - Mission generation tests
- `F:\GiljoAI_MCP\tests\api\` - API endpoint tests
- `F:\GiljoAI_MCP\tests\websocket\` - WebSocket tests

---

## Remaining Tasks - Detailed Breakdown

### Phase 2: Context Management - FINAL TASK ⚠️

#### Task 2.2 (COMPLETION): Implement `_build_context_with_priorities()`

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py` (line 516)
**Priority**: CRITICAL
**Dependencies**: None (helper methods already implemented)
**Estimated Time**: 4 hours

**Current State**: Method is a stub with `pass` statement at line 516

**Action**: Replace stub with full implementation that orchestrates field priority logic

**Implementation**:
```python
# File: F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py
# Location: Replace lines 516-518 (stub)

async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    user_id: UUID = None
) -> str:
    """
    Build context respecting user's field priorities for 70% token reduction.

    Args:
        product: Product model with vision document
        project: Project model with description
        field_priorities: Dict mapping field names to priority (1-10)
        user_id: User ID for logging (optional)

    Returns:
        Formatted context string with priority-based detail levels

    Example field_priorities:
        {
            "product_vision": 10,      # Full detail
            "project_description": 8,  # Full detail
            "codebase_summary": 4,     # Abbreviated (50% tokens)
            "architecture": 2,         # Minimal (20% tokens)
            "deployment_notes": 0      # Excluded
        }
    """
    if field_priorities is None:
        field_priorities = {}

    logger.info(
        f"Building context with field priorities (user_id: {user_id})",
        extra={
            "product_id": str(product.id),
            "project_id": str(project.id),
            "priorities": field_priorities
        }
    )

    context_sections = []
    total_tokens = 0

    # Product Vision (priority-based detail level)
    if priorities.get("product_vision", 0) > 0:
        vision_detail = self._get_detail_level(field_priorities["product_vision"])
        vision_text = await self._format_field(
            field_name="product_vision",
            content=product.vision_document,
            detail_level=vision_detail
        )
        context_sections.append(vision_text)
        total_tokens += self._count_tokens(vision_text)

    # Project Description (priority-based detail level)
    if field_priorities.get("project_description", 0) > 0:
        desc_detail = self._get_detail_level(field_priorities["project_description"])
        desc_text = await self._format_field(
            field_name="project_description",
            content=project.description,
            detail_level=desc_detail
        )
        context_sections.append(desc_text)
        total_tokens += self._count_tokens(desc_text)

    # Codebase Summary (abbreviated if priority < 8)
    if field_priorities.get("codebase_summary", 0) > 0:
        codebase_detail = self._get_detail_level(field_priorities["codebase_summary"])
        if codebase_detail == "full":
            codebase_text = project.codebase_summary or ""
        elif codebase_detail == "abbreviated":
            codebase_text = self._abbreviate_codebase_summary(project.codebase_summary)
        else:  # minimal
            codebase_text = self._minimal_codebase_summary(project.codebase_summary)

        if codebase_text:
            context_sections.append(f"## Codebase\n{codebase_text}")
            total_tokens += self._count_tokens(codebase_text)

    # Architecture (from product config_data)
    if field_priorities.get("architecture", 0) > 0 and product.config_data:
        arch_detail = self._get_detail_level(field_priorities["architecture"])
        arch_text = product.config_data.get("architecture", "")

        if arch_detail == "abbreviated":
            # Extract first paragraph only
            arch_text = arch_text.split("\n\n")[0] if arch_text else ""
        elif arch_detail == "minimal":
            # Extract first sentence only
            arch_text = arch_text.split(". ")[0] + "." if arch_text else ""

        if arch_text:
            context_sections.append(f"## Architecture\n{arch_text}")
            total_tokens += self._count_tokens(arch_text)

    # Log token usage and reduction
    logger.info(
        f"Context built: {total_tokens} tokens (priorities applied)",
        extra={
            "product_id": str(product.id),
            "project_id": str(project.id),
            "total_tokens": total_tokens,
            "priorities": field_priorities,
            "user_id": str(user_id) if user_id else None
        }
    )

    return "\n\n".join(context_sections)


def _count_tokens(self, text: str) -> int:
    """Simple token counting (4 chars per token approximation)."""
    return len(text) // 4 if text else 0
```

**Validation**:
```bash
# Test field priority system
cd F:\GiljoAI_MCP
python -m pytest tests/mission_planner/test_field_priorities.py -v

# Expected output:
# PASSED tests/mission_planner/test_field_priorities.py::test_full_detail_priority_10
# PASSED tests/mission_planner/test_field_priorities.py::test_abbreviated_priority_6
# PASSED tests/mission_planner/test_field_priorities.py::test_minimal_priority_2
# PASSED tests/mission_planner/test_field_priorities.py::test_exclude_priority_0
# PASSED tests/mission_planner/test_field_priorities.py::test_token_reduction_70_percent
```

**Success Criteria**:
- ✅ Priority 10 fields included with full detail
- ✅ Priority 6 fields abbreviated to 50% tokens
- ✅ Priority 2 fields minimal (20% tokens)
- ✅ Priority 0 fields completely excluded
- ✅ **Overall token reduction of 70%** compared to no priorities
- ✅ Structured logging with all context

---

### Phase 3: Mission Generation Enhancement (Weeks 5-7, 72 hours)

**Objective**: Production-grade mission generation with Serena integration

#### Task 3.1: Refactor agent_jobs.py WebSocket Emission

**File**: `F:\GiljoAI_MCP\api\endpoints\agent_jobs.py` (lines 203-240)
**Priority**: CRITICAL
**Dependencies**: Phase 1 complete ✅
**Estimated Time**: 4 hours

**Action**: Replace band-aid manual loop with dependency injection pattern

**Current Code (BAND-AID)**:
```python
# Lines 203-240
websocket_manager = getattr(state, "websocket_manager", None)
if websocket_manager:
    for client_id, ws in websocket_manager.active_connections.items():
        auth_context = websocket_manager.auth_contexts.get(client_id, {})
        if auth_context.get("tenant_key") == current_user.tenant_key:
            # ... manual broadcast
```

**Replace With (PRODUCTION-GRADE)**:
```python
# File: F:\GiljoAI_MCP\api\endpoints\agent_jobs.py
# Location: Replace lines 203-240

from api.dependencies.websocket import get_websocket_dependency, WebSocketDependency
from api.events.schemas import EventFactory
from fastapi import Depends

@router.post("/agent-jobs", response_model=AgentJobResponse)
async def create_agent_job(
    job_data: AgentJobCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency)  # INJECT
):
    """Create new agent job with WebSocket notification."""

    # ... existing job creation logic ...

    # Broadcast agent creation using injected dependency
    try:
        agent_data = {
            "job_id": str(job.job_id),
            "agent_type": job.agent_type,
            "status": "waiting",
            "priority": 5,
            "created_at": job.created_at.isoformat(),
        }

        # Use event factory for standardized format
        event_data = EventFactory.agent_created(
            project_id=job.project_id,
            tenant_key=current_user.tenant_key,
            agent=agent_data
        )

        # Broadcast via dependency
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="agent:created",
            data=event_data["data"]
        )

        logger.info(
            f"Agent creation broadcasted to {sent_count} clients",
            extra={
                "job_id": str(job.job_id),
                "agent_type": job.agent_type,
                "sent_count": sent_count
            }
        )
    except Exception as e:
        logger.error(f"Failed to broadcast agent creation: {e}", exc_info=True)

    return job
```

**Validation**:
```bash
cd F:\GiljoAI_MCP
python -m pytest tests/api/test_agent_jobs_websocket.py -v

# Expected output:
# PASSED tests/api/test_agent_jobs_websocket.py::test_create_agent_broadcasts
# PASSED tests/api/test_agent_jobs_websocket.py::test_tenant_isolation
```

**Success Criteria**:
- ✅ Uses FastAPI dependency injection
- ✅ Standardized event format via EventFactory
- ✅ Structured logging with context
- ✅ Graceful degradation when WebSocket unavailable

---

#### Task 3.2: Add Serena Integration Toggle to Mission Generation

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py` (lines 400-500)
**Priority**: HIGH
**Dependencies**: Task 2.2 (complete) ✅
**Estimated Time**: 8 hours

**Action**: Respect user's Serena toggle in mission generation

**Implementation**:
```python
# File: F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py
# Location: Add after _build_context_with_priorities method

async def _get_user_configuration(self, user_id: UUID) -> Dict[str, Any]:
    """
    Fetch user configuration including Serena toggle.

    Returns:
        {
            "field_priorities": {...},
            "serena_enabled": bool,
            "token_budget": int
        }
    """
    from src.giljo_mcp.models import UserSettings

    user_settings = await self.db.query(UserSettings).filter_by(
        user_id=user_id
    ).first()

    if not user_settings:
        # Return safe defaults
        return {
            "field_priorities": {},
            "serena_enabled": False,
            "token_budget": 100000  # Default 100K tokens
        }

    return {
        "field_priorities": user_settings.field_priorities or {},
        "serena_enabled": user_settings.serena_enabled or False,
        "token_budget": user_settings.token_budget or 100000
    }


async def generate_mission(
    self,
    project_id: UUID,
    user_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """Generate mission respecting user configuration."""

    # Get user config
    user_config = {}
    if user_id:
        user_config = await self._get_user_configuration(user_id)

    # Build context with priorities
    context = await self._build_context_with_priorities(
        project_id=project_id,
        field_priorities=user_config.get("field_priorities", {})
    )

    # Check Serena integration toggle
    serena_context = ""
    if user_config.get("serena_enabled", False):
        serena_context = await self._fetch_serena_codebase_context(project_id)
        logger.info(
            f"Serena context added ({len(serena_context) // 4} tokens)",
            extra={"project_id": str(project_id), "user_id": str(user_id)}
        )
    else:
        logger.info(
            "Serena disabled by user configuration",
            extra={"project_id": str(project_id), "user_id": str(user_id)}
        )

    # Combine contexts
    full_context = f"{context}\n\n{serena_context}" if serena_context else context

    # Generate mission
    mission = await self._generate_mission_from_context(
        full_context,
        token_budget=user_config.get("token_budget", 100000)
    )

    return {
        "mission": mission,
        "token_estimate": len(mission) // 4,
        "user_config_applied": bool(user_id),
        "serena_enabled": user_config.get("serena_enabled", False)
    }


async def _fetch_serena_codebase_context(self, project_id: UUID) -> str:
    """
    Fetch codebase context from Serena MCP tool.

    Returns empty string if Serena unavailable (graceful degradation).
    """
    try:
        # Call Serena MCP tool for codebase analysis
        from src.giljo_mcp.mcp_client import MCPClient

        mcp_client = MCPClient()
        result = await mcp_client.call_tool(
            tool_name="serena__get_symbols_overview",
            arguments={"relative_path": "."}
        )

        return result.get("content", "")
    except Exception as e:
        logger.warning(
            f"Failed to fetch Serena context: {e}",
            extra={"project_id": str(project_id)},
            exc_info=True
        )
        return ""
```

**Validation**:
```bash
cd F:\GiljoAI_MCP
python -m pytest tests/mission_planner/test_serena_toggle.py -v

# Expected output:
# PASSED tests/mission_planner/test_serena_toggle.py::test_serena_enabled_includes_context
# PASSED tests/mission_planner/test_serena_toggle.py::test_serena_disabled_skips_context
# PASSED tests/mission_planner/test_serena_toggle.py::test_serena_unavailable_graceful
```

**Success Criteria**:
- ✅ Serena context included only when user enables it
- ✅ Graceful degradation when Serena unavailable
- ✅ Logged for debugging
- ✅ Token estimate includes Serena context when applicable

---

#### Task 3.3: Add Mission Regeneration Endpoint

**File**: `F:\GiljoAI_MCP\api\endpoints\orchestration.py` (NEW FILE)
**Priority**: MEDIUM
**Dependencies**: Tasks 3.1, 3.2
**Estimated Time**: 6 hours

**Action**: Allow users to regenerate mission with different config

**Complete Endpoint**:
```python
# File: F:\GiljoAI_MCP\api\endpoints\orchestration.py
# Location: Create new file

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, UUID4
from typing import Optional
from api.dependencies.auth import get_current_active_user
from api.dependencies.websocket import get_websocket_dependency, WebSocketDependency
from api.dependencies.database import get_db
from api.events.schemas import EventFactory
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.models import User, Project
from sqlalchemy.orm import Session
import logging

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])
logger = logging.getLogger(__name__)


class RegenerateMissionRequest(BaseModel):
    """Request to regenerate mission with updated configuration."""
    project_id: UUID4
    override_field_priorities: Optional[dict] = None
    override_serena_enabled: Optional[bool] = None


class RegenerateMissionResponse(BaseModel):
    """Response from mission regeneration."""
    mission: str
    token_estimate: int
    user_config_applied: bool
    serena_enabled: bool
    field_priorities_used: dict


@router.post("/regenerate-mission", response_model=RegenerateMissionResponse)
async def regenerate_mission(
    request: RegenerateMissionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency)
):
    """
    Regenerate project mission with updated user configuration.

    Allows users to experiment with different field priorities
    or toggle Serena integration without changing saved settings.
    """
    # Validate project access
    project = db.query(Project).filter_by(
        id=request.project_id,
        tenant_key=current_user.tenant_key
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Apply overrides to user config
    user_config = await _get_user_config_with_overrides(
        user_id=current_user.id,
        db=db,
        override_priorities=request.override_field_priorities,
        override_serena=request.override_serena_enabled
    )

    # Generate mission with config
    orchestrator = ProjectOrchestrator(db)
    result = await orchestrator.process_product_vision(
        project_id=request.project_id,
        user_id=current_user.id
    )

    # Broadcast update via WebSocket
    try:
        event_data = EventFactory.project_mission_updated(
            project_id=request.project_id,
            tenant_key=current_user.tenant_key,
            mission=result["mission"],
            token_estimate=result["token_estimate"],
            generated_by="user",  # User-initiated regeneration
            user_config_applied=True,
            field_priorities=user_config["field_priorities"]
        )

        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="project:mission_updated",
            data=event_data["data"]
        )

        logger.info(
            f"Mission regeneration broadcasted to {sent_count} clients",
            extra={
                "project_id": str(request.project_id),
                "user_id": str(current_user.id),
                "sent_count": sent_count
            }
        )
    except Exception as e:
        logger.error(f"Failed to broadcast mission regeneration: {e}", exc_info=True)

    return RegenerateMissionResponse(
        mission=result["mission"],
        token_estimate=result["token_estimate"],
        user_config_applied=True,
        serena_enabled=user_config["serena_enabled"],
        field_priorities_used=user_config["field_priorities"]
    )


async def _get_user_config_with_overrides(
    user_id: UUID,
    db: Session,
    override_priorities: Optional[dict],
    override_serena: Optional[bool]
) -> dict:
    """Merge user settings with one-time overrides."""
    from src.giljo_mcp.models import UserSettings

    user_settings = db.query(UserSettings).filter_by(user_id=user_id).first()

    base_config = {
        "field_priorities": user_settings.field_priorities if user_settings else {},
        "serena_enabled": user_settings.serena_enabled if user_settings else False,
        "token_budget": user_settings.token_budget if user_settings else 100000
    }

    # Apply overrides (don't save to database)
    if override_priorities is not None:
        base_config["field_priorities"] = {
            **base_config["field_priorities"],
            **override_priorities
        }

    if override_serena is not None:
        base_config["serena_enabled"] = override_serena

    return base_config
```

**Register in app.py**:
```python
# File: F:\GiljoAI_MCP\api\app.py
# Location: Add with other router imports

from api.endpoints.orchestration import router as orchestration_router

app.include_router(orchestration_router)
```

**Validation**:
```bash
cd F:\GiljoAI_MCP
python -m pytest tests/api/test_regenerate_mission.py -v

# Expected output:
# PASSED tests/api/test_regenerate_mission.py::test_regenerate_with_overrides
# PASSED tests/api/test_regenerate_mission.py::test_regenerate_broadcasts
# PASSED tests/api/test_regenerate_mission.py::test_unauthorized_access_denied
```

**Success Criteria**:
- ✅ Users can regenerate mission with different settings
- ✅ Overrides don't save to user settings
- ✅ WebSocket broadcast notifies all tenant clients
- ✅ Multi-tenant isolation enforced

---

### Phase 4: Frontend Production-Grade (Weeks 8-9, 48 hours)

**Objective**: Fix memory leaks, race conditions, and UX issues

#### Task 4.1: Fix WebSocket Listener Memory Leak

**File**: `F:\GiljoAI_MCP\frontend\src\composables\useWebSocket.js` (lines 37-43, 87-96)
**Priority**: CRITICAL
**Dependencies**: None
**Estimated Time**: 4 hours

**Current Issue**: Unsubscribe functions not properly captured and called

**Action**: Properly capture and call unsubscribe functions

**Replace Entire File** (`F:\GiljoAI_MCP\frontend\src\composables\useWebSocket.js`):
```javascript
import { ref, onMounted, onUnmounted } from 'vue'
import websocketService from '@/services/websocket'

export function useWebSocket() {
  const isConnected = ref(false)
  const lastMessage = ref(null)
  const error = ref(null)

  // Store unsubscribe functions for cleanup
  const unsubscribeFunctions = new Map()  // eventType -> Set<unsubscribeFn>

  /**
   * Register a message handler for specific event type
   * FIXED: Now properly captures unsubscribe function
   */
  const on = (eventType, callback) => {
    // Register with WebSocket service and capture unsubscribe function
    const unsubscribe = websocketService.onMessage(eventType, callback)

    // Store unsubscribe function for cleanup
    if (!unsubscribeFunctions.has(eventType)) {
      unsubscribeFunctions.set(eventType, new Set())
    }
    unsubscribeFunctions.get(eventType).add(unsubscribe)

    console.log(`[useWebSocket] Registered listener for ${eventType}`)
  }

  /**
   * Unregister a message handler
   * FIXED: Now properly calls unsubscribe function
   */
  const off = (eventType, callback) => {
    const unsubscribes = unsubscribeFunctions.get(eventType)
    if (unsubscribes) {
      // Call all unsubscribe functions for this event type
      unsubscribes.forEach(unsubscribe => {
        try {
          unsubscribe()
        } catch (err) {
          console.warn(`[useWebSocket] Error unsubscribing from ${eventType}:`, err)
        }
      })
      unsubscribes.clear()
      unsubscribeFunctions.delete(eventType)

      console.log(`[useWebSocket] Unregistered listener for ${eventType}`)
    }
  }

  /**
   * Send message through WebSocket
   */
  const send = (type, data) => {
    try {
      websocketService.send({ type, ...data })
    } catch (err) {
      console.error('[useWebSocket] Send failed:', err)
      error.value = err.message
    }
  }

  /**
   * Connect to WebSocket server
   */
  const connect = async () => {
    try {
      if (!websocketService.isConnected) {
        await websocketService.connect()
      }
      isConnected.value = true
      error.value = null
    } catch (err) {
      console.error('[useWebSocket] Connection failed:', err)
      error.value = err.message
      isConnected.value = false
    }
  }

  /**
   * Disconnect from WebSocket server
   * FIXED: Now properly cleans up all listeners
   */
  const disconnect = () => {
    // Clean up all registered handlers
    unsubscribeFunctions.forEach((unsubscribes, eventType) => {
      unsubscribes.forEach(unsubscribe => {
        try {
          unsubscribe()
        } catch (err) {
          console.warn(`[useWebSocket] Error unsubscribing from ${eventType}:`, err)
        }
      })
    })
    unsubscribeFunctions.clear()

    console.log('[useWebSocket] All listeners cleaned up')
  }

  // Auto-connect on mount if WebSocket service is available
  onMounted(() => {
    if (websocketService && websocketService.isConnected) {
      isConnected.value = true
    }
  })

  // Clean up on unmount (CRITICAL for memory leak prevention)
  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    lastMessage,
    error,
    on,
    off,
    send,
    connect,
    disconnect
  }
}
```

**Validation**:
```bash
cd F:\GiljoAI_MCP\frontend
npm run test:unit tests/composables/useWebSocket.spec.js

# Expected output:
# ✓ registers listener and captures unsubscribe function
# ✓ unsubscribes properly on off() call
# ✓ cleans up all listeners on unmount
# ✓ no memory leak after 100 mount/unmount cycles
```

**Success Criteria**:
- ✅ Unsubscribe functions properly captured
- ✅ All listeners cleaned up on component unmount
- ✅ Zero memory leaks in 100+ mount/unmount cycles
- ✅ Logged for debugging

---

#### Task 4.2: Fix Agent Creation Race Condition

**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue` (lines 418-489)
**Priority**: HIGH
**Dependencies**: Task 4.1
**Estimated Time**: 3 hours

**Current Issue**: Array.some() check has race condition - duplicate agents possible

**Action**: Use Set for agent ID tracking to prevent duplicates

**Implementation**:
```javascript
// File: F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue
// Location: Add after reactive state (around line 280)

// Track agent IDs to prevent duplicates (race condition fix)
const agentIds = ref(new Set())

// Location: Replace handleAgentCreated (lines 450-489)
const handleAgentCreated = (data) => {
  console.log('[LaunchTab] Received agent:created:', data)

  // Multi-tenant isolation checks
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    console.warn('[LaunchTab] Agent creation rejected: tenant mismatch')
    return
  }

  if (data.project_id !== projectId.value) {
    console.log('[LaunchTab] Agent creation ignored: different project')
    return
  }

  // Use Set for atomic duplicate check (race condition fix)
  const agentId = data.agent?.id || data.agent?.job_id

  if (!agentId) {
    console.warn('[LaunchTab] Agent creation ignored: no ID')
    return
  }

  // Atomic check-and-add using Set
  if (agentIds.value.has(agentId)) {
    console.log('[LaunchTab] Agent already exists, skipping duplicate')
    return
  }

  // Add to Set first (atomic operation)
  agentIds.value.add(agentId)

  // Then add to reactive array
  agents.value.push({
    ...data.agent,
    id: agentId  // Normalize ID field
  })

  // Show notification
  toastMessage.value = `${data.agent.agent_type} agent assigned`
  showToast.value = true

  console.log('[LaunchTab] Agent added:', agentId)
}

// Location: Add cleanup in onUnmounted (around line 640)
onUnmounted(() => {
  // Cleanup WebSocket listeners
  off('project:mission_updated', handleMissionUpdate)
  off('agent:created', handleAgentCreated)

  // Clear agent tracking Set
  agentIds.value.clear()

  console.log('[LaunchTab] Cleanup complete')
})
```

**Validation**:
```bash
cd F:\GiljoAI_MCP\frontend
npm run test:unit tests/components/LaunchTab.spec.js

# Expected output:
# ✓ prevents duplicate agents in rapid succession
# ✓ handles 100 simultaneous agent:created events without duplicates
# ✓ cleans up agent IDs on unmount
```

**Success Criteria**:
- ✅ Zero duplicate agents even in race conditions
- ✅ Set provides atomic check-and-add
- ✅ Proper cleanup on component unmount
- ✅ Normalized ID field across all agents

---

#### Task 4.3: Remove project_id/id Band-Aid

**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue` (lines 328-333)
**Priority**: MEDIUM
**Dependencies**: Task 1.1 (backend) ✅
**Estimated Time**: 2 hours

**Action**: Remove computed property after backend returns consistent `id` field

**Replace**:
```javascript
// File: F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue
// Location: Replace lines 328-333

// Direct access - backend now consistently returns 'id'
const projectId = computed(() => props.project?.id)

// Add validation
if (!projectId.value) {
  console.error('[LaunchTab] Project missing ID field')
  throw new Error('Invalid project: missing ID')
}
```

**Success Criteria**:
- ✅ Computed property removed
- ✅ Direct access to `props.project.id`
- ✅ Validation throws on missing ID
- ✅ Zero references to `project_id` in frontend

---

#### Task 4.4: Add Loading States and Error Boundaries

**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue`
**Priority**: MEDIUM
**Dependencies**: None
**Estimated Time**: 6 hours

**Action**: Add proper loading states and error boundaries for UX

**Add to Script Section** (after reactive state, around line 280):
```javascript
// Loading states
const isLoadingMission = ref(false)
const isLoadingAgents = ref(false)
const missionError = ref(null)
const agentError = ref(null)
```

**Update stageProject function** (around line 500):
```javascript
const stageProject = async () => {
  if (!selectedTool.value) {
    toastMessage.value = 'Please select an AI coding tool first'
    showToast.value = true
    return
  }

  // Reset errors
  missionError.value = null
  agentError.value = null

  // Set loading state
  isLoadingMission.value = true
  stagingInProgress.value = true

  try {
    const response = await api.prompts.staging(
      projectId.value,
      selectedTool.value
    )

    if (!response.data?.prompt) {
      throw new Error('Invalid response from staging endpoint')
    }

    // Success - wait for WebSocket events
    console.log('[LaunchTab] Staging initiated, waiting for WebSocket updates')

  } catch (error) {
    // Handle error
    missionError.value = error.message || 'Failed to stage project'

    console.error('[LaunchTab] Staging failed:', error)

    // Show error toast
    toastMessage.value = `Staging failed: ${missionError.value}`
    showToast.value = true

    // Reset states
    stagingInProgress.value = false
    isLoadingMission.value = false
  }
}
```

**Update handleMissionUpdate** (around line 420):
```javascript
const handleMissionUpdate = (data) => {
  console.log('[LaunchTab] Received project:mission_updated:', data)

  // Validation...

  // Update mission
  missionText.value = data.mission

  // Clear loading state
  isLoadingMission.value = false
  stagingInProgress.value = false
  readyToLaunch.value = true

  // Show success with config info
  let message = `Mission generated (${data.token_estimate} tokens)`
  if (data.user_config_applied) {
    message += ' • Optimized for you'
  }

  toastMessage.value = message
  showToast.value = true
}
```

**Update Template** (around line 100):
```vue
<template>
  <v-card class="mission-card">
    <v-card-title>
      Mission
      <v-chip v-if="missionData?.user_config_applied" color="success" size="small" class="ml-2">
        Optimized for you
      </v-chip>
    </v-card-title>

    <v-card-text>
      <!-- Loading state -->
      <div v-if="isLoadingMission" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
        <p class="mt-4 text-body-1">Generating mission...</p>
        <p class="text-caption text-medium-emphasis">
          Analyzing project vision and applying your preferences
        </p>
      </div>

      <!-- Error state -->
      <v-alert
        v-else-if="missionError"
        type="error"
        variant="tonal"
        closable
        @click:close="missionError = null"
      >
        <v-alert-title>Mission Generation Failed</v-alert-title>
        {{ missionError }}
        <template #append>
          <v-btn size="small" @click="stageProject">Retry</v-btn>
        </template>
      </v-alert>

      <!-- Success state -->
      <v-textarea
        v-else
        v-model="missionText"
        label="Generated Mission"
        rows="8"
        readonly
        variant="outlined"
      ></v-textarea>
    </v-card-text>
  </v-card>
</template>
```

**Success Criteria**:
- ✅ Loading spinner during async operations
- ✅ Error alerts with retry option
- ✅ Success states with contextual info
- ✅ "Optimized for you" badge when config applied
- ✅ Accessible (ARIA labels, keyboard navigation)

---

### Phase 5: Testing & Quality Assurance (Weeks 10-11, 56 hours)

**Objective**: Achieve 85%+ test coverage with comprehensive test suite

#### Task 5.1: Backend Unit Tests

**Priority**: CRITICAL
**Dependencies**: Phases 1-3 complete
**Estimated Time**: 20 hours

**Test Files to Create**:

1. **`F:\GiljoAI_MCP\tests\dependencies\test_websocket_dependency.py`** - WebSocket DI tests (8 tests)
2. **`F:\GiljoAI_MCP\tests\mission_planner\test_field_priorities.py`** - Field priority system tests (10 tests)
3. **`F:\GiljoAI_MCP\tests\mission_planner\test_serena_toggle.py`** - Serena integration tests (5 tests)
4. **`F:\GiljoAI_MCP\tests\api\test_agent_jobs_websocket.py`** - Agent job WebSocket tests (8 tests)
5. **`F:\GiljoAI_MCP\tests\api\test_regenerate_mission.py`** - Mission regeneration endpoint tests (7 tests)
6. **`F:\GiljoAI_MCP\tests\events\test_user_config_flag.py`** - Event schema tests (4 tests)

**Coverage Target**: 85%+ for all new code

**Validation**:
```bash
cd F:\GiljoAI_MCP
python -m pytest tests/ -v --cov=src/giljo_mcp --cov=api --cov-report=html

# Expected output:
# ======================== Coverage Summary ========================
# src/giljo_mcp/mission_planner.py    88%
# src/giljo_mcp/context_manager.py    92%
# api/dependencies/websocket.py       95%
# api/events/schemas.py               90%
# api/endpoints/orchestration.py     87%
# ------------------------
# TOTAL                               87%
```

**Success Criteria**:
- ✅ 85%+ line coverage
- ✅ 80%+ branch coverage
- ✅ All critical paths tested
- ✅ Multi-tenant isolation validated in all tests

---

#### Task 5.2: Frontend Unit Tests

**Priority**: HIGH
**Dependencies**: Phase 4 complete
**Estimated Time**: 16 hours

**Test Files to Create**:

1. **`F:\GiljoAI_MCP\frontend\tests\composables\useWebSocket.spec.js`** - Memory leak tests (6 tests)
2. **`F:\GiljoAI_MCP\frontend\tests\components\LaunchTab.spec.js`** - Race condition tests (8 tests)

**Coverage Target**: 75%+ for modified frontend code

**Validation**:
```bash
cd F:\GiljoAI_MCP\frontend
npm run test:unit -- --coverage

# Expected output:
# File                              % Stmts  % Branch  % Funcs  % Lines
# composables/useWebSocket.js         92%      88%      95%      92%
# components/projects/LaunchTab.vue   78%      75%      80%      78%
```

**Success Criteria**:
- ✅ Memory leak prevention validated
- ✅ Race condition prevention validated
- ✅ Loading states tested
- ✅ Error boundaries tested

---

#### Task 5.3: Integration Tests

**Priority**: HIGH
**Dependencies**: Tasks 5.1, 5.2
**Estimated Time**: 12 hours

**Test Files to Create**:

1. **`F:\GiljoAI_MCP\tests\integration\test_stage_project_workflow.py`** - End-to-end staging tests (10 tests)
2. **`F:\GiljoAI_MCP\tests\integration\test_websocket_broadcast.py`** - WebSocket integration tests (8 tests)

**Test Scenarios**:
- Complete staging workflow with user config
- Mission regeneration with overrides
- WebSocket event propagation to multiple clients
- Multi-tenant isolation across entire workflow

**Success Criteria**:
- ✅ End-to-end workflow validated
- ✅ WebSocket events reach all tenant clients
- ✅ Zero cross-tenant leakage
- ✅ Serena integration toggle respected

---

#### Task 5.4: Performance Benchmarks

**Priority**: MEDIUM
**Dependencies**: Tasks 5.1-5.3
**Estimated Time**: 8 hours

**Benchmarks to Create**:

1. **Token Reduction Validation** - Verify 70% reduction with field priorities
2. **WebSocket Broadcast Performance** - 1000+ concurrent clients
3. **Mission Generation Time** - With/without Serena context
4. **Memory Leak Detection** - 1000+ component mount/unmount cycles

**File**: `F:\GiljoAI_MCP\tests\performance\test_stage_project_benchmarks.py`

**Success Criteria**:
- ✅ 70% token reduction achieved with priorities
- ✅ WebSocket broadcasts complete in <100ms for 1000 clients
- ✅ Mission generation <2 seconds
- ✅ Zero memory leaks after 1000 cycles

---

### Phase 6: Documentation & Deployment (Week 12, 24 hours)

**Objective**: Production-ready documentation and deployment prep

#### Task 6.1: Update Technical Documentation

**Priority**: HIGH
**Dependencies**: Phases 1-5 complete
**Estimated Time**: 8 hours

**Files to Update**:

1. **`F:\GiljoAI_MCP\docs\TECHNICAL_ARCHITECTURE.md`**
   - Add WebSocket dependency injection pattern
   - Document field priority system
   - Explain token reduction mechanism

2. **`F:\GiljoAI_MCP\docs\manuals\MCP_TOOLS_MANUAL.md`**
   - Update mission generation tools
   - Document Serena integration toggle

3. **`F:\GiljoAI_MCP\CLAUDE.md`**
   - Add production-grade coding standards
   - Document WebSocket event patterns
   - Update quick reference

**Success Criteria**:
- ✅ All new features documented
- ✅ API examples updated
- ✅ Architecture diagrams current

---

#### Task 6.2: Create User Guide for Field Priorities

**File**: `F:\GiljoAI_MCP\docs\user_guides\field_priorities_guide.md` (NEW)
**Priority**: HIGH
**Dependencies**: None
**Estimated Time**: 6 hours

**Content**:
- How to set field priorities in My Settings
- Understanding priority levels (1-10)
- Token reduction benefits
- Examples and best practices
- Serena integration toggle

**Success Criteria**:
- ✅ Clear for non-technical users
- ✅ Screenshots included
- ✅ Examples demonstrate 70% reduction

---

#### Task 6.3: Create Developer Guide for WebSocket Events

**File**: `F:\GiljoAI_MCP\docs\developer_guides\websocket_events_guide.md` (NEW)
**Priority**: MEDIUM
**Dependencies**: None
**Estimated Time**: 6 hours

**Content**:
- WebSocket dependency injection pattern
- Event schema standards (EventFactory)
- Broadcast best practices
- Multi-tenant isolation requirements
- Testing WebSocket events

**Success Criteria**:
- ✅ Code examples for all patterns
- ✅ Anti-patterns documented
- ✅ Security considerations highlighted

---

#### Task 6.4: Update Handover 0086A Status

**File**: `F:\GiljoAI_MCP\handovers\0086A_production_grade_stage_project.md`
**Priority**: LOW
**Dependencies**: Phases 1-6 complete
**Estimated Time**: 2 hours

**Action**: Mark as COMPLETE and link to 0086B

**Add to top**:
```markdown
**Status**: COMPLETE (Continued in Handover 0086B)
**Completion Date**: [DATE]
**Phase 1**: ✅ Complete
**Phase 2**: ✅ Complete
**Phases 3-6**: See Handover 0086B
```

---

## Dependencies & Execution Order

### Critical Path (Must Complete in Order):

1. **Phase 2 Final Task** → Task 2.2 completion (`_build_context_with_priorities`)
2. **Phase 3 Tasks** → Can run in parallel after Phase 2 complete
3. **Phase 4 Tasks** → Can run in parallel with Phase 3
4. **Phase 5 Tasks** → Require Phases 3-4 complete
5. **Phase 6 Tasks** → Require all phases complete

### Parallel Execution Opportunities:

**Week 5-7** (Phase 3):
- Task 3.1 (agent_jobs.py) can run in parallel with Task 3.2 (Serena toggle)
- Task 3.3 (regeneration endpoint) requires 3.1 and 3.2

**Week 8-9** (Phase 4):
- All frontend tasks can run in parallel
- Task 4.3 depends on backend Task 1.1 ✅ (already complete)

**Week 10-11** (Phase 5):
- Backend tests (5.1) and frontend tests (5.2) can run in parallel
- Integration tests (5.3) require 5.1 and 5.2
- Benchmarks (5.4) can run in parallel with 5.3

**Week 12** (Phase 6):
- All documentation tasks can run in parallel

---

## Testing Requirements

### Unit Test Requirements

**Coverage Targets**:
- Backend: 85%+ line coverage, 80%+ branch coverage
- Frontend: 75%+ line coverage, 70%+ branch coverage

**Required Test Files** (42 total tests):
1. `tests/dependencies/test_websocket_dependency.py` (8 tests)
2. `tests/mission_planner/test_field_priorities.py` (10 tests)
3. `tests/mission_planner/test_serena_toggle.py` (5 tests)
4. `tests/api/test_agent_jobs_websocket.py` (8 tests)
5. `tests/api/test_regenerate_mission.py` (7 tests)
6. `tests/events/test_user_config_flag.py` (4 tests)
7. `frontend/tests/composables/useWebSocket.spec.js` (6 tests)
8. `frontend/tests/components/LaunchTab.spec.js` (8 tests)

### Integration Test Requirements

**Required Test Files** (18 total tests):
1. `tests/integration/test_stage_project_workflow.py` (10 tests)
2. `tests/integration/test_websocket_broadcast.py` (8 tests)

**Critical Scenarios**:
- End-to-end staging with user config
- Mission regeneration with overrides
- WebSocket event propagation
- Multi-tenant isolation

### Performance Benchmarks

**Required Metrics**:
- ✅ 70% token reduction with field priorities
- ✅ WebSocket broadcasts <100ms for 1000 clients
- ✅ Mission generation <2 seconds
- ✅ Zero memory leaks after 1000 mount/unmount cycles

---

## Success Metrics

### Phase 2 Complete When:
- ✅ `_build_context_with_priorities()` fully implemented
- ✅ All 5 helper methods working
- ✅ Field priorities test suite passing (10 tests)
- ✅ 70% token reduction validated

### Phase 3 Complete When:
- ✅ All WebSocket broadcasts use dependency injection
- ✅ Serena toggle respected in mission generation
- ✅ Regeneration endpoint functional
- ✅ Integration tests passing

### Phase 4 Complete When:
- ✅ Zero memory leaks in useWebSocket composable
- ✅ Zero race conditions in agent creation
- ✅ Loading states and error boundaries working
- ✅ "Optimized for you" badge displaying

### Phase 5 Complete When:
- ✅ 85%+ backend test coverage
- ✅ 75%+ frontend test coverage
- ✅ All integration tests passing
- ✅ Performance benchmarks met

### Phase 6 Complete When:
- ✅ All documentation updated
- ✅ User guide published
- ✅ Developer guide published
- ✅ Handover 0086A marked complete

### Project Complete When:
- ✅ All phases 2-6 complete
- ✅ Zero band-aids remaining
- ✅ 85%+ test coverage achieved
- ✅ 70% token reduction validated
- ✅ Multi-tenant isolation verified
- ✅ Production deployment ready

---

## Quick Start for Implementers

### Day 1: Phase 2 Completion
```bash
# 1. Complete the stub
cd F:\GiljoAI_MCP
# Edit src/giljo_mcp/mission_planner.py line 516
# Implement _build_context_with_priorities() per Task 2.2

# 2. Run tests
python -m pytest tests/mission_planner/test_field_priorities.py -v

# 3. Validate 70% reduction
python -m pytest tests/mission_planner/test_token_reduction.py -v
```

### Week 1: Phase 3
```bash
# Day 2-3: Refactor agent_jobs.py (Task 3.1)
# Day 4-6: Add Serena toggle (Task 3.2)
# Day 7: Add regeneration endpoint (Task 3.3)

# Run integration tests
python -m pytest tests/api/ -v
```

### Week 2: Phase 4
```bash
# Day 8-9: Fix memory leak (Task 4.1)
cd frontend
# Edit src/composables/useWebSocket.js
npm run test:unit tests/composables/useWebSocket.spec.js

# Day 10: Fix race condition (Task 4.2)
# Day 11: Remove band-aid (Task 4.3)
# Day 12-13: Loading states (Task 4.4)
```

### Week 3-4: Phase 5
```bash
# Week 3: Backend tests (Task 5.1, 5.2)
python -m pytest tests/ --cov=src/giljo_mcp --cov=api

# Week 4: Integration & benchmarks (Task 5.3, 5.4)
python -m pytest tests/integration/ -v
python -m pytest tests/performance/ -v
```

### Week 5: Phase 6
```bash
# Documentation updates (Tasks 6.1-6.4)
# Review and update all docs
# Create user and developer guides
```

---

## Contact & Support

**Questions**: Reference Handover 0086A for complete implementation details
**Architecture**: See `docs/TECHNICAL_ARCHITECTURE.md`
**Standards**: See `CLAUDE.md` for coding guidelines

**Critical Files**:
- Handover 0086A: `F:\GiljoAI_MCP\handovers\0086A_production_grade_stage_project.md`
- MissionPlanner: `F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py`
- WebSocket DI: `F:\GiljoAI_MCP\api\dependencies\websocket.py`
- LaunchTab: `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue`

---

**End of Handover 0086B**
