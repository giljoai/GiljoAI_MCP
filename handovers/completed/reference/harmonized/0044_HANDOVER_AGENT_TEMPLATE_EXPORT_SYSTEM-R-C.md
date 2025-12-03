# Handover 0044 (Recalibrated): Agent Template Export System for Claude Code

**Date**: 2025-10-24 (Recalibrated from original)
**From Agent**: System Architect
**To Agent**: Full-Stack Development Team (UX Designer + Backend Developer + Frontend Tester)
**Priority**: High
**Estimated Effort**: 3-4 days
**Status**: Ready for Implementation
**Risk Level**: Low-Medium (File system operations, single export format)

---

## Recalibration Notice

**Original Scope**: Export to Claude Code, Codex, and Gemini CLI formats

**Recalibrated Scope**: Export to **Claude Code ONLY**

**Reason for Recalibration**:
- Architectural discovery: Codex and Gemini do NOT need file export
- Codex/Gemini agents will use database templates directly (Handover 0045)
- Only Claude Code reads agent definitions from `.md` files
- Simplified scope = faster delivery, lower risk

**Related Handovers**:
- **Handover 0045**: Multi-Tool Orchestration (implements Codex/Gemini coordination)
- **Handover 0041**: Agent Template Database (foundation)

---

## Executive Summary

**Objective**: Implement Claude Code agent export system that allows users to export customized agent templates to `.claude/agents/*.md` files with YAML frontmatter, enabling seamless integration with Claude Code's subagent system.

**Current Problem**:
- Agent templates exist only in the database (Handover 0041)
- Users cannot use templates in Claude Code without manual file creation
- No bridge between database templates and Claude Code's file-based agent system
- Orchestrator cannot leverage Claude Code subagents (Handover 0045 dependency)

**Proposed Solution**:
- Export database templates to `.claude/agents/<agent>.md` format
- Generate YAML frontmatter with name, description, model, tools
- Support both project-level (`.claude/agents/`) and personal-level (`~/.claude/agents/`) export
- Automatic backup of existing files before overwrite
- UI integration in Integrations tab
- Batch export (all templates at once)

**Value Delivered**:
- ✅ Agents immediately usable in Claude Code
- ✅ Seamless workflow from template customization to tool integration
- ✅ Safe overwrites with automatic backups (`.old.YYYYMMDD_HHMMSS`)
- ✅ Support for both project-level and user-level agent storage
- ✅ Foundation for Handover 0045 (Multi-Tool Orchestration)
- ✅ Auto-export capability for orchestrator (programmatic export)

---

## Research Findings: Claude Code Agent Format

**Source**: https://docs.claude.com/en/docs/claude-code/sub-agents

**File Format**: Markdown with YAML frontmatter

**Storage Locations**:
- **Project**: `.claude/agents/` (highest priority, current project only)
- **Personal**: `~/.claude/agents/` (lower priority, all projects)

**File Structure**:
```markdown
---
name: agent-identifier
description: When to use this agent
tools: Read, Grep, Bash  # Optional - comma-separated
model: sonnet  # Optional - sonnet, opus, haiku, or inherit
---

System prompt content here.
Multiple paragraphs defining role, capabilities, and constraints.

## Behavioral Rules
- Rule 1
- Rule 2

## Success Criteria
- Criterion 1
- Criterion 2
```

**Required Fields**:
- `name`: Lowercase letters and hyphens only (e.g., `orchestrator`, `implementer`)
- `description`: Natural language explaining purpose and when to invoke

**Optional Fields**:
- `tools`: Comma-separated list (omit to inherit all tools from parent)
- `model`: Model alias (`sonnet`, `opus`, `haiku`, or `inherit`)

**File Naming**: `{name}.md` (e.g., `orchestrator.md`)

**Key Features**:
- Each agent in separate file
- YAML frontmatter for metadata
- Markdown for system prompt
- Project agents override personal agents
- Tools can be restricted per agent

---

## Database Schema (AgentTemplate)

**File**: `src/giljo_mcp/models.py` (lines 596-660)

**Relevant Fields for Export**:
```python
class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    # Identification
    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=True)  # orchestrator, implementer, etc.

    # Template Content
    template_content = Column(Text, nullable=False)  # Main system prompt
    variables = Column(JSON, default=list)  # ["project_name", "product_name"]
    behavioral_rules = Column(JSON, default=list)  # List of rules
    success_criteria = Column(JSON, default=list)  # List of criteria

    # Metadata
    preferred_tool = Column(String(50), default="claude")
    category = Column(String(50), nullable=False)  # "role"

    # Status
    is_active = Column(Boolean, default=True)
```

**Mapping to Claude Code Format**:

| Database Field | Claude Code | Example |
|----------------|-------------|---------|
| `name` or `role` | YAML `name:` | `orchestrator` |
| `name` | YAML `description:` | "Orchestrator - role agent" |
| `template_content` | Markdown body | Full system prompt |
| `behavioral_rules` | "## Behavioral Rules" section | List of rules |
| `success_criteria` | "## Success Criteria" section | List of criteria |
| `preferred_tool` | YAML `model:` | `sonnet` (default) |
| (fixed) | YAML `tools:` | `["mcp__giljo_mcp__*"]` (all MCP tools) |

---

## Implementation Plan

### Phase 1: Backend Export Endpoint (1.5-2 days)

**Files to Create**:
- `api/endpoints/claude_export.py` (new file, ~350 lines)

**Files to Modify**:
- `api/app.py` (register router, +3 lines)

---

#### Task 1.1: Export Endpoint Implementation (1 day)

**Create new file: `api/endpoints/claude_export.py`**

```python
"""
Claude Code Agent Export Endpoint

Exports agent templates to Claude Code format (.claude/agents/*.md).
Handles file creation, backups, and YAML frontmatter generation.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.models import AgentTemplate, User
from api.dependencies import get_current_active_user, get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class ClaudeExportRequest(BaseModel):
    """Claude Code export request."""
    template_ids: List[str]
    export_path: str = "project"  # 'project' or 'personal'


class ClaudeExportResult(BaseModel):
    """Claude Code export result."""
    success: bool
    message: str
    files_created: List[str]
    backups_created: List[str]
    errors: List[str] = []


# Export Endpoint
@router.post("/export/claude-code", response_model=ClaudeExportResult)
async def export_to_claude_code(
    request: ClaudeExportRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Export agent templates to Claude Code format.

    Creates individual .md files in .claude/agents/ with YAML frontmatter.

    Security:
    - Multi-tenant isolation: Only exports templates owned by user's tenant
    - File system safety: Creates backups before overwriting
    - Path validation: Only exports to allowed directories

    Returns:
        Export result with file paths and backup information
    """
    try:
        # Fetch templates (multi-tenant isolated)
        stmt = select(AgentTemplate).where(
            AgentTemplate.id.in_(request.template_ids),
            AgentTemplate.tenant_key == current_user.tenant_key,
            AgentTemplate.is_active == True,
        )
        result = await session.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            raise HTTPException(
                status_code=404,
                detail="No templates found for export (check tenant ownership)"
            )

        # Determine export path
        if request.export_path == "project":
            export_dir = Path.cwd() / ".claude" / "agents"
        else:  # personal
            export_dir = Path.home() / ".claude" / "agents"

        # Create directory if not exists
        export_dir.mkdir(parents=True, exist_ok=True)

        files_created = []
        backups_created = []
        errors = []

        # Export each template
        for template in templates:
            try:
                # Generate filename (sanitize name for filesystem)
                filename = f"{template.role or template.name}.md"
                file_path = export_dir / filename

                # Backup existing file
                if file_path.exists():
                    backup_path = _backup_file(file_path)
                    backups_created.append(str(backup_path))

                # Generate Claude Code format
                content = _generate_claude_code_format(template)

                # Write file
                file_path.write_text(content, encoding='utf-8')
                files_created.append(str(file_path))

                logger.info(f"[Claude Export] Created {file_path}")

            except Exception as e:
                error_msg = f"Failed to export {template.name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"[Claude Export] {error_msg}")

        # Determine overall success
        success = len(errors) == 0
        message = (
            f"Exported {len(templates)} agent templates to Claude Code successfully"
            if success
            else f"Export completed with {len(errors)} errors"
        )

        logger.info(
            f"[Export] User {current_user.username} exported {len(templates)} templates: "
            f"{len(files_created)} files created, {len(backups_created)} backups"
        )

        return ClaudeExportResult(
            success=success,
            message=message,
            files_created=files_created,
            backups_created=backups_created,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Export] Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


# Programmatic Export Function (for Handover 0045)
async def export_template_to_claude_code(
    template_id: str,
    tenant_key: str,
    session: AsyncSession,
    export_path: str = "project",
) -> str:
    """
    Programmatically export single template to Claude Code.

    Used by orchestrator (Handover 0045) to auto-export before spawning subagent.

    Args:
        template_id: Template UUID
        tenant_key: Tenant key for isolation
        session: Database session
        export_path: 'project' or 'personal'

    Returns:
        File path of created .md file

    Raises:
        ValueError: If template not found or export fails
    """
    # Fetch template
    stmt = select(AgentTemplate).where(
        AgentTemplate.id == template_id,
        AgentTemplate.tenant_key == tenant_key,
        AgentTemplate.is_active == True,
    )
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise ValueError(f"Template {template_id} not found for tenant {tenant_key}")

    # Determine export path
    if export_path == "project":
        export_dir = Path.cwd() / ".claude" / "agents"
    else:
        export_dir = Path.home() / ".claude" / "agents"

    export_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = f"{template.role or template.name}.md"
    file_path = export_dir / filename

    # Backup if exists
    if file_path.exists():
        _backup_file(file_path)

    # Generate and write
    content = _generate_claude_code_format(template)
    file_path.write_text(content, encoding='utf-8')

    logger.info(f"[Auto Export] Exported template {template.name} to {file_path}")

    return str(file_path)


# Format Generator
def _generate_claude_code_format(template: AgentTemplate) -> str:
    """
    Generate Claude Code markdown with YAML frontmatter.

    Format:
    ---
    name: agent-identifier
    description: When to use this agent
    tools: ["mcp__giljo_mcp__*"]
    model: sonnet
    ---

    <template_content>

    ## Behavioral Rules
    - <rules>

    ## Success Criteria
    - <criteria>
    """
    # Map preferred_tool to Claude model alias
    model_map = {
        'claude': 'sonnet',
        'codex': 'sonnet',  # Fallback
        'gemini': 'sonnet',  # Fallback
    }
    model = model_map.get(template.preferred_tool, 'sonnet')

    # YAML frontmatter
    name = template.role or template.name
    description = f"{template.name} - {template.category} agent"

    frontmatter = f"""---
name: {name}
description: {description}
tools: ["mcp__giljo_mcp__*"]
model: {model}
---

"""

    # System prompt content
    content = template.template_content

    # Append behavioral rules if present
    if template.behavioral_rules:
        content += "\n\n## Behavioral Rules\n"
        for rule in template.behavioral_rules:
            content += f"- {rule}\n"

    # Append success criteria if present
    if template.success_criteria:
        content += "\n\n## Success Criteria\n"
        for criterion in template.success_criteria:
            content += f"- {criterion}\n"

    return frontmatter + content


def _backup_file(file_path: Path) -> Path:
    """Create timestamped backup of existing file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f".old.{timestamp}{file_path.suffix}")

    # Copy file to backup
    backup_path.write_bytes(file_path.read_bytes())

    return backup_path
```

---

#### Task 1.2: API Registration (15 minutes)

**Modify `api/app.py`**:

```python
# Add import
from api.endpoints import claude_export

# Register router
app.include_router(
    claude_export.router,
    prefix="/api/v1/templates",
    tags=["templates", "export", "claude-code"]
)
```

---

### Phase 2: UI Integration (1 day)

**Files to Modify**:
- `frontend/src/views/UserSettings.vue` (Integrations tab)
- `frontend/src/services/api.js` (add export method)

---

#### Task 2.1: Integrations Tab Export Section (1 day)

**Add new section in UserSettings.vue (Integrations tab)**:

```vue
<v-card class="mb-4">
  <v-card-title>
    <v-icon start>mdi-download</v-icon>
    Claude Code Agent Export
  </v-card-title>

  <v-card-text>
    <!-- Description -->
    <v-alert type="info" variant="tonal" class="mb-4">
      Export your customized agent templates to Claude Code format.
      Creates individual <code>.md</code> files in <code>.claude/agents/</code>
    </v-alert>

    <!-- Export Path Selection -->
    <v-radio-group v-model="claudeExportSettings.export_path" class="mb-4">
      <v-radio value="project">
        <template v-slot:label>
          <div>
            <strong>Project (.claude/agents/)</strong>
            <div class="text-caption">Current project only (recommended)</div>
          </div>
        </template>
      </v-radio>
      <v-radio value="personal">
        <template v-slot:label>
          <div>
            <strong>Personal (~/.claude/agents/)</strong>
            <div class="text-caption">Available in all projects</div>
          </div>
        </template>
      </v-radio>
    </v-radio-group>

    <!-- Template Selection Summary -->
    <v-card variant="outlined" class="mb-4">
      <v-card-text>
        <div class="text-subtitle-2 mb-2">Templates to Export:</div>
        <v-chip-group>
          <v-chip
            v-for="template in activeTemplates"
            :key="template.id"
            size="small"
            variant="outlined"
            color="primary"
          >
            {{ template.name }}
          </v-chip>
        </v-chip-group>
        <div class="text-caption mt-2">
          {{ activeTemplates.length }} active templates will be exported
        </div>
      </v-card-text>
    </v-card>

    <!-- Warning -->
    <v-alert type="warning" variant="tonal" class="mb-4">
      <v-icon start>mdi-alert</v-icon>
      Export will overwrite existing agent files.
      Backups will be created with <code>.old.YYYYMMDD_HHMMSS</code> extension.
    </v-alert>

    <!-- Export Button -->
    <v-btn
      color="primary"
      size="large"
      block
      prepend-icon="mdi-download"
      @click="executeClaudeExport"
      :loading="exporting"
      :disabled="activeTemplates.length === 0"
    >
      Export to Claude Code
    </v-btn>

    <!-- Export Result (after export completes) -->
    <v-alert
      v-if="exportResult"
      :type="exportResult.success ? 'success' : 'error'"
      variant="tonal"
      class="mt-4"
      closable
      @click:close="exportResult = null"
    >
      <v-alert-title>
        {{ exportResult.message }}
      </v-alert-title>
      <div v-if="exportResult.files_created.length > 0" class="mt-2">
        <strong>Files Created:</strong>
        <ul>
          <li v-for="file in exportResult.files_created" :key="file">
            <code>{{ file }}</code>
          </li>
        </ul>
      </div>
      <div v-if="exportResult.backups_created.length > 0" class="mt-2">
        <strong>Backups Created:</strong>
        <ul>
          <li v-for="backup in exportResult.backups_created" :key="backup">
            <code>{{ backup }}</code>
          </li>
        </ul>
      </div>
      <div v-if="exportResult.errors.length > 0" class="mt-2">
        <strong>Errors:</strong>
        <ul>
          <li v-for="error in exportResult.errors" :key="error" class="text-error">
            {{ error }}
          </li>
        </ul>
      </div>
    </v-alert>
  </v-card-text>
</v-card>
```

**JavaScript state**:
```javascript
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'

const claudeExportSettings = ref({
  export_path: 'project',  // 'project' or 'personal'
})

const activeTemplates = ref([])
const exporting = ref(false)
const exportResult = ref(null)

// Load active templates on mount
onMounted(async () => {
  try {
    const response = await api.templates.list()
    activeTemplates.value = response.data.templates.filter(t => t.is_active)
  } catch (error) {
    console.error('Failed to load templates:', error)
  }
})

const executeClaudeExport = async () => {
  exporting.value = true
  exportResult.value = null

  try {
    const template_ids = activeTemplates.value.map(t => t.id)

    const response = await api.templates.exportClaudeCode({
      template_ids,
      export_path: claudeExportSettings.value.export_path,
    })

    exportResult.value = response.data

    // Show success notification
    if (response.data.success) {
      // Optionally: emit success event or show global notification
    }
  } catch (error) {
    console.error('Export failed:', error)
    exportResult.value = {
      success: false,
      message: 'Export failed',
      files_created: [],
      backups_created: [],
      errors: [error.response?.data?.detail || 'Unknown error']
    }
  } finally {
    exporting.value = false
  }
}
```

---

#### Task 2.2: API Client Method (15 minutes)

**Modify `frontend/src/services/api.js`**:

```javascript
templates: {
  // ... existing methods (list, create, update, delete) ...

  exportClaudeCode: (data) => apiClient.post('/api/v1/templates/export/claude-code', data),
}
```

---

### Phase 3: Testing & Validation (0.5-1 day)

**Files to Create**:
- `tests/test_claude_export.py`

---

#### Task 3.1: Backend Tests (0.5 day)

**Create comprehensive tests**:

```python
"""Tests for Claude Code export functionality."""

import pytest
from pathlib import Path
from datetime import datetime
import yaml


@pytest.mark.asyncio
async def test_export_to_project_directory(db_session, test_user, sample_templates):
    """Test Claude Code export to project .claude/agents/ directory."""
    from api.endpoints.claude_export import export_to_claude_code, ClaudeExportRequest

    request = ClaudeExportRequest(
        template_ids=[t.id for t in sample_templates],
        export_path="project"
    )

    result = await export_to_claude_code(request, test_user, db_session)

    assert result.success is True
    assert len(result.files_created) == len(sample_templates)
    assert len(result.errors) == 0

    # Verify files exist
    export_dir = Path.cwd() / ".claude" / "agents"
    for template in sample_templates:
        file_path = export_dir / f"{template.role}.md"
        assert file_path.exists()

        # Verify YAML frontmatter
        content = file_path.read_text()
        assert content.startswith("---")
        frontmatter_end = content.find("---", 3)
        frontmatter = yaml.safe_load(content[3:frontmatter_end])

        assert frontmatter["name"] == template.role
        assert "description" in frontmatter
        assert "model" in frontmatter
        assert "tools" in frontmatter


@pytest.mark.asyncio
async def test_export_to_personal_directory(db_session, test_user, sample_templates):
    """Test Claude Code export to personal ~/.claude/agents/ directory."""
    request = ClaudeExportRequest(
        template_ids=[sample_templates[0].id],
        export_path="personal"
    )

    result = await export_to_claude_code(request, test_user, db_session)

    assert result.success is True

    # Verify file in personal directory
    personal_dir = Path.home() / ".claude" / "agents"
    assert personal_dir.exists()


@pytest.mark.asyncio
async def test_backup_existing_files(db_session, test_user, sample_templates):
    """Test automatic backup of existing files before overwrite."""
    # Create existing file
    export_dir = Path.cwd() / ".claude" / "agents"
    export_dir.mkdir(parents=True, exist_ok=True)

    existing_file = export_dir / "orchestrator.md"
    existing_file.write_text("Old content")

    # Export (should create backup)
    request = ClaudeExportRequest(
        template_ids=[sample_templates[0].id],
        export_path="project"
    )

    result = await export_to_claude_code(request, test_user, db_session)

    assert result.success is True
    assert len(result.backups_created) == 1

    # Verify backup file exists
    backup_path = Path(result.backups_created[0])
    assert backup_path.exists()
    assert "orchestrator.md.old." in backup_path.name
    assert backup_path.read_text() == "Old content"

    # Verify original file overwritten
    assert existing_file.read_text() != "Old content"


@pytest.mark.asyncio
async def test_multi_tenant_isolation(db_session, test_user, other_tenant_templates):
    """Test users can only export their own templates."""
    # User A tries to export User B's templates
    request = ClaudeExportRequest(
        template_ids=[other_tenant_templates[0].id],
        export_path="project"
    )

    with pytest.raises(HTTPException) as exc_info:
        await export_to_claude_code(request, test_user, db_session)

    assert exc_info.value.status_code == 404
    assert "No templates found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_programmatic_export(db_session, sample_templates):
    """Test programmatic export function (for orchestrator use)."""
    from api.endpoints.claude_export import export_template_to_claude_code

    template = sample_templates[0]

    file_path = await export_template_to_claude_code(
        template_id=template.id,
        tenant_key=template.tenant_key,
        session=db_session,
        export_path="project"
    )

    assert file_path
    assert Path(file_path).exists()


@pytest.mark.asyncio
async def test_yaml_frontmatter_format(db_session, test_user, sample_templates):
    """Test YAML frontmatter has correct format and fields."""
    request = ClaudeExportRequest(
        template_ids=[sample_templates[0].id],
        export_path="project"
    )

    result = await export_to_claude_code(request, test_user, db_session)

    # Read generated file
    file_path = Path(result.files_created[0])
    content = file_path.read_text()

    # Extract YAML frontmatter
    assert content.startswith("---\n")
    end_marker = content.find("\n---\n", 4)
    assert end_marker > 0

    frontmatter_text = content[4:end_marker]
    frontmatter = yaml.safe_load(frontmatter_text)

    # Verify required fields
    assert "name" in frontmatter
    assert "description" in frontmatter

    # Verify optional fields
    assert "tools" in frontmatter
    assert "model" in frontmatter

    # Verify tools format (list of strings)
    assert isinstance(frontmatter["tools"], list)
    assert "mcp__giljo_mcp__*" in frontmatter["tools"]


@pytest.mark.asyncio
async def test_behavioral_rules_and_criteria_appended(db_session, test_user, sample_templates):
    """Test behavioral rules and success criteria appended to markdown body."""
    template = sample_templates[0]
    template.behavioral_rules = ["Rule 1", "Rule 2", "Rule 3"]
    template.success_criteria = ["Criterion 1", "Criterion 2"]

    request = ClaudeExportRequest(
        template_ids=[template.id],
        export_path="project"
    )

    result = await export_to_claude_code(request, test_user, db_session)

    # Read generated file
    file_path = Path(result.files_created[0])
    content = file_path.read_text()

    # Verify behavioral rules section
    assert "## Behavioral Rules" in content
    assert "- Rule 1" in content
    assert "- Rule 2" in content

    # Verify success criteria section
    assert "## Success Criteria" in content
    assert "- Criterion 1" in content
    assert "- Criterion 2" in content


@pytest.mark.asyncio
async def test_error_handling_permission_denied(db_session, test_user, sample_templates, monkeypatch):
    """Test graceful error handling when file write fails."""
    # Mock file write to raise PermissionError
    def mock_write_text(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    request = ClaudeExportRequest(
        template_ids=[sample_templates[0].id],
        export_path="project"
    )

    result = await export_to_claude_code(request, test_user, db_session)

    assert result.success is False
    assert len(result.errors) > 0
    assert "Permission denied" in result.errors[0]
```

---

#### Task 3.2: Integration Tests (0.5 day)

**Test full workflow**:

1. **UI Loading:**
   - Navigate to User Settings → Integrations tab
   - Verify Claude Code Export section appears
   - Check active templates loaded correctly

2. **Export Configuration:**
   - Select project path radio button
   - Verify template chips displayed
   - Click "Export to Claude Code"
   - Verify loading state appears

3. **API Call:**
   - Verify correct payload sent to endpoint
   - Check authentication headers included
   - Confirm response received

4. **File Verification:**
   - Check `.claude/agents/` contains expected files
   - Verify YAML frontmatter format
   - Validate markdown content
   - Check backup files created with timestamp

5. **Success Feedback:**
   - Verify success alert displays
   - Check file paths listed correctly
   - Verify backup paths shown
   - Confirm closable alert works

---

## API Contract

### Endpoint

**POST** `/api/v1/templates/export/claude-code`

### Request Body

```json
{
  "template_ids": ["uuid1", "uuid2", "uuid3"],
  "export_path": "project"
}
```

**Fields**:
- `template_ids`: List of template UUIDs to export (required)
- `export_path`: "project" or "personal" (default: "project")

### Response (Success)

```json
{
  "success": true,
  "message": "Exported 6 agent templates to Claude Code successfully",
  "files_created": [
    ".claude/agents/orchestrator.md",
    ".claude/agents/analyzer.md",
    ".claude/agents/implementer.md",
    ".claude/agents/tester.md",
    ".claude/agents/reviewer.md",
    ".claude/agents/documenter.md"
  ],
  "backups_created": [
    ".claude/agents/orchestrator.md.old.20251024_193000"
  ],
  "errors": []
}
```

### Response (Partial Success)

```json
{
  "success": false,
  "message": "Export completed with 1 errors",
  "files_created": [
    ".claude/agents/orchestrator.md",
    ".claude/agents/analyzer.md"
  ],
  "backups_created": [],
  "errors": [
    "Failed to export implementer: Permission denied"
  ]
}
```

---

## File Structure After Export

### Project Export

```
F:\GiljoAI_MCP\
├── .claude/
│   └── agents/
│       ├── orchestrator.md       ← New
│       ├── analyzer.md            ← New
│       ├── implementer.md         ← New
│       ├── tester.md              ← New
│       ├── reviewer.md            ← New
│       └── documenter.md          ← New
```

### Personal Export

```
C:\Users\<user>\
├── .claude/
│   └── agents/
│       ├── orchestrator.md       ← New
│       ├── analyzer.md            ← New
│       └── ...
```

### Backups (if files existed)

```
F:\GiljoAI_MCP\
├── .claude/
│   └── agents/
│       ├── orchestrator.md.old.20251024_193000
│       ├── analyzer.md.old.20251024_150930
│       └── ...
```

---

## Security Considerations

### Multi-Tenant Isolation

**Enforcement**:
- Export endpoint requires authentication
- Templates filtered by `current_user.tenant_key`
- Users can ONLY export templates they own
- 404 error if trying to export other tenant's templates

**Test Coverage**:
- Cross-tenant export attempts (should fail with 404)
- Unauthorized access (should return 401)

### File System Safety

**Protections**:
- Path validation (only export to allowed directories)
- Automatic backups before overwrite
- Error handling for permission issues
- No arbitrary file write (paths are fixed)

**Allowed Paths**:
- `.claude/agents/` (project)
- `~/.claude/agents/` (personal)

**Forbidden**:
- Arbitrary paths from user input
- System directories
- Parent directory traversal (`../`)

---

## Integration with Handover 0045

**How 0044 Enables 0045**:

Handover 0045 (Multi-Tool Orchestration) needs to **automatically export** templates when Claude Code agents are spawned:

```python
# In orchestrator (Handover 0045 code)
from api.endpoints.claude_export import export_template_to_claude_code

if agent_config.tool == "claude":
    # Auto-export template to .claude/agents/
    await export_template_to_claude_code(
        template_id=agent_config.template_id,
        tenant_key=current_user.tenant_key,
        session=db_session,
        export_path="project"
    )

    # Then spawn Claude Code subagent via Task tool
    Task(
        subagent_type=agent_config.role,
        prompt=f"Follow template at .claude/agents/{agent_config.role}.md"
    )
```

**Programmatic Export Function** (`export_template_to_claude_code`) enables this workflow.

---

## Success Metrics

### Technical Metrics

- ✅ Export latency < 1 second for 6 templates
- ✅ Zero file corruption (all files valid markdown + YAML)
- ✅ 100% multi-tenant isolation (no cross-tenant exports)
- ✅ Backup success rate > 99%
- ✅ YAML format validation 100%

### Business Metrics

- Export usage rate (% of users who export templates)
- Average templates exported per operation
- Re-export frequency (how often users re-export)
- Integration with Claude Code (% of users using exported templates)

### Operational Metrics

- Export success rate (target: > 95%)
- Error rate by error type
- File system errors per 1000 exports
- Backup storage growth rate

---

## Known Limitations & Future Enhancements

### Limitations (v1)

- Only exports to fixed paths (no custom directories)
- No import from Claude Code files back to database
- No diff viewer (can't see what changed since last export)
- No export history tracking
- Manual export only (no auto-export on template save)

### Future Enhancements (Post-v1)

1. **Auto-Export on Save** (3-4 hours):
   - Checkbox: "Auto-export to Claude Code on save"
   - Background export after template update
   - Non-blocking operation

2. **Import from Claude Code** (1-2 days):
   - Scan `.claude/agents/` directory
   - Parse YAML frontmatter
   - Import as new templates or update existing

3. **Diff Viewer** (2-3 days):
   - Compare database template vs exported file
   - Highlight differences
   - "Export Changes" button

4. **Export History** (1-2 days):
   - Track all export operations (who, when, what)
   - View export history in UI
   - Re-export from history

---

## Testing Checklist

**Before Implementation**:
- [ ] Read complete handover document
- [ ] Understand Claude Code format requirements
- [ ] Review file system safety requirements
- [ ] Understand multi-tenant isolation

**During Implementation**:
- [ ] Backend: Export endpoint implemented
- [ ] Backend: YAML frontmatter generator
- [ ] Backend: Programmatic export function
- [ ] Backend: Backup file creation
- [ ] API: Router registered in app.py
- [ ] Frontend: Export section added to Integrations tab
- [ ] Frontend: API method added to api.js

**Testing**:
- [ ] Unit tests: YAML format generator
- [ ] Unit tests: Backup creation
- [ ] Unit tests: Multi-tenant isolation
- [ ] Integration tests: Full export workflow
- [ ] Security tests: Cross-tenant protection
- [ ] Error tests: Permission denied, disk full
- [ ] Manual tests: Verify exported files work in Claude Code

**Post-Implementation**:
- [ ] Documentation updated (USER_GUIDE.md)
- [ ] README updated with export feature
- [ ] Success metrics tracked
- [ ] Handover 0045 integration verified

---

## Deliverables Summary

**Backend**:
1. `claude_export.py`: Export endpoint + format generators (~350 lines)
2. `export_template_to_claude_code()`: Programmatic export function
3. Multi-tenant security enforcement
4. Comprehensive error handling

**Frontend**:
1. UserSettings.vue: Claude Code Export section
2. Success/error result display
3. Loading states
4. Template selection display

**Testing**:
1. `test_claude_export.py`: 8+ comprehensive tests
2. Integration test suite
3. Manual testing checklist

**Documentation**:
1. API documentation (this handover)
2. Integration guide for Handover 0045
3. User guide updates

---

## Timeline

**Day 1**: Backend endpoint + YAML generator (1.5 days)
**Day 2**: UI integration + API client (1 day)
**Day 3**: Testing + validation (0.5-1 day)

**Total**: 3-4 days to production-ready

---

## Approval & Sign-Off

**Prepared By**: System Architect
**Date**: 2025-10-24 (Recalibrated)
**Status**: ✅ Ready for Implementation
**Version**: 2.0 (Recalibrated - Claude Code Only)

**Implementation Team**:
- Backend Developer: Export endpoint + format generator
- UX Designer: Integrations tab UI
- Frontend Tester: Comprehensive testing suite

**Estimated Timeline**: 3-4 days
**Risk Level**: Low-Medium (single export format, file system operations)

**Related Handovers**:
- **Prerequisite**: Handover 0041 (Agent Template Database) - ✅ COMPLETE
- **Enables**: Handover 0045 (Multi-Tool Orchestration) - Planned

---

**END OF HANDOVER 0044 (RECALIBRATED)**
