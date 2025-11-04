---
Handover 0063: Per-Agent Tool Selection UI
Date: 2025-10-27
Status: SUPERSEDED (by Project 0073)
Priority: HIGH
Complexity: LOW
Duration: 6-8 hours
---

# Executive Summary

Superseded Notice

This specification is superseded by Project 0073 (Static Agent Grid) which delivers database-backed per-agent tool assignment and integrated grid display. The metadata-based UI selector proposed here is no longer the product direction.

See: docs/features/agent_grid_static_0073.md and 0060-series retirement summary in docs/archive/0060_SERIES_RETIREMENT_SUMMARY.md.

The GiljoAI MCP Server supports multiple external agent tools (Claude Code, Codex, Gemini CLI) via Integrations settings (Handover 0027), but currently lacks per-agent tool selection. This handover adds UI controls to assign a specific tool (Claude/Codex/Gemini) to each agent, with backend storage and validation.

**Key Principle**: Each agent should have a designated external tool, allowing users to leverage the strengths of different AI coding assistants for different types of work.

The system will add a tool selector dropdown to agent creation/edit forms, store the selection in the agent's metadata, and display the selected tool in agent cards and lists.

---

# Problem Statement

## Current State

External tools are configured globally but not assigned per-agent:
- Integrations tab has Claude Code, Codex, Gemini CLI settings (Handover 0027)
- No way to specify which tool an agent should use
- Agent cards don't show which tool is assigned
- Orchestrator can't route work to specific tools
- Manual coordination required to know which tool to use

## Gaps Without This Implementation

1. **No Tool Assignment**: Can't specify which agent uses which tool
2. **Inefficient Routing**: Can't automatically route work to best tool
3. **Poor Visibility**: Users don't know which tool each agent uses
4. **Manual Coordination**: Must manually track tool assignments
5. **No Validation**: Can assign tool that's not configured

---

# Implementation Plan

## Overview

This implementation adds a tool selector to agent forms, stores selection in agent metadata, and displays tool in agent UI components. No new database columns needed - uses existing metadata JSONB field.

**Total Estimated Lines of Code**: ~300 lines across 5 files

## Phase 1: Backend - Agent Tool Storage (2 hours)

**File**: `src/giljo_mcp/models.py`

**No Schema Changes Needed** - Use existing `metadata` JSONB field:

```python
# Agent metadata structure (already exists):
{
  "tool_type": "claude",  # NEW: claude, codex, gemini, or null
  "tool_config": {        # NEW: Tool-specific config
    "version": "claude-sonnet-4-5",
    "mcp_server_url": "http://localhost:7272"
  },
  # ... existing metadata fields
}
```

**File**: `api/endpoints/agents.py`

**Modify Create/Update Endpoints**:

```python
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any

class AgentToolConfig(BaseModel):
    """Agent tool configuration."""
    tool_type: Optional[str] = None  # claude, codex, gemini
    tool_config: Optional[Dict[str, Any]] = None

    @validator('tool_type')
    def validate_tool_type(cls, v):
        if v is not None and v not in ['claude', 'codex', 'gemini']:
            raise ValueError('tool_type must be one of: claude, codex, gemini')
        return v


class CreateAgentRequest(BaseModel):
    """Existing fields..."""
    name: str
    agent_type: str
    capabilities: List[str]
    # NEW FIELD:
    tool_config: Optional[AgentToolConfig] = None


class UpdateAgentRequest(BaseModel):
    """Existing fields..."""
    name: Optional[str] = None
    agent_type: Optional[str] = None
    # NEW FIELD:
    tool_config: Optional[AgentToolConfig] = None


@router.post("/", response_model=AgentResponse)
async def create_agent(
    request: CreateAgentRequest,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new agent with optional tool configuration."""

    # Validate tool is configured if tool_type specified
    if request.tool_config and request.tool_config.tool_type:
        await validate_tool_configured(
            request.tool_config.tool_type,
            tenant_key,
            db
        )

    # Build metadata
    metadata = request.metadata or {}
    if request.tool_config:
        metadata['tool_type'] = request.tool_config.tool_type
        metadata['tool_config'] = request.tool_config.tool_config or {}

    agent = MCPAgent(
        name=request.name,
        agent_type=request.agent_type,
        capabilities=request.capabilities,
        metadata=metadata,
        tenant_key=tenant_key
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return agent


async def validate_tool_configured(
    tool_type: str,
    tenant_key: str,
    db: AsyncSession
):
    """
    Validate that the specified tool is configured in tenant settings.

    Raises HTTPException if tool not configured.
    """
    from sqlalchemy import select
    from src.giljo_mcp.models import TenantSettings

    result = await db.execute(
        select(TenantSettings).where(
            TenantSettings.tenant_key == tenant_key
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assign {tool_type} - tenant settings not found"
        )

    integrations = settings.integrations or {}
    tool_configs = {
        'claude': integrations.get('claude_code', {}),
        'codex': integrations.get('codex', {}),
        'gemini': integrations.get('gemini_cli', {})
    }

    tool_config = tool_configs.get(tool_type, {})
    if not tool_config.get('enabled', False):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assign {tool_type} - tool not configured. Please configure in Settings > Integrations."
        )
```

**Add Helper Endpoint**:

```python
@router.get("/available-tools")
async def get_available_tools(
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of available (configured) tools for this tenant.

    Returns:
        {
            "tools": [
                {"type": "claude", "name": "Claude Code", "enabled": true},
                {"type": "codex", "name": "Codex", "enabled": false},
                {"type": "gemini", "name": "Gemini CLI", "enabled": true}
            ]
        }
    """
    from sqlalchemy import select
    from src.giljo_mcp.models import TenantSettings

    result = await db.execute(
        select(TenantSettings).where(
            TenantSettings.tenant_key == tenant_key
        )
    )
    settings = result.scalar_one_or_none()

    integrations = settings.integrations if settings else {}

    tools = [
        {
            "type": "claude",
            "name": "Claude Code",
            "enabled": integrations.get('claude_code', {}).get('enabled', False),
            "version": integrations.get('claude_code', {}).get('version', 'claude-sonnet-4-5')
        },
        {
            "type": "codex",
            "name": "Codex",
            "enabled": integrations.get('codex', {}).get('enabled', False),
            "version": integrations.get('codex', {}).get('version', 'latest')
        },
        {
            "type": "gemini",
            "name": "Gemini CLI",
            "enabled": integrations.get('gemini_cli', {}).get('enabled', False),
            "version": integrations.get('gemini_cli', {}).get('version', '2.0-flash-exp')
        }
    ]

    return {"tools": tools}
```

## Phase 2: Frontend - Tool Selector Component (2-3 hours)

**File**: `frontend/src/components/agents/AgentToolSelector.vue` (NEW)

```vue
<template>
  <v-select
    v-model="selectedTool"
    :items="availableTools"
    item-title="name"
    item-value="type"
    label="Agent Tool"
    placeholder="Select external tool"
    clearable
    :loading="loading"
    :disabled="disabled"
    prepend-icon="mdi-tools"
    hint="Select which external AI tool this agent will use"
    persistent-hint
  >
    <template v-slot:item="{ props, item }">
      <v-list-item
        v-bind="props"
        :disabled="!item.raw.enabled"
      >
        <template v-slot:prepend>
          <v-icon :color="item.raw.enabled ? 'primary' : 'grey'">
            {{ getToolIcon(item.raw.type) }}
          </v-icon>
        </template>

        <template v-slot:append v-if="!item.raw.enabled">
          <v-chip size="small" color="warning">
            Not Configured
          </v-chip>
        </template>

        <v-list-item-subtitle v-if="item.raw.version">
          Version: {{ item.raw.version }}
        </v-list-item-subtitle>
      </v-list-item>
    </template>

    <template v-slot:selection="{ item }">
      <v-chip :prepend-icon="getToolIcon(item.raw.type)">
        {{ item.raw.name }}
      </v-chip>
    </template>
  </v-select>

  <!-- Configuration Notice -->
  <v-alert
    v-if="hasUnconfiguredTools"
    type="info"
    variant="tonal"
    density="compact"
    class="mt-2"
  >
    Some tools are not configured. Visit
    <router-link to="/settings/integrations">Settings > Integrations</router-link>
    to enable them.
  </v-alert>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/services/api'

const props = defineProps({
  modelValue: {
    type: String,
    default: null
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const availableTools = ref([])
const loading = ref(false)

const selectedTool = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const hasUnconfiguredTools = computed(() => {
  return availableTools.value.some(tool => !tool.enabled)
})

function getToolIcon(type) {
  switch (type) {
    case 'claude': return 'mdi-robot'
    case 'codex': return 'mdi-code-braces'
    case 'gemini': return 'mdi-google'
    default: return 'mdi-tools'
  }
}

async function fetchAvailableTools() {
  loading.value = true
  try {
    const response = await api.agents.getAvailableTools()
    availableTools.value = response.data.tools
  } catch (error) {
    console.error('[TOOL SELECTOR] Error fetching tools:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAvailableTools()
})
</script>
```

## Phase 3: Integration with Agent Forms (1-2 hours)

**File**: `frontend/src/components/agents/AgentFormDialog.vue`

**Add Import**:

```javascript
import AgentToolSelector from './AgentToolSelector.vue'
```

**Add to Form**:

```vue
<v-form ref="form" v-model="valid">
  <!-- Existing fields: name, type, capabilities -->

  <!-- NEW: Tool Selector -->
  <AgentToolSelector
    v-model="formData.tool_type"
    :disabled="loading"
    class="mb-4"
  />

  <!-- Existing fields continue... -->
</v-form>
```

**Update Form Data**:

```javascript
const formData = ref({
  name: '',
  agent_type: '',
  capabilities: [],
  tool_type: null  // NEW
})

async function saveAgent() {
  if (!valid.value) return

  loading.value = true
  try {
    const payload = {
      ...formData.value,
      tool_config: formData.value.tool_type ? {
        tool_type: formData.value.tool_type,
        tool_config: {}
      } : null
    }

    if (isEditing.value) {
      await api.agents.updateAgent(props.agent.id, payload)
    } else {
      await api.agents.createAgent(payload)
    }

    emit('saved')
    closeDialog()
  } catch (error) {
    console.error('[AGENT FORM] Save error:', error)
    errorMessage.value = error.response?.data?.detail || 'Failed to save agent'
  } finally {
    loading.value = false
  }
}
```

## Phase 4: Display Tool in Agent Cards/Lists (1 hour)

**File**: `frontend/src/components/agents/EnhancedAgentCard.vue`

**Add Tool Display**:

```vue
<v-card-title>
  <v-avatar :color="agentStatusColor" size="40" class="mr-3">
    <v-icon color="white">{{ agentIcon }}</v-icon>
  </v-avatar>
  <div class="flex-grow-1">
    <div class="text-h6">{{ agent.name }}</div>
    <div class="text-caption text-grey">{{ agent.agent_type }}</div>
  </div>

  <!-- NEW: Tool Badge -->
  <v-chip
    v-if="agentTool"
    size="small"
    :prepend-icon="getToolIcon(agentTool)"
    color="primary"
    variant="tonal"
  >
    {{ getToolName(agentTool) }}
  </v-chip>
</v-card-title>
```

**Add Computed**:

```javascript
const agentTool = computed(() => {
  return agent.value.metadata?.tool_type || null
})

function getToolIcon(type) {
  switch (type) {
    case 'claude': return 'mdi-robot'
    case 'codex': return 'mdi-code-braces'
    case 'gemini': return 'mdi-google'
    default: return 'mdi-tools'
  }
}

function getToolName(type) {
  switch (type) {
    case 'claude': return 'Claude'
    case 'codex': return 'Codex'
    case 'gemini': return 'Gemini'
    default: return 'Unknown'
  }
}
```

## Phase 5: API Service Integration (30 minutes)

**File**: `frontend/src/services/api.js`

**Add Method**:

```javascript
agents: {
  // ... existing methods
  getAvailableTools: () => apiClient.get('/api/v1/agents/available-tools')
}
```

---

# Files to Modify

1. **api/endpoints/agents.py** (+120 lines)
   - Modify create/update endpoints to accept tool_config
   - Add validate_tool_configured helper
   - Add get_available_tools endpoint

2. **frontend/src/components/agents/AgentToolSelector.vue** (~100 lines, NEW FILE)
   - Complete tool selector component
   - Disabled state for unconfigured tools
   - Configuration notice

3. **frontend/src/components/agents/AgentFormDialog.vue** (+30 lines)
   - Import and integrate tool selector
   - Update save logic

4. **frontend/src/components/agents/EnhancedAgentCard.vue** (+30 lines)
   - Display tool badge
   - Tool icon and name helpers

5. **frontend/src/services/api.js** (+5 lines)
   - Add getAvailableTools method

**Total**: ~285 lines across 5 files (1 new, 4 modified)

---

# Success Criteria

## Functional Requirements
- Tool selector dropdown in agent create/edit forms
- Only configured tools selectable
- Validation prevents assigning unconfigured tools
- Tool selection stored in agent metadata
- Tool displayed in agent cards with icon/badge
- Clearing tool selection removes assignment
- Multi-tenant isolation enforced

## User Experience Requirements
- Clear indication which tools are configured
- Link to Integrations settings for unconfigured tools
- Tool icons visually distinct
- Smooth form validation
- Proper error messages

## Technical Requirements
- No database schema changes (uses metadata JSONB)
- Backward compatible (existing agents work without tool)
- Validation on both frontend and backend
- Available tools fetched from tenant settings
- Proper error handling

---

# Related Handovers

- **Handover 0027**: Integrations Tab (Admin Settings v3.0) (DEPENDS ON)
  - Provides tool configuration

- **Handover 0062**: Enhanced Agent Cards with Project Context (COMPLEMENTS)
  - Agent cards display tool assignments

- **Handover 0066**: Codex MCP Integration (ENABLES)
  - Allows assigning Codex to agents

- **Handover 0067**: Gemini MCP Integration (ENABLES)
  - Allows assigning Gemini to agents

---

# Risk Assessment

**Complexity**: LOW (simple metadata storage)
**Risk**: LOW (additive, no schema changes)
**Breaking Changes**: None
**Performance Impact**: None

---

# Timeline Estimate

**Phase 1**: 2 hours (Backend)
**Phase 2**: 2-3 hours (Tool selector component)
**Phase 3**: 1-2 hours (Form integration)
**Phase 4**: 1 hour (Display in cards)
**Phase 5**: 30 minutes (API service)

**Total**: 6-8 hours for experienced developer

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Priority**: HIGH (enables multi-tool workflows)

---

**End of Handover 0063**
