# Agent Template Integration Architecture - Discussion Document

**Date**: 2025-10-19
**Topic**: Reconciling Database-Driven Templates with File-Based Agent Configurations
**Participants**: User, Claude
**Status**: Design Discussion

---

## Executive Summary

We have identified a **critical architectural gap** between:
1. **Our System**: Database-driven agent templates (embedded in application)
2. **Claude Code/Codex/Gemini**: File-based agent configurations (`.claude/agents/*.md`)

This document explores solutions to bridge this gap and enable seamless integration.

---

## Current State Analysis

### 1. Our Agent Template System

**Location**: `src/giljo_mcp/template_manager.py`

**Architecture**:
```
Database (agent_templates table)
    ↓
UnifiedTemplateManager (_legacy_templates dict)
    ↓
API (GET /api/templates)
    ↓
Frontend UI (template management)
    ↓
Orchestrator spawns agents with templates
```

**Templates Stored**:
- 6 hardcoded templates (orchestrator, analyzer, implementer, tester, reviewer, documenter)
- Embedded in Python code as strings
- Stored in PostgreSQL `agent_templates` table
- Managed via UI (planned)

**Problems**:
- ❌ Templates NOT accessible to Claude Code/Codex/Gemini
- ❌ Changes in UI don't propagate to coding tools
- ❌ No file-based representation for external tools
- ❌ Restart required to load new agents in Claude Code

---

### 2. Claude Code Agent Configuration

**Location**: `.claude/agents/*.md`

**Current Agents** (12 found):
```
.claude/agents/
├── backend-integration-tester.md
├── database-expert.md
├── deep-researcher.md
├── documentation-manager.md
├── frontend-tester.md
├── installation-flow-agent.md
├── network-security-engineer.md
├── orchestrator-coordinator.md
├── system-architect.md
├── tdd-implementor.md
├── ux-designer.md
└── version-manager.md
```

**File Format** (Markdown with YAML frontmatter):
```markdown
---
name: agent-name
description: "Agent description"
model: sonnet
color: green
---

Agent instructions and behavior...
```

**Problems**:
- ❌ Manually created files, not synced with our database
- ❌ No UI for management
- ❌ Changes require manual file editing
- ❌ No versioning or history
- ❌ Restart required to discover new agents

---

## Vision: Unified Agent Management System

### User Experience Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User manages templates in GiljoAI MCP Web UI            │
│    - Create/edit/delete agent templates                     │
│    - Version control                                         │
│    - Test templates                                          │
│    - Publish to database                                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Templates indexed in PostgreSQL database                 │
│    - agent_templates table                                   │
│    - Full metadata (version, tags, behavioral_rules)         │
│    - Searchable and queryable                                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Orchestrator selects agent for mission                   │
│    - Query database for available agents                     │
│    - Match agent type to mission requirements                │
│    - Load template with variable substitution                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Template exported to .claude/agents/*.md                 │
│    - Auto-generate .md file with proper syntax               │
│    - YAML frontmatter + markdown body                        │
│    - Sync to .claude/agents/ directory                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Claude Code/Codex/Gemini discovers agent                 │
│    - File-based discovery (currently requires restart)       │
│    - Agent available for task execution                      │
│    - MCP integration for dynamic loading (future)            │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Deep Dive

### Problem 1: Database vs File System

**Current Mismatch**:
- **Database**: Single source of truth for templates
- **File System**: Required by Claude Code for agent discovery
- **No Sync**: Changes in one don't reflect in the other

**Solution Options**:

#### Option A: Bi-directional Sync (File ↔ Database)
```python
class AgentTemplateSyncManager:
    """Syncs agent templates between database and file system."""

    async def sync_db_to_files(self, tenant_key: str):
        """Export database templates to .claude/agents/*.md"""
        templates = await self.get_all_templates(tenant_key)

        for template in templates:
            md_content = self._generate_markdown(template)
            file_path = Path(f".claude/agents/{template.name}.md")
            file_path.write_text(md_content)

    async def sync_files_to_db(self, tenant_key: str):
        """Import .claude/agents/*.md to database"""
        agent_files = Path(".claude/agents").glob("*.md")

        for file_path in agent_files:
            template = self._parse_markdown(file_path.read_text())
            await self.upsert_template(tenant_key, template)

    def _generate_markdown(self, template: AgentTemplate) -> str:
        """Convert database template to .md format"""
        return f"""---
name: {template.name}
description: "{template.description}"
model: {template.preferred_tool or 'sonnet'}
color: blue
---

{template.template_content}
"""

    def _parse_markdown(self, content: str) -> dict:
        """Parse .md file into template dict"""
        # Split YAML frontmatter from body
        # Extract name, description, model, color
        # Return dict for database insertion
```

**Pros**:
- ✅ Both systems stay synchronized
- ✅ Users can edit in UI or files
- ✅ Changes propagate automatically

**Cons**:
- ❌ Conflict resolution needed
- ❌ Sync timing issues
- ❌ Complex error handling

---

#### Option B: Database Primary, Files Generated (Recommended)
```python
class AgentFileGenerator:
    """Generate .claude/agents/*.md files from database templates."""

    async def export_template_to_file(
        self,
        template: AgentTemplate,
        output_dir: Path = Path(".claude/agents")
    ):
        """Export single template to .md file"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate markdown content
        md_content = self._template_to_markdown(template)

        # Write to file
        file_path = output_dir / f"{template.name}.md"
        file_path.write_text(md_content, encoding='utf-8')

        logger.info(f"Exported template: {template.name} → {file_path}")

    async def export_all_templates(
        self,
        tenant_key: str,
        tool: str = "claude"  # claude, codex, gemini
    ):
        """Export all active templates for tenant"""
        templates = await self.template_repo.get_active_templates(tenant_key)

        for template in templates:
            if tool == "claude":
                await self.export_template_to_file(template)
            elif tool == "codex":
                await self.export_to_codex_format(template)
            elif tool == "gemini":
                await self.export_to_gemini_format(template)

    def _template_to_markdown(self, template: AgentTemplate) -> str:
        """Convert AgentTemplate to Claude Code .md format"""
        # Map our fields to Claude Code frontmatter
        frontmatter = {
            "name": template.name,
            "description": template.description or "",
            "model": template.preferred_tool or "sonnet",
            "color": self._get_agent_color(template.role)
        }

        # Build YAML frontmatter
        yaml_section = "---\n"
        for key, value in frontmatter.items():
            yaml_section += f"{key}: \"{value}\"\n" if isinstance(value, str) else f"{key}: {value}\n"
        yaml_section += "---\n\n"

        # Add template content
        body = template.template_content

        # Add behavioral rules as checklist (if any)
        if template.behavioral_rules:
            body += "\n\n## Behavioral Rules\n\n"
            for rule in template.behavioral_rules:
                body += f"- {rule}\n"

        # Add success criteria (if any)
        if template.success_criteria:
            body += "\n\n## Success Criteria\n\n"
            for criterion in template.success_criteria:
                body += f"- [ ] {criterion}\n"

        return yaml_section + body

    def _get_agent_color(self, role: str) -> str:
        """Map agent role to color"""
        colors = {
            "orchestrator": "purple",
            "analyzer": "blue",
            "implementer": "green",
            "tester": "orange",
            "reviewer": "red",
            "documenter": "yellow"
        }
        return colors.get(role, "gray")
```

**Pros**:
- ✅ Single source of truth (database)
- ✅ No sync conflicts
- ✅ Version control in database
- ✅ UI-driven management
- ✅ Export to multiple formats (Claude, Codex, Gemini)

**Cons**:
- ❌ File edits overwritten on next export
- ❌ Still requires restart for Claude Code

---

### Problem 2: Runtime Agent Discovery

**Current Limitation**: Claude Code requires restart to discover new agents

**Investigation Needed**:
1. Does Claude Code support **hot reload** of agents?
2. Can we use **MCP (Model Context Protocol)** for dynamic loading?
3. Are there **Claude Code API hooks** for agent registration?

**Potential Solutions**:

#### Option A: File Watcher + Auto-Restart
```python
import watchdog.observers
import watchdog.events

class AgentFileWatcher(watchdog.events.FileSystemEventHandler):
    """Watch .claude/agents/ and restart Claude Code on changes"""

    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            logger.info(f"Agent file modified: {event.src_path}")
            self.notify_claude_code_restart()

    def notify_claude_code_restart(self):
        # Send signal to Claude Code process
        # OR display notification to user
        # OR trigger auto-restart (if API available)
        pass
```

**Pros**:
- ✅ Automatic detection
- ✅ User doesn't manually restart

**Cons**:
- ❌ Still requires restart
- ❌ May interrupt user workflow

---

#### Option B: MCP Dynamic Agent Registration (Future)
```python
class MCPAgentRegistrar:
    """Use MCP to dynamically register agents without restart"""

    async def register_agent(self, template: AgentTemplate):
        """Register agent via MCP protocol"""
        # Use MCP server to push agent definition
        # Claude Code listens for agent registration events
        # Agent becomes available immediately

        await self.mcp_server.register_resource(
            uri=f"agent://{template.name}",
            name=template.name,
            description=template.description,
            mimeType="text/markdown",
            content=self._template_to_markdown(template)
        )
```

**Pros**:
- ✅ No restart required
- ✅ Instant agent availability
- ✅ MCP is Anthropic's protocol

**Cons**:
- ❌ Requires MCP support in Claude Code (unknown if available)
- ❌ May not exist yet

---

### Problem 3: Multi-Tool Support (Claude, Codex, Gemini)

**Challenge**: Each coding tool has different agent configuration formats

**Current Knowledge**:
- **Claude Code**: `.claude/agents/*.md` with YAML frontmatter
- **Codex**: Unknown format (need research)
- **Gemini**: Unknown format (need research)

**Solution: Abstract Export Layer**
```python
class AgentExporter:
    """Export templates to multiple coding tool formats"""

    def export(
        self,
        template: AgentTemplate,
        format: str  # "claude", "codex", "gemini"
    ) -> str:
        exporters = {
            "claude": self._export_claude,
            "codex": self._export_codex,
            "gemini": self._export_gemini
        }

        return exporters[format](template)

    def _export_claude(self, template: AgentTemplate) -> str:
        """Export to Claude Code .md format"""
        # YAML frontmatter + markdown body
        return f"""---
name: {template.name}
description: "{template.description}"
model: sonnet
---

{template.template_content}
"""

    def _export_codex(self, template: AgentTemplate) -> str:
        """Export to GitHub Codex format"""
        # Research needed: What format does Codex use?
        # Possibly .codex/agents/*.json or similar
        pass

    def _export_gemini(self, template: AgentTemplate) -> str:
        """Export to Gemini format"""
        # Research needed: What format does Gemini use?
        pass
```

---

## Proposed Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────┐
│                    GiljoAI MCP Web UI                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Template Management Dashboard                         │  │
│  │  - Create/Edit/Delete templates                        │  │
│  │  - Version control                                      │  │
│  │  - Test templates                                       │  │
│  │  - Export to coding tools                               │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              PostgreSQL (agent_templates table)              │
│  - Single source of truth                                    │
│  - Versioning and history                                    │
│  - Multi-tenant isolation                                    │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│               AgentFileGenerator Service                      │
│  - Export templates to file system                           │
│  - Multi-format support (Claude, Codex, Gemini)             │
│  - Auto-sync on template changes                             │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    File System                                │
│  .claude/agents/*.md     (Claude Code)                       │
│  .codex/agents/*.json    (GitHub Codex)                      │
│  .gemini/agents/*.yaml   (Google Gemini)                     │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              Coding Tools (Claude/Codex/Gemini)              │
│  - Discover agents via file system                           │
│  - Execute missions with agent templates                     │
│  - Report results back to GiljoAI MCP                        │
└──────────────────────────────────────────────────────────────┘
```

---

### Implementation Plan

#### Phase 1: Database to File Export (Week 1)
**Goal**: Export database templates to Claude Code format

**Tasks**:
1. ✅ Create `AgentFileGenerator` class
2. ✅ Implement `_template_to_markdown()` method
3. ✅ Add export endpoint: `POST /api/templates/export`
4. ✅ Test with existing 6 templates
5. ✅ Verify Claude Code can discover exported agents

**Deliverables**:
- `src/giljo_mcp/agent_file_generator.py`
- API endpoint for export
- Tests

---

#### Phase 2: UI for Template Management (Week 2-3)
**Goal**: Build web UI for template CRUD

**Tasks**:
1. Create Vue component: `TemplateManager.vue`
2. Add routes: `/admin/templates`
3. Features:
   - List all templates
   - Create new template
   - Edit existing template
   - Delete template
   - Preview template
   - Export to file
4. Integrate with backend API

**Deliverables**:
- `frontend/src/views/admin/TemplateManager.vue`
- `frontend/src/components/templates/` components
- API integration

---

#### Phase 3: Auto-Sync on Changes (Week 4)
**Goal**: Automatically export templates when changed

**Tasks**:
1. Add database trigger on `agent_templates` table
2. Create background worker for file generation
3. Implement file watcher (optional)
4. Add notification system

**Deliverables**:
- Auto-sync service
- Database triggers
- User notifications

---

#### Phase 4: Multi-Tool Support (Week 5-6)
**Goal**: Support Codex and Gemini

**Research Tasks**:
1. Investigate Codex agent configuration format
2. Investigate Gemini agent configuration format
3. Map our schema to their formats

**Implementation**:
1. Add `_export_codex()` method
2. Add `_export_gemini()` method
3. Test with Codex and Gemini tools

**Deliverables**:
- Multi-format export
- Documentation for each tool

---

#### Phase 5: Runtime Agent Discovery (Future)
**Goal**: Dynamic agent registration without restart

**Research**:
1. Claude Code API documentation
2. MCP protocol for agent registration
3. Alternative approaches

**Implementation**:
- TBD based on research findings

---

## Open Questions & Research Needed

### 1. Claude Code Agent System

**Questions**:
- ❓ Can agents be registered at runtime without restart?
- ❓ Is there a Claude Code API for agent management?
- ❓ Can MCP be used for dynamic agent registration?
- ❓ What happens if `.claude/agents/*.md` changes while running?

**Research Actions**:
- [ ] Review Claude Code documentation (blocked - auth error)
- [ ] Test manual agent file changes during runtime
- [ ] Investigate MCP capabilities for agent registration
- [ ] Contact Anthropic support for clarification

---

### 2. GitHub Codex Agent System

**Questions**:
- ❓ What format does Codex use for agents?
- ❓ Where are agent configurations stored?
- ❓ Can agents be added dynamically?
- ❓ Is there an API for agent management?

**Research Actions**:
- [ ] Review Codex documentation
- [ ] Inspect Codex configuration directory
- [ ] Test agent creation workflow
- [ ] Map our schema to Codex format

---

### 3. Google Gemini Agent System

**Questions**:
- ❓ Does Gemini support sub-agents?
- ❓ What format for agent configurations?
- ❓ Integration with our system possible?

**Research Actions**:
- [ ] Review Gemini Code Assist documentation
- [ ] Test agent capabilities
- [ ] Determine compatibility

---

## SDK Integration Opportunities

### Potential SDKs to Leverage

#### 1. Anthropic Agent SDK
**URL**: https://docs.claude.com/en/api/agent-sdk/subagents

**Capabilities** (need verification):
- Programmatic agent creation
- Agent lifecycle management
- Message passing between agents
- Context sharing

**Integration Opportunity**:
```python
from anthropic_agent_sdk import AgentManager

class GiljoAIMCPIntegration:
    """Integrate GiljoAI MCP with Anthropic Agent SDK"""

    async def deploy_agent(self, template: AgentTemplate):
        """Deploy template as Anthropic agent"""
        agent = await AgentManager.create_agent(
            name=template.name,
            instructions=template.template_content,
            model=template.preferred_tool or "claude-3-5-sonnet-20241022",
            tools=self._get_tools_for_role(template.role)
        )

        return agent.id
```

---

#### 2. MCP (Model Context Protocol) SDK
**What**: Anthropic's protocol for context sharing

**Integration Opportunity**:
```python
from mcp import Server, Resource

class AgentTemplateServer(Server):
    """MCP server exposing agent templates as resources"""

    async def list_resources(self):
        """Expose templates as MCP resources"""
        templates = await self.db.get_all_templates()

        return [
            Resource(
                uri=f"agent://{t.name}",
                name=t.name,
                description=t.description,
                mimeType="text/markdown"
            )
            for t in templates
        ]

    async def read_resource(self, uri: str):
        """Return template content"""
        name = uri.split("://")[1]
        template = await self.db.get_template_by_name(name)
        return self._template_to_markdown(template)
```

**Benefits**:
- ✅ Standard protocol (Anthropic-supported)
- ✅ Dynamic resource exposure
- ✅ No file system needed
- ✅ Real-time updates

---

## Web-Based Terminal Integration

### Concept: Embedded Claude Code Terminal

**Vision**: Instead of separate terminal, embed Claude Code interface in our web UI

```
┌────────────────────────────────────────────────────────┐
│  GiljoAI MCP Dashboard                                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Mission Control                                 │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Embedded Claude Code Terminal                   │  │
│  │  > User: Implement feature X                     │  │
│  │  > Orchestrator: Spawning implementer agent...   │  │
│  │  > Implementer: Working on task...               │  │
│  │  > Implementer: Completed ✓                      │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

**Technologies**:

#### Option A: Xterm.js + WebSocket
```javascript
// Frontend (Vue)
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'

export default {
  mounted() {
    const term = new Terminal()
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(this.$refs.terminal)

    // Connect to backend WebSocket
    const ws = new WebSocket('ws://localhost:7272/ws/terminal')

    ws.onmessage = (event) => {
      term.write(event.data)
    }

    term.onData((data) => {
      ws.send(data)
    })
  }
}
```

```python
# Backend (FastAPI)
@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()

    # Create PTY (pseudo-terminal)
    import pty
    import os

    master, slave = pty.openpty()

    # Spawn Claude Code process
    process = subprocess.Popen(
        ["claude", "code"],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=os.environ
    )

    # Relay terminal I/O
    while True:
        data = await websocket.receive_text()
        os.write(master, data.encode())

        output = os.read(master, 1024)
        await websocket.send_text(output.decode())
```

**Pros**:
- ✅ Unified interface (no separate terminal)
- ✅ Session persistence
- ✅ Multi-user support
- ✅ Terminal recording/playback

**Cons**:
- ❌ Complex implementation
- ❌ PTY handling challenges
- ❌ Security concerns (terminal access)

---

#### Option B: Claude Code CLI Integration (Simpler)
```python
class ClaudeCodeCLI:
    """Wrapper for Claude Code CLI"""

    async def run_mission(
        self,
        mission: str,
        agent: str,
        callback: callable
    ):
        """Run mission via Claude Code CLI"""
        process = await asyncio.create_subprocess_exec(
            "claude", "code",
            "--agent", agent,
            "--prompt", mission,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Stream output to WebSocket
        async for line in process.stdout:
            await callback(line.decode())

        await process.wait()
```

**Pros**:
- ✅ Simpler implementation
- ✅ Uses official CLI
- ✅ Less security risk

**Cons**:
- ❌ Limited interactivity
- ❌ No real terminal feel

---

## Recommended Next Steps

### Immediate Actions (This Week)

1. **Research Claude Code Capabilities**
   - [ ] Test manual agent file changes during runtime
   - [ ] Investigate if Claude Code can hot-reload agents
   - [ ] Review MCP documentation for agent registration
   - [ ] Contact Anthropic support if needed

2. **Implement Database → File Export**
   - [ ] Create `AgentFileGenerator` class
   - [ ] Implement Claude Code .md export
   - [ ] Add API endpoint: `POST /api/templates/export`
   - [ ] Test with existing templates

3. **Design Template Management UI**
   - [ ] Wireframe template manager screen
   - [ ] Design CRUD operations
   - [ ] Plan export workflow
   - [ ] User approval on design

### Short-Term (Next 2 Weeks)

1. **Build Template Management UI**
   - [ ] Implement Vue components
   - [ ] API integration
   - [ ] Testing

2. **Implement Auto-Sync**
   - [ ] Database triggers
   - [ ] Background export service
   - [ ] User notifications

### Medium-Term (Next Month)

1. **Multi-Tool Support**
   - [ ] Research Codex format
   - [ ] Research Gemini format
   - [ ] Implement exporters

2. **SDK Integration**
   - [ ] Explore Anthropic Agent SDK
   - [ ] MCP server for templates
   - [ ] Test dynamic registration

### Long-Term (Future)

1. **Web Terminal Integration**
   - [ ] Evaluate xterm.js
   - [ ] Prototype embedded terminal
   - [ ] Security review

2. **Advanced Features**
   - [ ] Template versioning UI
   - [ ] Template marketplace
   - [ ] Community templates

---

## Decision Points

### Decision 1: Sync Strategy

**Options**:
- A) Bi-directional sync (Database ↔ Files)
- B) Database primary, files generated (Recommended)
- C) Files primary, database cache

**Recommendation**: **Option B** - Database primary
- Single source of truth
- UI-driven workflow
- No conflict resolution needed
- Version control in database

**User Decision Needed**: ❓ Approve Option B?

---

### Decision 2: Export Trigger

**Options**:
- A) Manual export (user clicks "Export")
- B) Auto-export on template save
- C) Scheduled export (every N minutes)
- D) Hybrid (auto + manual)

**Recommendation**: **Option D** - Hybrid
- Auto-export on save (convenience)
- Manual export button (user control)
- Background sync every 5 minutes (safety)

**User Decision Needed**: ❓ Approve hybrid approach?

---

### Decision 3: Multi-Tool Priority

**Options**:
- A) Claude Code only (simplest)
- B) Claude + Codex
- C) Claude + Codex + Gemini (full support)

**Recommendation**: **Phase approach**
- Phase 1: Claude Code (immediate)
- Phase 2: Codex (after research)
- Phase 3: Gemini (future)

**User Decision Needed**: ❓ Approve phased approach?

---

## Conclusion

We have a clear path forward to reconcile our database-driven template system with file-based agent configurations:

1. **Database remains single source of truth**
2. **Auto-generate .md files for Claude Code**
3. **Build UI for template management**
4. **Research and support additional tools (Codex, Gemini)**
5. **Explore MCP for dynamic agent registration**
6. **Consider web terminal integration long-term**

**Next Step**: User approval on recommended architecture and immediate action items.

---

**Status**: Awaiting user feedback and decisions
**Last Updated**: 2025-10-19
