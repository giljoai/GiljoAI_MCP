# Handover 0075: Eight-Agent Active Limit Enforcement
<!-- Harmonized on 2025-11-04; archived spec. See docs/archive/0075_EIGHT_AGENT_LIMIT_SPEC.md -->

**Status**: Specification (ARCHIVED)
**Priority**: High
**Estimated Effort**: 8-12 hours
**Dependencies**: Handover 0041 (Agent Template Management), Handover 0069 (MCP Integration)

---

## Problem Statement

### Context Budget Constraints

Claude Code consumes context budget for each agent definition loaded at session start. With each agent template exported to `.claude/agents/`, Claude Code must parse and hold the agent definition in memory, reducing available tokens for actual project work.

**Claude Code Recommendation**: 6-8 agents maximum for optimal performance

### Current Limitations

1. **No Active Limit**: Users can activate unlimited agent templates (10, 20, 50+)
2. **Context Budget Drain**: Each active agent reduces available context for code analysis
3. **Orchestrator Uses All**: Orchestrator selects from all active templates without constraint
4. **No Export Tracking**: Users don't know when active constellation changes require re-export
5. **No Backup Protection**: Exporting overwrites `.claude/agents/` without backup safety net

### User Impact

- **Performance Degradation**: Claude Code sessions become sluggish with >8 agents
- **Token Exhaustion**: Less context available for deep code analysis
- **Confusion**: Users don't understand why Claude Code performance varies
- **Risk**: Custom agents can be overwritten without backups

---

## Solution Overview

Implement **8-agent active limit** with enforcement, user guidance, and backup protection.

### Core Features

1. **Hard 8-Agent Limit**: Max 8 templates can be active simultaneously
2. **Default 6 Active**: Seeded agents auto-enabled on first setup
3. **Orchestrator Constraint**: Only selects from 8 active template types
4. **Export Change Detection**: Track when active constellation changes
5. **User Notifications**: Toast + badge warnings to re-export (Options A + C)
6. **Auto-Backup**: Zip `.claude/agents/` before every export

---

## Requirements

### 1. Database Layer

#### AgentTemplate Model (Already Exists)
```python
class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # ← Use this field
    # ... other fields
```

**No schema changes needed** - `is_active` field already exists.

#### Validation Logic (NEW)

**Location**: `api/endpoints/templates.py`

**Function**: `validate_active_agent_limit()`
```python
async def validate_active_agent_limit(
    db: AsyncSession,
    tenant_key: str,
    template_id: str,
    new_is_active: bool
) -> tuple[bool, str]:
    """
    Validate 8-agent active limit before toggling.

    Args:
        db: Database session
        tenant_key: Tenant key for isolation
        template_id: Template being toggled
        new_is_active: Desired active state

    Returns:
        (is_valid, error_message)

    Example:
        >>> valid, msg = await validate_active_agent_limit(db, "tenant-1", "tpl-123", True)
        >>> if not valid:
        ...     raise HTTPException(400, msg)
    """
    # If deactivating, always allow
    if not new_is_active:
        return True, ""

    # Count currently active templates (excluding the one being toggled)
    stmt = select(func.count(AgentTemplate.id)).where(
        AgentTemplate.tenant_key == tenant_key,
        AgentTemplate.is_active == True,
        AgentTemplate.id != template_id
    )

    result = await db.execute(stmt)
    active_count = result.scalar_one()

    # Check limit (8 max)
    if active_count >= 8:
        return False, (
            f"Maximum 8 active agents allowed (currently {active_count} active). "
            f"Deactivate another agent before enabling this one. "
            f"Reason: Claude Code context budget limit (6-8 agents recommended)."
        )

    return True, ""
```

---

### 2. API Endpoint Changes

#### Update Template Endpoint (PATCH `/api/templates/{template_id}`)

**File**: `api/endpoints/templates.py`

**Current Behavior**: Updates template without validation

**New Behavior**: Validate 8-agent limit before allowing `is_active=True`

```python
@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    update_data: TemplateUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update agent template with 8-agent active limit validation."""

    # Fetch existing template
    template = await get_template_by_id(db, template_id, current_user.tenant_key)
    if not template:
        raise HTTPException(404, "Template not found")

    # Validate 8-agent limit if toggling active
    if update_data.is_active is not None and update_data.is_active != template.is_active:
        valid, error_msg = await validate_active_agent_limit(
            db=db,
            tenant_key=current_user.tenant_key,
            template_id=template_id,
            new_is_active=update_data.is_active
        )

        if not valid:
            raise HTTPException(400, error_msg)

    # Apply updates
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return template
```

#### Get Active Count Endpoint (NEW)

**Endpoint**: `GET /api/templates/stats/active-count`

**Purpose**: Frontend needs to display "Active: 6/8" counter

```python
@router.get("/stats/active-count", response_model=dict)
async def get_active_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get count of active templates for current tenant."""

    stmt = select(func.count(AgentTemplate.id)).where(
        AgentTemplate.tenant_key == current_user.tenant_key,
        AgentTemplate.is_active == True
    )

    result = await db.execute(stmt)
    active_count = result.scalar_one()

    return {
        "active_count": active_count,
        "max_allowed": 8,
        "remaining_slots": max(0, 8 - active_count)
    }
```

---

### 3. Frontend UI Changes

#### Template Manager Component

**File**: `frontend/src/components/TemplateManager.vue`

##### 3.1. Active Agent Counter (NEW)

**Location**: Above template list

```vue
<template>
  <!-- Active Agent Counter -->
  <v-alert
    v-if="activeCount !== null"
    :type="activeCount >= 8 ? 'warning' : 'info'"
    variant="tonal"
    density="compact"
    class="mb-4"
  >
    <div class="d-flex align-center justify-space-between">
      <div>
        <strong>Active Agents:</strong>
        <span :class="activeCount >= 8 ? 'text-warning' : ''">
          {{ activeCount }} / 8
        </span>
        <span class="text-medium-emphasis ml-2">
          ({{ 8 - activeCount }} slots remaining)
        </span>
      </div>
      <v-chip
        v-if="activeCount >= 8"
        size="small"
        color="warning"
        prepend-icon="mdi-alert"
      >
        Limit Reached
      </v-chip>
    </div>
    <div v-if="activeCount >= 8" class="text-body-2 mt-2">
      Maximum active agents reached. Deactivate an agent to enable another.
      <strong>Reason:</strong> Claude Code context budget limit.
    </div>
  </v-alert>

  <!-- Template List -->
  <v-list>
    <v-list-item v-for="template in templates" :key="template.id">
      <!-- ... existing template item content ... -->

      <!-- Active Toggle -->
      <template #append>
        <v-switch
          v-model="template.is_active"
          :disabled="!template.is_active && activeCount >= 8"
          color="primary"
          hide-details
          @update:model-value="handleToggleActive(template)"
        >
          <template #label>
            {{ template.is_active ? 'Active' : 'Inactive' }}
          </template>
        </v-switch>

        <!-- Tooltip for disabled toggle -->
        <v-tooltip
          v-if="!template.is_active && activeCount >= 8"
          location="top"
        >
          <template #activator="{ props }">
            <v-icon v-bind="props" color="warning" class="ml-2">
              mdi-information-outline
            </v-icon>
          </template>
          <span>
            Maximum 8 active agents allowed (context budget limit).
            Deactivate another agent first.
          </span>
        </v-tooltip>
      </template>
    </v-list-item>
  </v-list>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

const activeCount = ref(null)
const templates = ref([])
const toast = useToast()

async function loadActiveCount() {
  try {
    const response = await api.templates.getActiveCount()
    activeCount.value = response.data.active_count
  } catch (error) {
    console.error('[TEMPLATE MANAGER] Failed to load active count:', error)
  }
}

async function handleToggleActive(template) {
  try {
    // Attempt to update
    await api.templates.update(template.id, {
      is_active: template.is_active
    })

    // Reload active count
    await loadActiveCount()

    // Show toast notification (Option A)
    if (template.is_active) {
      toast.warning(
        'Agent Activated - Re-Export Required',
        'Export agents to Claude Code and restart sessions to apply changes.',
        { timeout: 8000 }
      )
    } else {
      toast.info(
        'Agent Deactivated',
        'Export agents to Claude Code to apply changes.',
        { timeout: 5000 }
      )
    }

    // Mark export as stale (for Option C badge)
    localStorage.setItem('agent_export_stale', 'true')

  } catch (error) {
    // Validation failed (8-agent limit)
    const errorMsg = error.response?.data?.detail || 'Failed to update agent'

    toast.error('Cannot Activate Agent', errorMsg, { timeout: 10000 })

    // Revert toggle
    template.is_active = !template.is_active

    // Reload to ensure sync
    await loadTemplates()
  }
}

onMounted(() => {
  loadTemplates()
  loadActiveCount()
})
</script>
```

##### 3.2. Export Stale Badge (NEW - Option C)

**Location**: My Settings → Integrations tab

**File**: `frontend/src/views/SettingsView.vue` or navigation component

```vue
<template>
  <v-tabs v-model="activeTab">
    <v-tab value="integrations">
      <v-badge
        v-if="exportStale"
        color="warning"
        dot
        offset-x="-10"
        offset-y="-10"
      >
        Integrations
      </v-badge>
      <span v-else>Integrations</span>
    </v-tab>
  </v-tabs>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const exportStale = ref(false)

function checkExportStale() {
  exportStale.value = localStorage.getItem('agent_export_stale') === 'true'
}

onMounted(() => {
  checkExportStale()

  // Poll for changes (in case toggled in another tab)
  setInterval(checkExportStale, 2000)
})
</script>
```

##### 3.3. Export Page Alert (Option C Enhancement)

**File**: `frontend/src/components/ClaudeCodeExport.vue`

```vue
<template>
  <!-- Export Stale Warning -->
  <v-alert
    v-if="exportStale"
    type="warning"
    variant="tonal"
    class="mb-4"
    closable
    @click:close="exportStale = false"
  >
    <div class="text-subtitle-2 mb-1">
      ⚠️ Active Agent Configuration Changed
    </div>
    <div class="text-body-2">
      You have modified which agents are active since the last export.
      Export now to update Claude Code, then restart your sessions.
    </div>
  </v-alert>

  <!-- ... existing export UI ... -->
</template>

<script setup>
import { ref, onMounted } from 'vue'

const exportStale = ref(false)

onMounted(() => {
  exportStale.value = localStorage.getItem('agent_export_stale') === 'true'
})

async function handleExport() {
  // ... existing export logic ...

  // Clear stale flag after successful export
  if (exportResult.value?.success) {
    localStorage.removeItem('agent_export_stale')
    exportStale.value = false
  }
}
</script>
```

---

### 4. Orchestrator Changes

#### Agent Selection Logic

**File**: `src/giljo_mcp/orchestrator.py`

**Current Behavior**: Uses all templates where `is_active=True` (no limit awareness)

**New Behavior**: Filter by `is_active=True` (already correct, just document constraint)

**Method**: `_get_agent_template()`

```python
async def _get_agent_template(
    self,
    role: AgentRole,
    tenant_key: str,
    product_id: Optional[str] = None,
) -> Optional[AgentTemplate]:
    """
    Get agent template with cascade resolution.

    Cascade Priority:
    1. Product-specific template (if product_id provided)
    2. Tenant-specific template
    3. System default template

    IMPORTANT: Only considers templates where is_active=True.
    Maximum 8 agent types can be active per tenant (enforced at API layer).

    Args:
        role: Agent role enum
        tenant_key: Tenant key for isolation
        product_id: Optional product ID for product-specific templates

    Returns:
        AgentTemplate or None if not found
    """
    # ... existing implementation already filters by is_active=True ...

    # Query with is_active filter
    stmt = select(AgentTemplate).where(
        AgentTemplate.tenant_key == tenant_key,
        AgentTemplate.role == role.value,
        AgentTemplate.is_active == True,  # ← Already enforces 8-agent limit
    )

    # ... rest of cascade logic ...
```

**Documentation Update**: Add docstring note about 8-agent constraint

**Agent Spawning**: Can spawn **multiple instances** of same template type
```python
# Example: Spawn 3 implementers from same template (different missions)
implementer_template = await self._get_agent_template(
    role=AgentRole.IMPLEMENTER,
    tenant_key=project.tenant_key
)

# Spawn instance 1
agent1 = await self._spawn_claude_code_agent(
    project=project,
    role=AgentRole.IMPLEMENTER,
    template=implementer_template,
    custom_mission="Implement authentication module"
)

# Spawn instance 2 (same template, different mission)
agent2 = await self._spawn_claude_code_agent(
    project=project,
    role=AgentRole.IMPLEMENTER,
    template=implementer_template,
    custom_mission="Implement payment integration"
)

# ✅ Valid: 8 TYPES limit, not 8 INSTANCES limit
```

---

### 5. Template Seeding Changes

#### Auto-Enable 6 Default Agents

**File**: `src/giljo_mcp/template_seeder.py`

**Current Behavior**: Seeds 6 templates with `is_active=True` (already correct!)

**Validation**: Ensure seeding logic sets `is_active=True` for defaults

```python
async def seed_default_templates(db: AsyncSession, tenant_key: str):
    """
    Seed 6 default agent templates for new tenant.

    Default agents (auto-enabled):
    1. orchestrator (is_active=True)
    2. analyzer (is_active=True)
    3. implementor (is_active=True)
    4. tester (is_active=True)
    5. documenter (is_active=True)
    6. reviewer (is_active=True)

    This leaves 2 slots for custom agents (8-agent limit).
    """

    default_templates = [
        {
            "name": "orchestrator",
            "role": "orchestrator",
            "is_active": True,  # ← Auto-enabled
            # ... other fields ...
        },
        {
            "name": "analyzer",
            "role": "analyzer",
            "is_active": True,  # ← Auto-enabled
            # ... other fields ...
        },
        # ... 4 more defaults ...
    ]

    for template_data in default_templates:
        # Check if exists
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.name == template_data["name"]
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            # Create with is_active=True
            template = AgentTemplate(
                id=f"tpl-{uuid4().hex[:12]}",
                tenant_key=tenant_key,
                **template_data
            )
            db.add(template)

    await db.commit()
```

**Verification**: Check `is_active` field in seeded data (should already be `True`)

---

### 6. Export Enhancement - Auto-Backup

#### Backup Before Export

**File**: `api/endpoints/claude_export.py`

**Function**: `create_zip_backup()` (NEW)

```python
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

def create_zip_backup(agents_dir: Path) -> Optional[Path]:
    """
    Create timestamped zip backup of .claude/agents/ directory.

    Process:
    1. Check if agents_dir exists and has .md files
    2. Create .claude/backups/ directory if needed
    3. Generate backup: agents_backup_YYYYMMDD_HHMMSS.zip
    4. Zip all .md files from agents_dir
    5. Return backup path

    Args:
        agents_dir: Path to .claude/agents/ directory

    Returns:
        Path to created zip file, or None if nothing to backup

    Example:
        >>> backup = create_zip_backup(Path.cwd() / ".claude" / "agents")
        >>> print(backup)
        F:/project/.claude/backups/agents_backup_20251030_153045.zip
    """
    # Check if directory exists
    if not agents_dir.exists() or not agents_dir.is_dir():
        logger.info(f"[create_zip_backup] No agents directory to backup: {agents_dir}")
        return None

    # Find .md files to backup
    md_files = list(agents_dir.glob("*.md"))
    if not md_files:
        logger.info(f"[create_zip_backup] No .md files to backup in {agents_dir}")
        return None

    # Create backups directory
    backups_dir = agents_dir.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"agents_backup_{timestamp}.zip"
    backup_path = backups_dir / backup_filename

    # Create zip archive
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for md_file in md_files:
                # Add file to zip (arcname = relative path in zip)
                zipf.write(md_file, arcname=md_file.name)
                logger.debug(f"[create_zip_backup] Added to zip: {md_file.name}")

        logger.info(
            f"[create_zip_backup] Created backup: {backup_path} "
            f"({len(md_files)} files, {backup_path.stat().st_size} bytes)"
        )

        return backup_path

    except Exception as e:
        logger.exception(f"[create_zip_backup] Failed to create backup: {e}")
        return None
```

**Integration**: Call before export

```python
async def export_templates_to_claude_code(
    db: AsyncSession,
    current_user: User,
    export_path: str,
) -> dict[str, Any]:
    """Export agent templates to Claude Code format with auto-backup."""

    # Validate export path
    normalized_path = export_path.replace("\\", "/")
    if not normalized_path.endswith(".claude/agents"):
        raise ValueError("Export path must end with '.claude/agents'")

    # Expand home directory
    export_dir = Path(export_path).expanduser()

    # Verify directory exists
    if not export_dir.exists():
        raise ValueError(f"Export directory does not exist: {export_dir}")

    # ✅ NEW: Create backup before export
    backup_path = create_zip_backup(export_dir)
    backup_info = None
    if backup_path:
        backup_info = {
            "backup_created": True,
            "backup_path": str(backup_path),
            "backup_size_bytes": backup_path.stat().st_size
        }
        logger.info(f"[export_templates] Created pre-export backup: {backup_path}")
    else:
        backup_info = {"backup_created": False, "reason": "No existing files to backup"}

    # Query active templates (already limited to 8 by validation)
    stmt = (
        select(AgentTemplate)
        .where(
            AgentTemplate.tenant_key == current_user.tenant_key,
            AgentTemplate.is_active == True,  # ← Max 8 enforced
        )
        .order_by(AgentTemplate.name)
    )

    result = await db.execute(stmt)
    templates = result.scalars().all()

    # Validate agent count (should never exceed 8 due to API validation)
    active_count = len(templates)
    if active_count > 8:
        logger.warning(
            f"[export_templates] UNEXPECTED: {active_count} active agents found "
            f"(exceeds 8-agent limit). tenant={current_user.tenant_key}"
        )

    # Export each template (existing logic)
    exported_files = []
    for template in templates:
        # ... existing export logic ...
        pass

    # Return results with backup info
    return {
        "success": True,
        "exported_count": len(exported_files),
        "files": exported_files,
        "backup": backup_info,  # ← NEW: Include backup details
        "message": f"Successfully exported {len(exported_files)} template(s) to {export_dir}",
    }
```

**Response Model Update**: Add backup info to `ClaudeExportResult`

```python
class ClaudeExportResult(BaseModel):
    """Result model for Claude Code template export"""

    success: bool
    exported_count: int
    files: list[dict[str, str]]
    backup: Optional[dict[str, Any]] = None  # ← NEW
    message: str
```

**UI Display**: Show backup confirmation in export result

```vue
<!-- Export Result -->
<v-alert type="success" v-if="exportResult.success">
  <div class="text-subtitle-2 mb-2">{{ exportResult.message }}</div>

  <!-- Backup Info -->
  <div v-if="exportResult.backup?.backup_created" class="mt-2">
    <v-chip size="small" color="success" prepend-icon="mdi-backup-restore">
      Backup Created
    </v-chip>
    <div class="text-body-2 text-medium-emphasis mt-1">
      Previous agents backed up to:
      <code>{{ formatBackupPath(exportResult.backup.backup_path) }}</code>
    </div>
  </div>

  <!-- Files Exported -->
  <div class="mt-2">
    <div class="text-body-2 font-weight-medium">Exported {{ exportResult.exported_count }} agents:</div>
    <ul class="text-body-2">
      <li v-for="file in exportResult.files" :key="file.path">
        <code>{{ file.name }}.md</code>
      </li>
    </ul>
  </div>
</v-alert>
```

---

## Testing Checklist

### Database Layer
- [ ] Validate 8-agent limit enforced in API
- [ ] Attempt to activate 9th agent → returns 400 error
- [ ] Deactivate agent → always succeeds
- [ ] Count active agents correctly per tenant (multi-tenant isolation)

### API Endpoints
- [ ] `PATCH /api/templates/{id}` blocks 9th activation
- [ ] `GET /api/templates/stats/active-count` returns correct count
- [ ] Export with <8 agents → backup created
- [ ] Export with 0 agents → no backup created

### Frontend UI
- [ ] Active counter displays "6/8" correctly
- [ ] Toggle disabled when limit reached
- [ ] Tooltip shows on disabled toggle
- [ ] Toast notification shown on toggle (Option A)
- [ ] Badge appears on Integrations tab when stale (Option C)
- [ ] Export page shows warning when stale (Option C)
- [ ] Export result displays backup confirmation

### Orchestrator
- [ ] Only selects from active templates (is_active=True)
- [ ] Can spawn multiple instances of same template type
- [ ] Respects 8-type limit even with multiple instances

### Template Seeding
- [ ] 6 default agents seeded with is_active=True
- [ ] Fresh tenant has 6 active agents (2 slots remaining)

### Export & Backup
- [ ] Backup zip created before export
- [ ] Backup stored in `.claude/backups/`
- [ ] Backup filename format: `agents_backup_YYYYMMDD_HHMMSS.zip`
- [ ] Backup contains all .md files from agents directory
- [ ] Export succeeds even if backup fails (non-blocking)

### Edge Cases
- [ ] Activate 8th agent → succeeds
- [ ] Activate 9th agent → blocked with clear error
- [ ] Deactivate agent → re-enables toggle for others
- [ ] Multiple users (same tenant) toggling concurrently → no race conditions
- [ ] Export with 8 active agents → all 8 exported
- [ ] Export after deactivating 3 agents → only 5 exported

---

## User Documentation

### User Guide Updates

**Location**: `docs/USER_GUIDE.md` or in-app help

#### Managing Active Agents

**8-Agent Limit**: Only 8 agent templates can be active at once due to Claude Code's context budget constraints. This ensures optimal performance and sufficient tokens for deep code analysis.

**Default Configuration**: GiljoAI seeds 6 default agents (orchestrator, analyzer, implementor, tester, documenter, reviewer), leaving 2 slots for custom agents.

**How to Activate/Deactivate Agents**:

1. Navigate to **Dashboard → Templates** tab
2. View active count: **"Active Agents: 6/8"**
3. Toggle agent active/inactive using the switch
4. If limit reached, deactivate another agent first
5. After toggling, **re-export agents** to Claude Code:
   - Go to **My Settings → Integrations**
   - Click **"Export Agents to Claude Code"**
   - **Restart Claude Code sessions** for changes to apply

**Why 8 Agents?**:
- Each agent definition consumes context budget
- Claude Code recommends 6-8 agents for optimal performance
- More agents = less context for actual code analysis
- 8-type limit allows multiple instances of same agent type

**Backup Protection**:
- Every export automatically creates a timestamped backup
- Backups stored in `.claude/backups/` as zip files
- Restore from backup if needed: unzip to `.claude/agents/`

---

## Implementation Plan

### Phase 1: Backend Validation (2-3 hours)
1. Add `validate_active_agent_limit()` function
2. Update `PATCH /api/templates/{id}` endpoint
3. Add `GET /api/templates/stats/active-count` endpoint
4. Write unit tests for validation logic

### Phase 2: Export Backup (2-3 hours)
1. Implement `create_zip_backup()` function
2. Integrate backup into `export_templates_to_claude_code()`
3. Update `ClaudeExportResult` model
4. Test backup creation and zip contents

### Phase 3: Frontend UI (3-4 hours)
1. Add active counter component to TemplateManager
2. Disable toggle when limit reached
3. Add tooltip for disabled toggle
4. Implement toast notifications (Option A)
5. Add badge to Integrations tab (Option C)
6. Add export stale warning to export page
7. Display backup info in export results

### Phase 4: Orchestrator Documentation (1 hour)
1. Update `_get_agent_template()` docstring
2. Add comments about 8-type vs instances distinction
3. Verify existing logic already filters by `is_active=True`

### Phase 5: Testing & Documentation (2-3 hours)
1. Run full test suite
2. Manual UI testing (toggle, export, backup)
3. Multi-tenant isolation testing
4. Update user documentation
5. Update CLAUDE.md with 8-agent guidance

---

## Rollout Strategy

### Database Migration
**None required** - `is_active` field already exists

### Deployment Steps
1. Deploy backend changes (API validation)
2. Deploy frontend changes (UI components)
3. Clear localStorage for all users (`agent_export_stale` flag)
4. Announce feature in release notes

### User Communication

**Release Notes**: Version 3.1 - Active Agent Management

**New Features**:
- ✅ 8-agent active limit enforcement (Claude Code context budget optimization)
- ✅ Active agent counter in Templates tab
- ✅ Automatic backup before every export (`.claude/backups/`)
- ✅ Export change detection with warnings

**Breaking Changes**: None (existing configurations preserved)

**User Action Required**:
1. Review active agents (Dashboard → Templates)
2. Deactivate agents if >8 active (system will prompt)
3. Re-export agents if configuration changed

---

## Success Metrics

### Performance
- [ ] Claude Code sessions remain responsive with 6-8 agents
- [ ] Export creates backup in <1 second
- [ ] Active count API responds in <100ms

### User Experience
- [ ] 95%+ users stay within 8-agent limit
- [ ] Zero data loss incidents (backup protection)
- [ ] Clear error messages when limit reached

### System Health
- [ ] No database constraint violations
- [ ] Multi-tenant isolation maintained
- [ ] Backup storage remains manageable (<100MB per tenant)

---

## Related Handovers

- **0041**: Agent Template Management (base template system)
- **0069**: MCP Integration (Claude Code, Codex, Gemini support)
- **0074**: Agent Export Auto-Spawn Removal (manual export workflow)

---

## Future Enhancements (Out of Scope)

- **Override Option**: Allow power users to exceed 8-agent limit (with performance warning)
- **Backup Management UI**: View/restore/delete backups from dashboard
- **Agent Presets**: "Development Team" (6 agents), "Full Stack" (8 agents), "Security Focused" (4 agents)
- **Context Budget Meter**: Real-time estimation of Claude Code context usage
- **Auto-Export**: Trigger export automatically when toggling (with confirmation)

---

**END OF HANDOVER 0075**
