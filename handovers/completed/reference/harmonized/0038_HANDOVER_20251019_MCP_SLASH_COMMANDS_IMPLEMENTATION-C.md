# Handover 0038: MCP Slash Commands Implementation

**Handover ID**: 0038
**Creation Date**: 2025-10-19
**Target Date**: 2025-10-22 (3-day timeline)
**Priority**: HIGH
**Type**: FEATURE IMPLEMENTATION
**Estimated Complexity**: 16-22 hours
**Status**: NOT STARTED
**Dependencies**: Handover 0037 (Readiness Assessment - APPROVED)

---

## 1. Context and Background

### Vision

Enable **automated agent workflow setup** via MCP slash commands, eliminating manual file management and multi-step copy/paste workflows.

### Current Workflow (Manual - 12+ steps)

```
1. User creates project in web UI
2. User clicks "Download Agents"
3. User downloads agents.zip
4. User extracts to ~/.claude/agents/
5. User restarts Claude Code
6. User copies orchestrator prompt from UI
7. User pastes into Claude Code
8. User waits for mission plan
9. User copies agent prompts (one per agent)
10. User opens 4-5 terminal windows
11. User pastes each agent prompt
12. Agents start working
```

**Pain Points:** 12 manual steps, 5 copy/paste operations, multiple terminal windows

### Target Workflow (Automated - 3 commands)

```
1. User: /mcp__gil__fetch_agents
   → Claude installs agents → Restart once

2. User: /mcp__gil__activate_project ABC123
   → Claude creates mission, selects agents, stages templates

3. User: /mcp__gil__launch_project ABC123
   → Claude spawns subagents, begins orchestration ✅
```

**Benefits:** 3 commands, 0 copy/paste, 0 terminal management, 1 restart

---

## 2. Implementation Scope

### Features to Implement

| Feature | Commands | Complexity | Priority |
|---------|----------|------------|----------|
| Agent Installation | `/mcp__gil__fetch_agents` | Medium | P0 |
| Project Activation | `/mcp__gil__activate_project <alias>` | High | P0 |
| Mission Launch | `/mcp__gil__launch_project <alias>` | High | P0 |
| Agent Updates | `/mcp__gil__update_agents` | Low | P1 |
| Project Alias System | N/A (backend) | Medium | P0 |

### Out of Scope

- ❌ Terminal emulation in web UI (future)
- ❌ Electron desktop app (future)
- ❌ Custom agent creation via commands (use UI)
- ❌ Real-time agent monitoring in CLI (use dashboard)

---

## 3. Technical Design

### Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│ User's Claude Code CLI                                   │
│ ├─ Connects to: gil MCP server                          │
│ ├─ Slash commands available:                            │
│ │   • /mcp__gil__fetch_agents                           │
│ │   • /mcp__gil__activate_project <alias>               │
│ │   • /mcp__gil__launch_project <alias>                 │
│ │   • /mcp__gil__update_agents                          │
│ └─ Agents: ~/.claude/agents/*.md                        │
└──────────────────────────────────────────────────────────┘
                      ↕ MCP Protocol
┌──────────────────────────────────────────────────────────┐
│ GiljoAI MCP Server                                       │
│ ├─ src/giljo_mcp/commands.py (NEW)                      │
│ │   └─ @mcp.prompt() functions                          │
│ ├─ src/giljo_mcp/tools/orchestration.py (NEW)           │
│ │   └─ activate_project_mission, get_launch_prompt      │
│ └─ api/endpoints/agent_templates.py (NEW)               │
│     └─ List/download agent .md files                    │
└──────────────────────────────────────────────────────────┘
                      ↕ REST API
┌──────────────────────────────────────────────────────────┐
│ PostgreSQL Database                                      │
│ ├─ projects.alias (NEW COLUMN)                          │
│ └─ agent_templates (existing)                           │
└──────────────────────────────────────────────────────────┘
```

---

## 4. Phase 1: Foundation (6-8 hours)

### Task 1.1: Project Alias System (2-3 hours)

**Database Migration:**
```python
# migrations/versions/add_project_alias.py

def upgrade():
    op.add_column('projects', sa.Column('alias', sa.String(6), nullable=True))
    op.create_index('ix_projects_alias', 'projects', ['alias'], unique=True)

    # Generate aliases for existing projects
    connection = op.get_bind()
    projects = connection.execute("SELECT id FROM projects").fetchall()

    for project in projects:
        alias = generate_unique_alias(connection)
        connection.execute(
            f"UPDATE projects SET alias = '{alias}' WHERE id = '{project[0]}'"
        )

    # Make alias NOT NULL after backfilling
    op.alter_column('projects', 'alias', nullable=False)

def generate_unique_alias(connection):
    import random
    import string
    while True:
        alias = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=6
        ))
        result = connection.execute(
            f"SELECT id FROM projects WHERE alias = '{alias}'"
        ).fetchone()
        if not result:
            return alias
```

**Model Update:**
```python
# src/giljo_mcp/models.py

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    alias = Column(String(6), nullable=False, unique=True, index=True)  # NEW
    # ... rest of model

    def __init__(self, **kwargs):
        if 'alias' not in kwargs:
            kwargs['alias'] = self._generate_alias()
        super().__init__(**kwargs)

    @staticmethod
    def _generate_alias():
        """Generate 6-char alphanumeric alias"""
        import random
        import string
        return ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=6
        ))
```

**API Endpoint:**
```python
# api/endpoints/projects.py

@router.get("/projects/by-alias/{alias}")
async def get_project_by_alias(
    alias: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project by short alias"""
    project = db.query(Project).filter(
        Project.alias == alias.upper(),
        Project.tenant_key == current_user.tenant_key
    ).first()

    if not project:
        raise HTTPException(404, f"Project '{alias}' not found")

    return project
```

**Tests:**
```python
# tests/test_project_alias.py

def test_generate_unique_alias():
    alias = Project._generate_alias()
    assert len(alias) == 6
    assert alias.isupper()
    assert alias.isalnum()

def test_get_project_by_alias(client, auth_headers):
    # Create project
    response = client.post("/api/products/", json={...})
    project_id = response.json()['id']

    # Get project
    project = client.get(f"/api/projects/{project_id}").json()
    alias = project['alias']

    # Get by alias
    response = client.get(f"/api/projects/by-alias/{alias}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['id'] == project_id
```

**Acceptance Criteria:**
- [ ] All existing projects have unique aliases
- [ ] New projects auto-generate aliases
- [ ] Alias collision handled gracefully
- [ ] API endpoint returns project by alias
- [ ] Multi-tenant isolation enforced

---

### Task 1.2: Agent Template HTTP Endpoints (1-2 hours)

**New Endpoint File:**
```python
# api/endpoints/agent_templates.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from src.giljo_mcp.template_manager import get_template_manager

router = APIRouter(prefix="/agents/templates", tags=["Agent Templates"])

template_manager = get_template_manager()

@router.get("/")
async def list_agent_templates():
    """List all standard agent templates for installation"""
    templates = await template_manager.get_all_templates()

    base_url = "http://192.168.1.100:7272/agents/templates"  # TODO: Get from config

    return {
        "count": len(templates),
        "base_url": base_url,
        "files": [
            {
                "filename": f"{t.name.lower().replace(' ', '-')}.md",
                "url": f"{base_url}/{t.name.lower().replace(' ', '-')}.md",
                "role": t.name,
                "description": t.description,
                "version": t.version
            }
            for t in templates
            if t.is_active
        ]
    }

@router.get("/{filename}")
async def get_agent_template(filename: str):
    """Download individual agent template as .md file"""

    # Extract role from filename
    role = filename.replace('.md', '').replace('-', ' ').title()

    template = await template_manager.get_template_by_name(role)

    if not template or not template.is_active:
        raise HTTPException(404, f"Agent template '{role}' not found")

    # Format as markdown file
    md_content = f"""# {template.name}

**Role:** {template.name}
**Version:** {template.version}
**Description:** {template.description}

---

{template.content}

---

## MCP Integration

This agent has access to the following MCP tools:

- `get_agent_messages()` - Check for messages from other agents
- `send_agent_message(to, content)` - Send message to another agent
- `get_project_context(project_id)` - Fetch product vision and tech stack
- `update_agent_status(status)` - Update your status (working, blocked, complete)

Use these tools to coordinate with the orchestrator and other agents.
"""

    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )
```

**Register Router:**
```python
# api/app.py

from api.endpoints import agent_templates

app.include_router(agent_templates.router, prefix="/api")
```

**Tests:**
```python
# tests/test_agent_templates_api.py

def test_list_agent_templates(client):
    response = client.get("/api/agents/templates/")
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert len(data['files']) > 0
    assert data['files'][0]['filename'].endswith('.md')

def test_download_agent_template(client):
    response = client.get("/api/agents/templates/orchestrator.md")
    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/markdown'
    assert '# Orchestrator' in response.text

def test_download_nonexistent_template(client):
    response = client.get("/api/agents/templates/fake-agent.md")
    assert response.status_code == 404
```

**Acceptance Criteria:**
- [ ] `/agents/templates/` returns list of all active templates
- [ ] `/agents/templates/{filename}` serves markdown file
- [ ] Content-Disposition header set for download
- [ ] 404 for non-existent templates
- [ ] Markdown includes MCP integration instructions

---

### Task 1.3: MCP Command Infrastructure (2-3 hours)

**New Commands Module:**
```python
# src/giljo_mcp/commands.py

"""
MCP Slash Commands for GiljoAI Agent Workflow Automation

These commands are exposed as slash commands in Claude Code CLI:
- /mcp__gil__fetch_agents
- /mcp__gil__activate_project <alias>
- /mcp__gil__launch_project <alias>
- /mcp__gil__update_agents
"""

import os
from pathlib import Path
from mcp import MCPServer

# Use short server name for shorter command syntax
mcp = MCPServer("gil")

@mcp.prompt()
async def fetch_agents(server_url: str = None) -> str:
    """Install GiljoAI agent templates to local AI tool directory

    Downloads all standard agent templates from the GiljoAI server
    and installs them to ~/.claude/agents/ for use with subagents.

    Args:
        server_url: GiljoAI server URL (default: from MCP config)
    """

    # If no server URL provided, try to get from environment
    if not server_url:
        server_url = os.environ.get('GILJO_SERVER_URL', 'http://192.168.1.100:7272')

    return f"""# Install GiljoAI Agent Templates

You will now install the standard GiljoAI agent templates to enable subagent orchestration.

## Steps to Execute:

### 1. Fetch Agent List
Use the WebFetch tool to get the list of available agents:
```
URL: {server_url}/agents/templates/
```

This returns JSON with all agent files.

### 2. Create Local Directory
Determine the correct agent directory for this system:
- **Windows**: `%USERPROFILE%\\.claude\\agents\\`
- **Mac/Linux**: `~/.claude/agents/`

Create the directory if it doesn't exist (use Bash tool or Write tool).

### 3. Download Each Agent File
For each agent in the JSON response:
1. Use WebFetch to download: `{{file.url}}`
2. Use Write tool to save as: `<agent-dir>/{{file.filename}}`

### 4. Verify Installation
After all files are written, list the directory contents to confirm installation.

### 5. Notify User
Tell the user:
```
✅ Successfully installed {{count}} GiljoAI agents:
  • Agent 1
  • Agent 2
  • ...

📁 Location: <agent-directory>

⚠️ IMPORTANT: You must restart your AI tool for agents to be loaded.

After restart, use: /mcp__gil__activate_project <project-alias>
```

## Begin Installation

Start with step 1 now. Work through each step systematically.
"""

@mcp.prompt()
async def activate_project(alias: str) -> str:
    """Activate a project and create the mission plan

    Fetches project context, creates mission plan, selects agents,
    and stages everything for launch.

    Args:
        alias: 6-character project alias (e.g., "A3F7K2")
    """

    return f"""# Activate GiljoAI Project: {alias}

You will now activate this project and prepare it for mission execution.

## Steps to Execute:

### 1. Fetch Project Details
Use the MCP tool: `get_project_by_alias("{alias}")`

This returns:
- Project ID
- Project name
- Project description (mission request)
- Product ID

### 2. Activate Project via Orchestrator
Use the MCP tool: `activate_project_mission("{alias}")`

This will:
- Analyze product vision and tech stack
- Create detailed mission plan
- Select appropriate agents
- Assign jobs to each agent
- Stage agent prompts

The tool returns:
- Mission plan text
- List of selected agents
- Agent job assignments

### 3. Display Mission Plan to User
Show the user:
```
✅ Project Activated: {{project_name}} ({alias})

📋 Mission Plan:
{{mission_plan_text}}

🤖 Selected Agents:
  • Orchestrator - Coordinate overall mission
  • Code Reviewer - Review implementation for issues
  • Tester - Write and run tests
  • Implementer - Write production code

📊 Status: Ready to Launch

Next step: Restart AI tool (if custom agents added), then run:
  /mcp__gil__launch_project {alias}
```

### 4. Check for Custom Agents
If custom agents were created for this project:
- Notify user they must restart AI tool
- Otherwise, can proceed directly to launch

## Begin Activation

Start with step 1 now.
"""

@mcp.prompt()
async def launch_project(alias: str) -> str:
    """Launch project mission with subagent orchestration

    Loads the mission plan and begins executing it by spawning
    and coordinating specialized subagents.

    Args:
        alias: 6-character project alias
    """

    return f"""# Launch GiljoAI Project: {alias}

You will now begin mission execution as the Orchestrator agent.

## Steps to Execute:

### 1. Load Mission Context
Use the MCP tool: `get_launch_prompt("{alias}")`

This returns:
- Full mission plan
- Agent assignments
- Coordination instructions
- MCP communication protocols

### 2. Verify Agents Available
Check that all required agents are available as slash commands:
- `/orchestrator` (you)
- `/code-reviewer`
- `/tester`
- `/implementer`
- (any custom agents)

If any agents are missing, notify the user and stop.

### 3. Begin Orchestration
As the Orchestrator, you now:

**A. Invoke First Agent**
Use the SlashCommand tool to invoke the first agent with their task:
```
/code-reviewer Analyze the authentication module for security issues
```

**B. Monitor Progress**
Use MCP tools to track agent work:
- `get_agent_messages()` - Check for agent reports
- `get_agent_status(agent_name)` - Check if agent is working/blocked/done

**C. Coordinate Handoffs**
When an agent completes their task:
1. Acknowledge their work
2. Review their output
3. Invoke the next agent in sequence

**D. Communicate via MCP**
All agents should also send messages via MCP so the user can monitor via dashboard:
- `send_agent_message(to="User", content="Status update...")`

### 4. Mission Completion
When all agents have completed their tasks:
1. Summarize results
2. Mark project as complete via MCP
3. Notify user

## Begin Mission

Load the mission context (step 1) and begin orchestration.
"""

@mcp.prompt()
async def update_agents() -> str:
    """Update GiljoAI agent templates to latest versions

    Re-downloads all agent templates from the server to get
    the latest updates, fixes, and new features.
    """

    return """# Update GiljoAI Agent Templates

This command re-downloads all agent templates to get the latest versions.

## Steps:

1. Run the same installation process as `/mcp__gil__fetch_agents`
2. Overwrite existing .md files in ~/.claude/agents/
3. Notify user to restart AI tool

After restart, updated agents will be loaded.

## Begin Update

Proceed with the installation steps from fetch_agents.
"""
```

**Register Commands:**
```python
# src/giljo_mcp/__init__.py

from .commands import mcp

__all__ = ['mcp', ...]
```

**Acceptance Criteria:**
- [ ] All 4 prompts return structured instructions
- [ ] Instructions are clear and actionable for Claude
- [ ] Commands appear in `/help` when connected to MCP
- [ ] Command names follow `/mcp__gil__*` pattern

---

## 5. Phase 2: Core Commands (6-8 hours)

### Task 2.1: Orchestration MCP Tools (2-3 hours)

**New Orchestration Tools:**
```python
# src/giljo_mcp/tools/orchestration.py

"""
MCP Tools for Project Orchestration Workflow

These tools are called by MCP slash commands to perform
actual orchestration logic.
"""

from mcp import MCPServer
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.database import get_db

mcp = MCPServer("gil")

@mcp.tool()
async def get_project_by_alias(alias: str) -> dict:
    """Fetch project details by short alias

    Args:
        alias: 6-character project alias (e.g., "A3F7K2")

    Returns:
        Project details including ID, name, mission, product context
    """
    db = next(get_db())

    from src.giljo_mcp.models import Project
    project = db.query(Project).filter(
        Project.alias == alias.upper()
    ).first()

    if not project:
        return {"error": f"Project '{alias}' not found"}

    return {
        "id": project.id,
        "alias": project.alias,
        "name": project.name,
        "mission": project.mission,
        "product_id": project.product_id,
        "status": project.status
    }

@mcp.tool()
async def activate_project_mission(alias: str) -> dict:
    """Activate project and create mission plan

    This triggers the orchestrator to:
    1. Analyze product vision and tech stack
    2. Generate detailed mission plan
    3. Select appropriate agents
    4. Create job assignments

    Args:
        alias: 6-character project alias

    Returns:
        Mission plan, selected agents, and status
    """
    db = next(get_db())
    orchestrator = ProjectOrchestrator(db)

    # Get project
    from src.giljo_mcp.models import Project
    project = db.query(Project).filter(
        Project.alias == alias.upper()
    ).first()

    if not project:
        return {"error": f"Project '{alias}' not found"}

    # Activate and generate mission
    result = await orchestrator.activate_project(project.id)

    return {
        "project_id": project.id,
        "alias": project.alias,
        "mission": result['mission_plan'],
        "agents": result['selected_agents'],
        "status": "activated"
    }

@mcp.tool()
async def get_launch_prompt(alias: str) -> str:
    """Get orchestration prompt for launching project mission

    Returns detailed instructions for the Orchestrator agent
    to begin coordinating the mission.

    Args:
        alias: 6-character project alias

    Returns:
        Formatted prompt with mission details and orchestration instructions
    """
    db = next(get_db())
    orchestrator = ProjectOrchestrator(db)

    from src.giljo_mcp.models import Project
    project = db.query(Project).filter(
        Project.alias == alias.upper()
    ).first()

    if not project:
        return f"Error: Project '{alias}' not found"

    return await orchestrator.generate_launch_prompt(project.id)
```

**Register Tools:**
```python
# src/giljo_mcp/tools/__init__.py

from .orchestration import register_orchestration_tools

def register_all_tools(mcp):
    """Register all MCP tools"""
    register_agent_tools(mcp)
    register_project_tools(mcp)
    # ... existing tools ...
    register_orchestration_tools(mcp)  # NEW
```

**Tests:**
```python
# tests/test_orchestration_tools.py

async def test_get_project_by_alias():
    result = await get_project_by_alias("ABC123")
    assert result['alias'] == "ABC123"
    assert 'id' in result
    assert 'name' in result

async def test_activate_project_mission():
    result = await activate_project_mission("ABC123")
    assert result['status'] == "activated"
    assert 'mission' in result
    assert 'agents' in result

async def test_get_launch_prompt():
    prompt = await get_launch_prompt("ABC123")
    assert "# Launch" in prompt
    assert "Mission Plan" in prompt
    assert "Orchestrator" in prompt
```

**Acceptance Criteria:**
- [ ] MCP tools callable from Claude Code
- [ ] Tools integrate with ProjectOrchestrator
- [ ] Error handling for invalid aliases
- [ ] Returns structured data for prompts to use

---

### Task 2.2: Enhanced Orchestrator Logic (3-4 hours)

**Add Mission Generation:**
```python
# src/giljo_mcp/orchestrator.py

class ProjectOrchestrator:

    async def activate_project(self, project_id: str) -> dict:
        """Enhanced activation with mission generation"""

        # Get project and product context
        project = await self.db.get_project(project_id)
        product = await self.db.get_product(project.product_id)

        # 1. Generate mission plan (NEW)
        mission_plan = await self._generate_mission_plan(
            product=product,
            project=project
        )

        # 2. Select agents (NEW)
        selected_agents = await self._select_agents_for_mission(
            mission_plan=mission_plan
        )

        # 3. Create agents and jobs
        created_agents = []
        for agent_config in selected_agents:
            agent = await self.spawn_agent(
                project_id=project_id,
                role=agent_config['role'],
                mission=agent_config['mission']
            )
            created_agents.append(agent)

        # 4. Update project
        project.mission = mission_plan['summary']
        project.meta_data['mission_plan'] = mission_plan
        project.status = 'active'
        await self.db.commit()

        return {
            "mission_plan": mission_plan,
            "selected_agents": selected_agents,
            "created_agents": created_agents
        }

    async def _generate_mission_plan(self, product, project) -> dict:
        """Generate detailed mission plan from context"""

        # Extract context
        vision = product.vision_document or "No vision provided"
        tech_stack = product.config_data.get('tech_stack', [])
        guidelines = product.config_data.get('guidelines', [])
        project_desc = project.mission  # User's description

        # TODO: Use AI/LLM to generate plan (for now, template-based)
        mission_plan = {
            "summary": f"Build {project.name} following product vision",
            "objectives": [
                "Analyze requirements",
                "Design architecture",
                "Implement features",
                "Test thoroughly",
                "Document code"
            ],
            "tech_stack": tech_stack,
            "constraints": guidelines,
            "success_criteria": [
                "All tests passing",
                "Code reviewed",
                "Documentation complete"
            ]
        }

        return mission_plan

    async def _select_agents_for_mission(self, mission_plan: dict) -> list:
        """Select appropriate agents based on mission"""

        # Default agent set (can be enhanced with AI selection)
        agents = [
            {
                "role": "orchestrator",
                "mission": "Coordinate overall mission execution"
            },
            {
                "role": "code-reviewer",
                "mission": "Review all code for quality and security"
            },
            {
                "role": "tester",
                "mission": "Write and execute comprehensive tests"
            },
            {
                "role": "implementer",
                "mission": "Implement features per specifications"
            }
        ]

        # TODO: Smart agent selection based on mission objectives

        return agents

    async def generate_launch_prompt(self, project_id: str) -> str:
        """Generate orchestrator launch prompt"""

        project = await self.db.get_project(project_id)
        agents = await self.db.get_project_agents(project_id)

        agent_list = "\n".join([
            f"- /{a.role} - {a.mission}"
            for a in agents
        ])

        return f"""# Launch Project: {project.name} ({project.alias})

## Mission
{project.mission}

## Assigned Agents
{agent_list}

## Your Role (Orchestrator)

You are the Orchestrator agent. Your responsibilities:

1. **Coordinate the mission** described above
2. **Invoke subagents** using SlashCommand tool:
   {chr(10).join([f"   //{a.role}" for a in agents if a.role != 'orchestrator'])}
3. **Monitor progress** via MCP:
   - Check messages: get_agent_messages()
   - Send updates: send_agent_message(to="agent_name", content="...")
4. **Ensure quality** by coordinating reviews and testing
5. **Report completion** when mission objectives met

## Workflow

1. Start with planning and architecture
2. Invoke implementer for coding tasks
3. Invoke code-reviewer after each implementation
4. Invoke tester to validate functionality
5. Iterate until all objectives complete

Begin orchestration now.
"""
```

**Tests:**
```python
# tests/test_orchestrator_enhanced.py

async def test_activate_project_generates_mission():
    result = await orchestrator.activate_project(project_id)
    assert 'mission_plan' in result
    assert 'objectives' in result['mission_plan']
    assert len(result['selected_agents']) >= 3

async def test_generate_launch_prompt():
    prompt = await orchestrator.generate_launch_prompt(project_id)
    assert "Orchestrator" in prompt
    assert "Mission" in prompt
    assert "code-reviewer" in prompt.lower()
```

**Acceptance Criteria:**
- [ ] Mission plan generated from product context
- [ ] Agents selected based on mission
- [ ] Launch prompt includes all context
- [ ] Project status updated correctly

---

## 6. Phase 3: Integration & Testing (4-6 hours)

### Task 3.1: End-to-End Workflow Testing (2-3 hours)

**Test Scenario 1: Fresh Installation**
```python
# tests/integration/test_e2e_slash_commands.py

async def test_complete_workflow_fresh_install():
    """Test full workflow from scratch"""

    # 1. Setup: Create product and project in database
    product = await create_test_product()
    project = await create_test_project(product_id=product.id)

    # 2. Simulate: /mcp__gil__fetch_agents
    # (Claude would do this, we simulate the HTTP calls)
    response = client.get("/api/agents/templates/")
    assert response.status_code == 200
    templates = response.json()['files']
    assert len(templates) >= 4

    # Download each template
    for template in templates:
        response = client.get(template['url'])
        assert response.status_code == 200
        # In real scenario, Claude would write to disk

    # 3. Simulate: /mcp__gil__activate_project ABC123
    result = await activate_project_mission(project.alias)
    assert result['status'] == 'activated'
    assert 'mission' in result
    assert len(result['agents']) >= 3

    # 4. Verify project state
    db_project = await db.get_project(project.id)
    assert db_project.status == 'active'
    assert db_project.mission is not None

    # 5. Simulate: /mcp__gil__launch_project ABC123
    prompt = await get_launch_prompt(project.alias)
    assert "Orchestrator" in prompt
    assert "Mission" in prompt

    # 6. Verify agents created
    agents = await db.get_project_agents(project.id)
    assert len(agents) >= 3
    assert any(a.role == 'orchestrator' for a in agents)
    assert any(a.role == 'code-reviewer' for a in agents)
```

**Test Scenario 2: Update Workflow**
```python
async def test_agent_update_workflow():
    """Test updating agents after templates change"""

    # 1. Initial install
    # ... (same as above)

    # 2. Update template in database
    template = await template_manager.get_template('code-reviewer')
    template.content += "\n\n## New Feature\nAdded security scanning"
    template.version = "1.1.0"
    await db.commit()

    # 3. Simulate: /mcp__gil__update_agents
    response = client.get("/api/agents/templates/code-reviewer.md")
    assert "New Feature" in response.text
    assert "1.1.0" in response.text
```

**Acceptance Criteria:**
- [ ] Full workflow completes without errors
- [ ] Agent templates downloaded successfully
- [ ] Project activation creates mission and agents
- [ ] Launch prompt contains all required context
- [ ] Agent updates fetch latest versions

---

### Task 3.2: Error Handling (1-2 hours)

**Error Scenarios:**
```python
# Error handling in commands.py and tools

async def activate_project_mission(alias: str) -> dict:
    """With error handling"""
    try:
        db = next(get_db())
        project = db.query(Project).filter(
            Project.alias == alias.upper()
        ).first()

        if not project:
            return {
                "error": "project_not_found",
                "message": f"Project with alias '{alias}' does not exist",
                "suggestion": "Check the alias and try again, or create a new project in the dashboard"
            }

        if project.status == 'active':
            return {
                "error": "already_activated",
                "message": f"Project '{alias}' is already activated",
                "suggestion": "Use /mcp__gil__launch_project to launch, or deactivate first"
            }

        # ... rest of logic

    except Exception as e:
        return {
            "error": "activation_failed",
            "message": str(e),
            "suggestion": "Check server logs and database connection"
        }
```

**Tests:**
```python
# tests/test_error_handling.py

async def test_activate_nonexistent_project():
    result = await activate_project_mission("FAKE99")
    assert result['error'] == 'project_not_found'
    assert 'suggestion' in result

async def test_activate_already_active_project():
    # Activate once
    await activate_project_mission("ABC123")

    # Try again
    result = await activate_project_mission("ABC123")
    assert result['error'] == 'already_activated'
```

**Acceptance Criteria:**
- [ ] Graceful error messages for all failure modes
- [ ] Helpful suggestions in error responses
- [ ] No stack traces exposed to user
- [ ] Errors logged on server side

---

### Task 3.3: UI Updates (1-2 hours)

**Dashboard Changes:**
```vue
<!-- frontend/src/views/ProjectDetail.vue -->

<template>
  <v-container>
    <!-- Existing project details -->

    <!-- NEW: MCP Command Helper -->
    <v-card class="mt-4">
      <v-card-title>Quick Start with Claude Code</v-card-title>

      <v-stepper v-model="step">
        <v-stepper-header>
          <v-stepper-item :value="1">Install Agents</v-stepper-item>
          <v-stepper-item :value="2">Activate Project</v-stepper-item>
          <v-stepper-item :value="3">Launch Mission</v-stepper-item>
        </v-stepper-header>

        <v-stepper-window>
          <!-- Step 1: Install Agents -->
          <v-stepper-window-item :value="1">
            <v-card-text>
              <p>First-time setup: Install GiljoAI agents</p>
              <v-code-block>
                /mcp__gil__fetch_agents
              </v-code-block>
              <v-btn @click="copyCommand('/mcp__gil__fetch_agents')">
                Copy Command
              </v-btn>
              <v-alert type="info" class="mt-2">
                After installation, restart Claude Code
              </v-alert>
            </v-card-text>
          </v-stepper-window-item>

          <!-- Step 2: Activate -->
          <v-stepper-window-item :value="2">
            <v-card-text>
              <p>Create mission plan for project: <strong>{{ project.alias }}</strong></p>
              <v-code-block>
                /mcp__gil__activate_project {{ project.alias }}
              </v-code-block>
              <v-btn @click="copyCommand(`/mcp__gil__activate_project ${project.alias}`)">
                Copy Command
              </v-btn>
            </v-card-text>
          </v-stepper-window-item>

          <!-- Step 3: Launch -->
          <v-stepper-window-item :value="3">
            <v-card-text>
              <p>Launch mission orchestration</p>
              <v-code-block>
                /mcp__gil__launch_project {{ project.alias }}
              </v-code-block>
              <v-btn @click="copyCommand(`/mcp__gil__launch_project ${project.alias}`)">
                Copy Command
              </v-btn>
              <v-alert type="success" class="mt-2">
                Mission will begin automatically!
              </v-alert>
            </v-card-text>
          </v-stepper-window-item>
        </v-stepper-window>
      </v-stepper>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useClipboard } from '@vueuse/core'

const { copy } = useClipboard()
const step = ref(1)

const copyCommand = (command) => {
  copy(command)
  // Show toast notification
}
</script>
```

**Settings Page:**
```vue
<!-- frontend/src/views/Settings.vue -->

<v-card>
  <v-card-title>Agent Templates</v-card-title>
  <v-card-text>
    <p>Install or update GiljoAI agent templates:</p>

    <v-list>
      <v-list-item>
        <template #prepend>
          <v-icon>mdi-download</v-icon>
        </template>
        <v-list-item-title>First-Time Install</v-list-item-title>
        <v-list-item-subtitle>
          /mcp__gil__fetch_agents
        </v-list-item-subtitle>
        <template #append>
          <v-btn @click="copyCommand('/mcp__gil__fetch_agents')">
            Copy
          </v-btn>
        </template>
      </v-list-item>

      <v-list-item>
        <template #prepend>
          <v-icon>mdi-update</v-icon>
        </template>
        <v-list-item-title>Update Agents</v-list-item-title>
        <v-list-item-subtitle>
          /mcp__gil__update_agents
        </v-list-item-subtitle>
        <template #append>
          <v-btn @click="copyCommand('/mcp__gil__update_agents')">
            Copy
          </v-btn>
        </template>
      </v-list-item>
    </v-list>
  </v-card-text>
</v-card>
```

**Acceptance Criteria:**
- [ ] Project detail shows 3-step wizard
- [ ] Commands include project alias
- [ ] Copy buttons work
- [ ] Settings shows install/update commands
- [ ] Clear instructions for restart requirements

---

## 7. Testing Strategy

### Unit Tests (8-10 tests)
- [ ] Project alias generation uniqueness
- [ ] Agent template endpoint returns valid markdown
- [ ] MCP tool error handling
- [ ] Mission plan generation logic
- [ ] Launch prompt formatting

### Integration Tests (5-7 tests)
- [ ] Full activation workflow
- [ ] Agent download and parsing
- [ ] MCP tool → Orchestrator integration
- [ ] Multi-tenant isolation
- [ ] Agent update workflow

### E2E Tests (3-5 tests)
- [ ] Fresh install → Activate → Launch
- [ ] Update agents after template changes
- [ ] Error recovery (invalid alias, network failure)
- [ ] Multi-project workflow
- [ ] Cross-platform compatibility (Windows/Mac/Linux paths)

**Total Test Coverage Goal:** 85%+

---

## 8. Documentation

### User Guide
- [ ] "Getting Started with MCP Slash Commands"
- [ ] Command reference (all 4 commands)
- [ ] Troubleshooting guide
- [ ] FAQ

### Developer Guide
- [ ] MCP prompt architecture
- [ ] Adding new commands
- [ ] Extending mission generation logic
- [ ] Testing slash commands

### API Documentation
- [ ] `/agents/templates/` endpoint
- [ ] `/agents/templates/{filename}` endpoint
- [ ] `/projects/by-alias/{alias}` endpoint

---

## 9. Deployment Plan

### Prerequisites
- [ ] Database migration applied (add alias column)
- [ ] MCP server name updated to "gil"
- [ ] Server URL configurable (not hardcoded)
- [ ] Agent templates seeded in database

### Deployment Steps
1. Run database migration
2. Deploy backend changes (API + MCP tools)
3. Deploy frontend changes (UI updates)
4. Restart MCP server
5. Test with one project end-to-end
6. Document for users
7. Roll out to all users

### Rollback Plan
- Revert database migration
- Deploy previous backend version
- Frontend gracefully handles missing API endpoints

---

## 10. Success Metrics

### Functional Metrics
- [ ] 100% of slash commands functional
- [ ] <5 seconds per command execution
- [ ] 0% project alias collisions
- [ ] 100% agent template downloads successful

### User Experience Metrics
- [ ] User completes setup in <5 minutes
- [ ] ≤1 restart required (only after fetch_agents)
- [ ] <3 commands from project creation to mission launch
- [ ] User satisfaction: Positive feedback

### Technical Metrics
- [ ] 85%+ test coverage
- [ ] 0 critical bugs in production
- [ ] <100ms API response time
- [ ] Works on Windows/Mac/Linux

---

## 11. Timeline

### Day 1 (6-8 hours)
- ✅ Task 1.1: Project alias system
- ✅ Task 1.2: Agent template endpoints
- ✅ Task 1.3: MCP command infrastructure

### Day 2 (6-8 hours)
- ✅ Task 2.1: Orchestration MCP tools
- ✅ Task 2.2: Enhanced orchestrator logic

### Day 3 (4-6 hours)
- ✅ Task 3.1: E2E testing
- ✅ Task 3.2: Error handling
- ✅ Task 3.3: UI updates
- ✅ Documentation

**Total: 16-22 hours over 3 days**

---

## 12. Acceptance Checklist

### Functional Requirements
- [ ] `/mcp__gil__fetch_agents` downloads and installs all templates
- [ ] `/mcp__gil__activate_project <alias>` creates mission and agents
- [ ] `/mcp__gil__launch_project <alias>` begins orchestration
- [ ] `/mcp__gil__update_agents` syncs latest templates
- [ ] Project aliases are unique 6-char codes
- [ ] Agent templates served as downloadable .md files

### Non-Functional Requirements
- [ ] Commands execute in <30 seconds
- [ ] Error messages are clear and actionable
- [ ] Cross-platform compatible (Win/Mac/Linux)
- [ ] No hardcoded URLs (configurable)
- [ ] Logging for all command executions

### Quality Requirements
- [ ] 85%+ test coverage
- [ ] All tests passing
- [ ] No critical security issues
- [ ] Code reviewed
- [ ] Documentation complete

---

## 13. Next Steps

1. **Review this handover** - Approve scope and timeline
2. **Begin Phase 1** - Database migration and foundation
3. **Daily check-ins** - Review progress and blockers
4. **Complete in 3 days** - Full implementation and testing

---

**Implementation Plan Created By:** Claude (Sonnet 4.5)
**Creation Date:** 2025-10-19
**Status:** 🟢 READY TO START
**Complexity:** Medium-High (16-22 hours)
**Risk Level:** Low (all dependencies met, clear path)
