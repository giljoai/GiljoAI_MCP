# Handover 0088: Thin Client Stage Project Architecture Fix

**Date**: 2025-11-02
**Type**: CRITICAL - Architecture Refactoring
**Priority**: P0 - Blocks Commercialization
**Status**: Ready for Implementation
**Estimated Effort**: 24 hours (3 days)

---

## Executive Summary

**CRITICAL PROBLEM**: The Stage Project feature currently generates "fat prompts" (2000-3000 lines) that embed the entire mission content directly into the launch prompt. This completely defeats the purpose of our 70% token reduction feature and creates a terrible user experience (copying 3000 lines into Claude Code CLI).

**ROOT CAUSE**: The `OrchestratorPromptGenerator` in `src/giljo_mcp/prompt_generator.py` was designed to generate comprehensive, self-contained prompts for orchestrators. However, this violates the thin client architecture pattern that MCP was designed to enable.

**SOLUTION**: Implement a "thin client" pattern where launch prompts contain only identity information (~10 lines) and orchestrators fetch their missions dynamically via MCP tools. This restores the 70% token reduction and provides a professional user experience.

**BUSINESS IMPACT**:
- ✅ Restores 70% token reduction promise
- ✅ Professional appearance for commercial product
- ✅ Reduced API costs for customers
- ✅ Better UX (copy 10 lines, not 3000)
- ✅ Enables dynamic mission updates without re-launching agents

---

## The Problem: Fat Prompts vs Thin Client

### Current "Fat Prompt" Architecture (BROKEN)

**File**: `src/giljo_mcp/prompt_generator.py` (636 lines)

**What it does**:
```python
# Current approach - WRONG
prompt = f"""
ORCHESTRATOR STAGING PROMPT
════════════════════════════

PROJECT MISSION: {project_name}
DESCRIPTION: {project_description}

PHASE 1: INTELLIGENT DISCOVERY (500 lines of instructions)
...

PHASE 2: MISSION CREATION (800 lines of instructions)
...

PHASE 3: AGENT SELECTION (600 lines of agent templates)
...

PHASE 4: COORDINATION PROTOCOL (400 lines of workflows)
...

PHASE 5: EXECUTION (200 lines of final instructions)
...
"""  # RESULT: 2000-3000 LINE PROMPT
```

**Why this is catastrophically bad**:

1. **Defeats Token Reduction**: We spent months building field priority system to reduce tokens by 70%, then embed the entire mission in the prompt anyway
2. **Terrible UX**: Users must copy/paste 3000 lines into Claude Code CLI
3. **Immutable Missions**: Once launched, orchestrator can't fetch updated mission
4. **Database Redundancy**: Mission is stored in database AND pasted into prompt
5. **Unprofessional**: Commercial products don't ask users to copy novels

### Desired "Thin Client" Architecture (CORRECT)

**What it should be**:
```python
# Thin client approach - CORRECT
prompt = f"""
I am Orchestrator #{instance_number} for GiljoAI Project "{project_name}".

IDENTITY:
- Orchestrator ID: {orchestrator_id}
- Project ID: {project_id}
- MCP Server: giljo-mcp (connected)

INSTRUCTIONS:
1. Fetch my mission: get_orchestrator_instructions('{orchestrator_id}')
2. Execute the mission according to instructions
3. Report progress via MCP tools

Begin by fetching your mission.
"""  # RESULT: ~10 LINE PROMPT
```

**Why this is correct**:

1. **Enables Token Reduction**: Orchestrator fetches only Priority 1-2 fields from database
2. **Professional UX**: Users copy 10 lines, not 3000
3. **Dynamic Missions**: Orchestrator can refetch updated mission anytime
4. **Single Source of Truth**: Database is the only mission storage
5. **Commercial Grade**: This is how professional products work

---

## Architecture Comparison Diagrams

### Current Architecture (Fat Prompt)

```
┌─────────────────────────────────────────────────────────────┐
│                      USER WORKFLOW (CURRENT)                │
└─────────────────────────────────────────────────────────────┘

1. User clicks "Stage Project" in UI
   ↓
2. OrchestratorPromptGenerator.generate()
   ↓
   ├── Fetch product vision (20K tokens)
   ├── Fetch project description (2K tokens)
   ├── Fetch agent templates (8K tokens)
   ├── Fetch field priorities
   └── EMBED ALL IN PROMPT (30K tokens)
   ↓
3. Frontend displays 3000-line prompt in modal
   ↓
4. User copies entire 3000 lines to clipboard
   ↓
5. User pastes into Claude Code CLI
   ↓
6. Claude Code receives 30K token prompt
   ↓
7. 70% token reduction feature COMPLETELY BYPASSED
   ↓
8. Orchestrator runs with fat context (expensive API costs)

┌─────────────────────────────────────────────────────────────┐
│                      DATA FLOW (CURRENT)                    │
└─────────────────────────────────────────────────────────────┘

Database (Mission)  ────┐
                        ├──→ prompt_generator.py ──→ Fat Prompt (3000 lines)
Vision Docs (20K)  ─────┤                                 ↓
Agent Templates    ─────┘                              User Clipboard
                                                           ↓
                                                     Claude Code CLI
                                                           ↓
                                                  Orchestrator (ignores MCP)
```

### Desired Architecture (Thin Client)

```
┌─────────────────────────────────────────────────────────────┐
│                      USER WORKFLOW (DESIRED)                │
└─────────────────────────────────────────────────────────────┘

1. User clicks "Stage Project" in UI
   ↓
2. ThinClientPromptGenerator.generate()
   ↓
   ├── Create orchestrator_id in database
   ├── Store mission with field priorities applied
   └── Generate 10-line identity prompt
   ↓
3. Frontend displays 10-line prompt in modal
   ↓
4. User copies 10 lines to clipboard
   ↓
5. User pastes into Claude Code CLI
   ↓
6. Claude Code receives 10-line prompt (~50 tokens)
   ↓
7. Orchestrator calls get_orchestrator_instructions(orchestrator_id)
   ↓
8. MCP tool applies field priorities and returns condensed mission (6K tokens)
   ↓
9. 70% token reduction FULLY ACTIVE
   ↓
10. Orchestrator runs with thin context (low API costs)

┌─────────────────────────────────────────────────────────────┐
│                      DATA FLOW (DESIRED)                    │
└─────────────────────────────────────────────────────────────┘

Database (Mission) ──→ MCP Tool: get_orchestrator_instructions()
                            ↓
                       Apply Field Priorities
                            ↓
                       Return Condensed Mission (6K tokens)
                            ↓
                       Orchestrator (via MCP call)
                            ↑
                       Thin Prompt (10 lines, 50 tokens)
                            ↑
                       User Clipboard
                            ↑
                       Claude Code CLI
```

---

## Step-by-Step Implementation Plan

### Phase 1: Create New MCP Tools (4 hours)

#### Task 1.1: Add `get_orchestrator_instructions()` MCP Tool

**File**: `src/giljo_mcp/tools/orchestration.py`
**Location**: After existing orchestration tools (~line 200)

**Implementation**:

```python
@mcp.tool()
async def get_orchestrator_instructions(
    orchestrator_id: str,
    tenant_key: str
) -> dict[str, Any]:
    """
    Fetch orchestrator-specific mission and instructions.

    This is the CRITICAL tool that enables thin client architecture.
    Orchestrator calls this on startup to get its condensed mission.

    Process:
    1. Fetch orchestrator job from database
    2. Get associated project and product
    3. Apply field priorities to vision content
    4. Return condensed mission (70% token reduction)

    Args:
        orchestrator_id: Orchestrator job UUID
        tenant_key: Tenant isolation key

    Returns:
        {
            'orchestrator_id': 'uuid',
            'project_id': 'uuid',
            'project_name': 'My Project',
            'mission': 'Condensed mission with priority fields only',
            'context_budget': 150000,
            'context_used': 0,
            'agent_templates': [...],
            'field_priorities': {...},
            'token_reduction_applied': True,
            'estimated_tokens': 6000
        }

    Example:
        instructions = await get_orchestrator_instructions(
            orchestrator_id='orch-123',
            tenant_key='tenant-abc'
        )
        # Returns condensed mission, not entire vision
    """
    try:
        # Validate inputs
        if not orchestrator_id or not orchestrator_id.strip():
            return {'error': 'Orchestrator ID is required'}

        if not tenant_key or not tenant_key.strip():
            return {'error': 'Tenant key is required'}

        async with db_manager.get_session_async() as session:
            # Get orchestrator job
            result = await session.execute(
                select(MCPAgentJob).where(
                    MCPAgentJob.id == orchestrator_id,
                    MCPAgentJob.tenant_key == tenant_key,
                    MCPAgentJob.agent_type == 'orchestrator'
                )
            )
            orchestrator = result.scalar_one_or_none()

            if not orchestrator:
                return {
                    'error': f'Orchestrator {orchestrator_id} not found',
                    'tenant_key': tenant_key
                }

            # Get project
            result = await session.execute(
                select(Project).where(
                    Project.id == orchestrator.project_id,
                    Project.tenant_key == tenant_key
                )
            )
            project = result.scalar_one_or_none()

            if not project:
                return {'error': 'Project not found'}

            # Get product (if exists)
            product = None
            if project.product_id:
                result = await session.execute(
                    select(Product).where(
                        Product.id == project.product_id,
                        Product.tenant_key == tenant_key
                    )
                )
                product = result.scalar_one_or_none()

            # Use MissionPlanner to build condensed mission
            from giljo_mcp.mission_planner import MissionPlanner

            planner = MissionPlanner(session, tenant_key)

            # Get user's field priorities (stored in orchestrator metadata)
            field_priorities = orchestrator.metadata.get('field_priorities', {})
            user_id = orchestrator.metadata.get('user_id')

            # Generate condensed mission with field priorities
            condensed_mission = await planner._build_context_with_priorities(
                product=product,
                project=project,
                field_priorities=field_priorities,
                user_id=user_id
            )

            # Get agent templates
            result = await session.execute(
                select(AgentTemplate).where(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.is_active == True
                ).limit(8)  # Max 8 agent types
            )
            templates = result.scalars().all()

            template_list = [
                {
                    'name': t.name,
                    'role': t.role,
                    'description': t.description[:200] if t.description else ''
                }
                for t in templates
            ]

            # Calculate token estimate
            estimated_tokens = len(condensed_mission) // 4  # 1 token ≈ 4 chars

            return {
                'orchestrator_id': orchestrator_id,
                'project_id': str(project.id),
                'project_name': project.name,
                'project_description': project.description,
                'mission': condensed_mission,
                'context_budget': project.context_budget,
                'context_used': orchestrator.context_used or 0,
                'agent_templates': template_list,
                'field_priorities': field_priorities,
                'token_reduction_applied': bool(field_priorities),
                'estimated_tokens': estimated_tokens,
                'instance_number': orchestrator.instance_number or 1
            }

    except Exception as e:
        logger.error(f"Error fetching orchestrator instructions: {e}", exc_info=True)
        return {
            'error': f'Failed to fetch instructions: {str(e)}',
            'orchestrator_id': orchestrator_id
        }
```

**Validation**:
```bash
# Test the MCP tool
python -m pytest tests/tools/test_get_orchestrator_instructions.py -v
```

**Success Criteria**:
- ✅ Tool returns condensed mission (6K tokens, not 30K)
- ✅ Field priorities applied correctly
- ✅ Multi-tenant isolation enforced
- ✅ Error handling for missing orchestrator
- ✅ Token estimate accurate

---

#### Task 1.2: Add `get_agent_mission()` MCP Tool

**File**: `src/giljo_mcp/tools/orchestration.py`
**Location**: After `get_orchestrator_instructions()` (~line 350)

**Implementation**:

```python
@mcp.tool()
async def get_agent_mission(
    agent_job_id: str,
    tenant_key: str
) -> dict[str, Any]:
    """
    Fetch agent-specific mission and context.

    Agents call this to get their targeted mission (not entire project vision).
    Similar to orchestrator tool but returns agent-scoped mission.

    Args:
        agent_job_id: Agent job UUID
        tenant_key: Tenant isolation key

    Returns:
        {
            'agent_job_id': 'uuid',
            'agent_name': 'Backend Implementor',
            'agent_type': 'implementer',
            'mission': 'Your specific mission for this sprint',
            'project_context': 'Relevant project context',
            'dependencies': ['job-id-1', 'job-id-2'],
            'estimated_tokens': 2000
        }
    """
    try:
        async with db_manager.get_session_async() as session:
            # Get agent job
            result = await session.execute(
                select(MCPAgentJob).where(
                    MCPAgentJob.id == agent_job_id,
                    MCPAgentJob.tenant_key == tenant_key
                )
            )
            agent_job = result.scalar_one_or_none()

            if not agent_job:
                return {'error': f'Agent job {agent_job_id} not found'}

            # Mission already stored in job.mission field
            # This was created by orchestrator during agent spawning

            estimated_tokens = len(agent_job.mission or '') // 4

            return {
                'agent_job_id': agent_job_id,
                'agent_name': agent_job.agent_name,
                'agent_type': agent_job.agent_type,
                'mission': agent_job.mission or '',
                'project_id': str(agent_job.project_id),
                'parent_job_id': str(agent_job.parent_job_id) if agent_job.parent_job_id else None,
                'estimated_tokens': estimated_tokens,
                'status': agent_job.status
            }

    except Exception as e:
        logger.error(f"Error fetching agent mission: {e}", exc_info=True)
        return {'error': f'Failed to fetch mission: {str(e)}'}
```

---

### Phase 2: Create Thin Client Prompt Generator (6 hours)

#### Task 2.1: Create New `ThinClientPromptGenerator` Class

**File**: `src/giljo_mcp/thin_prompt_generator.py` (NEW FILE)

**Complete Implementation**:

```python
"""
Thin Client Prompt Generator (Handover 0088)

REPLACES: OrchestratorPromptGenerator (prompt_generator.py)

KEY DIFFERENCE: Generates ~10 line prompts with identity only.
Orchestrators fetch missions via MCP tools (70% token reduction enabled).

Author: GiljoAI Development Team
Date: 2025-11-02
Priority: CRITICAL - Enables Commercial Product
"""

import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.models import Project, Product, MCPAgentJob
from src.giljo_mcp.mission_planner import MissionPlanner

logger = logging.getLogger(__name__)


@dataclass
class ThinPromptResponse:
    """Thin client prompt response."""
    prompt: str
    orchestrator_id: str
    project_id: str
    project_name: str
    estimated_prompt_tokens: int
    mcp_tool_name: str
    instructions_stored: bool


class ThinClientPromptGenerator:
    """
    Generates thin client prompts for orchestrators.

    CRITICAL: This enables the 70% token reduction feature.

    Architecture:
    - Prompt contains only identity (~10 lines, 50 tokens)
    - Mission fetched via get_orchestrator_instructions() MCP tool
    - Field priorities applied at fetch time, not embed time

    Workflow:
    1. Create orchestrator job in database
    2. Store condensed mission with field priorities
    3. Generate thin prompt with orchestrator_id
    4. Return prompt to user
    5. User pastes into Claude Code CLI
    6. Orchestrator calls get_orchestrator_instructions(orchestrator_id)
    7. MCP returns condensed mission (6K tokens)

    Benefits:
    - Professional UX (copy 10 lines, not 3000)
    - 70% token reduction ACTIVE
    - Dynamic mission updates possible
    - Commercial-grade appearance
    """

    def __init__(self, db: AsyncSession, tenant_key: str):
        """
        Initialize thin client prompt generator.

        Args:
            db: Database session
            tenant_key: Tenant isolation key
        """
        self.db = db
        self.tenant_key = tenant_key
        self.mission_planner = MissionPlanner(db, tenant_key)

    async def generate(
        self,
        project_id: str,
        user_id: Optional[str] = None,
        tool: str = "claude-code",
        instance_number: int = 1
    ) -> ThinPromptResponse:
        """
        Generate thin client orchestrator prompt.

        Process:
        1. Get project and product from database
        2. Create orchestrator job
        3. Store condensed mission (with field priorities)
        4. Generate thin prompt with orchestrator_id
        5. Return prompt for user to copy

        Args:
            project_id: Project UUID
            user_id: User UUID (for field priorities)
            tool: Target AI tool (claude-code, codex, gemini)
            instance_number: Orchestrator instance number (for succession)

        Returns:
            ThinPromptResponse with ~10 line prompt

        Raises:
            ValueError: Project not found or invalid tool
        """
        logger.info(
            f"[THIN PROMPT] Generating for project={project_id}, "
            f"user={user_id}, tool={tool}"
        )

        # Validate tool
        if tool not in ["claude-code", "codex", "gemini"]:
            raise ValueError(f"Invalid tool: {tool}")

        # Get project
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.tenant_key == self.tenant_key
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get product (if exists)
        product = None
        if project.product_id:
            result = await self.db.execute(
                select(Product).where(
                    Product.id == project.product_id,
                    Product.tenant_key == self.tenant_key
                )
            )
            product = result.scalar_one_or_none()

        # Get user's field priorities (if user_id provided)
        field_priorities = {}
        if user_id:
            field_priorities = await self._get_user_field_priorities(user_id)

        # Generate condensed mission using MissionPlanner
        condensed_mission = await self.mission_planner._build_context_with_priorities(
            product=product,
            project=project,
            field_priorities=field_priorities,
            user_id=user_id
        )

        # Create orchestrator job in database
        orchestrator = MCPAgentJob(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=self.tenant_key,
            agent_name=f"Orchestrator #{instance_number}",
            agent_type="orchestrator",
            status="pending",
            mission=condensed_mission,  # Store condensed mission
            instance_number=instance_number,
            context_budget=project.context_budget,
            context_used=0,
            metadata={
                'field_priorities': field_priorities,
                'user_id': user_id,
                'tool': tool,
                'created_via': 'thin_client_generator'
            }
        )

        self.db.add(orchestrator)
        await self.db.commit()
        await self.db.refresh(orchestrator)

        # Generate thin prompt
        thin_prompt = self._build_thin_prompt(
            orchestrator_id=orchestrator.id,
            project_id=project_id,
            project_name=project.name,
            instance_number=instance_number,
            tool=tool
        )

        # Calculate token estimate for prompt
        prompt_tokens = len(thin_prompt) // 4  # ~50 tokens

        logger.info(
            f"[THIN PROMPT] Generated - orchestrator={orchestrator.id}, "
            f"prompt_tokens={prompt_tokens}, mission_tokens={len(condensed_mission) // 4}"
        )

        return ThinPromptResponse(
            prompt=thin_prompt,
            orchestrator_id=orchestrator.id,
            project_id=project_id,
            project_name=project.name,
            estimated_prompt_tokens=prompt_tokens,
            mcp_tool_name="get_orchestrator_instructions",
            instructions_stored=True
        )

    def _build_thin_prompt(
        self,
        orchestrator_id: str,
        project_id: str,
        project_name: str,
        instance_number: int,
        tool: str
    ) -> str:
        """
        Build thin client prompt (~10 lines).

        This is THE critical output - must be concise and professional.
        """
        return f"""I am Orchestrator #{instance_number} for GiljoAI Project "{project_name}".

IDENTITY:
- Orchestrator ID: {orchestrator_id}
- Project ID: {project_id}
- MCP Server: giljo-mcp (connected via {tool})

INSTRUCTIONS:
1. Call get_orchestrator_instructions('{orchestrator_id}', '<your-tenant-key>') to fetch your condensed mission
2. The mission has been optimized using field priorities (70% token reduction applied)
3. Execute the mission according to the instructions provided
4. Coordinate agents via MCP tools (spawn_agent_job, send_message, etc.)
5. Report progress via update_job_progress('{orchestrator_id}', percent, message)

Begin by fetching your mission using the MCP tool.
"""

    async def _get_user_field_priorities(self, user_id: str) -> Dict[str, int]:
        """
        Fetch user's field priority configuration.

        Returns dict like:
            {
                'product_vision': 10,  # Full detail
                'architecture': 7,      # Moderate
                'codebase_summary': 4,  # Abbreviated
                'dependencies': 2       # Minimal
            }
        """
        # Get user config from database
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        user = result.scalar_one_or_none()

        if not user or not user.config_data:
            return {}

        return user.config_data.get('field_priorities', {})
```

**Validation**:
```bash
# Test thin prompt generator
python -m pytest tests/thin_prompt/test_thin_client_generator.py -v
```

**Success Criteria**:
- ✅ Prompt is ~10 lines (~50 tokens)
- ✅ Orchestrator job created in database
- ✅ Condensed mission stored with field priorities
- ✅ Multi-tenant isolation enforced
- ✅ Returns professional, copy-pasteable prompt

---

### Phase 3: Refactor API Endpoint (2 hours)

#### Task 3.1: Update `POST /api/prompts/orchestrator` Endpoint

**File**: `api/endpoints/prompts.py`
**Location**: Around line 330 (existing `generate_orchestrator_prompt` endpoint)

**BEFORE (Fat Prompt)**:
```python
@router.post("/orchestrator", response_model=OrchestratorPromptResponse)
async def generate_orchestrator_prompt(
    request: OrchestratorPromptRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate comprehensive orchestrator staging prompt (2000-3000 lines)."""
    from src.giljo_mcp.prompt_generator import OrchestratorPromptGenerator

    generator = OrchestratorPromptGenerator(db, current_user.tenant_key)
    result = await generator.generate(request.project_id, request.tool)

    return OrchestratorPromptResponse(**result)  # Returns 3000-line prompt
```

**AFTER (Thin Prompt)**:
```python
@router.post("/orchestrator", response_model=ThinPromptResponse)
async def generate_orchestrator_prompt(
    request: OrchestratorPromptRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate thin client orchestrator prompt (~10 lines).

    CRITICAL CHANGE (Handover 0088):
    - OLD: Returns 2000-3000 line prompt with embedded mission
    - NEW: Returns 10-line prompt with MCP tool reference
    - BENEFIT: 70% token reduction ACTIVE + professional UX

    Process:
    1. Create orchestrator job in database
    2. Store condensed mission with user's field priorities
    3. Return thin prompt with orchestrator_id
    4. User pastes prompt into CLI
    5. Orchestrator calls get_orchestrator_instructions() via MCP
    6. Token reduction achieved
    """
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    generator = ThinClientPromptGenerator(db, current_user.tenant_key)
    result = await generator.generate(
        project_id=request.project_id,
        user_id=str(current_user.id),  # CRITICAL: Pass user_id for field priorities
        tool=request.tool,
        instance_number=request.instance_number or 1
    )

    # Broadcast WebSocket event
    await ws_dep.broadcast_to_tenant(
        tenant_key=current_user.tenant_key,
        event_type="orchestrator:prompt_generated",
        data={
            'orchestrator_id': result.orchestrator_id,
            'project_id': result.project_id,
            'estimated_prompt_tokens': result.estimated_prompt_tokens,
            'thin_client': True
        }
    )

    return result  # Returns 10-line prompt
```

**Success Criteria**:
- ✅ Endpoint returns thin prompt (~10 lines)
- ✅ user_id passed through for field priorities
- ✅ WebSocket event broadcast correctly
- ✅ Backwards compatible response structure

---

### Phase 4: Update Frontend (4 hours)

#### Task 4.1: Update LaunchTab.vue to Display Thin Prompts

**File**: `frontend/src/components/projects/LaunchTab.vue`
**Location**: Around line 200 (prompt display section)

**Changes**:

1. **Update prompt display with "Thin Client" badge**:

```vue
<!-- BEFORE -->
<v-card-text>
  <pre class="prompt-text">{{ generatedPrompt }}</pre>
  <div class="text-caption">
    Token estimate: {{ tokenEstimate }}
  </div>
</v-card-text>

<!-- AFTER -->
<v-card-text>
  <v-chip
    color="success"
    size="small"
    class="mb-2"
  >
    <v-icon start>mdi-lightning-bolt</v-icon>
    Thin Client (70% Token Reduction Active)
  </v-chip>

  <pre class="prompt-text">{{ generatedPrompt }}</pre>

  <div class="text-caption mt-2">
    <v-icon size="small">mdi-information</v-icon>
    Prompt size: {{ estimatedPromptTokens }} tokens (~10 lines)
    <br>
    Mission fetched via MCP: {{ missionTokens }} tokens (optimized)
  </div>
</v-card-text>
```

2. **Update copy button tooltip**:

```vue
<!-- BEFORE -->
<v-btn @click="copyPrompt">
  Copy to Clipboard (3000 lines)
</v-btn>

<!-- AFTER -->
<v-btn @click="copyPrompt">
  <v-icon start>mdi-content-copy</v-icon>
  Copy Thin Prompt (10 lines)
  <v-tooltip activator="parent">
    Professional thin client prompt.
    Orchestrator fetches mission via MCP.
  </v-tooltip>
</v-btn>
```

3. **Add informational callout**:

```vue
<v-alert type="info" variant="tonal" class="mt-4">
  <v-alert-title>Thin Client Architecture</v-alert-title>
  <div class="text-body-2">
    This prompt is optimized for professional use:
    <ul class="mt-2">
      <li>Only 10 lines to copy (not 3000!)</li>
      <li>Mission fetched dynamically via MCP</li>
      <li>70% token reduction ACTIVE</li>
      <li>Lower API costs for you</li>
    </ul>
  </div>
</v-alert>
```

**Success Criteria**:
- ✅ UI clearly indicates thin client architecture
- ✅ Token savings highlighted visually
- ✅ Professional appearance maintained
- ✅ User understands what they're copying

---

### Phase 5: Deprecate Old Prompt Generator (2 hours)

#### Task 5.1: Add Deprecation Warning to `prompt_generator.py`

**File**: `src/giljo_mcp/prompt_generator.py`
**Location**: Top of file

**Add deprecation notice**:

```python
"""
Orchestrator Staging Prompt Generator (DEPRECATED - Handover 0088)

⚠️ DEPRECATED: This module generates "fat prompts" (2000-3000 lines)
that defeat the 70% token reduction feature.

REPLACEMENT: Use ThinClientPromptGenerator (thin_prompt_generator.py)

MIGRATION PATH:
- Phase 1 (v3.1): Both generators available (backwards compatibility)
- Phase 2 (v3.2): ThinClientPromptGenerator becomes default
- Phase 3 (v4.0): OrchestratorPromptGenerator removed

DO NOT USE THIS MODULE FOR NEW DEVELOPMENT.

See: handovers/0088_thin_client_stage_project_fix.md
"""

import warnings

warnings.warn(
    "OrchestratorPromptGenerator is deprecated. "
    "Use ThinClientPromptGenerator instead. "
    "See Handover 0088.",
    DeprecationWarning,
    stacklevel=2
)
```

**Success Criteria**:
- ✅ Clear deprecation warning in code
- ✅ Developers redirected to new module
- ✅ Migration path documented
- ✅ No breaking changes in v3.1

---

### Phase 6: Testing (6 hours)

#### Task 6.1: Create Comprehensive Test Suite

**File**: `tests/thin_prompt/test_thin_client_e2e.py` (NEW FILE)

**Test Cases**:

```python
"""
End-to-end tests for thin client prompt architecture (Handover 0088).

Tests the complete workflow:
1. User generates thin prompt
2. Prompt copied to clipboard
3. Orchestrator launched in Claude Code CLI
4. Orchestrator calls get_orchestrator_instructions()
5. Condensed mission returned (70% reduction)
6. Orchestrator executes mission
"""

import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_thin_prompt_generation_e2e(
    db_session,
    test_user,
    test_project,
    test_product
):
    """
    Test complete thin prompt generation workflow.

    Expected Flow:
    1. User has field priorities configured
    2. Generate thin prompt for project
    3. Verify prompt is ~10 lines
    4. Verify orchestrator job created
    5. Verify condensed mission stored
    6. Verify token estimate accurate
    """
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    # Configure user field priorities
    test_user.config_data = {
        'field_priorities': {
            'product_vision': 10,  # Full
            'architecture': 7,      # Moderate
            'codebase_summary': 4,  # Abbreviated
            'dependencies': 2       # Minimal
        }
    }
    await db_session.commit()

    # Generate thin prompt
    generator = ThinClientPromptGenerator(db_session, test_user.tenant_key)
    result = await generator.generate(
        project_id=str(test_project.id),
        user_id=str(test_user.id),
        tool='claude-code',
        instance_number=1
    )

    # Verify prompt is thin
    assert len(result.prompt.split('\n')) <= 15, "Prompt should be ~10-15 lines"
    assert result.estimated_prompt_tokens < 100, "Prompt should be <100 tokens"

    # Verify orchestrator job created
    orchestrator = await db_session.get(MCPAgentJob, result.orchestrator_id)
    assert orchestrator is not None
    assert orchestrator.agent_type == 'orchestrator'
    assert orchestrator.status == 'pending'

    # Verify mission stored
    assert orchestrator.mission is not None
    assert len(orchestrator.mission) > 0

    # Verify field priorities stored
    assert orchestrator.metadata['field_priorities'] == test_user.config_data['field_priorities']
    assert orchestrator.metadata['user_id'] == str(test_user.id)

    # Verify token estimate
    mission_tokens = len(orchestrator.mission) // 4
    assert mission_tokens < 10000, "Mission should be <10K tokens (70% reduction)"


@pytest.mark.asyncio
async def test_orchestrator_fetches_instructions_via_mcp(
    db_session,
    test_orchestrator_job,
    test_project
):
    """
    Simulate orchestrator calling get_orchestrator_instructions() MCP tool.

    Expected Flow:
    1. Orchestrator job exists in database
    2. Call get_orchestrator_instructions(orchestrator_id)
    3. Verify condensed mission returned
    4. Verify field priorities applied
    5. Verify 70% token reduction achieved
    """
    from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Store condensed mission in orchestrator
    condensed_mission = "This is a condensed mission with priority fields only."
    test_orchestrator_job.mission = condensed_mission
    test_orchestrator_job.metadata = {
        'field_priorities': {
            'product_vision': 10,
            'architecture': 4
        },
        'user_id': str(uuid4())
    }
    await db_session.commit()

    # Simulate orchestrator calling MCP tool
    result = await get_orchestrator_instructions(
        orchestrator_id=str(test_orchestrator_job.id),
        tenant_key=test_orchestrator_job.tenant_key
    )

    # Verify response
    assert 'error' not in result
    assert result['orchestrator_id'] == str(test_orchestrator_job.id)
    assert result['mission'] == condensed_mission
    assert result['token_reduction_applied'] is True
    assert result['estimated_tokens'] < 10000  # 70% reduction

    # Verify field priorities returned
    assert result['field_priorities']['product_vision'] == 10
    assert result['field_priorities']['architecture'] == 4


@pytest.mark.asyncio
async def test_token_reduction_comparison(
    db_session,
    test_user,
    test_project,
    test_product_with_large_vision
):
    """
    Compare token counts: fat prompt vs thin client.

    Measure:
    - Fat prompt: ~30,000 tokens (old approach)
    - Thin prompt: ~50 tokens (new approach)
    - Mission via MCP: ~6,000 tokens (70% reduction)
    - Total savings: 24,000 tokens (80% reduction)
    """
    # Generate fat prompt (old way)
    from src.giljo_mcp.prompt_generator import OrchestratorPromptGenerator

    fat_generator = OrchestratorPromptGenerator(db_session, test_user.tenant_key)
    fat_result = await fat_generator.generate(str(test_project.id), 'claude-code')

    fat_tokens = fat_result['token_estimate']

    # Generate thin prompt (new way)
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    thin_generator = ThinClientPromptGenerator(db_session, test_user.tenant_key)
    thin_result = await thin_generator.generate(
        project_id=str(test_project.id),
        user_id=str(test_user.id),
        tool='claude-code'
    )

    thin_tokens = thin_result.estimated_prompt_tokens

    # Fetch mission via MCP (simulating orchestrator)
    from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

    mcp_result = await get_orchestrator_instructions(
        orchestrator_id=thin_result.orchestrator_id,
        tenant_key=test_user.tenant_key
    )

    mcp_tokens = mcp_result['estimated_tokens']

    # Calculate savings
    total_thin_tokens = thin_tokens + mcp_tokens
    savings = fat_tokens - total_thin_tokens
    reduction_percent = (savings / fat_tokens) * 100

    # Verify savings
    assert reduction_percent >= 70, f"Should achieve ≥70% reduction, got {reduction_percent:.1f}%"
    assert thin_tokens < 100, f"Thin prompt should be <100 tokens, got {thin_tokens}"
    assert mcp_tokens < 10000, f"MCP mission should be <10K tokens, got {mcp_tokens}"

    print(f"""
    TOKEN REDUCTION COMPARISON:
    - Fat Prompt: {fat_tokens:,} tokens (old approach)
    - Thin Prompt: {thin_tokens:,} tokens (new approach)
    - Mission via MCP: {mcp_tokens:,} tokens (field priorities applied)
    - Total New: {total_thin_tokens:,} tokens
    - Savings: {savings:,} tokens ({reduction_percent:.1f}% reduction)
    """)


@pytest.mark.asyncio
async def test_multi_tenant_isolation(
    db_session,
    tenant1_user,
    tenant2_user,
    tenant1_project,
    tenant2_orchestrator
):
    """
    Verify thin client architecture enforces multi-tenant isolation.

    Attack Scenarios:
    1. Tenant 1 user tries to fetch Tenant 2 orchestrator instructions
    2. Cross-tenant orchestrator_id access
    3. Field priority leakage
    """
    from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Attempt cross-tenant access
    result = await get_orchestrator_instructions(
        orchestrator_id=str(tenant2_orchestrator.id),
        tenant_key=tenant1_user.tenant_key  # WRONG tenant
    )

    # Verify access denied
    assert 'error' in result
    assert 'not found' in result['error'].lower()

    # Verify no data leaked
    assert 'mission' not in result
    assert 'field_priorities' not in result
```

**Additional Test Files**:

1. `tests/thin_prompt/test_thin_client_generator.py` - Unit tests for generator
2. `tests/thin_prompt/test_mcp_tools.py` - Unit tests for MCP tools
3. `tests/api/test_thin_prompt_endpoint.py` - API endpoint tests
4. `tests/frontend/test_thin_prompt_ui.spec.js` - Frontend component tests

**Success Criteria**:
- ✅ All tests pass
- ✅ Code coverage ≥85%
- ✅ Multi-tenant isolation verified
- ✅ Token reduction validated
- ✅ E2E workflow tested

---

## Common Pitfalls to Avoid

### Pitfall 1: Forgetting to Pass user_id

**WRONG**:
```python
# This bypasses field priorities!
result = await generator.generate(project_id=project_id)
```

**CORRECT**:
```python
# This applies user's field priorities
result = await generator.generate(
    project_id=project_id,
    user_id=str(current_user.id)  # CRITICAL
)
```

**Impact**: Without user_id, field priorities are ignored and 70% token reduction is lost.

---

### Pitfall 2: Embedding Mission in Prompt Anyway

**WRONG**:
```python
# Defeats thin client architecture!
prompt = f"""
Orchestrator ID: {orchestrator_id}

YOUR MISSION:
{condensed_mission}  # DON'T EMBED THIS
"""
```

**CORRECT**:
```python
# Thin client - mission fetched via MCP
prompt = f"""
Orchestrator ID: {orchestrator_id}

Call get_orchestrator_instructions('{orchestrator_id}')
"""
```

**Impact**: Embedding mission defeats the entire purpose of this handover.

---

### Pitfall 3: Not Storing Metadata in Orchestrator Job

**WRONG**:
```python
# Field priorities lost!
orchestrator = MCPAgentJob(
    id=orchestrator_id,
    mission=condensed_mission
    # NO metadata!
)
```

**CORRECT**:
```python
# Store field priorities for MCP tool
orchestrator = MCPAgentJob(
    id=orchestrator_id,
    mission=condensed_mission,
    metadata={
        'field_priorities': field_priorities,  # CRITICAL
        'user_id': user_id,                    # CRITICAL
        'tool': tool
    }
)
```

**Impact**: MCP tool can't apply field priorities without metadata.

---

### Pitfall 4: Frontend Still Showing "Fat Prompt" Language

**WRONG**:
```vue
<v-card-title>
  Your 3000-Line Orchestrator Prompt
</v-card-title>
```

**CORRECT**:
```vue
<v-card-title>
  <v-chip color="success" size="small">Thin Client</v-chip>
  Your Optimized Orchestrator Prompt (~10 lines)
</v-card-title>
```

**Impact**: Users don't understand what changed or why it's better.

---

## Migration Plan: Fat to Thin

### Phase 1: Backwards Compatibility (v3.1)

**Week 1**:
- Implement ThinClientPromptGenerator
- Keep OrchestratorPromptGenerator (deprecated)
- Add feature flag: `USE_THIN_CLIENT_PROMPTS` (default: false)

**Week 2**:
- Add toggle in Admin Settings: "Use Thin Client Prompts (Recommended)"
- Beta test with internal team
- Gather feedback

**Week 3**:
- Make thin client default for new users
- Existing users opt-in via settings
- Monitor metrics (token usage, error rates)

### Phase 2: Default Migration (v3.2)

**Week 4**:
- Flip feature flag: `USE_THIN_CLIENT_PROMPTS` (default: true)
- Add migration banner in UI: "Upgrade to Thin Client (70% Token Savings)"
- Auto-migrate users with <5 active projects

**Week 5**:
- Migrate all remaining users
- Send notification emails explaining benefits
- Provide rollback option for 30 days

**Week 6**:
- Remove rollback option
- Deprecation warnings in logs for fat prompt usage
- Update documentation

### Phase 3: Complete Removal (v4.0)

**Week 12**:
- Remove `OrchestratorPromptGenerator` entirely
- Remove backwards compatibility code
- Clean up database (remove legacy fields)
- Archive old handovers

---

## Success Criteria

### Functional Requirements

- ✅ Thin prompts are ~10 lines (~50 tokens)
- ✅ Orchestrator calls get_orchestrator_instructions() successfully
- ✅ Condensed mission returned with field priorities applied
- ✅ 70% token reduction achieved
- ✅ Multi-tenant isolation enforced
- ✅ User experience improved (copy 10 lines, not 3000)

### Technical Requirements

- ✅ ThinClientPromptGenerator class implemented
- ✅ get_orchestrator_instructions() MCP tool implemented
- ✅ get_agent_mission() MCP tool implemented
- ✅ API endpoint refactored
- ✅ Frontend UI updated
- ✅ Old prompt generator deprecated

### Quality Requirements

- ✅ Test coverage ≥85%
- ✅ All E2E tests pass
- ✅ No breaking changes for existing users
- ✅ Performance: prompt generation <500ms
- ✅ Documentation updated

### Business Requirements

- ✅ Professional appearance (not copying novels)
- ✅ Token costs reduced by 70%
- ✅ Commercial product ready for launch
- ✅ Competitive advantage restored
- ✅ User testimonials positive

---

## Validation Checklist

Before marking this handover complete:

### Developer Checklist

- [ ] Read entire handover document
- [ ] Understand fat vs thin architecture
- [ ] Implement ThinClientPromptGenerator
- [ ] Implement get_orchestrator_instructions() MCP tool
- [ ] Implement get_agent_mission() MCP tool
- [ ] Refactor API endpoint
- [ ] Update frontend UI
- [ ] Add deprecation warnings
- [ ] Write comprehensive tests
- [ ] All tests passing
- [ ] Code reviewed by peer
- [ ] Documentation updated

### QA Checklist

- [ ] Generate thin prompt in UI
- [ ] Verify prompt is ~10 lines
- [ ] Copy prompt to clipboard
- [ ] Paste into Claude Code CLI (manual test)
- [ ] Verify orchestrator calls MCP tool
- [ ] Verify mission fetched correctly
- [ ] Check token estimates accurate
- [ ] Test multi-tenant isolation
- [ ] Test error handling (missing orchestrator, etc.)
- [ ] Verify field priorities applied
- [ ] Compare token usage before/after
- [ ] Validate 70% reduction achieved

### Product Owner Checklist

- [ ] User experience improved
- [ ] Professional appearance achieved
- [ ] Token reduction validated
- [ ] Commercial viability confirmed
- [ ] Documentation complete
- [ ] Migration plan approved
- [ ] Stakeholders notified
- [ ] Ready for production deployment

---

## Key Files Reference

### New Files Created

```
F:\GiljoAI_MCP\src\giljo_mcp\thin_prompt_generator.py (280 lines)
F:\GiljoAI_MCP\tests\thin_prompt\test_thin_client_e2e.py (350 lines)
F:\GiljoAI_MCP\tests\thin_prompt\test_thin_client_generator.py (200 lines)
F:\GiljoAI_MCP\tests\thin_prompt\test_mcp_tools.py (180 lines)
F:\GiljoAI_MCP\tests\api\test_thin_prompt_endpoint.py (150 lines)
```

### Modified Files

```
F:\GiljoAI_MCP\src\giljo_mcp\tools\orchestration.py (+200 lines)
F:\GiljoAI_MCP\api\endpoints\prompts.py (~30 lines changed)
F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue (~100 lines changed)
F:\GiljoAI_MCP\src\giljo_mcp\prompt_generator.py (deprecation notice added)
```

### Deprecated Files

```
F:\GiljoAI_MCP\src\giljo_mcp\prompt_generator.py (deprecated, remove in v4.0)
```

---

## Timeline

**Total Estimated Effort**: 24 hours (3 working days)

**Phase 1 - MCP Tools**: 4 hours
- Task 1.1: get_orchestrator_instructions() (3 hours)
- Task 1.2: get_agent_mission() (1 hour)

**Phase 2 - Prompt Generator**: 6 hours
- Task 2.1: ThinClientPromptGenerator (6 hours)

**Phase 3 - API Refactor**: 2 hours
- Task 3.1: Update endpoint (2 hours)

**Phase 4 - Frontend**: 4 hours
- Task 4.1: Update LaunchTab.vue (4 hours)

**Phase 5 - Deprecation**: 2 hours
- Task 5.1: Add warnings (2 hours)

**Phase 6 - Testing**: 6 hours
- Task 6.1: E2E tests (3 hours)
- Task 6.2: Unit tests (2 hours)
- Task 6.3: Frontend tests (1 hour)

---

## Conclusion

This handover addresses a **CRITICAL architectural flaw** that defeats our 70% token reduction promise. The fix is straightforward but must be implemented carefully to avoid breaking existing workflows.

**The Core Problem**: We built an amazing token reduction system (field priorities), then bypassed it by embedding everything in prompts anyway.

**The Solution**: Thin client architecture - prompts contain identity only, missions fetched via MCP.

**The Result**:
- Professional user experience (copy 10 lines, not 3000)
- 70% token reduction ACTIVE
- Lower API costs for customers
- Commercial-grade product ready for launch

**DO NOT SKIP THIS HANDOVER**. It is fundamental to our commercial viability.

---

**Last Updated**: 2025-11-02
**Status**: Ready for Implementation
**Priority**: P0 - CRITICAL
**Approver**: Product Owner + Tech Lead

---

**Related Handovers**:
- [Handover 0079: Orchestrator Staging Prompt Generation](completed/0079_orchestrator_staging_prompt_generation-C.md) (DEPRECATED by this handover)
- [Handover 0086A: Production-Grade Stage Project](0086A_production_grade_stage_project.md) (Context management)
- [Handover 0087: Token Estimation Active Project Link](0087_token_estimation_active_project_link.md) (Field priorities)

**Documentation**:
- [MCP Tools Manual](../docs/manuals/MCP_TOOLS_MANUAL.md) (Add new tools)
- [Stage Project Feature](../docs/STAGE_PROJECT_FEATURE.md) (Update architecture)
- [Field Priorities Guide](../docs/user_guides/field_priorities_guide.md) (Update workflow)
