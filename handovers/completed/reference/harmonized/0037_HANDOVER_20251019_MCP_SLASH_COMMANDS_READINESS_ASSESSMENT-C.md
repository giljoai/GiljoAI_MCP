# Handover 0037: MCP Slash Commands Readiness Assessment

**Handover ID**: 0037
**Creation Date**: 2025-10-19
**Priority**: HIGH
**Type**: READINESS ASSESSMENT
**Status**: ASSESSMENT COMPLETE
**Dependencies**: None

---

## 1. Executive Summary

This handover assesses the **readiness** of the GiljoAI MCP system to implement **MCP-exposed slash commands** for automating agent workflow setup and project orchestration.

### Proposed Workflow (Target State)

```
User → Web Dashboard → Create Project
     → Copy slash command: /mcp__gil__activate_project ABC123
     → Paste in Claude Code CLI
     → Claude Code:
         - Fetches project context via MCP
         - Creates mission plan
         - Selects agents
         - Stages agent templates
     → User restarts Claude Code (agents loaded)
     → User: /mcp__gil__launch_project ABC123
     → Claude Code:
         - Loads mission
         - Spawns subagents
         - Begins orchestration
```

### Key Commands to Implement

1. `/mcp__gil__fetch_agents` - Install agent templates locally
2. `/mcp__gil__activate_project <alias>` - Create mission, stage agents
3. `/mcp__gil__launch_project <alias>` - Execute mission with subagents
4. `/mcp__gil__update_agents` - Sync latest agent templates from server

---

## 2. Current System Inventory

### ✅ What EXISTS (Production-Ready)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Database Models** | ✅ Complete | `src/giljo_mcp/models.py` | Product, Project, Agent, Job, Message, AgentTemplate |
| **ProjectOrchestrator** | ✅ Complete | `src/giljo_mcp/orchestrator.py` | 915 lines, spawn_agent, activate_project, handoff |
| **AgentJobManager** | ✅ Complete | `src/giljo_mcp/agent_job_manager.py` | Job creation, status tracking |
| **JobCoordinator** | ✅ Complete | `src/giljo_mcp/job_coordinator.py` | Multi-agent coordination |
| **AgentCommunicationQueue** | ✅ Complete | `src/giljo_mcp/agent_communication_queue.py` | Message passing, acknowledgments |
| **UnifiedTemplateManager** | ✅ Complete | `src/giljo_mcp/template_manager.py` | CRUD for agent templates |
| **MCP Tools (12+)** | ✅ Complete | `src/giljo_mcp/tools/*.py` | agent, project, context, message, task, optimization |
| **REST API Endpoints** | ✅ Complete | `api/endpoints/*.py` | Products, Projects, Agents, Jobs, Templates |
| **Vue Dashboard** | ✅ Complete | `frontend/` | Product/Project management, agent monitoring |
| **Multi-Tenant Isolation** | ✅ Complete | All layers | tenant_key enforcement |
| **WebSocket Events** | ✅ Complete | `api/websockets.py` | Real-time agent status updates |

### ❌ What's MISSING (Gaps for Implementation)

| Component | Status | Required For | Estimated Effort |
|-----------|--------|--------------|------------------|
| **MCP Prompts (Slash Commands)** | ❌ Missing | All 4 commands | 4-6 hours |
| **Project Alias System** | ❌ Missing | Short project IDs (ABC123) | 2-3 hours |
| **Agent Template HTTP Endpoints** | ❌ Missing | fetch_agents command | 1-2 hours |
| **Mission Staging Logic** | ⚠️ Partial | activate_project command | 3-4 hours |
| **Subagent Invocation Prompts** | ❌ Missing | launch_project command | 2-3 hours |
| **Orchestrator MCP Integration** | ⚠️ Partial | All commands | 2-3 hours |

**Total Gap:** ~14-21 hours of development

---

## 3. Detailed Gap Analysis

### Gap 1: MCP Slash Command Infrastructure ❌

**Current State:**
- MCP tools exist (`@mcp.tool()`) but no prompts (`@mcp.prompt()`)
- No slash command exposure to Claude Code

**Required:**
```python
# src/giljo_mcp/commands.py (NEW FILE)

from mcp import MCPServer

mcp = MCPServer("gil")  # Short name for /mcp__gil__*

@mcp.prompt()
async def fetch_agents(server_url: str = None) -> str:
    """Install GiljoAI agent templates"""
    # Return instructions for Claude to:
    # 1. Fetch agent list from /agents/templates/
    # 2. Download each .md file
    # 3. Write to ~/.claude/agents/
    # 4. Notify user to restart

@mcp.prompt()
async def activate_project(alias: str) -> str:
    """Activate project and create mission"""
    # Return instructions for Claude to:
    # 1. Call MCP tool: get_project_by_alias(alias)
    # 2. Call MCP tool: orchestrator_activate_project(project_id)
    # 3. Display mission plan to user
    # 4. Stage agents (if custom agents exist)

@mcp.prompt()
async def launch_project(alias: str) -> str:
    """Launch project mission with subagents"""
    # Return instructions for Claude to:
    # 1. Load mission via MCP
    # 2. Invoke subagents with SlashCommand tool
    # 3. Begin orchestration

@mcp.prompt()
async def update_agents() -> str:
    """Update agent templates from server"""
    # Same as fetch_agents (re-download)
```

**Effort:** 4-6 hours
**Priority:** P0 (Critical path)

---

### Gap 2: Project Alias System ❌

**Current State:**
- Projects use 36-character UUIDs (`abc-def-123-456-789...`)
- Too long for command-line usage

**Required:**
1. **Database Migration:**
   ```python
   # New column in Project model
   alias = Column(String(6), unique=True, index=True)
   # Format: A-Z0-9 (e.g., "A3F7K2")
   ```

2. **Alias Generation Logic:**
   ```python
   import random
   import string

   def generate_project_alias(db: Session) -> str:
       """Generate unique 6-char alphanumeric alias"""
       while True:
           alias = ''.join(random.choices(
               string.ascii_uppercase + string.digits, k=6
           ))
           if not db.query(Project).filter(Project.alias == alias).first():
               return alias
   ```

3. **API Endpoint:**
   ```python
   @router.get("/projects/by-alias/{alias}")
   async def get_project_by_alias(alias: str):
       project = await db.get_project_by_alias(alias)
       if not project:
           raise HTTPException(404, f"Project alias '{alias}' not found")
       return project
   ```

4. **MCP Tool:**
   ```python
   @mcp.tool()
   async def get_project_by_alias(alias: str) -> dict:
       """Fetch project details by short alias"""
       # Call REST API
   ```

**Effort:** 2-3 hours
**Priority:** P0 (Required for all commands)

---

### Gap 3: Agent Template Staging Endpoints ❌

**Current State:**
- Templates stored in PostgreSQL
- No HTTP endpoints to serve as `.md` files

**Required:**
1. **List Endpoint:**
   ```python
   @router.get("/agents/templates/")
   async def list_agent_templates():
       """List all standard agent templates"""
       templates = await template_manager.get_all_templates()
       return {
           "base_url": "http://192.168.1.100:7272/agents/templates",
           "files": [
               {
                   "filename": f"{t.name.lower()}.md",
                   "url": f".../{t.name.lower()}.md",
                   "role": t.name,
                   "description": t.description
               }
               for t in templates
           ]
       }
   ```

2. **Download Endpoint:**
   ```python
   @router.get("/agents/templates/{filename}")
   async def get_agent_template(filename: str):
       """Serve individual agent template MD file"""
       role = filename.replace('.md', '')
       template = await template_manager.get_template(role)

       return Response(
           content=template.content,
           media_type="text/markdown"
       )
   ```

**Effort:** 1-2 hours
**Priority:** P0 (Required for fetch_agents)

---

### Gap 4: Mission Staging Logic ⚠️

**Current State:**
- `ProjectOrchestrator.activate_project()` exists BUT:
  - Doesn't create mission plan text
  - Doesn't select agents automatically
  - Doesn't stage agent prompts

**Required Enhancements:**
```python
async def activate_project(self, project_id: str) -> dict:
    """Activate project and generate mission plan"""

    # 1. Fetch product context (vision, tech stack)
    product = await self.get_product_context(project_id)

    # 2. Analyze project description
    project = await self.db.get_project(project_id)

    # 3. Generate mission plan (NEW)
    mission_plan = await self.generate_mission_plan(
        product_vision=product.vision_document,
        tech_stack=product.config_data['tech_stack'],
        project_description=project.mission
    )

    # 4. Select agents based on mission (NEW)
    selected_agents = await self.select_agents_for_mission(
        mission_plan=mission_plan
    )

    # 5. Create agent job assignments (NEW)
    for agent_config in selected_agents:
        await self.spawn_agent(
            project_id=project_id,
            role=agent_config['role'],
            mission=agent_config['mission']
        )

    # 6. Store mission in database
    project.mission = mission_plan['text']
    project.meta_data['mission_plan'] = mission_plan
    await self.db.commit()

    return {
        "project_id": project_id,
        "alias": project.alias,
        "mission": mission_plan,
        "agents": selected_agents
    }
```

**Effort:** 3-4 hours
**Priority:** P0 (Core workflow)

---

### Gap 5: Subagent Invocation Prompts ❌

**Current State:**
- No mechanism to generate "launch" instructions for Claude Code

**Required:**
```python
async def generate_launch_prompt(self, project_id: str) -> str:
    """Generate prompt for Claude to launch project mission"""

    project = await self.db.get_project(project_id)
    agents = await self.db.get_project_agents(project_id)

    return f"""# Launch Project: {project.name} ({project.alias})

## Mission
{project.mission}

## Assigned Agents
{chr(10).join([f"- /{a.role} - {a.mission}" for a in agents])}

## Instructions

You are the Orchestrator agent. Your mission:

1. **Coordinate the mission** described above
2. **Invoke subagents** using the SlashCommand tool:
   {chr(10).join([f"   - Invoke /{a.role} with task: {a.jobs[0].tasks[0]}" for a in agents])}
3. **Monitor progress** via MCP messages:
   - Check for messages: get_agent_messages()
   - Send messages: send_agent_message(to="{agents[0].name}", content="...")
4. **Report completion** when all tasks done

Begin orchestration now.
"""
```

**Effort:** 2-3 hours
**Priority:** P0 (Required for launch_project)

---

### Gap 6: Orchestrator ↔ MCP Integration ⚠️

**Current State:**
- MCP tools exist but not fully wired to ProjectOrchestrator

**Required:**
1. **New MCP Tool Wrappers:**
   ```python
   # src/giljo_mcp/tools/orchestration.py (NEW FILE)

   @mcp.tool()
   async def activate_project_mission(alias: str) -> dict:
       """Activate project and create mission plan"""
       orchestrator = ProjectOrchestrator(db)
       project = await db.get_project_by_alias(alias)
       return await orchestrator.activate_project(project.id)

   @mcp.tool()
   async def get_launch_prompt(alias: str) -> str:
       """Get prompt to launch project mission"""
       orchestrator = ProjectOrchestrator(db)
       project = await db.get_project_by_alias(alias)
       return await orchestrator.generate_launch_prompt(project.id)
   ```

2. **Register Tools:**
   ```python
   # src/giljo_mcp/tools/__init__.py
   from .orchestration import register_orchestration_tools

   __all__ = [
       ...,
       "register_orchestration_tools"
   ]
   ```

**Effort:** 2-3 hours
**Priority:** P0 (Glue layer)

---

## 4. Readiness Matrix

| Feature | Database | Backend Logic | MCP Tools | MCP Prompts | API Endpoints | UI | Readiness |
|---------|----------|---------------|-----------|-------------|---------------|----|-----------|
| **fetch_agents** | N/A | N/A | ✅ | ❌ | ❌ | ✅ | 40% |
| **activate_project** | ⚠️ (needs alias) | ⚠️ (partial) | ⚠️ (partial) | ❌ | ✅ | ✅ | 50% |
| **launch_project** | ✅ | ⚠️ (needs prompt gen) | ✅ | ❌ | ✅ | ✅ | 60% |
| **update_agents** | N/A | N/A | ✅ | ❌ | ❌ | ✅ | 40% |

**Overall System Readiness: 47.5% complete**

---

## 5. Dependencies & Blockers

### Hard Dependencies (Must Have)
1. ✅ **PostgreSQL database** - EXISTS
2. ✅ **MCP server infrastructure** - EXISTS
3. ✅ **Agent templates in database** - EXISTS
4. ✅ **Project/Agent models** - EXISTS

### Soft Dependencies (Nice to Have)
1. ⚠️ **Claude Code CLI installed** - User responsibility
2. ⚠️ **MCP connection configured** - User setup once

### Blockers
❌ **None** - All dependencies met, just missing implementation

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MCP prompts don't work as expected | Medium | High | Test early with simple prompt |
| Project alias collisions | Low | Low | Use crypto-random generation |
| Claude Code can't write local files | Low | High | Test WebFetch + Write tools first |
| Restart requirement frustrates users | High | Medium | Clear UI messaging, one-time setup |
| Mission generation quality varies | Medium | Medium | Human review before launch |

---

## 7. Implementation Recommendation

### Phase 1: Foundation (6-8 hours)
1. ✅ Project alias system (database + API)
2. ✅ Agent template HTTP endpoints
3. ✅ MCP prompt infrastructure (commands.py)

### Phase 2: Core Commands (6-8 hours)
4. ✅ `/mcp__gil__fetch_agents` implementation
5. ✅ `/mcp__gil__activate_project` implementation
6. ✅ `/mcp__gil__launch_project` implementation
7. ✅ `/mcp__gil__update_agents` implementation

### Phase 3: Integration & Testing (4-6 hours)
8. ✅ End-to-end workflow testing
9. ✅ Error handling & edge cases
10. ✅ UI updates (show commands, copy buttons)
11. ✅ Documentation

**Total Estimated Effort: 16-22 hours**

---

## 8. Success Criteria

### Functional Requirements
- [ ] User can install agents with one command
- [ ] User can activate project with 6-char alias
- [ ] User can launch mission with subagent spawning
- [ ] User can update agents without manual downloads

### Non-Functional Requirements
- [ ] Commands complete in <30 seconds
- [ ] Error messages are clear and actionable
- [ ] Works across Windows/Mac/Linux
- [ ] No manual file management required

### User Experience
- [ ] ≤3 commands to go from project creation to mission launch
- [ ] ≤1 restart required (after fetch_agents)
- [ ] Dashboard shows command strings to copy
- [ ] Clear status feedback at each step

---

## 9. Verdict

### ✅ READY TO PROCEED

**Reasoning:**
- 47.5% of infrastructure already exists
- No hard blockers
- All dependencies met
- Clear implementation path
- Manageable scope (16-22 hours)

**Recommendation:**
Proceed to **Handover 0038: Implementation Plan**

---

## 10. Next Steps

1. Review this readiness assessment
2. Approve scope and timeline
3. Create detailed implementation plan (Handover 0038)
4. Begin Phase 1 development

---

**Assessment Completed By:** Claude (Sonnet 4.5)
**Assessment Date:** 2025-10-19
**Status:** ✅ READY FOR IMPLEMENTATION
