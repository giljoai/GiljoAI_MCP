# Handover 0044: Agent Template Export System

**Date**: 2025-10-24
**From Agent**: System Architect & Research Agent
**To Agent**: Full-Stack Development Team (UX Designer + Backend Developer + Frontend Tester)
**Priority**: High
**Estimated Effort**: 6-8 hours
**Status**: Ready for Implementation
**Risk Level**: Medium (File system operations, multiple export formats)

---

## Executive Summary

**Objective**: Implement a comprehensive agent template export system that allows users to export their customized agent templates to Claude Code, Codex, and Gemini CLI formats, enabling seamless integration with AI coding tools.

**Current Problem**:
- Agent templates exist only in the database
- Users cannot export templates to actual AI coding tools (Claude Code, Codex, Gemini CLI)
- Orchestrator cannot use these templates without manual file creation
- No bridge between database templates and tool-specific agent files
- Each tool has different file format and storage location requirements

**Proposed Solution**:
- Add export toggle to each template in Template Manager
- Create dedicated export configuration in Integrations tab
- Implement backend export endpoint supporting all three formats:
  - **Claude Code**: Individual `.md` files with YAML frontmatter (`.claude/agents/` or `~/.claude/agents/`)
  - **Codex**: Combined `AGENTS.md` in project root
  - **Gemini CLI**: Combined `GEMINI.md` in project root
- Automatic backup of existing files before overwrite
- Multi-format export in single operation

**Value Delivered**:
- ✅ Agents immediately usable in Claude Code, Codex, and Gemini CLI
- ✅ Seamless workflow from template customization to tool integration
- ✅ Safe overwrites with automatic backups (`.old.YYYYMMDD_HHMMSS`)
- ✅ Per-template export control (select which to export)
- ✅ Support for both project-level and user-level agent storage
- ✅ Orchestrator can leverage actual tool agents for better coordination

---

## Research Findings

### 1. Claude Code Agent Format (VERIFIED)

**Source**: https://docs.claude.com/en/docs/claude-code/sub-agents

**File Format**: Markdown with YAML frontmatter

**Storage Locations**:
- **Project**: `.claude/agents/` (highest priority)
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
```

**Required Fields**:
- `name`: Lowercase letters and hyphens only
- `description`: Natural language explaining purpose and when to invoke

**Optional Fields**:
- `tools`: Comma-separated list (omit to inherit all tools)
- `model`: Model alias or 'inherit'

**File Naming**: `{name}.md` (e.g., `orchestrator.md`)

**Key Features**:
- Each agent in separate file
- YAML frontmatter for metadata
- Markdown for system prompt
- Project agents override personal agents
- Tools can be restricted per agent

---

### 2. Codex (OpenAI) Format (VERIFIED)

**Source**: https://github.com/openai/agents.md

**File Format**: Single Markdown file

**Storage Location**: Project root: `AGENTS.md`

**Purpose**: Project context for AI coding agents (NOT individual agent definitions)

**File Structure**:
```markdown
# AI Agent Instructions

## Available Agents

### Orchestrator Agent
**Role:** Project manager and delegation expert
**When to use:** Complex multi-step development tasks requiring team coordination

**Behavioral Rules:**
- Read vision document completely (all parts)
- Delegate instead of implementing (3-tool rule)
- Challenge scope drift proactively

**Success Criteria:**
- All project objectives met
- Clean handoff documentation created
- Zero scope creep maintained

---

### Analyzer Agent
**Role:** Requirements analysis and architecture design
**When to use:** Understanding requirements, designing system architecture

**Behavioral Rules:**
- Analyze thoroughly before proposing solutions
- Document findings clearly

**Success Criteria:**
- Complete requirements documented
- Architecture aligned with vision

---

(Repeat for all selected agents)
```

**Key Features**:
- Single file for all agents
- Markdown sections with clear hierarchy
- Agent roles, use cases, rules, and criteria
- Human-readable project documentation

---

### 3. Gemini CLI Format (VERIFIED)

**Source**: https://github.com/google-gemini/gemini-cli

**File Format**: Single Markdown file

**Storage Location**: Project root: `GEMINI.md`

**Purpose**: Project-specific context file for Gemini CLI

**File Structure**:
```markdown
# Project Agent Configuration

This project uses specialized AI agents for different development tasks.

## Agent Roles

### Orchestrator
**Description:** Project manager and delegation expert

**Responsibilities:**
- Reads vision documents completely
- Delegates instead of implementing (3-tool rule)
- Challenges scope drift proactively
- Creates 3 documentation artifacts at project close

**Tools:** spawn_agent, get_vision, send_agent_message, get_product_settings

**Success Metrics:**
- All project objectives met
- Clean handoff documentation
- Zero scope creep

---

### Analyzer
**Description:** Requirements analysis specialist

**Responsibilities:**
- Analyzes requirements thoroughly
- Documents findings clearly
- Designs system architecture

**Tools:** Read, Grep, Glob

**Success Metrics:**
- Complete requirements documented
- Architecture aligned with vision

---

(Repeat for all selected agents)
```

**Key Features**:
- Single file for all agents
- Markdown with clear section hierarchy
- Agent descriptions, responsibilities, tools, metrics
- Persistent context for Gemini CLI sessions

---

## Current Database Schema (AgentTemplate)

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
    tags = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)
```

**Mapping to Export Formats**:

| Database Field | Claude Code | Codex | Gemini |
|----------------|-------------|-------|--------|
| `name` | YAML `name:` | Section heading | Section heading |
| `role` | Filename | Role label | Description |
| `template_content` | Markdown body | Full content | Responsibilities |
| `behavioral_rules` | Include in body | Behavioral Rules section | Responsibilities section |
| `success_criteria` | Include in body | Success Criteria section | Success Metrics section |
| `variables` | (omit or document) | (omit) | (omit) |
| `preferred_tool` | YAML `model:` | (omit) | Tools section |
| `tags` | (omit) | (omit) | (omit) |

---

## Implementation Plan

### Phase 1: UI Enhancements (2 hours)

**Files to Modify**:
- `frontend/src/components/TemplateManager.vue`
- `frontend/src/views/UserSettings.vue` (Integrations tab)

#### Task 1.1: Template Manager Export Toggles (45 minutes)

**Add to each template row in data table**:
```vue
<template v-slot:item.export="{ item }">
  <v-checkbox
    v-model="item.export_enabled"
    hide-details
    density="compact"
    @change="updateExportSelection"
  />
</template>
```

**Add Export button to toolbar**:
```vue
<v-btn
  color="primary"
  prepend-icon="mdi-download"
  @click="redirectToExport"
>
  Export Agents ({{ selectedExportCount }})
</v-btn>
```

**Reactive state**:
```javascript
const selectedExportCount = computed(() =>
  templates.value.filter(t => t.export_enabled).length
)

const redirectToExport = () => {
  // Store selected templates in localStorage or Vuex
  localStorage.setItem('export_templates', JSON.stringify(
    templates.value.filter(t => t.export_enabled).map(t => t.id)
  ))
  // Navigate to Integrations tab
  router.push({ name: 'UserSettings', hash: '#integrations' })
}
```

**Column definition update**:
```javascript
const headers = [
  { title: 'Export', key: 'export', align: 'center', sortable: false, width: 80 },
  { title: 'Name', key: 'name', align: 'start' },
  { title: 'Role', key: 'role', align: 'start' },
  // ... existing columns
]
```

**Default behavior**: All templates checked by default on load

---

#### Task 1.2: Integrations Tab Export Section (1 hour 15 minutes)

**Add new section in UserSettings.vue (Integrations tab)**:

```vue
<v-card class="mb-4">
  <v-card-title>
    <v-icon start>mdi-download</v-icon>
    Agent Configuration Export
  </v-card-title>

  <v-card-text>
    <!-- Selected Templates Summary -->
    <v-alert type="info" variant="tonal" class="mb-4">
      <strong>{{ selectedTemplatesCount }} templates</strong> selected for export
      <v-chip-group class="mt-2">
        <v-chip
          v-for="template in selectedTemplates"
          :key="template.id"
          size="small"
          variant="outlined"
        >
          {{ template.name }}
        </v-chip>
      </v-chip-group>
    </v-alert>

    <!-- Claude Code Export Settings -->
    <v-expansion-panels class="mb-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <div class="d-flex align-center">
            <v-img src="/claude_pix.svg" width="24" height="24" class="mr-2" />
            <strong>Claude Code Export</strong>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-radio-group v-model="exportSettings.claude_path">
            <v-radio
              label="Project (.claude/agents/) - Recommended"
              value="project"
            >
              <template v-slot:label>
                <div>
                  <strong>Project (.claude/agents/)</strong>
                  <div class="text-caption">Current project only (highest priority)</div>
                </div>
              </template>
            </v-radio>
            <v-radio
              label="Personal (~/.claude/agents/)"
              value="personal"
            >
              <template v-slot:label>
                <div>
                  <strong>Personal (~/.claude/agents/)</strong>
                  <div class="text-caption">Available in all projects</div>
                </div>
              </template>
            </v-radio>
          </v-radio-group>

          <v-alert type="info" density="compact" class="mt-2">
            Creates individual .md files for each selected template
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Codex Export Settings -->
      <v-expansion-panel>
        <v-expansion-panel-title>
          <div class="d-flex align-center">
            <v-img src="/codex_logo.svg" width="24" height="24" class="mr-2" />
            <strong>Codex (OpenAI) Export</strong>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-checkbox
            v-model="exportSettings.export_codex"
            label="Generate AGENTS.md"
            hide-details
          >
            <template v-slot:label>
              <div>
                <strong>Generate AGENTS.md</strong>
                <div class="text-caption">Project root - combined agent instructions</div>
              </div>
            </template>
          </v-checkbox>

          <v-alert type="info" density="compact" class="mt-2">
            Creates single AGENTS.md file with all selected templates
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Gemini CLI Export Settings -->
      <v-expansion-panel>
        <v-expansion-panel-title>
          <div class="d-flex align-center">
            <v-img src="/gemini-icon.svg" width="24" height="24" class="mr-2" />
            <strong>Gemini CLI Export</strong>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-checkbox
            v-model="exportSettings.export_gemini"
            label="Generate GEMINI.md"
            hide-details
          >
            <template v-slot:label>
              <div>
                <strong>Generate GEMINI.md</strong>
                <div class="text-caption">Project root - agent configuration context</div>
              </div>
            </template>
          </v-checkbox>

          <v-alert type="info" density="compact" class="mt-2">
            Creates single GEMINI.md file with all selected templates
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Warning -->
    <v-alert type="warning" variant="tonal" class="mb-4">
      <v-icon start>mdi-alert</v-icon>
      <strong>Warning:</strong> Export will overwrite existing agent files.
      Backups will be created with <code>.old.YYYYMMDD_HHMMSS</code> extension.
    </v-alert>

    <!-- Export Button -->
    <v-btn
      color="primary"
      size="large"
      block
      prepend-icon="mdi-download"
      @click="executeExport"
      :loading="exporting"
      :disabled="selectedTemplatesCount === 0"
    >
      Export Agent Configurations
    </v-btn>
  </v-card-text>
</v-card>
```

**JavaScript state**:
```javascript
const exportSettings = ref({
  claude_path: 'project',  // 'project' or 'personal'
  export_codex: true,
  export_gemini: true,
})

const selectedTemplates = ref([])
const selectedTemplatesCount = computed(() => selectedTemplates.value.length)
const exporting = ref(false)

// Load selected templates from localStorage on mount
onMounted(() => {
  const templateIds = JSON.parse(localStorage.getItem('export_templates') || '[]')
  if (templateIds.length > 0) {
    loadSelectedTemplates(templateIds)
  }
})

const executeExport = async () => {
  exporting.value = true
  try {
    const response = await api.templates.export({
      template_ids: selectedTemplates.value.map(t => t.id),
      claude_path: exportSettings.value.claude_path,
      export_codex: exportSettings.value.export_codex,
      export_gemini: exportSettings.value.export_gemini,
    })

    // Show success notification with file details
    showSuccessNotification(response.data)
  } catch (error) {
    console.error('Export failed:', error)
    showErrorNotification(error.response?.data?.detail || 'Export failed')
  } finally {
    exporting.value = false
  }
}
```

---

### Phase 2: Backend Export Endpoint (3 hours)

**Files to Create**:
- `api/endpoints/template_export.py` (new file)

**Files to Modify**:
- `api/app.py` (register router)
- `frontend/src/services/api.js` (add export method)

#### Task 2.1: Export Endpoint Implementation (2 hours)

**Create new file: `api/endpoints/template_export.py`**

```python
"""
Agent Template Export Endpoint

Exports agent templates to Claude Code, Codex, and Gemini CLI formats.
Handles file creation, backups, and multi-format conversion.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.models import AgentTemplate, User
from api.dependencies import get_current_active_user, get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class ExportRequest(BaseModel):
    """Agent template export request."""
    template_ids: List[str]
    claude_path: str = "project"  # 'project' or 'personal'
    export_codex: bool = True
    export_gemini: bool = True


class ExportResult(BaseModel):
    """Export operation result."""
    success: bool
    message: str
    files_created: List[str]
    backups_created: List[str]
    errors: List[str] = []


# Export Endpoint
@router.post("/export", response_model=ExportResult)
async def export_templates(
    request: ExportRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Export agent templates to Claude Code, Codex, and Gemini CLI formats.

    Security:
    - Multi-tenant isolation: Only exports templates owned by user's tenant
    - File system safety: Creates backups before overwriting
    - Path validation: Validates export paths exist and are writable

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

        files_created = []
        backups_created = []
        errors = []

        # Export to Claude Code (individual .md files)
        if templates:
            claude_result = await export_to_claude_code(
                templates,
                request.claude_path,
                current_user.tenant_key
            )
            files_created.extend(claude_result["files"])
            backups_created.extend(claude_result["backups"])
            errors.extend(claude_result["errors"])

        # Export to Codex (single AGENTS.md)
        if request.export_codex and templates:
            codex_result = await export_to_codex(templates)
            files_created.extend(codex_result["files"])
            backups_created.extend(codex_result["backups"])
            errors.extend(codex_result["errors"])

        # Export to Gemini CLI (single GEMINI.md)
        if request.export_gemini and templates:
            gemini_result = await export_to_gemini(templates)
            files_created.extend(gemini_result["files"])
            backups_created.extend(gemini_result["backups"])
            errors.extend(gemini_result["errors"])

        # Determine overall success
        success = len(errors) == 0
        message = (
            f"Exported {len(templates)} agent configurations successfully"
            if success
            else f"Export completed with {len(errors)} errors"
        )

        logger.info(
            f"[Export] User {current_user.username} exported {len(templates)} templates: "
            f"{len(files_created)} files created, {len(backups_created)} backups"
        )

        return ExportResult(
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


# Export Format Implementations
async def export_to_claude_code(
    templates: List[AgentTemplate],
    path_type: str,
    tenant_key: str,
) -> dict:
    """
    Export templates to Claude Code format (individual .md files with YAML frontmatter).

    File format:
    ---
    name: agent-identifier
    description: When to use this agent
    tools: Read, Grep, Bash
    model: sonnet
    ---

    System prompt content...
    """
    files_created = []
    backups_created = []
    errors = []

    try:
        # Determine export path
        if path_type == "project":
            export_path = Path.cwd() / ".claude" / "agents"
        else:  # personal
            export_path = Path.home() / ".claude" / "agents"

        # Create directory if not exists
        export_path.mkdir(parents=True, exist_ok=True)

        for template in templates:
            try:
                # Generate filename (sanitize name for filesystem)
                filename = f"{template.role or template.name}.md"
                file_path = export_path / filename

                # Backup existing file
                if file_path.exists():
                    backup_path = backup_file(file_path)
                    backups_created.append(str(backup_path))

                # Generate Claude Code format
                content = generate_claude_code_format(template)

                # Write file
                file_path.write_text(content, encoding='utf-8')
                files_created.append(str(file_path))

                logger.info(f"[Claude Export] Created {file_path}")

            except Exception as e:
                error_msg = f"Failed to export {template.name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"[Claude Export] {error_msg}")

    except Exception as e:
        error_msg = f"Claude Code export failed: {str(e)}"
        errors.append(error_msg)
        logger.error(f"[Claude Export] {error_msg}")

    return {
        "files": files_created,
        "backups": backups_created,
        "errors": errors,
    }


async def export_to_codex(templates: List[AgentTemplate]) -> dict:
    """
    Export templates to Codex format (single AGENTS.md in project root).

    File format:
    # AI Agent Instructions

    ## Available Agents

    ### Orchestrator Agent
    **Role:** Project manager and delegation expert
    ...
    """
    files_created = []
    backups_created = []
    errors = []

    try:
        # Export to project root
        file_path = Path.cwd() / "AGENTS.md"

        # Backup existing file
        if file_path.exists():
            backup_path = backup_file(file_path)
            backups_created.append(str(backup_path))

        # Generate combined Codex format
        content = generate_codex_format(templates)

        # Write file
        file_path.write_text(content, encoding='utf-8')
        files_created.append(str(file_path))

        logger.info(f"[Codex Export] Created {file_path}")

    except Exception as e:
        error_msg = f"Codex export failed: {str(e)}"
        errors.append(error_msg)
        logger.error(f"[Codex Export] {error_msg}")

    return {
        "files": files_created,
        "backups": backups_created,
        "errors": errors,
    }


async def export_to_gemini(templates: List[AgentTemplate]) -> dict:
    """
    Export templates to Gemini CLI format (single GEMINI.md in project root).

    File format:
    # Project Agent Configuration

    ## Agent Roles

    ### Orchestrator
    **Description:** Project manager and delegation expert
    ...
    """
    files_created = []
    backups_created = []
    errors = []

    try:
        # Export to project root
        file_path = Path.cwd() / "GEMINI.md"

        # Backup existing file
        if file_path.exists():
            backup_path = backup_file(file_path)
            backups_created.append(str(backup_path))

        # Generate Gemini format
        content = generate_gemini_format(templates)

        # Write file
        file_path.write_text(content, encoding='utf-8')
        files_created.append(str(file_path))

        logger.info(f"[Gemini Export] Created {file_path}")

    except Exception as e:
        error_msg = f"Gemini export failed: {str(e)}"
        errors.append(error_msg)
        logger.error(f"[Gemini Export] {error_msg}")

    return {
        "files": files_created,
        "backups": backups_created,
        "errors": errors,
    }


# Format Generators
def generate_claude_code_format(template: AgentTemplate) -> str:
    """Generate Claude Code markdown with YAML frontmatter."""
    # Map preferred_tool to Claude model alias
    model_map = {
        'claude': 'sonnet',
        'codex': 'sonnet',  # Fallback to sonnet
        'gemini': 'sonnet',  # Fallback to sonnet
    }
    model = model_map.get(template.preferred_tool, 'sonnet')

    # YAML frontmatter
    frontmatter = f"""---
name: {template.role or template.name}
description: {template.name} - {template.category} agent
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


def generate_codex_format(templates: List[AgentTemplate]) -> str:
    """Generate combined AGENTS.md for Codex."""
    content = "# AI Agent Instructions\n\n"
    content += "This project uses specialized AI agents for different development tasks.\n\n"
    content += "## Available Agents\n\n"

    for template in templates:
        content += f"### {template.name.title()} Agent\n"
        content += f"**Role:** {template.role or template.category}\n"
        content += f"**When to use:** {template.category} tasks\n\n"

        # Template content (first paragraph as description)
        lines = template.template_content.split('\n\n')
        if lines:
            content += f"{lines[0]}\n\n"

        # Behavioral rules
        if template.behavioral_rules:
            content += "**Behavioral Rules:**\n"
            for rule in template.behavioral_rules:
                content += f"- {rule}\n"
            content += "\n"

        # Success criteria
        if template.success_criteria:
            content += "**Success Criteria:**\n"
            for criterion in template.success_criteria:
                content += f"- {criterion}\n"
            content += "\n"

        content += "---\n\n"

    return content


def generate_gemini_format(templates: List[AgentTemplate]) -> str:
    """Generate GEMINI.md for Gemini CLI."""
    content = "# Project Agent Configuration\n\n"
    content += "This project uses specialized AI agents for different development tasks.\n\n"
    content += "## Agent Roles\n\n"

    for template in templates:
        content += f"### {template.name.title()}\n"
        content += f"**Description:** {template.role or template.category} agent\n\n"

        # Responsibilities (behavioral rules)
        if template.behavioral_rules:
            content += "**Responsibilities:**\n"
            for rule in template.behavioral_rules:
                content += f"- {rule}\n"
            content += "\n"

        # Success metrics (success criteria)
        if template.success_criteria:
            content += "**Success Metrics:**\n"
            for criterion in template.success_criteria:
                content += f"- {criterion}\n"
            content += "\n"

        content += "---\n\n"

    return content


def backup_file(file_path: Path) -> Path:
    """Create timestamped backup of existing file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f".old.{timestamp}{file_path.suffix}")

    # Copy file to backup
    backup_path.write_bytes(file_path.read_bytes())

    return backup_path
```

---

#### Task 2.2: API Registration (15 minutes)

**Modify `api/app.py`**:

```python
# Add import
from api.endpoints import template_export

# Register router
app.include_router(
    template_export.router,
    prefix="/api/v1/templates",
    tags=["templates", "export"]
)
```

**Modify `frontend/src/services/api.js`**:

```javascript
templates: {
  // ... existing methods ...

  export: (data) => apiClient.post('/api/v1/templates/export', data),
}
```

---

### Phase 3: Testing & Validation (1.5 hours)

**Files to Create**:
- `tests/test_template_export.py`

#### Task 3.1: Backend Tests (45 minutes)

**Create comprehensive tests**:

```python
"""Tests for agent template export functionality."""

import pytest
from pathlib import Path
from datetime import datetime


@pytest.mark.asyncio
async def test_export_to_claude_code_project(db_session, test_user, sample_templates):
    """Test Claude Code export to project directory."""
    # Test creates .claude/agents/ files
    # Verify YAML frontmatter format
    # Check file content matches template
    pass


@pytest.mark.asyncio
async def test_export_to_claude_code_personal(db_session, test_user, sample_templates):
    """Test Claude Code export to personal directory."""
    # Test creates ~/.claude/agents/ files
    pass


@pytest.mark.asyncio
async def test_export_to_codex(db_session, test_user, sample_templates):
    """Test Codex AGENTS.md generation."""
    # Test creates AGENTS.md in project root
    # Verify markdown structure
    # Check all templates included
    pass


@pytest.mark.asyncio
async def test_export_to_gemini(db_session, test_user, sample_templates):
    """Test Gemini GEMINI.md generation."""
    # Test creates GEMINI.md in project root
    # Verify markdown structure
    pass


@pytest.mark.asyncio
async def test_backup_creation(db_session, test_user, sample_templates):
    """Test automatic backup of existing files."""
    # Create existing file
    # Export (should backup)
    # Verify backup has .old.YYYYMMDD_HHMMSS format
    # Verify original overwritten
    pass


@pytest.mark.asyncio
async def test_multi_tenant_isolation(db_session, test_user, other_tenant_user):
    """Test users can only export their own templates."""
    # User A tries to export User B's templates
    # Should return 404 (not found)
    pass


@pytest.mark.asyncio
async def test_export_subset_of_templates(db_session, test_user, sample_templates):
    """Test exporting only selected templates."""
    # Export 3 out of 6 templates
    # Verify only 3 files created
    pass


@pytest.mark.asyncio
async def test_export_error_handling(db_session, test_user, sample_templates):
    """Test graceful error handling on file system errors."""
    # Mock file write failure
    # Verify errors list populated
    # Verify success=False in result
    pass
```

---

#### Task 3.2: Integration Tests (45 minutes)

**Test full workflow**:

1. **Template Selection:**
   - Load Template Manager
   - Check export toggles for specific templates
   - Click "Export Agents" button
   - Verify redirect to Integrations tab

2. **Export Configuration:**
   - Select Claude Code path (project vs personal)
   - Toggle Codex/Gemini checkboxes
   - Click "Export Agent Configurations"
   - Verify API call made with correct payload

3. **File Verification:**
   - Check `.claude/agents/` contains expected files
   - Verify YAML frontmatter format
   - Check `AGENTS.md` and `GEMINI.md` created
   - Verify backup files created with timestamp

4. **Success Feedback:**
   - Verify success notification displays
   - Check file paths listed
   - Verify backup paths shown

---

## API Contract

### Endpoint

**POST** `/api/v1/templates/export`

### Request Body

```json
{
  "template_ids": ["uuid1", "uuid2", "uuid3"],
  "claude_path": "project",
  "export_codex": true,
  "export_gemini": true
}
```

### Response (Success)

```json
{
  "success": true,
  "message": "Exported 6 agent configurations successfully",
  "files_created": [
    ".claude/agents/orchestrator.md",
    ".claude/agents/analyzer.md",
    ".claude/agents/implementer.md",
    ".claude/agents/tester.md",
    ".claude/agents/reviewer.md",
    ".claude/agents/documenter.md",
    "AGENTS.md",
    "GEMINI.md"
  ],
  "backups_created": [
    ".claude/agents/orchestrator.md.old.20251024_193000",
    "AGENTS.md.old.20251024_193000",
    "GEMINI.md.old.20251024_193000"
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
    "AGENTS.md"
  ],
  "backups_created": [
    ".claude/agents/orchestrator.md.old.20251024_193000"
  ],
  "errors": [
    "Failed to export analyzer: Permission denied"
  ]
}
```

---

## File Structure After Export

### Claude Code (Project)

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

### Codex & Gemini (Project Root)

```
F:\GiljoAI_MCP\
├── AGENTS.md                      ← New (Codex)
├── GEMINI.md                      ← New (Gemini)
```

### Backups (if files existed)

```
F:\GiljoAI_MCP\
├── .claude/
│   └── agents/
│       ├── orchestrator.md.old.20251024_193000
│       └── ...
├── AGENTS.md.old.20251024_193000
└── GEMINI.md.old.20251024_193000
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
- Cross-tenant export attempts (should fail)
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
- `./AGENTS.md` (project root)
- `./GEMINI.md` (project root)

**Forbidden**:
- Arbitrary paths from user input
- System directories
- Parent directory traversal (`../`)

---

## Edge Cases & Error Handling

### Edge Case 1: No Templates Selected

**Scenario**: User clicks export with 0 templates checked

**Handling**:
- Export button disabled when `selectedTemplatesCount === 0`
- API returns 404 if no templates found

### Edge Case 2: Missing .claude Directory

**Scenario**: `.claude/agents/` doesn't exist

**Handling**:
- Create directory automatically: `export_path.mkdir(parents=True, exist_ok=True)`
- Log directory creation

### Edge Case 3: Permission Denied

**Scenario**: No write permission to export directory

**Handling**:
- Catch `PermissionError`
- Add to `errors` list
- Set `success=False`
- Return partial results (files that succeeded)

### Edge Case 4: Disk Full

**Scenario**: Insufficient disk space

**Handling**:
- Catch `OSError`
- Roll back partial writes
- Return error to user

### Edge Case 5: Large Template Content

**Scenario**: Template content > 1MB

**Handling**:
- No size limit (templates are text)
- File system handles large files
- Consider warning if > 100KB

---

## Success Metrics

### Technical Metrics

- ✅ Export latency < 2 seconds for 6 templates
- ✅ Zero file corruption (all files valid markdown)
- ✅ 100% multi-tenant isolation (no cross-tenant exports)
- ✅ Backup success rate > 99%

### Business Metrics

- Export usage rate (% of users who export templates)
- Most exported tools (Claude vs Codex vs Gemini)
- Average templates exported per operation
- Re-export frequency (how often users re-export)

### Operational Metrics

- Export success rate (target: > 95%)
- Error rate by error type
- File system errors per 1000 exports
- Backup storage growth rate

---

## Future Enhancements (Post-v1)

### Enhancement 1: Export Scheduling

**Feature**: Auto-export on template save
- Checkbox: "Auto-export to Claude Code on save"
- Automatically exports updated template
- Background job (non-blocking)

### Enhancement 2: Import from Files

**Feature**: Import Claude Code agents into database
- Scan `.claude/agents/` directory
- Parse YAML frontmatter
- Import as new templates
- Merge with existing

### Enhancement 3: Diff Viewer

**Feature**: Compare database template vs exported file
- Show what changed since last export
- Highlight differences
- "Export Changes" button

### Enhancement 4: Export History

**Feature**: Track all export operations
- Export log table (who, when, what, where)
- View export history in UI
- Re-export from history

### Enhancement 5: Batch Operations

**Feature**: Export all tenants' templates (admin only)
- Admin-only endpoint
- Export all templates for all tenants
- Organized by tenant_key folders

---

## Testing Checklist

**Before Implementation**:
- [ ] Read complete handover document
- [ ] Understand all three export formats
- [ ] Review file system safety requirements
- [ ] Understand multi-tenant isolation

**During Implementation**:
- [ ] UI: Export toggles added to Template Manager
- [ ] UI: Export section added to Integrations tab
- [ ] Backend: Export endpoint implemented
- [ ] Backend: Claude Code format generator
- [ ] Backend: Codex format generator
- [ ] Backend: Gemini format generator
- [ ] Backend: Backup file creation
- [ ] API: Router registered in app.py
- [ ] Frontend: API method added to api.js

**Testing**:
- [ ] Unit tests: All format generators
- [ ] Unit tests: Backup creation
- [ ] Integration tests: Full export workflow
- [ ] Security tests: Multi-tenant isolation
- [ ] Error tests: Permission denied, disk full
- [ ] UI tests: Toggle interaction, redirect flow
- [ ] Manual tests: Verify exported files work in actual tools

**Post-Implementation**:
- [ ] Documentation updated (USER_GUIDE.md)
- [ ] README updated with export feature
- [ ] Success metrics tracked
- [ ] User feedback collected

---

## Deliverables Summary

**Frontend**:
1. TemplateManager.vue: Export toggles + Export button
2. UserSettings.vue: Export configuration section
3. Success/error notifications
4. Loading states

**Backend**:
1. template_export.py: Export endpoint + format generators
2. app.py: Router registration
3. Multi-tenant security enforcement
4. Comprehensive error handling

**Testing**:
1. test_template_export.py: 8+ comprehensive tests
2. Integration test suite
3. Manual testing checklist

**Documentation**:
1. API documentation (this handover)
2. User guide updates
3. Developer guide updates

---

## Questions & Answers

**Q: What if user exports to Claude Code but Claude Code isn't installed?**
A: Files are created anyway. User can install Claude Code later and files will be available immediately.

**Q: Can users export to custom paths?**
A: No (v1). Only predefined safe paths. Custom paths could be added in v2 with strict validation.

**Q: What if template content contains invalid YAML characters?**
A: Content goes in markdown body, not YAML. YAML only contains metadata (name, description, model).

**Q: How do we handle template variables like {project_name}?**
A: Variables remain in exported templates. They're replaced at runtime by Claude Code when agent is invoked.

**Q: Can admins export all tenants' templates?**
A: Not in v1. Each tenant exports their own. Admin batch export could be added in v2.

**Q: What if export takes > 10 seconds?**
A: Unlikely for text files. If needed, implement async export with status polling endpoint.

---

## Approval & Sign-Off

**Prepared By**: System Architect & Research Agent
**Date**: 2025-10-24
**Status**: ✅ Ready for Implementation

**Implementation Team**:
- UX Designer: UI enhancements (Template Manager + Integrations)
- Backend Developer: Export endpoint + format generators
- Frontend Tester: Comprehensive testing suite

**Estimated Timeline**: 6-8 hours
**Risk Level**: Medium (file system operations, multiple formats)

---

**END OF HANDOVER 0044**
