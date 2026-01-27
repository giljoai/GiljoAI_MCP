# Handover 0427: Integration Status Icons

**Status**: Ready for Implementation
**Priority**: MEDIUM (UX Enhancement)
**Estimated Effort**: E2 (2-4 hours)
**Complexity**: Medium
**Dependencies**: None
**Supersedes**: Handover 0426 (Git Confirmation Checkbox - now removed)

---

## Executive Summary

### What
Replace the per-project `git_confirmed` checkbox with system-level integration status icons next to the Stage Project button. Icons for GitHub and Serena MCP indicate whether each integration is enabled in user settings.

### Why
1. **Clarity**: Current `git_confirmed` checkbox conflates two concerns (user assertion vs system feature)
2. **Discoverability**: Icons make integration status immediately visible
3. **Consistency**: Same UX pattern for all integrations
4. **Actionable**: Faded icons with tooltips guide users to enable features

### Impact
- **Files Changed**: 5-6 files
- **Schema Changes**: REMOVE `git_confirmed` column from `projects` table
- **Breaking Changes**: Yes - removes `git_confirmed` field (acceptable, feature was not released)
- **Frontend Changes**: Add integration icons, remove warning banner

---

## Design Decisions

### Icons Visibility Logic

| Integration State | Icon Appearance | Tooltip |
|-------------------|-----------------|---------|
| **ON** | Full color | "GitHub integration enabled. Commit history included in project summaries. See Settings > Integrations" |
| **OFF** | Greyed/faded (opacity: 0.3) | "GitHub integration disabled. Enable in Settings > Integrations" |

Same pattern applies to Serena MCP.

### Context Priority Independence

GitHub icon shows based on **integration toggle only**, not context priority settings:
- Integration ON + Context Priority OFF = Icon shows (full color)
- Integration OFF = Icon shows faded

Rationale: Icon indicates the integration is *available*, not whether it's actively fetched. Context priority is a separate granular control.

### Removal of git_confirmed

The per-project `git_confirmed` checkbox is removed because:
1. It cannot verify git is actually linked (user assertion only)
2. System-level integration toggle is more meaningful
3. Warning banner created noise without actionable value

---

## Implementation

### Phase 1: Remove git_confirmed (Database Cleanup)

#### 1.1 Migration to Remove Column

**File**: `migrations/versions/XXXX_remove_git_confirmed_from_projects.py`

```python
"""Remove git_confirmed from projects (superseded by integration icons)

Revision ID: xxxx
Revises: 317d63e2e8cd
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.drop_column('projects', 'git_confirmed')

def downgrade():
    op.add_column('projects', sa.Column('git_confirmed', sa.Boolean(),
                                         nullable=False, server_default='false'))
```

#### 1.2 Remove from Model

**File**: `src/giljo_mcp/models/projects.py`

```python
# REMOVE this line:
# git_confirmed = Column(Boolean, default=False, nullable=False, server_default="false")
```

#### 1.3 Remove from API Schema

**File**: `api/endpoints/projects/models.py`

```python
# REMOVE git_confirmed from ProjectCreate, ProjectUpdate, ProjectResponse
```

#### 1.4 Remove from Service

**File**: `src/giljo_mcp/services/project_service.py`

```python
# REMOVE any git_confirmed handling
```

#### 1.5 Delete Tests

**File**: `tests/api/test_project_git_confirmed.py` - DELETE entire file

---

### Phase 2: Add Integration Status Icons

#### 2.1 Update LaunchTab.vue

**File**: `frontend/src/components/projects/LaunchTab.vue`

**Remove**: Git warning banner (lines 27-48)

**Add**: Integration icons section near Stage button

```vue
<template>
  <!-- Integration Status Icons (Handover 0427) -->
  <div class="integration-icons" data-testid="integration-status-icons">
    <!-- GitHub Integration -->
    <v-tooltip location="bottom" max-width="300">
      <template #activator="{ props }">
        <v-icon
          v-bind="props"
          :class="{ 'icon-disabled': !gitEnabled }"
          size="20"
          data-testid="github-status-icon"
        >
          mdi-github
        </v-icon>
      </template>
      <span v-if="gitEnabled">
        GitHub integration enabled. Commit history will be included in project summaries.
        <a href="#" @click.prevent="goToIntegrations">Settings &rarr; Integrations</a>
      </span>
      <span v-else>
        GitHub integration disabled.
        <a href="#" @click.prevent="goToIntegrations">Enable in Settings &rarr; Integrations</a>
      </span>
    </v-tooltip>

    <!-- Serena MCP Integration -->
    <v-tooltip location="bottom" max-width="300">
      <template #activator="{ props }">
        <v-img
          v-bind="props"
          src="/Serena.png"
          width="20"
          height="20"
          :class="{ 'icon-disabled': !serenaEnabled }"
          data-testid="serena-status-icon"
        />
      </template>
      <span v-if="serenaEnabled">
        Serena MCP enabled. Agents will use semantic code navigation.
        <a href="#" @click.prevent="goToIntegrations">Settings &rarr; Integrations</a>
      </span>
      <span v-else>
        Serena MCP disabled.
        <a href="#" @click.prevent="goToIntegrations">Enable in Settings &rarr; Integrations</a>
      </span>
    </v-tooltip>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  project: { type: Object, required: true },
  gitEnabled: { type: Boolean, default: false },
  serenaEnabled: { type: Boolean, default: false },
})

const router = useRouter()

function goToIntegrations() {
  router.push({ path: '/settings', query: { tab: 'integrations' } })
}
</script>

<style scoped>
.integration-icons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.icon-disabled {
  opacity: 0.3;
  filter: grayscale(100%);
}
</style>
```

#### 2.2 Pass Integration State to LaunchTab

**File**: `frontend/src/views/ProjectDetailView.vue` (or parent component)

LaunchTab needs `gitEnabled` and `serenaEnabled` props. These should be fetched from user settings or provided via a composable/store.

```vue
<LaunchTab
  :project="project"
  :git-enabled="gitEnabled"
  :serena-enabled="serenaEnabled"
/>
```

#### 2.3 Create Composable for Integration Status (Optional)

**File**: `frontend/src/composables/useIntegrationStatus.js`

```javascript
import { ref, onMounted } from 'vue'
import { setupService } from '@/services/setupService'

export function useIntegrationStatus() {
  const gitEnabled = ref(false)
  const serenaEnabled = ref(false)
  const loading = ref(true)

  async function loadStatus() {
    loading.value = true
    try {
      const [gitSettings, serenaStatus] = await Promise.all([
        setupService.getGitSettings(),
        setupService.getSerenaStatus(),
      ])
      gitEnabled.value = gitSettings.enabled || false
      serenaEnabled.value = serenaStatus.enabled || false
    } catch (error) {
      console.error('[useIntegrationStatus] Failed to load:', error)
    } finally {
      loading.value = false
    }
  }

  onMounted(loadStatus)

  return { gitEnabled, serenaEnabled, loading, refresh: loadStatus }
}
```

---

### Phase 3: Update 360 Memory Text

#### 3.1 Update GitIntegrationCard

**File**: `frontend/src/components/settings/integrations/GitIntegrationCard.vue`

Update the description text:

```vue
<p class="text-body-2 text-medium-emphasis mb-3">
  Enable to automatically include git commit history in project summaries.
  Commits are stored in product memory for future orchestrator reference.
  <strong>Git configuration is your responsibility on your local system.</strong>
</p>
```

---

## File Changes Summary

| File | Change |
|------|--------|
| `migrations/versions/XXXX_remove_git_confirmed.py` | NEW - Remove column |
| `src/giljo_mcp/models/projects.py` | Remove `git_confirmed` column |
| `api/endpoints/projects/models.py` | Remove field from schemas |
| `api/endpoints/projects/crud.py` | Remove any git_confirmed handling |
| `src/giljo_mcp/services/project_service.py` | Remove git_confirmed handling |
| `tests/api/test_project_git_confirmed.py` | DELETE file |
| `frontend/src/components/projects/LaunchTab.vue` | Remove banner, add icons |
| `frontend/src/composables/useIntegrationStatus.js` | NEW - Integration status composable |
| `frontend/src/components/settings/integrations/GitIntegrationCard.vue` | Update description text |
| `handovers/0426_git_confirmation_checkbox.md` | Mark as SUPERSEDED |

---

## Test Plan

### Unit Tests

```python
# test_project_no_git_confirmed.py
@pytest.mark.asyncio
async def test_project_model_has_no_git_confirmed(db_session):
    """Verify git_confirmed column was removed."""
    project = Project(
        tenant_key="test",
        product_id="test-product",
        name="Test",
        description="Test"
    )
    assert not hasattr(project, 'git_confirmed')
```

### Frontend Tests

```javascript
// LaunchTab.spec.js
describe('Integration Status Icons', () => {
  it('shows GitHub icon at full opacity when enabled', async () => {
    const wrapper = mount(LaunchTab, {
      props: { project: mockProject, gitEnabled: true, serenaEnabled: false }
    })
    const icon = wrapper.find('[data-testid="github-status-icon"]')
    expect(icon.classes()).not.toContain('icon-disabled')
  })

  it('shows GitHub icon faded when disabled', async () => {
    const wrapper = mount(LaunchTab, {
      props: { project: mockProject, gitEnabled: false, serenaEnabled: false }
    })
    const icon = wrapper.find('[data-testid="github-status-icon"]')
    expect(icon.classes()).toContain('icon-disabled')
  })

  it('shows Serena icon at full opacity when enabled', async () => {
    const wrapper = mount(LaunchTab, {
      props: { project: mockProject, gitEnabled: false, serenaEnabled: true }
    })
    const icon = wrapper.find('[data-testid="serena-status-icon"]')
    expect(icon.classes()).not.toContain('icon-disabled')
  })

  it('navigates to integrations settings on tooltip link click', async () => {
    // Test router navigation
  })
})
```

---

## Manual Testing Checklist

1. [ ] Create new project - verify no `git_confirmed` field in API response
2. [ ] LaunchTab shows GitHub icon (faded if OFF, solid if ON)
3. [ ] LaunchTab shows Serena icon (faded if OFF, solid if ON)
4. [ ] Tooltip shows correct text for ON state
5. [ ] Tooltip shows correct text for OFF state
6. [ ] Clicking tooltip link navigates to Settings > Integrations
7. [ ] Toggling integration in settings updates icon state (may need refresh)
8. [ ] GitIntegrationCard shows updated description text
9. [ ] Old warning banner is removed

---

## Success Criteria

- [ ] `git_confirmed` column removed from database
- [ ] No `git_confirmed` in API schemas
- [ ] Integration icons visible next to Stage button
- [ ] Icons reflect actual integration state (ON = solid, OFF = faded)
- [ ] Tooltips provide context and link to settings
- [ ] 360 Memory description clarifies user responsibility
- [ ] All tests pass

---

## Rollback Plan

If issues arise, the migration can be reverted:

```bash
alembic downgrade -1
```

And the frontend changes can be reverted via git.

---

**Document Version**: 1.0
**Created**: 2026-01-20
**Author**: Claude (Opus 4.5)
**Status**: Ready for Implementation
**Supersedes**: Handover 0426 (Git Confirmation Checkbox)
