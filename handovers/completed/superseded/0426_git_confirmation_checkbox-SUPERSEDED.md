# Handover 0426: Git Confirmation Checkbox

**Status**: SUPERSEDED by Handover 0427
**Superseded Date**: 2026-01-20
**Reason**: Replaced per-project checkbox with system-level integration status icons

---

> **Note**: This handover has been superseded. See [0427_integration_status_icons.md](0427_integration_status_icons.md) for the replacement design that shows GitHub and Serena icons based on user settings toggles rather than a per-project checkbox.

---

**Original Status**: Ready for Implementation
**Priority**: LOW (Quality of Life)
**Estimated Effort**: E1 (< 1 hour)
**Complexity**: Simple
**Dependencies**: Phase 0 (0424) should be completed first (security fix)

---

## Executive Summary

### What
Add a "Git is linked (developer responsibility)" checkbox to the Project UI. This is a self-managed reminder, not a blocker.

### Why
Orchestrator agents can make significant code changes. Without version control, these changes may be unrecoverable. The checkbox serves as:
1. Visual reminder for developers
2. Warning banner trigger when unchecked
3. Audit trail for 360 Memory entries

### Impact
- **Files Changed**: 3-4 files
- **Schema Changes**: 1 boolean column on `projects` table
- **Breaking Changes**: None (defaults to `false`)
- **Frontend Changes**: Checkbox + warning banner

---

## Design Decision

**Reminder (Chosen)** vs **Blocker (Rejected)**

| Approach | Pros | Cons |
|----------|------|------|
| **Reminder** ✅ | Non-intrusive, honest, simple | Relies on user discipline |
| **Blocker** ❌ | Forces awareness | Easily bypassed, annoying for docs-only projects |

The checkbox cannot *verify* git is actually linked - it only records the user's assertion. A blocker would give false security.

---

## Implementation

### 1. Database Schema

**File**: `src/giljo_mcp/models/projects.py`

Add column after `workspace_path`:

```python
class Project(Base):
    # ... existing columns ...

    # Git confirmation checkbox (Handover 0426)
    git_confirmed = Column(Boolean, default=False, nullable=False, server_default="false")
```

### 2. Migration

**File**: `migrations/versions/XXXX_add_git_confirmed_to_projects.py`

```python
"""Add git_confirmed to projects

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('projects', sa.Column('git_confirmed', sa.Boolean(),
                                         nullable=False, server_default='false'))

def downgrade():
    op.drop_column('projects', 'git_confirmed')
```

**Run**:
```bash
alembic revision --autogenerate -m "Add git_confirmed to projects"
alembic upgrade head
```

### 3. API Schema Update

**File**: `api/schemas/projects.py`

Add to `ProjectCreate`, `ProjectUpdate`, and `ProjectResponse`:

```python
class ProjectBase(BaseModel):
    # ... existing fields ...
    git_confirmed: bool = False

class ProjectResponse(ProjectBase):
    # ... existing fields ...
    git_confirmed: bool
```

### 4. Frontend - Project Settings

**File**: `frontend/src/components/projects/ProjectSettings.vue` (or equivalent)

Add checkbox in project configuration section:

```vue
<template>
  <!-- After workspace_path field -->
  <v-checkbox
    v-model="project.git_confirmed"
    label="Git is linked (developer responsibility)"
    hint="Check this when you've confirmed the project directory is under version control"
    persistent-hint
    density="compact"
    class="mt-2"
    @update:model-value="handleGitConfirmChange"
  />
</template>

<script setup>
const handleGitConfirmChange = async (value) => {
  await api.projects.update(project.value.id, { git_confirmed: value })
}
</script>
```

### 5. Frontend - Warning Banner

**File**: `frontend/src/components/projects/LaunchTab.vue` (or ProjectHeader.vue)

Add warning banner when git not confirmed:

```vue
<template>
  <!-- At top of launch section -->
  <v-alert
    v-if="!project.git_confirmed"
    type="warning"
    variant="tonal"
    density="compact"
    class="mb-4"
  >
    <v-icon start>mdi-source-branch</v-icon>
    Git not confirmed for this project. Orchestrator changes may be unrecoverable.
    <template #append>
      <v-btn
        size="small"
        variant="text"
        @click="confirmGit"
      >
        Confirm Now
      </v-btn>
    </template>
  </v-alert>
</template>
```

### 6. 360 Memory Integration (Optional)

**File**: `src/giljo_mcp/tools/write_360_memory.py`

When writing 360 memory entry, include git_confirmed status:

```python
# In write_360_memory function, after loading project
entry_data = {
    # ... existing fields ...
    "git_confirmed_at_close": project.git_confirmed,  # Track if git was confirmed
}
```

This provides audit trail: "Was git confirmed when this project closed?"

---

## Test Plan (TDD)

### Test 1: Default Value

```python
@pytest.mark.asyncio
async def test_project_git_confirmed_defaults_to_false(db_session):
    """New projects should have git_confirmed = False by default."""
    project = Project(
        tenant_key="test-tenant",
        product_id="test-product",
        name="Test Project",
        description="Test"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert project.git_confirmed is False
```

### Test 2: Can Update git_confirmed

```python
@pytest.mark.asyncio
async def test_project_git_confirmed_can_be_updated(db_session, test_project):
    """git_confirmed can be toggled."""
    test_project.git_confirmed = True
    await db_session.commit()
    await db_session.refresh(test_project)

    assert test_project.git_confirmed is True
```

### Test 3: API Returns git_confirmed

```python
@pytest.mark.asyncio
async def test_get_project_returns_git_confirmed(api_client, test_project):
    """GET /api/projects/{id} includes git_confirmed field."""
    response = await api_client.get(f"/api/projects/{test_project.id}")
    assert response.status_code == 200
    data = response.json()
    assert "git_confirmed" in data
    assert data["git_confirmed"] is False
```

### Test 4: API Can Update git_confirmed

```python
@pytest.mark.asyncio
async def test_update_project_git_confirmed(api_client, test_project):
    """PATCH /api/projects/{id} can update git_confirmed."""
    response = await api_client.patch(
        f"/api/projects/{test_project.id}",
        json={"git_confirmed": True}
    )
    assert response.status_code == 200
    assert response.json()["git_confirmed"] is True
```

---

## File Changes Summary

| File | Change |
|------|--------|
| `src/giljo_mcp/models/projects.py` | Add `git_confirmed` column |
| `migrations/versions/XXXX_...py` | New migration file |
| `api/schemas/projects.py` | Add field to schemas |
| `frontend/.../ProjectSettings.vue` | Add checkbox |
| `frontend/.../LaunchTab.vue` | Add warning banner |
| `src/giljo_mcp/tools/write_360_memory.py` | (Optional) Include in memory entry |

---

## Manual Testing Checklist

1. [ ] Create new project → verify `git_confirmed` defaults to `false`
2. [ ] Check the checkbox → verify it persists on page refresh
3. [ ] Uncheck the checkbox → verify warning banner appears
4. [ ] Click "Confirm Now" in banner → verify checkbox gets checked
5. [ ] Launch orchestrator with unchecked git → verify warning shown (not blocked)
6. [ ] Close project → verify 360 memory includes `git_confirmed_at_close`

---

## Success Criteria

- [ ] Checkbox visible in project settings
- [ ] Warning banner shows when unchecked
- [ ] Value persists in database
- [ ] API returns and accepts git_confirmed field
- [ ] Does NOT block any functionality (reminder only)
- [ ] All 4 unit tests pass

---

## Rollback Plan

```sql
-- Remove column if needed
ALTER TABLE projects DROP COLUMN git_confirmed;
```

```bash
# Or via Alembic
alembic downgrade -1
```

---

**Document Version**: 1.0
**Created**: 2026-01-19
**Author**: Claude (Opus 4.5)
**Status**: Ready for Implementation
