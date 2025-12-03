# Handover 0048: Product Field Priority Configuration in User Settings

**Date**: 2025-10-26
**From**: System Architect
**To**: Full-Stack Development Team
**Priority**: Medium
**Estimated Effort**: 4-6 hours
**Status**: Ready to Implement
**Dependencies**: Handover 0042 (Product Rich Context Fields - COMPLETE)

---

## Executive Summary

**Objective**: Implement intelligent field prioritization for AI agent mission generation, allowing power users to customize which product configuration fields are prioritized when building agent context within token budget constraints.

**Current Problem**:
- Handover 0042 added rich `config_data` fields (tech_stack, architecture, features, test_config)
- Only `tech_stack` is currently included in agent mission prompts
- No prioritization system exists - all fields treated equally
- Token budget (1500 tokens) can be exceeded with all fields included
- Users have no visibility into what agents receive

**Proposed Solution**:
- Add **Field Priority Configuration** to User Settings → General tab
- Implement smart default priority order (3 tiers: P1/P2/P3)
- Include ALL config_data fields in mission prompts (ordered by priority)
- Allow power users to customize priority via drag-drop interface
- Visual token budget indicator shows real-time impact
- Product creation form stays clean with small info tooltip

**Value Delivered**:
- **Intelligent Context**: Agents receive most important fields first
- **Token Optimization**: P3 fields dropped if budget exceeded
- **User Control**: Power users can fine-tune for their workflow
- **Discoverability**: Clear separation of content entry vs. configuration
- **Professional UX**: Matches industry patterns (VS Code, IDEs)

---

## Research Findings

### Current Mission Prompt Structure

**File**: `src/giljo_mcp/mission_planner.py:420-470`

```python
mission_content = f"""# Mission: {agent_config.role.title()} for {project.name}

## Project Context
Product: {product.name}
Project: {project.name}
Mission: {project.mission}
Complexity: {analysis.complexity}

## Your Role
{responsibilities}

## Relevant Vision Sections
{vision_chunks}

## Technology Stack          ← ONLY config_data field currently used
{tech_stack}

## Success Criteria
{success_criteria}

## Scope Boundary
{scope}

## Communication Protocol
{protocol}
"""
```

### Missing Fields (Handover 0042 Data NOT in Prompts)

❌ **`config_data.architecture.pattern`** - Architecture approach
❌ **`config_data.architecture.api_style`** - API communication style
❌ **`config_data.architecture.design_patterns`** - Design patterns
❌ **`config_data.features.core`** - Core feature descriptions
❌ **`config_data.test_config.strategy`** - Testing methodology
❌ **`config_data.test_config.frameworks`** - Testing tools

**Result**: Agents miss critical context despite users providing it!

---

## Implementation Plan

### Phase 1: Backend - User Settings Schema (1 hour)

#### 1.1 Update User Model

**File**: `src/giljo_mcp/models.py` (User class)

Add field priority configuration:

```python
class User(Base):
    # ... existing fields ...

    # Handover 0048: Field priority configuration
    field_priority_config = Column(
        JSONB,
        nullable=True,
        default=None,
        comment="User-customizable field priority for agent mission generation"
    )
```

#### 1.2 Default Priority Schema

**File**: `src/giljo_mcp/config/defaults.py` (new file)

```python
"""Default configurations for GiljoAI MCP"""

DEFAULT_FIELD_PRIORITY = {
    "priority_1": [
        "tech_stack.languages",
        "tech_stack.backend",
        "tech_stack.frontend",
        "architecture.pattern",
        "features.core",
    ],
    "priority_2": [
        "tech_stack.database",
        "architecture.api_style",
        "test_config.strategy",
    ],
    "priority_3": [
        "tech_stack.infrastructure",
        "architecture.design_patterns",
        "architecture.notes",
        "test_config.frameworks",
        "test_config.coverage_target",
    ],
    "token_budget": 1500,
    "version": "1.0",  # For future migrations
}
```

#### 1.3 Database Migration

**File**: `migrations/versions/XXXX_add_field_priority_config.py`

```python
"""Add field_priority_config to users table

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-10-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def upgrade():
    op.add_column('users',
        sa.Column('field_priority_config', JSONB, nullable=True)
    )


def downgrade():
    op.drop_column('users', 'field_priority_config')
```

---

### Phase 2: Backend - Mission Generation Enhancement (2 hours)

#### 2.1 Update Mission Planner

**File**: `src/giljo_mcp/mission_planner.py`

**Step 1**: Add field priority resolver

```python
class MissionPlanner:

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.default_priority = DEFAULT_FIELD_PRIORITY

    def _get_field_priority_config(self, user_id: str) -> dict:
        """
        Get user's field priority configuration or default.

        Args:
            user_id: User ID

        Returns:
            Field priority config dict
        """
        # Query user settings
        user = self.db_manager.session.query(User).filter_by(id=user_id).first()

        # Return user custom config or default
        if user and user.field_priority_config:
            return user.field_priority_config

        return self.default_priority

    def _build_config_data_section(
        self,
        product: Product,
        priority_config: dict,
        token_budget: int
    ) -> tuple[str, int]:
        """
        Build config_data section respecting priority and token budget.

        Args:
            product: Product with config_data
            priority_config: Priority configuration
            token_budget: Remaining token budget

        Returns:
            (section_content, tokens_used)
        """
        if not product.config_data:
            return "", 0

        content = "\n## Product Configuration\n"
        tokens_used = self._count_tokens(content)

        # Process Priority 1 (always include)
        for field_path in priority_config.get("priority_1", []):
            field_content = self._get_field_value(product.config_data, field_path)
            if field_content:
                section = self._format_field(field_path, field_content)
                content += section
                tokens_used += self._count_tokens(section)

        # Process Priority 2 (include if budget allows)
        for field_path in priority_config.get("priority_2", []):
            field_content = self._get_field_value(product.config_data, field_path)
            if field_content:
                section = self._format_field(field_path, field_content)
                section_tokens = self._count_tokens(section)

                if tokens_used + section_tokens <= token_budget:
                    content += section
                    tokens_used += section_tokens
                else:
                    break  # Stop if budget exceeded

        # Process Priority 3 (include if budget allows)
        for field_path in priority_config.get("priority_3", []):
            field_content = self._get_field_value(product.config_data, field_path)
            if field_content:
                section = self._format_field(field_path, field_content)
                section_tokens = self._count_tokens(section)

                if tokens_used + section_tokens <= token_budget:
                    content += section
                    tokens_used += section_tokens
                else:
                    break  # Stop if budget exceeded

        return content, tokens_used

    def _get_field_value(self, config_data: dict, field_path: str) -> any:
        """
        Get field value from config_data using dot notation.

        Args:
            config_data: Product config_data dict
            field_path: Dot-separated path (e.g., "tech_stack.languages")

        Returns:
            Field value or None
        """
        keys = field_path.split(".")
        value = config_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def _format_field(self, field_path: str, value: any) -> str:
        """
        Format field for mission content.

        Args:
            field_path: Field path (e.g., "tech_stack.languages")
            value: Field value

        Returns:
            Formatted section
        """
        # Human-readable labels
        labels = {
            "tech_stack.languages": "Programming Languages",
            "tech_stack.backend": "Backend Stack",
            "tech_stack.frontend": "Frontend Stack",
            "tech_stack.database": "Databases",
            "tech_stack.infrastructure": "Infrastructure",
            "architecture.pattern": "Architecture Pattern",
            "architecture.api_style": "API Style",
            "architecture.design_patterns": "Design Patterns",
            "architecture.notes": "Architecture Notes",
            "features.core": "Core Features",
            "test_config.strategy": "Testing Strategy",
            "test_config.frameworks": "Testing Frameworks",
            "test_config.coverage_target": "Coverage Target",
        }

        label = labels.get(field_path, field_path)

        # Format based on type
        if isinstance(value, list):
            items = "\n".join(f"- {item}" for item in value)
            return f"\n### {label}\n{items}\n"
        elif isinstance(value, (int, float)):
            return f"\n### {label}\n{value}%\n"
        else:
            return f"\n### {label}\n{value}\n"
```

**Step 2**: Update mission generation

```python
async def _generate_agent_mission(
    self,
    agent_config: AgentConfig,
    analysis: RequirementAnalysis,
    product: Product,
    project: Project,
    vision_chunks: List[str],
    user_id: str,  # NEW: Pass user ID
) -> Mission:
    """Generate a condensed mission for a specific agent."""

    # Get user's field priority configuration
    priority_config = self._get_field_priority_config(user_id)

    # ... existing code for responsibilities, vision chunks, etc. ...

    # Build base mission content
    mission_content = f"""# Mission: {agent_config.role.title()} for {project.name}

## Project Context
Product: {product.name}
Project: {project.name}
Mission: {project.mission}
Complexity: {analysis.complexity}

## Your Role
{responsibilities}

## Relevant Vision Sections
{vision_sections}
"""

    # Calculate remaining token budget
    base_tokens = self._count_tokens(mission_content)
    token_budget = priority_config.get("token_budget", 1500)
    remaining_budget = token_budget - base_tokens - 200  # Reserve 200 for footer

    # Add config_data section with priority
    config_section, config_tokens = self._build_config_data_section(
        product,
        priority_config,
        remaining_budget
    )
    mission_content += config_section

    # Add success criteria and footer
    mission_content += f"""
## Success Criteria
{success_criteria}

## Scope Boundary
- Focus ONLY on {agent_config.role} responsibilities
- Stay within the context of {project.name}
- Coordinate with other agents through the Orchestrator

## Communication Protocol
- Report progress and blockers to the Orchestrator
- Request clarification when requirements are unclear
- Share insights and findings with relevant agents
"""

    token_count = self._count_tokens(mission_content)

    return Mission(
        agent_role=agent_config.role,
        content=mission_content,
        token_count=token_count,
        priority=agent_config.priority,
        # ... rest of mission fields ...
    )
```

---

### Phase 3: API Endpoints (1 hour)

#### 3.1 User Settings Endpoint

**File**: `api/endpoints/users.py` (new or extend existing)

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Any

class FieldPriorityConfig(BaseModel):
    priority_1: List[str] = Field(..., description="Highest priority fields (always included)")
    priority_2: List[str] = Field(..., description="High priority fields (included if budget allows)")
    priority_3: List[str] = Field(..., description="Medium priority fields (included last)")
    token_budget: int = Field(1500, description="Maximum tokens for config_data section")
    version: str = Field("1.0", description="Config schema version")


@router.get("/api/v1/users/me/field-priority", response_model=FieldPriorityConfig)
async def get_field_priority_config(
    current_user: User = Depends(get_current_user)
):
    """Get user's field priority configuration or default"""
    if current_user.field_priority_config:
        return FieldPriorityConfig(**current_user.field_priority_config)

    # Return default
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
    return FieldPriorityConfig(**DEFAULT_FIELD_PRIORITY)


@router.put("/api/v1/users/me/field-priority", response_model=FieldPriorityConfig)
async def update_field_priority_config(
    config: FieldPriorityConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's field priority configuration"""

    # Validate that all fields are valid
    all_fields = config.priority_1 + config.priority_2 + config.priority_3
    valid_fields = {
        "tech_stack.languages", "tech_stack.backend", "tech_stack.frontend",
        "tech_stack.database", "tech_stack.infrastructure",
        "architecture.pattern", "architecture.api_style", "architecture.design_patterns",
        "architecture.notes", "features.core",
        "test_config.strategy", "test_config.frameworks", "test_config.coverage_target",
    }

    for field in all_fields:
        if field not in valid_fields:
            raise HTTPException(status_code=400, detail=f"Invalid field: {field}")

    # Ensure no duplicates across priorities
    if len(all_fields) != len(set(all_fields)):
        raise HTTPException(status_code=400, detail="Duplicate fields across priorities")

    # Update user settings
    current_user.field_priority_config = config.dict()
    db.commit()

    return config


@router.post("/api/v1/users/me/field-priority/reset")
async def reset_field_priority_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset field priority to defaults"""
    current_user.field_priority_config = None
    db.commit()

    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
    return FieldPriorityConfig(**DEFAULT_FIELD_PRIORITY)
```

---

### Phase 4: Frontend - Settings UI (2 hours)

#### 4.1 Settings Store

**File**: `frontend/src/stores/settings.js` (extend or create)

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useSettingsStore = defineStore('settings', () => {
  const fieldPriorityConfig = ref(null)
  const loading = ref(false)

  async function fetchFieldPriorityConfig() {
    loading.value = true
    try {
      const response = await api.users.getFieldPriorityConfig()
      fieldPriorityConfig.value = response.data
    } catch (error) {
      console.error('Failed to fetch field priority config:', error)
    } finally {
      loading.value = false
    }
  }

  async function updateFieldPriorityConfig(config) {
    loading.value = true
    try {
      const response = await api.users.updateFieldPriorityConfig(config)
      fieldPriorityConfig.value = response.data
      return true
    } catch (error) {
      console.error('Failed to update field priority config:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function resetFieldPriorityConfig() {
    loading.value = true
    try {
      const response = await api.users.resetFieldPriorityConfig()
      fieldPriorityConfig.value = response.data
      return true
    } catch (error) {
      console.error('Failed to reset field priority config:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    fieldPriorityConfig,
    loading,
    fetchFieldPriorityConfig,
    updateFieldPriorityConfig,
    resetFieldPriorityConfig,
  }
})
```

#### 4.2 API Service Extension

**File**: `frontend/src/services/api.js`

```javascript
// Add to users section
users: {
  // ... existing methods ...

  // Handover 0048: Field priority configuration
  getFieldPriorityConfig: () => apiClient.get('/api/v1/users/me/field-priority'),
  updateFieldPriorityConfig: (config) => apiClient.put('/api/v1/users/me/field-priority', config),
  resetFieldPriorityConfig: () => apiClient.post('/api/v1/users/me/field-priority/reset'),
}
```

#### 4.3 Settings View Component

**File**: `frontend/src/views/SettingsView.vue` (extend General tab)

Add new section:

```vue
<template>
  <!-- Existing Settings tabs -->
  <v-tabs v-model="activeTab">
    <v-tab value="general">General</v-tab>
    <v-tab value="security">Security</v-tab>
    <!-- ... other tabs ... -->
  </v-tabs>

  <v-tabs-window v-model="activeTab">
    <v-tabs-window-item value="general">
      <!-- Existing general settings -->

      <!-- Handover 0048: Field Priority Configuration -->
      <v-divider class="my-6"></v-divider>

      <div class="text-h6 mb-4">
        <v-icon start>mdi-priority-high</v-icon>
        Field Priority for AI Agents
      </div>

      <v-alert type="info" variant="tonal" density="compact" class="mb-4">
        Controls which product configuration fields are prioritized when generating
        AI agent missions. Fields are included top-to-bottom until token budget ({{ tokenBudget }}) is reached.
      </v-alert>

      <!-- Priority 1 -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="d-flex align-center">
          <v-icon color="error" start>mdi-numeric-1-circle</v-icon>
          Priority 1 - Always Included
        </v-card-title>
        <v-card-text>
          <draggable
            v-model="priority1Fields"
            group="fields"
            item-key="id"
            handle=".drag-handle"
            @change="onPriorityChange"
          >
            <template #item="{ element }">
              <v-chip
                class="ma-1 drag-handle"
                closable
                @click:close="removeField(element, 'priority_1')"
              >
                <v-icon start size="small">mdi-drag-vertical</v-icon>
                {{ getFieldLabel(element) }}
              </v-chip>
            </template>
          </draggable>
        </v-card-text>
      </v-card>

      <!-- Priority 2 -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="d-flex align-center">
          <v-icon color="warning" start>mdi-numeric-2-circle</v-icon>
          Priority 2 - High (Included if Token Budget Allows)
        </v-card-title>
        <v-card-text>
          <draggable
            v-model="priority2Fields"
            group="fields"
            item-key="id"
            handle=".drag-handle"
            @change="onPriorityChange"
          >
            <template #item="{ element }">
              <v-chip
                class="ma-1 drag-handle"
                closable
                @click:close="removeField(element, 'priority_2')"
              >
                <v-icon start size="small">mdi-drag-vertical</v-icon>
                {{ getFieldLabel(element) }}
              </v-chip>
            </template>
          </draggable>
        </v-card-text>
      </v-card>

      <!-- Priority 3 -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="d-flex align-center">
          <v-icon color="info" start>mdi-numeric-3-circle</v-icon>
          Priority 3 - Medium (Included Last)
        </v-card-title>
        <v-card-text>
          <draggable
            v-model="priority3Fields"
            group="fields"
            item-key="id"
            handle=".drag-handle"
            @change="onPriorityChange"
          >
            <template #item="{ element }">
              <v-chip
                class="ma-1 drag-handle"
                closable
                @click:close="removeField(element, 'priority_3')"
              >
                <v-icon start size="small">mdi-drag-vertical</v-icon>
                {{ getFieldLabel(element) }}
              </v-chip>
            </template>
          </draggable>
        </v-card-text>
      </v-card>

      <!-- Token Budget Indicator -->
      <v-card variant="tonal" color="primary" class="mb-4">
        <v-card-text>
          <div class="d-flex align-center justify-space-between">
            <div>
              <div class="text-caption">Estimated Context Size</div>
              <div class="text-h6">{{ estimatedTokens }} / {{ tokenBudget }} tokens</div>
            </div>
            <v-progress-circular
              :model-value="tokenPercentage"
              :color="tokenPercentage > 90 ? 'error' : tokenPercentage > 70 ? 'warning' : 'success'"
              size="64"
            >
              {{ tokenPercentage }}%
            </v-progress-circular>
          </div>
        </v-card-text>
      </v-card>

      <!-- Actions -->
      <div class="d-flex gap-2">
        <v-btn
          color="primary"
          variant="flat"
          @click="saveFieldPriority"
          :loading="saving"
          :disabled="!hasChanges"
        >
          <v-icon start>mdi-content-save</v-icon>
          Save Changes
        </v-btn>

        <v-btn
          variant="outlined"
          @click="resetToDefaults"
          :disabled="saving"
        >
          <v-icon start>mdi-restore</v-icon>
          Reset to Defaults
        </v-btn>
      </div>
    </v-tabs-window-item>
  </v-tabs-window>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useToast } from '@/composables/useToast'
import draggable from 'vuedraggable'

const settingsStore = useSettingsStore()
const { showToast } = useToast()

const activeTab = ref('general')
const priority1Fields = ref([])
const priority2Fields = ref([])
const priority3Fields = ref([])
const tokenBudget = ref(1500)
const saving = ref(false)
const hasChanges = ref(false)

// Field labels for display
const fieldLabels = {
  'tech_stack.languages': 'Programming Languages',
  'tech_stack.backend': 'Backend Stack',
  'tech_stack.frontend': 'Frontend Stack',
  'tech_stack.database': 'Databases',
  'tech_stack.infrastructure': 'Infrastructure',
  'architecture.pattern': 'Architecture Pattern',
  'architecture.api_style': 'API Style',
  'architecture.design_patterns': 'Design Patterns',
  'architecture.notes': 'Architecture Notes',
  'features.core': 'Core Features',
  'test_config.strategy': 'Testing Strategy',
  'test_config.frameworks': 'Testing Frameworks',
  'test_config.coverage_target': 'Coverage Target',
}

const estimatedTokens = computed(() => {
  // Rough estimation: ~50 tokens per P1 field, ~30 per P2, ~20 per P3
  const p1 = priority1Fields.value.length * 50
  const p2 = priority2Fields.value.length * 30
  const p3 = priority3Fields.value.length * 20
  return p1 + p2 + p3 + 500 // +500 for base mission structure
})

const tokenPercentage = computed(() => {
  return Math.round((estimatedTokens.value / tokenBudget.value) * 100)
})

function getFieldLabel(fieldPath) {
  return fieldLabels[fieldPath] || fieldPath
}

function onPriorityChange() {
  hasChanges.value = true
}

function removeField(field, priority) {
  // Remove from current priority
  if (priority === 'priority_1') {
    priority1Fields.value = priority1Fields.value.filter(f => f !== field)
  } else if (priority === 'priority_2') {
    priority2Fields.value = priority2Fields.value.filter(f => f !== field)
  } else if (priority === 'priority_3') {
    priority3Fields.value = priority3Fields.value.filter(f => f !== field)
  }
  hasChanges.value = true
}

async function saveFieldPriority() {
  saving.value = true
  try {
    await settingsStore.updateFieldPriorityConfig({
      priority_1: priority1Fields.value,
      priority_2: priority2Fields.value,
      priority_3: priority3Fields.value,
      token_budget: tokenBudget.value,
      version: '1.0',
    })

    hasChanges.value = false

    showToast({
      message: 'Field priority configuration saved',
      type: 'success',
      duration: 3000,
    })
  } catch (error) {
    showToast({
      message: 'Failed to save configuration',
      type: 'error',
      duration: 5000,
    })
  } finally {
    saving.value = false
  }
}

async function resetToDefaults() {
  if (!confirm('Reset field priorities to defaults?')) return

  saving.value = true
  try {
    await settingsStore.resetFieldPriorityConfig()
    await loadConfig()

    hasChanges.value = false

    showToast({
      message: 'Reset to default priorities',
      type: 'success',
      duration: 3000,
    })
  } catch (error) {
    showToast({
      message: 'Failed to reset configuration',
      type: 'error',
      duration: 5000,
    })
  } finally {
    saving.value = false
  }
}

async function loadConfig() {
  await settingsStore.fetchFieldPriorityConfig()

  const config = settingsStore.fieldPriorityConfig
  if (config) {
    priority1Fields.value = [...config.priority_1]
    priority2Fields.value = [...config.priority_2]
    priority3Fields.value = [...config.priority_3]
    tokenBudget.value = config.token_budget
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.drag-handle {
  cursor: move;
}
</style>
```

#### 4.4 Product Form Tooltip

**File**: `frontend/src/views/ProductsView.vue`

Add small info alert at top of config tabs:

```vue
<!-- Tech Stack Tab -->
<v-tabs-window-item value="tech">
  <v-alert type="info" variant="tonal" density="compact" class="mb-4">
    <v-icon start size="small">mdi-information-outline</v-icon>
    Field priority affects AI agent context delivery.
    <a href="/settings?tab=general" class="text-decoration-none">
      Configure in Settings → General
    </a>
  </v-alert>

  <div class="text-subtitle-1 mb-4">Technology Stack Configuration</div>

  <!-- Existing textarea fields -->
</v-tabs-window-item>
```

---

### Phase 5: Testing (1 hour)

#### 5.1 Backend Tests

**File**: `tests/unit/test_mission_planner_priority.py` (new)

```python
"""Tests for field priority in mission generation"""

import pytest
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY


def test_default_priority_config():
    """Test default priority configuration"""
    config = DEFAULT_FIELD_PRIORITY

    assert "priority_1" in config
    assert "priority_2" in config
    assert "priority_3" in config
    assert config["token_budget"] == 1500

    # Verify no duplicates
    all_fields = config["priority_1"] + config["priority_2"] + config["priority_3"]
    assert len(all_fields) == len(set(all_fields))


def test_field_priority_in_mission(mission_planner, product_with_config):
    """Test that P1 fields always included, P3 dropped if over budget"""

    # Create product with full config_data
    product_with_config.config_data = {
        "tech_stack": {
            "languages": "Python, JavaScript",
            "backend": "FastAPI",
            "frontend": "Vue 3",
            "database": "PostgreSQL",
            "infrastructure": "Docker, Kubernetes",
        },
        "architecture": {
            "pattern": "Modular Monolith",
            "api_style": "REST",
            "design_patterns": "Repository, Factory",
            "notes": "Very long architecture notes" * 100,  # Force over budget
        },
        "features": {
            "core": "Multi-tenant orchestration",
        },
        "test_config": {
            "strategy": "TDD",
            "frameworks": "pytest, Playwright",
            "coverage_target": 90,
        },
    }

    mission = mission_planner._generate_agent_mission(
        agent_config=mock_agent_config,
        analysis=mock_analysis,
        product=product_with_config,
        project=mock_project,
        vision_chunks=[],
        user_id="test_user_123",
    )

    # Assert P1 fields always present
    assert "Python, JavaScript" in mission.content
    assert "FastAPI" in mission.content
    assert "Vue 3" in mission.content

    # Assert P3 fields may be missing (architecture.notes over budget)
    # This is acceptable - priority works

    # Assert token budget respected
    assert mission.token_count <= 1500


def test_custom_priority_config(mission_planner, user_with_custom_priority):
    """Test user custom priority configuration"""

    user_with_custom_priority.field_priority_config = {
        "priority_1": ["features.core", "architecture.pattern"],  # User prioritizes features
        "priority_2": ["tech_stack.languages"],
        "priority_3": ["tech_stack.backend"],
        "token_budget": 1500,
        "version": "1.0",
    }

    priority_config = mission_planner._get_field_priority_config(user_with_custom_priority.id)

    assert priority_config["priority_1"][0] == "features.core"
    assert "tech_stack.languages" in priority_config["priority_2"]
```

#### 5.2 API Tests

**File**: `tests/api/test_field_priority_endpoints.py` (new)

```python
"""Tests for field priority API endpoints"""

def test_get_default_field_priority(client, auth_headers):
    """Test getting default field priority config"""
    response = client.get("/api/v1/users/me/field-priority", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "priority_1" in data
    assert "priority_2" in data
    assert "priority_3" in data
    assert data["token_budget"] == 1500


def test_update_field_priority(client, auth_headers):
    """Test updating field priority configuration"""
    custom_config = {
        "priority_1": ["features.core", "architecture.pattern"],
        "priority_2": ["tech_stack.languages"],
        "priority_3": ["tech_stack.backend"],
        "token_budget": 1500,
        "version": "1.0",
    }

    response = client.put(
        "/api/v1/users/me/field-priority",
        json=custom_config,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["priority_1"] == ["features.core", "architecture.pattern"]


def test_update_invalid_field(client, auth_headers):
    """Test that invalid fields are rejected"""
    invalid_config = {
        "priority_1": ["invalid.field"],
        "priority_2": [],
        "priority_3": [],
        "token_budget": 1500,
        "version": "1.0",
    }

    response = client.put(
        "/api/v1/users/me/field-priority",
        json=invalid_config,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "Invalid field" in response.json()["detail"]


def test_reset_field_priority(client, auth_headers):
    """Test resetting to default priorities"""
    response = client.post(
        "/api/v1/users/me/field-priority/reset",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should match defaults
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
    assert data["priority_1"] == DEFAULT_FIELD_PRIORITY["priority_1"]
```

---

## Files to Create/Modify

### Backend
1. **`src/giljo_mcp/config/defaults.py`** (NEW) - Default priority configuration
2. **`src/giljo_mcp/models.py`** - Add `field_priority_config` to User model
3. **`src/giljo_mcp/mission_planner.py`** - Update mission generation logic
4. **`migrations/versions/XXXX_add_field_priority_config.py`** (NEW) - Database migration
5. **`api/endpoints/users.py`** - Field priority CRUD endpoints

### Frontend
6. **`frontend/src/stores/settings.js`** - Settings store extension
7. **`frontend/src/services/api.js`** - API service methods
8. **`frontend/src/views/SettingsView.vue`** - Settings UI with drag-drop
9. **`frontend/src/views/ProductsView.vue`** - Add info tooltip

### Testing
10. **`tests/unit/test_mission_planner_priority.py`** (NEW) - Mission generation tests
11. **`tests/api/test_field_priority_endpoints.py`** (NEW) - API endpoint tests

---

## Success Criteria

### Functional
- [ ] Users can view default field priority configuration
- [ ] Users can customize field priorities via drag-drop
- [ ] Users can reset to defaults
- [ ] Settings persist across sessions
- [ ] Mission prompts include ALL config_data fields (ordered by priority)
- [ ] P3 fields dropped if token budget exceeded

### Technical
- [ ] Database migration runs successfully
- [ ] User model includes `field_priority_config` JSONB field
- [ ] Mission planner respects priority order
- [ ] Token budget enforced (max 1500 tokens for config section)
- [ ] API validates field names and prevents duplicates
- [ ] Backward compatible (users without config get defaults)

### UX
- [ ] Settings → General has "Field Priority" section
- [ ] Drag-drop interface intuitive
- [ ] Token budget indicator updates in real-time
- [ ] Product form shows small info tooltip (not intrusive)
- [ ] Clear visual distinction (P1/P2/P3 with color-coded icons)
- [ ] Mobile-responsive

### Quality
- [ ] All tests pass (10+ new tests)
- [ ] No breaking changes to existing mission generation
- [ ] Performance: Priority resolution < 10ms
- [ ] Accessibility: Drag-drop keyboard-navigable

---

## Rollback Strategy

1. **Database**: Migration can be safely rolled back (no data loss)
2. **API**: New endpoints optional - old code works without them
3. **Frontend**: Settings tab additions don't affect existing views
4. **Mission Generation**: Falls back to defaults if user config missing

**Migration Rollback**:
```bash
alembic downgrade -1
```

---

## Documentation Updates

1. **User Guide**: Add "Customizing Field Priorities" section with screenshots
2. **Developer Guide**: Document priority system architecture
3. **CLAUDE.md**: Update with field priority feature
4. **API Docs**: Document new endpoints

---

## Future Enhancements (Out of Scope)

- [ ] Per-product priority overrides (not just user-wide)
- [ ] A/B testing different priority configs
- [ ] Analytics: Which fields correlate with agent success
- [ ] AI-suggested priority based on project type
- [ ] Field importance heatmap visualization

---

## References

- **Handover 0042**: Product Rich Context Fields UI (prerequisite)
- **Mission Planner**: `src/giljo_mcp/mission_planner.py`
- **Vuetify Drag & Drop**: `vuedraggable` library
- **Token Counting**: tiktoken library (already in use)

---

## Implementation Notes

**Key Insight**: Settings-based approach keeps product form clean while empowering power users. Most users never customize - smart defaults work great.

**Priority Philosophy**:
- P1 = "Agents can't work without this"
- P2 = "Significantly improves agent performance"
- P3 = "Nice to have, context-dependent"

**Token Budget Strategy**: Reserve ~60% for P1 fields, ~30% for P2, ~10% for P3. Vision chunks already handled separately.

---

**Status**: Ready for implementation
**Estimated Total Time**: 4-6 hours
**Risk Level**: Low (additive feature, backward compatible)
