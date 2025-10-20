# Template System Implementation Roadmap

**Project**: Agent Template Integration & Management System
**Status**: Planning → Implementation Ready
**Timeline**: 6 weeks (phased approach)
**Priority**: High - Critical for Claude Code/Codex/Gemini integration

---

## Executive Summary

This roadmap outlines the complete implementation of a unified agent template management system that bridges the gap between our database-driven templates and file-based agent configurations required by external coding tools (Claude Code, Codex, Gemini).

**Goals**:
- ✅ Database as single source of truth for templates
- ✅ Auto-export templates to `.claude/agents/*.md` format
- ✅ Web UI for template CRUD operations
- ✅ Multi-tool support (Claude → Codex → Gemini)
- ✅ Production-grade code quality (Chef's kiss standard)

---

## Architecture Overview

### Current State
```
Database (PostgreSQL agent_templates table)
    ↓
Embedded in template_manager.py (_legacy_templates dict)
    ↓
Used by JobCoordinator for agent spawning
```

### Target State
```
Database (PostgreSQL) ← [UI for Management]
    ↓
AgentFileGenerator (Auto-export)
    ↓
.claude/agents/*.md files (Claude Code)
.codex/agents/*.md files (Codex) [Future]
.gemini/agents/*.md files (Gemini) [Future]
    ↓
External Coding Tools discover and use agents
```

---

## Phase 1: Database to File Export (Week 1)

**Goal**: Implement core export functionality to generate `.claude/agents/*.md` files from database templates.

### Tasks

#### 1.1 Create AgentFileGenerator Class
**File**: `src/giljo_mcp/agent_file_generator.py`

**Implementation**:
```python
from pathlib import Path
from typing import Dict, Any, Optional
from src.giljo_mcp.models import AgentTemplate

class AgentFileGenerator:
    """Generate .claude/agents/*.md files from database templates."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(".claude/agents")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def export_template_to_file(
        self,
        template: AgentTemplate,
        format: str = "claude"
    ) -> Dict[str, Any]:
        """
        Export single template to .md file.
        
        Args:
            template: AgentTemplate from database
            format: "claude", "codex", or "gemini"
        
        Returns:
            {
                "file_path": Path to created file,
                "content": Generated file content,
                "success": True/False
            }
        """
        exporters = {
            "claude": self._export_claude_format,
            "codex": self._export_codex_format,
            "gemini": self._export_gemini_format
        }
        
        if format not in exporters:
            raise ValueError(f"Unsupported format: {format}")
        
        md_content = exporters[format](template)
        file_path = self.output_dir / f"{template.name}.md"
        
        try:
            file_path.write_text(md_content, encoding='utf-8')
            return {
                "file_path": str(file_path),
                "content": md_content,
                "success": True
            }
        except Exception as e:
            return {
                "file_path": str(file_path),
                "error": str(e),
                "success": False
            }
    
    def _export_claude_format(self, template: AgentTemplate) -> str:
        """Generate Claude Code .md format with YAML frontmatter."""
        frontmatter = f"""---
name: {template.name}
description: "{template.description or template.role}"
model: sonnet
color: blue
---

"""
        content = template.template_content
        
        # Add metadata sections
        if template.variables:
            content += "\n\n## Template Variables\n"
            for var in template.variables:
                content += f"- {{{var}}}\n"
        
        if template.behavioral_rules:
            content += "\n\n## Behavioral Rules\n"
            for rule in template.behavioral_rules:
                content += f"- {rule}\n"
        
        if template.success_criteria:
            content += "\n\n## Success Criteria\n"
            for criterion in template.success_criteria:
                content += f"- {criterion}\n"
        
        return frontmatter + content
    
    def _export_codex_format(self, template: AgentTemplate) -> str:
        """Generate Codex format (to be determined)."""
        # TODO: Research Codex agent format
        return self._export_claude_format(template)
    
    def _export_gemini_format(self, template: AgentTemplate) -> str:
        """Generate Gemini format (to be determined)."""
        # TODO: Research Gemini agent format
        return self._export_claude_format(template)
    
    async def export_all_templates(
        self,
        templates: list[AgentTemplate],
        format: str = "claude"
    ) -> Dict[str, Any]:
        """
        Export all templates to files.
        
        Returns:
            {
                "total": 6,
                "succeeded": 6,
                "failed": 0,
                "results": [...]
            }
        """
        results = []
        for template in templates:
            result = await self.export_template_to_file(template, format)
            results.append({
                "template_name": template.name,
                **result
            })
        
        succeeded = sum(1 for r in results if r['success'])
        failed = len(results) - succeeded
        
        return {
            "total": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "results": results
        }
```

**Tests**: `tests/test_agent_file_generator.py` (25 tests)
- Test Claude format generation
- Test Codex format generation (placeholder)
- Test Gemini format generation (placeholder)
- Test file writing
- Test error handling
- Test bulk export

**Acceptance Criteria**:
- ✅ Exports orchestrator template to `.claude/agents/orchestrator.md`
- ✅ YAML frontmatter correctly formatted
- ✅ Template content preserved
- ✅ Variables, rules, criteria appended
- ✅ All 6 existing templates export successfully

**Timeline**: 2 days

---

#### 1.2 Add Export API Endpoint
**File**: `api/endpoints/templates.py`

**Implementation**:
```python
from fastapi import APIRouter, HTTPException, Depends
from api.schemas.template import ExportTemplateRequest, ExportTemplateResponse
from src.giljo_mcp.agent_file_generator import AgentFileGenerator

router = APIRouter(prefix="/api/templates", tags=["templates"])

@router.post("/{template_id}/export", response_model=ExportTemplateResponse)
async def export_template(
    template_id: int,
    request: ExportTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export template to .md file format.
    
    Permissions: Admin only
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Fetch template from database
    template = await db.get(AgentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Multi-tenant isolation
    if template.tenant_key != current_user.tenant_key:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Export to file
    generator = AgentFileGenerator(output_dir=Path(request.output_path))
    result = await generator.export_template_to_file(template, request.format)
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error'))
    
    return ExportTemplateResponse(
        file_path=result['file_path'],
        content=result['content'] if request.include_content else None,
        format=request.format
    )

@router.post("/export-all", response_model=BulkExportResponse)
async def export_all_templates(
    request: BulkExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export all active templates to .md files.
    
    Permissions: Admin only
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Fetch all active templates for tenant
    query = select(AgentTemplate).where(
        AgentTemplate.tenant_key == current_user.tenant_key,
        AgentTemplate.is_active == True
    )
    result = await db.execute(query)
    templates = result.scalars().all()
    
    # Bulk export
    generator = AgentFileGenerator(output_dir=Path(request.output_path))
    export_result = await generator.export_all_templates(templates, request.format)
    
    return BulkExportResponse(**export_result)
```

**Tests**: `tests/test_templates_export_api.py` (15 tests)
- Test single template export
- Test bulk export
- Test authorization (admin only)
- Test multi-tenant isolation
- Test invalid template ID
- Test invalid format
- Test file path validation

**Acceptance Criteria**:
- ✅ `POST /api/templates/:id/export` returns file path and content
- ✅ `POST /api/templates/export-all` exports all templates
- ✅ Admin-only access enforced
- ✅ Multi-tenant isolation verified
- ✅ Error handling comprehensive

**Timeline**: 2 days

---

#### 1.3 Manual Export Test
**Goal**: Validate end-to-end export functionality

**Test Script**: `scripts/test_template_export.py`
```python
"""
Manual test script for template export functionality.

Usage:
    python scripts/test_template_export.py
"""
import asyncio
from pathlib import Path
from sqlalchemy import select
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.agent_file_generator import AgentFileGenerator

async def main():
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Fetch all templates
    async with db_manager.get_session() as session:
        query = select(AgentTemplate).where(AgentTemplate.is_active == True)
        result = await session.execute(query)
        templates = result.scalars().all()
        
        print(f"Found {len(templates)} active templates")
    
    # Export to .claude/agents/
    generator = AgentFileGenerator(output_dir=Path(".claude/agents"))
    export_result = await generator.export_all_templates(templates, format="claude")
    
    print(f"\nExport Results:")
    print(f"  Total: {export_result['total']}")
    print(f"  Succeeded: {export_result['succeeded']}")
    print(f"  Failed: {export_result['failed']}")
    
    for result in export_result['results']:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['template_name']} → {result.get('file_path', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Validation Steps**:
1. Run script: `python scripts/test_template_export.py`
2. Verify 6 files created in `.claude/agents/`
3. Manually inspect each .md file for correct format
4. Test Claude Code can discover agents (restart Claude Code)
5. Create test job using exported agent

**Acceptance Criteria**:
- ✅ 6 .md files created
- ✅ YAML frontmatter valid
- ✅ Content matches database templates
- ✅ Claude Code discovers agents
- ✅ No errors during export

**Timeline**: 1 day

---

**Phase 1 Deliverables**:
- ✅ `AgentFileGenerator` class (production-ready)
- ✅ Export API endpoints (single + bulk)
- ✅ 40+ tests (unit + integration)
- ✅ Manual validation script
- ✅ 6 .md files exported to `.claude/agents/`

**Phase 1 Duration**: 5 days (1 week)

---

## Phase 2: UI for Template Management (Weeks 2-3)

**Goal**: Implement comprehensive web UI for template CRUD operations, building on the design specification.

### Tasks

#### 2.1 Backend: Template CRUD API
**File**: `api/endpoints/templates.py` (expand existing)

**New Endpoints**:
```python
# Already exists (from Phase 1)
GET  /api/templates
GET  /api/templates/:id
POST /api/templates/:id/export

# NEW for Phase 2
POST   /api/templates                    # Create template
PATCH  /api/templates/:id                # Update template
DELETE /api/templates/:id                # Delete template
PATCH  /api/templates/:id/status         # Activate/deactivate
PATCH  /api/templates/:id/default        # Set as default
```

**Implementation**: See `docs/ui/TEMPLATE_MANAGEMENT_UI_DESIGN.md` for complete API specifications

**Tests**: `tests/test_templates_crud_api.py` (30 tests)

**Acceptance Criteria**:
- ✅ All 8 endpoints functional
- ✅ Pydantic schemas validated
- ✅ Multi-tenant isolation enforced
- ✅ Authorization (admin only) enforced

**Timeline**: 3 days

---

#### 2.2 Frontend: Template Store (State Management)
**File**: `frontend/src/stores/templateStore.js`

**Implementation**: See `docs/ui/TEMPLATE_MANAGEMENT_UI_DESIGN.md` - Template Store Module section

**Features**:
- Fetch templates with filtering
- Create/update/delete templates
- Export templates
- Toggle status and default
- Search and pagination

**Tests**: `frontend/tests/unit/templateStore.spec.js` (20 tests)

**Acceptance Criteria**:
- ✅ All store actions working
- ✅ Getters return correct filtered data
- ✅ Error handling comprehensive
- ✅ Loading states managed

**Timeline**: 2 days

---

#### 2.3 Frontend: Template List View
**File**: `frontend/src/views/Templates.vue`

**Implementation**: See `docs/ui/TEMPLATE_MANAGEMENT_UI_DESIGN.md` - Template List View section

**Components Used**:
- TemplateCard.vue (new)
- SearchBar.vue (existing)
- FilterDropdown.vue (existing)
- Pagination.vue (existing)

**Tests**: `frontend/tests/unit/Templates.spec.js` (15 tests)

**Acceptance Criteria**:
- ✅ Display all templates in grid
- ✅ Search filters in real-time
- ✅ Category/status filters work
- ✅ Pagination functional
- ✅ Responsive design (mobile, tablet, desktop)

**Timeline**: 3 days

---

#### 2.4 Frontend: Template Detail View
**File**: `frontend/src/views/TemplateDetail.vue`

**Implementation**: See `docs/ui/TEMPLATE_MANAGEMENT_UI_DESIGN.md` - Template Detail View section

**Tabs**:
- Overview (metadata, tags, status)
- Template Content (markdown preview)
- Variables (list with descriptions)
- Rules (behavioral rules + success criteria)

**Tests**: `frontend/tests/unit/TemplateDetail.spec.js` (12 tests)

**Acceptance Criteria**:
- ✅ All template data displayed
- ✅ Tabs navigate correctly
- ✅ Markdown rendered properly
- ✅ Variables/rules formatted nicely

**Timeline**: 2 days

---

#### 2.5 Frontend: Template Editor (Create/Edit)
**File**: `frontend/src/views/TemplateEditor.vue`

**Implementation**: See `docs/ui/TEMPLATE_MANAGEMENT_UI_DESIGN.md` - Create/Edit Template Form section

**Components Used**:
- MarkdownEditor.vue (new - with syntax highlighting)
- VariableManager.vue (new)
- RulesEditor.vue (new)
- FormValidation.vue (existing)

**Features**:
- Markdown editor with live preview
- Variable management (add/remove)
- Behavioral rules editor
- Success criteria editor
- Auto-save to drafts
- Unsaved changes warning

**Tests**: `frontend/tests/unit/TemplateEditor.spec.js` (25 tests)

**Acceptance Criteria**:
- ✅ Create new templates
- ✅ Edit existing templates
- ✅ Validation errors displayed
- ✅ Auto-save working
- ✅ Unsaved changes warning

**Timeline**: 4 days

---

#### 2.6 Frontend: Export Modal
**File**: `frontend/src/components/templates/ExportModal.vue`

**Implementation**: See `docs/ui/TEMPLATE_MANAGEMENT_UI_DESIGN.md` - Export Template Modal section

**Features**:
- Format selection (Claude/Codex/Gemini)
- Output path customization
- Live preview of generated file
- Download button

**Tests**: `frontend/tests/unit/ExportModal.spec.js` (10 tests)

**Acceptance Criteria**:
- ✅ Export to Claude format
- ✅ Preview accurate
- ✅ Download works
- ✅ Path validation

**Timeline**: 2 days

---

**Phase 2 Deliverables**:
- ✅ Complete Template CRUD API (8 endpoints)
- ✅ Template store (Pinia)
- ✅ 5 Vue components (List, Detail, Editor, Card, Export)
- ✅ 82+ frontend tests
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Accessibility (WCAG 2.1 AA)

**Phase 2 Duration**: 16 days (2-3 weeks)

---

## Phase 3: Auto-Sync on Changes (Week 4)

**Goal**: Automatically export templates to .md files when they are created or updated in the database.

### Tasks

#### 3.1 Database Event Listener
**File**: `src/giljo_mcp/template_sync_service.py`

**Implementation**:
```python
from sqlalchemy import event
from sqlalchemy.orm import Session
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.agent_file_generator import AgentFileGenerator
import asyncio

class TemplateSyncService:
    """Service to auto-sync templates to file system on database changes."""
    
    def __init__(self):
        self.generator = AgentFileGenerator()
        self._register_listeners()
    
    def _register_listeners(self):
        """Register SQLAlchemy event listeners."""
        event.listen(AgentTemplate, 'after_insert', self.on_template_created)
        event.listen(AgentTemplate, 'after_update', self.on_template_updated)
        event.listen(AgentTemplate, 'after_delete', self.on_template_deleted)
    
    def on_template_created(self, mapper, connection, target: AgentTemplate):
        """Auto-export when template created."""
        if target.is_active:
            asyncio.create_task(
                self.generator.export_template_to_file(target, format="claude")
            )
    
    def on_template_updated(self, mapper, connection, target: AgentTemplate):
        """Auto-export when template updated."""
        if target.is_active:
            asyncio.create_task(
                self.generator.export_template_to_file(target, format="claude")
            )
        else:
            # If deactivated, remove file
            self._remove_template_file(target.name)
    
    def on_template_deleted(self, mapper, connection, target: AgentTemplate):
        """Remove file when template deleted."""
        self._remove_template_file(target.name)
    
    def _remove_template_file(self, template_name: str):
        """Remove .md file for template."""
        file_path = self.generator.output_dir / f"{template_name}.md"
        if file_path.exists():
            file_path.unlink()

# Initialize service at app startup
sync_service = TemplateSyncService()
```

**Tests**: `tests/test_template_sync_service.py` (15 tests)

**Acceptance Criteria**:
- ✅ Create template → .md file created
- ✅ Update template → .md file updated
- ✅ Delete template → .md file removed
- ✅ Deactivate template → .md file removed
- ✅ Activate template → .md file created

**Timeline**: 2 days

---

#### 3.2 User Notification System
**File**: `api/websocket.py` (expand existing)

**New WebSocket Event**:
```python
async def broadcast_template_exported(
    self,
    template_id: int,
    template_name: str,
    file_path: str,
    tenant_key: str
):
    """Broadcast template:exported event to users."""
    event = {
        "event_type": "template:exported",
        "data": {
            "template_id": template_id,
            "template_name": template_name,
            "file_path": file_path,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await self.broadcast_to_tenant(tenant_key, event)
```

**Frontend Listener**:
```javascript
// In frontend/src/services/websocket.js
websocket.on('template:exported', (data) => {
  notifications.success(
    `Template "${data.template_name}" exported to ${data.file_path}`
  )
})
```

**Tests**: `tests/integration/test_template_export_notifications.py` (8 tests)

**Acceptance Criteria**:
- ✅ Real-time notification on template export
- ✅ Notification includes file path
- ✅ Scoped to tenant
- ✅ No errors if WebSocket disconnected

**Timeline**: 1 day

---

#### 3.3 Configuration Option: Enable/Disable Auto-Sync
**File**: `config.yaml`

**New Config Section**:
```yaml
templates:
  auto_sync:
    enabled: true  # Enable auto-sync to .claude/agents/
    formats:
      - claude      # Export to Claude Code format
      # - codex     # Future: Export to Codex format
      # - gemini    # Future: Export to Gemini format
    output_paths:
      claude: .claude/agents/
      codex: .codex/agents/
      gemini: .gemini/agents/
```

**Implementation**: Read config in `TemplateSyncService.__init__()`

**Tests**: `tests/test_template_auto_sync_config.py` (10 tests)

**Acceptance Criteria**:
- ✅ Auto-sync respects config setting
- ✅ Can enable/disable per format
- ✅ Custom output paths supported
- ✅ Config changes applied without restart (hot reload)

**Timeline**: 1 day

---

#### 3.4 End-to-End Auto-Sync Test
**Goal**: Validate complete auto-sync workflow

**Test Script**: `scripts/test_auto_sync.py`
```python
"""
E2E test for auto-sync functionality.

Test Flow:
1. Create template via API
2. Verify .md file created in .claude/agents/
3. Update template via API
4. Verify .md file updated
5. Delete template via API
6. Verify .md file removed
"""
import asyncio
import httpx
from pathlib import Path

async def main():
    api_url = "http://localhost:7272"
    token = "YOUR_ADMIN_TOKEN"
    
    # 1. Create template
    print("Creating template...")
    response = await httpx.post(
        f"{api_url}/api/templates",
        json={
            "name": "test-agent",
            "role": "tester",
            "category": "role",
            "template_content": "You are a test agent...",
            "version": "1.0.0"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    template_id = response.json()['id']
    
    # Verify file created
    file_path = Path(".claude/agents/test-agent.md")
    assert file_path.exists(), "File not created"
    print("✅ File created on template creation")
    
    # 2. Update template
    print("Updating template...")
    await httpx.patch(
        f"{api_url}/api/templates/{template_id}",
        json={"description": "Updated description"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify file updated
    content = file_path.read_text()
    assert "Updated description" in content, "File not updated"
    print("✅ File updated on template update")
    
    # 3. Delete template
    print("Deleting template...")
    await httpx.delete(
        f"{api_url}/api/templates/{template_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify file removed
    assert not file_path.exists(), "File not removed"
    print("✅ File removed on template deletion")
    
    print("\n🎉 Auto-sync test passed!")

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance Criteria**:
- ✅ Create → File created within 1 second
- ✅ Update → File updated within 1 second
- ✅ Delete → File removed within 1 second
- ✅ No errors in logs

**Timeline**: 1 day

---

**Phase 3 Deliverables**:
- ✅ `TemplateSyncService` with SQLAlchemy event listeners
- ✅ Real-time WebSocket notifications
- ✅ Auto-sync configuration options
- ✅ E2E validation script
- ✅ 33+ tests (unit + integration + E2E)

**Phase 3 Duration**: 5 days (1 week)

---

## Phase 4: Multi-Tool Support (Weeks 5-6)

**Goal**: Extend export functionality to support Codex and Gemini agent formats.

### Tasks

#### 4.1 Research Codex Agent Format
**Deliverable**: `docs/research/CODEX_AGENT_FORMAT.md`

**Research Questions**:
- What file format does Codex use for agents?
- Does Codex support YAML frontmatter or alternative metadata format?
- How does Codex discover agents (directory, config file)?
- What agent properties are required/optional?
- Are there examples or templates available?

**Research Methods**:
- Review Codex documentation
- Inspect Codex installation directories
- Contact Codex support if needed
- Review community examples

**Timeline**: 2 days

---

#### 4.2 Research Gemini Agent Format
**Deliverable**: `docs/research/GEMINI_AGENT_FORMAT.md`

**Research Questions**:
- Does Gemini support sub-agents or agent-like constructs?
- What file format does Gemini use?
- How does Gemini discover and load agents?
- What metadata is required?

**Research Methods**:
- Review Gemini API documentation
- Test Gemini CLI/SDK for agent support
- Contact Google support if needed
- Review community examples

**Timeline**: 2 days

---

#### 4.3 Implement Codex Exporter
**File**: `src/giljo_mcp/agent_file_generator.py` (expand `_export_codex_format()`)

**Implementation** (example - adjust based on research):
```python
def _export_codex_format(self, template: AgentTemplate) -> str:
    """Generate Codex agent format."""
    # Assuming Codex uses JSON format with specific schema
    codex_schema = {
        "agent_name": template.name,
        "agent_role": template.role,
        "version": template.version,
        "description": template.description,
        "instructions": template.template_content,
        "variables": {
            var: {"required": True, "description": ""}
            for var in template.variables
        },
        "behavioral_rules": template.behavioral_rules,
        "success_criteria": template.success_criteria
    }
    
    return json.dumps(codex_schema, indent=2)
```

**Tests**: `tests/test_codex_export.py` (15 tests)

**Acceptance Criteria**:
- ✅ Exports to Codex format
- ✅ Codex can discover and use agents
- ✅ All template properties mapped correctly

**Timeline**: 3 days

---

#### 4.4 Implement Gemini Exporter
**File**: `src/giljo_mcp/agent_file_generator.py` (expand `_export_gemini_format()`)

**Implementation**: Based on Phase 4.2 research results

**Tests**: `tests/test_gemini_export.py` (15 tests)

**Acceptance Criteria**:
- ✅ Exports to Gemini format
- ✅ Gemini can discover and use agents
- ✅ All template properties mapped correctly

**Timeline**: 3 days

---

#### 4.5 UI: Multi-Format Export
**File**: `frontend/src/components/templates/ExportModal.vue` (update)

**Changes**:
- Add format dropdown with Claude/Codex/Gemini options
- Show format-specific preview
- Update output path based on format
- Add "Export to All Formats" button

**Tests**: `frontend/tests/unit/ExportModal.spec.js` (update)

**Acceptance Criteria**:
- ✅ Can export to Claude, Codex, Gemini
- ✅ Preview updates based on format
- ✅ Bulk export to all formats works

**Timeline**: 2 days

---

#### 4.6 End-to-End Multi-Tool Test
**Goal**: Validate agents work in Claude Code, Codex, and Gemini

**Test Script**: `scripts/test_multi_tool_export.py`
```python
"""
Test template export to multiple coding tools.

Steps:
1. Export orchestrator template to Claude format
2. Restart Claude Code, verify agent discovered
3. Export same template to Codex format
4. Verify Codex discovers agent
5. Export same template to Gemini format
6. Verify Gemini discovers agent
"""
# Implementation based on tool-specific discovery mechanisms
```

**Manual Validation**:
1. Export to all formats
2. Verify files created in correct directories
3. Restart each tool (Claude Code, Codex, Gemini)
4. Create test task using agent in each tool
5. Verify agent behavior matches template

**Acceptance Criteria**:
- ✅ Claude Code discovers agent
- ✅ Codex discovers agent
- ✅ Gemini discovers agent (if supported)
- ✅ All agents behave according to template

**Timeline**: 2 days

---

**Phase 4 Deliverables**:
- ✅ Codex agent format research document
- ✅ Gemini agent format research document
- ✅ Codex exporter implementation
- ✅ Gemini exporter implementation
- ✅ Multi-format UI support
- ✅ E2E multi-tool validation
- ✅ 30+ tests (Codex + Gemini)

**Phase 4 Duration**: 14 days (2 weeks)

---

## Phase 5: Runtime Agent Discovery (Future - Optional)

**Goal**: Enable dynamic agent registration without tool restarts.

**Status**: Research phase - pending investigation

### Research Topics

#### 5.1 Claude Code Runtime Loading
**Questions**:
- Can Claude Code hot-reload agents without restart?
- Does Claude Code API support dynamic agent registration?
- Can file watchers trigger agent discovery?

**Investigation Methods**:
- Test manual agent file changes during runtime
- Review Claude Code API documentation
- Contact Anthropic support
- Review MCP protocol for agent registration

---

#### 5.2 MCP Dynamic Registration
**Questions**:
- Does MCP support dynamic resource exposure?
- Can agents be registered via MCP tools?
- What are the performance implications?

**Investigation Methods**:
- Review MCP SDK documentation
- Test MCP resource registration
- Benchmark performance

---

#### 5.3 Agent SDK Integration
**Questions**:
- Can Anthropic Agent SDK programmatically register agents?
- What are the authentication requirements?
- Can this work with self-hosted deployments?

**Investigation Methods**:
- Review Agent SDK documentation
- Test programmatic agent creation
- Evaluate security implications

---

**Phase 5 Status**: ON HOLD - Awaiting Phase 1-4 completion and further research

---

## Success Criteria (Overall Project)

### Functional Requirements
- ✅ Database is single source of truth for templates
- ✅ Templates auto-export to `.claude/agents/*.md` on save
- ✅ Web UI allows full CRUD operations on templates
- ✅ Export supports Claude Code, Codex, Gemini formats
- ✅ Multi-tenant isolation enforced throughout
- ✅ Authorization (admin-only) enforced
- ✅ Real-time notifications on template changes

### Non-Functional Requirements
- ✅ Code quality: Production-grade (Chef's kiss standard)
- ✅ Test coverage: ≥85% for core components
- ✅ Performance: Export completes in <2 seconds
- ✅ Accessibility: WCAG 2.1 AA compliance
- ✅ Responsive: Mobile, tablet, desktop support
- ✅ Documentation: Complete user and developer docs

### User Experience
- ✅ Template creation takes <2 minutes
- ✅ Export to all formats takes <5 seconds
- ✅ UI is intuitive (no training required)
- ✅ Error messages are clear and actionable
- ✅ Real-time feedback on all actions

---

## Risk Assessment & Mitigation

### Risk 1: Codex/Gemini Agent Format Unknown
**Probability**: Medium
**Impact**: High (blocks Phase 4)

**Mitigation**:
- Front-load research (Phase 4.1, 4.2)
- Contact vendor support early
- Fallback: Use Claude format as universal interim
- Document limitations clearly

---

### Risk 2: Claude Code Cannot Hot-Reload Agents
**Probability**: High
**Impact**: Medium (Phase 5 blocked)

**Mitigation**:
- Document current limitation
- Implement file watcher + auto-restart script
- Investigate MCP alternatives
- Phase 5 remains optional

---

### Risk 3: Performance Issues with Large Template Libraries
**Probability**: Low
**Impact**: Medium

**Mitigation**:
- Implement pagination (limit 20 templates per page)
- Use virtual scrolling for large lists
- Cache exported files (don't re-generate on every request)
- Benchmark with 100+ templates

---

### Risk 4: Multi-Tenant Security Breach
**Probability**: Low
**Impact**: Critical

**Mitigation**:
- 100% test coverage for multi-tenant isolation
- Security audit before production deployment
- Penetration testing on template CRUD APIs
- Regular security reviews

---

## Testing Strategy

### Unit Tests (Target: 90% coverage)
- `AgentFileGenerator`: 25 tests
- `TemplateSyncService`: 15 tests
- API endpoints: 45 tests
- Vue components: 82 tests
- **Total**: 167 unit tests

### Integration Tests (Target: 100% of workflows)
- Template CRUD workflow: 10 tests
- Auto-sync workflow: 8 tests
- Export workflow: 12 tests
- WebSocket notifications: 6 tests
- **Total**: 36 integration tests

### E2E Tests (Critical paths)
- Create template → Export → Use in Claude: 1 test
- Update template → Auto-sync → Verify file: 1 test
- Delete template → File removed: 1 test
- Bulk export to all formats: 1 test
- **Total**: 4 E2E tests

### Manual Testing
- Cross-browser testing (Chrome, Firefox, Safari, Edge)
- Mobile testing (iOS, Android)
- Accessibility testing (screen readers, keyboard navigation)
- Performance testing (100+ templates)

---

## Documentation Deliverables

### User Documentation
1. **Template Management Guide** (`docs/user/TEMPLATE_MANAGEMENT_GUIDE.md`)
   - How to create templates
   - How to edit templates
   - How to export templates
   - Best practices

2. **Multi-Tool Integration Guide** (`docs/user/MULTI_TOOL_INTEGRATION.md`)
   - Setting up Claude Code
   - Setting up Codex
   - Setting up Gemini
   - Troubleshooting

### Developer Documentation
1. **Template System Architecture** (`docs/dev/TEMPLATE_SYSTEM_ARCHITECTURE.md`)
   - System design
   - Database schema
   - API specifications
   - Component diagrams

2. **API Reference** (`docs/api/TEMPLATES_API_REFERENCE.md`)
   - All endpoint specifications
   - Request/response examples
   - Error codes
   - Authentication

3. **Testing Guide** (`docs/testing/TEMPLATE_SYSTEM_TESTING.md`)
   - How to run tests
   - How to add new tests
   - Coverage reports
   - CI/CD integration

---

## Timeline Summary

| Phase | Duration | Start | End | Deliverables |
|-------|----------|-------|-----|--------------|
| Phase 1: Database to File Export | 1 week | Week 1 | Week 1 | AgentFileGenerator, Export API, Tests |
| Phase 2: UI for Template Management | 2-3 weeks | Week 2 | Week 3-4 | Complete CRUD UI, 82 tests |
| Phase 3: Auto-Sync on Changes | 1 week | Week 4 | Week 4 | Sync service, WebSocket, Config |
| Phase 4: Multi-Tool Support | 2 weeks | Week 5 | Week 6 | Codex/Gemini exporters, Multi-format UI |
| **Total** | **6 weeks** | | | **Full system operational** |

---

## Resource Requirements

### Development Team
- **Backend Developer**: 1 FTE (Phases 1, 3, 4)
- **Frontend Developer**: 1 FTE (Phase 2)
- **QA Engineer**: 0.5 FTE (All phases - testing)
- **Technical Writer**: 0.25 FTE (Documentation)

### Infrastructure
- **PostgreSQL Database**: Existing (no changes)
- **File Storage**: `.claude/agents/`, `.codex/agents/`, `.gemini/agents/`
- **CI/CD**: GitHub Actions for automated testing
- **Deployment**: Existing GiljoAI MCP infrastructure

---

## Deployment Plan

### Week 1 (Phase 1 Complete)
- Deploy `AgentFileGenerator` to production
- Enable manual export via API
- Monitor export success rate
- Collect user feedback

### Week 4 (Phase 2 Complete)
- Deploy Template Management UI
- Enable template CRUD operations
- Train admins on new features
- Monitor usage metrics

### Week 4 (Phase 3 Complete)
- Enable auto-sync feature
- Monitor file system performance
- Verify WebSocket notifications
- Collect user feedback

### Week 6 (Phase 4 Complete)
- Deploy multi-tool support
- Create integration tutorials
- Monitor export success for all formats
- Final validation with all coding tools

---

## Conclusion

This roadmap provides a comprehensive, phased approach to implementing a production-grade agent template management system. By following Chef's Kiss quality standards and leveraging specialized subagents where appropriate, we will deliver a robust solution that bridges the gap between our database-driven templates and file-based agent configurations required by Claude Code, Codex, and Gemini.

**Key Success Factors**:
- ✅ Phased approach allows incremental value delivery
- ✅ Database remains single source of truth
- ✅ Auto-sync ensures file system always in sync
- ✅ Multi-tool support enables broad integration
- ✅ Comprehensive testing ensures production readiness

**Next Steps**:
1. Review and approve roadmap
2. Assign resources for Phase 1
3. Begin implementation Week 1
4. Provide regular progress updates

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-19
**Author**: AI Architecture Team
**Status**: Awaiting approval for implementation
**Estimated Completion**: 6 weeks from start date
