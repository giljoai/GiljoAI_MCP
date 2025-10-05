# Claude Code Orchestration Workflow

## Overview

This document explains how to orchestrate multi-agent projects using GiljoAI MCP with Claude Code's sub-agent system.

## Key Concept: Static Types, Dynamic Missions

**Claude Code agent types are predefined and cannot be created at runtime.**

However, you can:
- Map any MCP agent role to an existing Claude Code agent type
- Pass dynamic missions from MCP to Claude Code agents
- Spawn agents during orchestration with custom missions

## The One-Paste Workflow

### Step 1: Developer Creates Project in MCP

```python
# Via MCP tools or API
project = create_project(
    name="User Authentication System",
    mission="Implement secure user authentication with JWT tokens"
)

# Spawn agents
spawn_agent(name="Database Agent", role="database", mission="Design auth schema")
spawn_agent(name="Backend Agent", role="backend", mission="Implement JWT auth")
spawn_agent(name="Security Agent", role="security", mission="Security audit")
spawn_agent(name="Tester Agent", role="tester", mission="Write integration tests")
```

### Step 2: Generate Orchestrator Prompt

```python
# Call MCP tool to generate prompt
prompt = get_orchestrator_prompt(project_id="abc-123")

# Copy prompt to clipboard
print(prompt)
```

### Step 3: Developer Pastes into Claude Code CLI

```bash
# Developer opens Claude Code
claude code

# Pastes the generated prompt (example below)
```

**Example Generated Prompt:**

```
# GiljoAI MCP Orchestration Request

## Project Details
- **Project ID**: abc-123
- **Project Name**: User Authentication System
- **Mission**: Implement secure user authentication with JWT tokens

## Instructions for Orchestrator

You are coordinating a multi-agent project from GiljoAI MCP. Follow these steps:

1. **Verify MCP Connection**: Call `mcp__giljo-mcp__list_agents` to confirm you can read project agents
2. **Spawn Sub-Agents**: For each agent listed below, spawn a Claude Code sub-agent with the specified mission
3. **Coordinate Work**: Manage handoffs, track progress, and ensure completion

## Agents to Spawn (4 total)

### 1. Database Agent (database)
- **Claude Code Agent Type**: `database-expert`
- **MCP Agent ID**: `agent-001`
- **Mission**: Design auth schema with users, sessions, and tokens tables
- **Context Budget**: 50000 tokens

### 2. Backend Agent (backend)
- **Claude Code Agent Type**: `tdd-implementor`
- **MCP Agent ID**: `agent-002`
- **Mission**: Implement JWT authentication endpoints with proper error handling
- **Context Budget**: 60000 tokens

### 3. Security Agent (security)
- **Claude Code Agent Type**: `network-security-engineer`
- **MCP Agent ID**: `agent-003`
- **Mission**: Security audit of authentication implementation
- **Context Budget**: 40000 tokens

### 4. Tester Agent (tester)
- **Claude Code Agent Type**: `backend-integration-tester`
- **MCP Agent ID**: `agent-004`
- **Mission**: Write comprehensive integration tests for all auth endpoints
- **Context Budget**: 50000 tokens

## Workflow

1. Read full agent details from MCP using `mcp__giljo-mcp__list_agents`
2. Spawn each agent using the `Task` tool with the mapped Claude Code type
3. Coordinate their work according to the project mission
4. Track progress and handle handoffs as needed

Begin orchestration now.
```

### Step 4: Claude Code Orchestrator Executes

The orchestrator automatically:

1. **Reads from MCP:**
   ```python
   agents = mcp__giljo-mcp__list_agents(agent_id="current")
   # Gets all agent details from MCP server
   ```

2. **Spawns Sub-Agents:**
   ```python
   # For each agent from MCP
   Task(
       subagent_type="database-expert",
       description="Design auth schema",
       prompt="""
       Design authentication database schema.

       Requirements from MCP:
       - Users table with secure password hashing
       - Sessions table for JWT token management
       - Proper indexes and constraints

       MCP Agent ID: agent-001
       Report back to orchestrator when complete.
       """
   )
   ```

3. **Coordinates Execution:**
   - Database expert creates schema → Tester writes schema tests
   - Backend implementor builds endpoints → Security audits
   - Handoffs managed automatically

## Role Mapping Reference

| MCP Role | Claude Code Type | Use Case |
|----------|------------------|----------|
| `orchestrator` | `orchestrator-coordinator` | Top-level coordination |
| `database` | `database-expert` | Schema design, queries, migrations |
| `backend` | `tdd-implementor` | API endpoints, business logic |
| `frontend` | `ux-designer` | UI/UX design and implementation |
| `tester` | `backend-integration-tester` | Testing and QA |
| `researcher` | `deep-researcher` | Research and investigation |
| `architect` | `system-architect` | Architecture decisions |
| `security` | `network-security-engineer` | Security review and hardening |
| `documentation` | `documentation-manager` | Docs and knowledge management |
| `reviewer` | `general-purpose` | Code review and analysis |

## Advanced: Dynamic Role Detection

The orchestrator can also discover agents dynamically:

```python
# Orchestrator reads project
project_info = mcp__giljo-mcp__list_projects(status="active")
agents = mcp__giljo-mcp__list_agents(agent_id="current")

# Maps roles automatically
for agent in agents:
    claude_type = map_mcp_role_to_claude_type(agent.role)
    spawn_subagent(
        type=claude_type,
        mission=agent.mission,
        mcp_agent_id=agent.id
    )
```

## Benefits of This Approach

1. **Single Entry Point**: Developer pastes one prompt, everything else is automatic
2. **No Manual Agent Creation**: No need to configure Claude Code before starting
3. **Dynamic Missions**: Missions come from MCP, not hardcoded
4. **Flexible Mapping**: Same Claude Code type can serve multiple MCP roles
5. **Persistent State**: MCP maintains state, Claude Code provides execution

## Troubleshooting

### Problem: "Agent type not found"
**Solution**: Check role mapping in `claude_code_integration.py`. Use `general-purpose` as fallback.

### Problem: "Cannot spawn agent during execution"
**Solution**: All agent spawning must happen in the orchestrator's initial phase, not mid-execution.

### Problem: "Mission not specific enough"
**Solution**: Enhance mission descriptions in MCP when spawning agents. Include:
- Specific deliverables
- Context about dependencies
- Success criteria

## Example: Complete Flow

```bash
# 1. Developer creates project in MCP (via API or tools)
curl -X POST http://localhost:7272/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Auth System",
    "mission": "Build JWT authentication"
  }'

# 2. Spawn agents via MCP
curl -X POST http://localhost:7272/api/agents \
  -d '{"name": "DB Agent", "role": "database", ...}'

# 3. Get orchestrator prompt
curl http://localhost:7272/api/orchestrate/abc-123

# 4. Copy output and paste into Claude Code CLI
claude code
# [paste prompt]

# 5. Watch orchestrator spawn agents and coordinate work
# All happens automatically!
```

## Next Steps

1. Implement `get_orchestrator_prompt` MCP tool
2. Add role mapping to your agent spawning logic
3. Test with a simple 2-agent project
4. Scale to complex multi-agent workflows
