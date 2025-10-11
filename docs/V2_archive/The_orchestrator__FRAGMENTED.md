# The Orchestrator Agent - Complete Implementation Guide

**Source:** AKE-MCP Project (F:/AKE-MCP)
**Target:** GiljoAI-MCP Implementation
**Date:** January 2025

---

## Table of Contents

1. [Overview](#1-overview)
2. [Orchestrator Role Definition](#2-orchestrator-role-definition)
3. [Initialization & Startup](#3-initialization--startup)
4. [In-App Profiling System](#4-in-app-profiling-system)
5. [Context Loading Architecture](#5-context-loading-architecture)
6. [Discovery Workflow](#6-discovery-workflow)
7. [Agent Coordination & Spawning](#7-agent-coordination--spawning)
8. [Orchestrator Prompts & Instructions](#8-orchestrator-prompts--instructions)
9. [Sub-Agent Kickoff Patterns](#9-sub-agent-kickoff-patterns)
10. [Vision Document Management](#10-vision-document-management)
11. [After-Action Documentation](#11-after-action-documentation-mandatory)
12. [Database Schema](#12-database-schema)
13. [MCP Tools Reference](#13-mcp-tools-reference)
14. [Implementation Checklist](#14-implementation-checklist-for-giljoai-mcp)
15. [Code Examples](#15-code-examples)
16. [Anti-Patterns to Avoid](#16-anti-patterns-to-avoid)

---

## 1. Overview

### What the Orchestrator Is

The orchestrator is a **Project Manager/Team Lead agent** (NOT a CEO) that coordinates specialized worker agents to complete complex projects. It acts as the central coordinator that:

- **Discovers context dynamically** using MCP tools (Serena MCP, vision documents, config)
- **Creates specific missions** for worker agents based on discoveries
- **Spawns and coordinates agents** through a database-driven message queue
- **Delegates work** rather than executing implementation itself
- **Monitors progress** and handles handoffs between agents
- **Documents outcomes** with mandatory after-action reports

### Core Philosophy

**"You're a project manager, not a solo developer. Your value is in coordination and delegation, not in doing all the work yourself."**

The orchestrator follows the **30-80-10 principle**:
- **30% Discovery**: Explore codebase, read vision, review settings
- **80% Delegation**: Coordinate agents, plan work, manage handoffs
- **10% Closure**: Create documentation, validate, close project

### Key Innovation

**Hierarchical Context Loading**: The orchestrator gets FULL context (all vision + all config), while worker agents get FILTERED context based on their specific role.

---

## 2. Orchestrator Role Definition

### Role: Project Manager & Team Lead

**Location:** `F:/AKE-MCP/server.py` - `generate_orchestrator_mission()` (lines 95-268)

```python
def generate_orchestrator_mission(project_name: str, project_mission: str, product_name: str, agents: list) -> str:
    """Generate the orchestrator mission with consistent instructions"""
    return f"""
    You are the Project Manager and Team Lead for: {project_name}

    PROJECT: {project_name}
    PRODUCT: {product_name}
    INITIAL DESCRIPTION: {project_mission}

    YOUR ROLE: Project Manager & Team Lead (NOT CEO)
    - You coordinate and lead the team
    - You ensure project success through delegation
    - The user has final authority on all decisions
    - You document everything for transparency
    """
```

### The 30-80-10 Effort Distribution

1. **Discovery Phase (30% effort)**
   - Use Serena MCP to explore codebase
   - Read vision documents dynamically
   - Review product settings
   - Find pain points and successes from recent devlogs

2. **Delegation Planning (80% effort)**
   - Create specific missions based on discoveries
   - Spawn worker agents with bounded scope
   - Coordinate work through message queue
   - Monitor progress and handle handoffs
   - **Never do implementation work yourself**

3. **Project Closure (10% effort)**
   - Create after-action documentation (3 reports)
   - Validate all documentation exists
   - Close project only after validation

### The "3-Tool Rule"

**Critical Pattern:** If the orchestrator finds itself using more than 3 tools in sequence for implementation work, it MUST STOP and delegate to an agent instead.

```python
# ❌ WRONG - Orchestrator doing implementation
orchestrator.read_file('config.py')
orchestrator.edit_file('config.py', changes)
orchestrator.run_tests()
orchestrator.commit_changes()
# More than 3 tools = should delegate!

# ✅ CORRECT - Orchestrator delegating
ensure_agent('implementer', 'Update config.py with new settings')
assign_job('implementer', 'implementation', project_id, [
    "Update config.py with database settings",
    "Run tests to validate changes",
    "Commit changes with clear message"
])
```

### Mission Creation Requirements

**MANDATORY:** Never create generic missions. Always create SPECIFIC missions based on discoveries.

```python
# ❌ WRONG - Generic mission
mission = "Update the documentation"

# ✅ CORRECT - Specific mission based on discoveries
mission = """Update CLAUDE.md to:
1. Fix SQL patterns found in session_20240112.md (lines 45-67)
2. Add vLLM config from docs/deployment/vllm_setup.md
3. Remove deprecated Ollama references (search found 12 instances)
4. Add new agent coordination patterns from recent devlog
"""
```

---

## 3. Initialization & Startup

### Agent Activation Mechanisms

**Two Different Functions for Different Purposes:**

#### For Orchestrator Only: `activate_agent()`

```python
# Triggers immediate discovery workflow
activate_agent(project_id, 'orchestrator', mission)
# - Loads FULL context (all vision + all config)
# - Starts discovery phase immediately
# - Only used for orchestrator
```

#### For Worker Agents: `ensure_agent()` (Idempotent)

```python
# Creates or returns existing agent - safe to call multiple times
ensure_agent(project_id, 'analyzer', mission)
# - Idempotent: won't create duplicates
# - Returns existing agent if already exists
# - Safe for worker agents
```

### Startup Workflow

```
User Request → Project Creation → Switch/Activate Project → Orchestrator Activation → Discovery Phase → Mission Creation → Agent Spawning
```

**Location:** `F:/AKE-MCP/server.py` - `switch_project()` (lines 343-399)

```python
@mcp.tool()
def switch_project(project_id: str) -> Dict:
    """Switch to a different project"""
    # Update status to active
    db.update_project_status(project_id, "active")

    # Check if orchestrator exists
    has_orchestrator = db.get_active_job(project_id, 'orchestrator')

    if not has_orchestrator:
        # Get product for dynamic discovery
        product = db.get_active_product()

        # Generate orchestrator mission
        orchestrator_mission = generate_orchestrator_mission(
            project["name"],
            project.get("description", ""),
            product_name,
            agents
        )

        # Create orchestrator session with FULL context
        orchestrator_session = session_mgr.create_session(
            agent_name="orchestrator",
            project_id=project_id,
            mission=orchestrator_mission,
            job_type="orchestration"
        )
```

---

## 4. In-App Profiling System

### Three-Level Profiling Architecture

#### 4.1 Project Profiling

**Table:** `mcp_projects`

```sql
CREATE TABLE mcp_projects (
    id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES mcp_products(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,                    -- User's initial input
    mission TEXT,                        -- Orchestrator's expanded mission after discovery
    orchestrator_sequence TEXT[],        -- Ordered agent list ["analyzer", "implementer", "tester"]
    current_agent VARCHAR(100),          -- Which agent is working now
    current_step INTEGER DEFAULT 0,      -- Progress through sequence
    status VARCHAR(50) DEFAULT 'planning',
    context_used DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Key Fields:**
- `description`: The user's original request (input to orchestrator)
- `mission`: The orchestrator's specific, actionable mission created after discovery
- `orchestrator_sequence`: Ordered list of agents to execute work
- `current_agent` + `current_step`: Track workflow progress

#### 4.2 Agent Profiling

**Table:** `mcp_agent_jobs`

```sql
CREATE TABLE mcp_agent_jobs (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(50) REFERENCES mcp_projects(id),
    agent_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL,      -- 'orchestration', 'analysis', 'implementation', etc.
    mission TEXT,
    status VARCHAR(50) DEFAULT 'created',
    health VARCHAR(20) DEFAULT 'green', -- green/yellow/orange/red
    context_used DECIMAL(5,2) DEFAULT 0.0,
    max_context DECIMAL(5,2) DEFAULT 100.0,
    handoff_context JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(project_id, agent_name)      -- One job per agent per project
);
```

**State Machine:**
```
CREATED → ACTIVE → READY_FOR_HANDOFF → COMPLETED/FAILED → DECOMMISSIONED
```

**Health Status:**
- `green`: < 50% context used, healthy
- `yellow`: 50-75% context used, warning
- `orange`: 75-90% context used, critical
- `red`: > 90% context used, needs handoff

#### 4.3 Context Profiling

**Field:** `config_data` JSONB in `mcp_products` table

```json
{
    "architecture": "FastAPI + PostgreSQL + Vue.js",
    "tech_stack": ["Python 3.11", "PostgreSQL 18", "Vue 3"],
    "codebase_structure": {
        "api": "REST endpoints",
        "frontend": "Vue dashboard",
        "core": "Orchestration engine"
    },
    "critical_features": ["Multi-tenant isolation", "Agent coordination"],
    "test_commands": ["pytest tests/", "npm run test"],
    "known_issues": ["Port conflicts", "WebSocket drops"],
    "serena_mcp_enabled": true,
    "api_docs": "/docs/api_reference.md",
    "documentation_style": "Markdown with mermaid diagrams"
}
```

---

## 5. Context Loading Architecture

### Hierarchical Context Loading

**Location:** `F:/AKE-MCP/core/session_manager.py` - `prepare_agent_context()` (lines 200-243)

```python
def prepare_agent_context(self, agent_name: str, project_id: str) -> Dict:
    """Prepare context for agent - HIERARCHICAL LOADING"""

    job = self.db.get_active_job(project_id, agent_name)
    is_orchestrator = agent_name.lower() == "orchestrator" or (job and job.get("job_type") == "orchestration")

    if is_orchestrator:
        # ORCHESTRATOR: Gets FULL context
        vision_content = self.load_product_vision(product)
        if vision_content:
            context["product"]["vision"] = vision_content

        # Add ALL config data
        if product.get("config_data"):
            context["product"]["config"] = product["config_data"]

        logger.info("Loaded FULL context for orchestrator (vision + all config)")

    else:
        # WORKER AGENTS: Get FILTERED context
        context["product"]["vision_summary"] = self._get_vision_summary(product)
        context["product"]["relevant_config"] = self._get_filtered_config(agent_name, product)

        logger.info(f"Loaded FILTERED context for {agent_name}")
```

### Role-Based Config Filtering

**Location:** `F:/AKE-MCP/core/session_manager.py` - `_get_filtered_config()` (lines 436-466)

```python
def _get_filtered_config(self, agent_name: str, product: Dict) -> Dict:
    """Get filtered config based on agent role"""
    config = product["config_data"]
    filtered = {}
    agent_lower = agent_name.lower()

    if "developer" in agent_lower or "implementer" in agent_lower:
        # Developers get architecture, tech stack, codebase info
        filtered["architecture"] = config.get("architecture", "")
        filtered["tech_stack"] = config.get("tech_stack", "")
        filtered["codebase_structure"] = config.get("codebase_structure", "")

    elif "test" in agent_lower or "qa" in agent_lower:
        # Testers get test config, critical features
        filtered["test_config"] = config.get("test_config", "")
        filtered["test_commands"] = config.get("test_commands", "")
        filtered["critical_features"] = config.get("critical_features", "")

    elif "document" in agent_lower or "doc" in agent_lower:
        # Documenters get API docs and style info
        filtered["api_docs"] = config.get("api_docs", "")
        filtered["documentation_style"] = config.get("documentation_style", "")

    elif "design" in agent_lower:
        # Designers get architecture and patterns
        filtered["architecture"] = config.get("architecture", "")

    # All agents get basic features and database info
    filtered["features"] = config.get("features", [])
    filtered["database_name"] = config.get("database_name", "")

    return filtered
```

---

## 6. Discovery Workflow

### Step-by-Step Discovery Process

**Pattern from orchestrator mission (F:/AKE-MCP/server.py, lines 112-132):**

```
1. Serena MCP First → 2. Vision Second → 3. Settings Third → 4. Create Mission → 5. Spawn Agents
```

#### Phase 1: Serena MCP Discovery (Primary Intelligence)

```python
# a. USE SERENA MCP FIRST to explore and understand:
serena.list_dir("/docs/devlog/", recursive=False)      # Recent sessions
serena.list_dir("/docs/", recursive=True)              # Full documentation structure
serena.read_file("CLAUDE.md")                          # Current context state
serena.read_file("CLAUDE.local.md")                    # Local context
serena.get_file_summary()                              # Last 3-5 devlogs - Recent learnings
serena.search_files("problem|issue|bug|fix")           # Find pain points
serena.search_files("pattern|solution|works")          # Find successes
```

#### Phase 2: Vision Document Reading

```python
# b. THEN read vision using get_vision() - ALL parts
get_vision_index()                                     # Get structure (creates index on first call)
get_vision(1)                                          # Read part 1
get_vision(2)                                          # Read part 2
# ... continue for all parts
```

#### Phase 3: Product Settings Review

```python
# c. Review product settings with get_product_settings()
settings = get_product_settings()
# Note any missing fields and use Serena to find them
```

#### Phase 4: Mission Creation (MANDATORY)

```python
# ✅ Use intelligence from discoveries to create SPECIFIC mission
mission = """
Based on discoveries:
1. Fix SQL patterns from session_20240112.md (serena found these)
2. Add vLLM config from docs/deployment/vllm_setup.md (vision part 3)
3. Remove deprecated Ollama refs (serena search found 12 instances)
4. Success criteria: All tests pass, config validated
"""

# ❌ NEVER create generic mission
mission = "Update the configuration"  # TOO VAGUE!
```

### Anti-Pattern: Static Context Loading

**DON'T DO THIS:**
```python
# ❌ Pre-building static contexts
context = load_all_files_into_memory()
# This wastes tokens and gives stale information
```

**DO THIS:**
```python
# ✅ Dynamic discovery on-demand
serena.search_files("relevant_pattern")  # Only when needed
get_vision(specific_chunk)                # Only specific parts
```

---

## 7. Agent Coordination & Spawning

### 7.1 Spawning Mechanisms

#### activate_agent() - For Orchestrator Only

**Location:** `F:/AKE-MCP/server.py`

```python
@mcp.tool()
def activate_agent(project_id: str, agent_name: str) -> Dict:
    """
    Activate an agent and trigger its workflow
    Used ONLY for orchestrator - triggers immediate discovery
    """
    # Create session with FULL context
    session = session_mgr.create_session(
        agent_name=agent_name,
        project_id=project_id,
        mission=mission,
        job_type="orchestration"
    )

    # Return activation message
    return {
        "success": True,
        "message": f"Execute MCP: ake-mcp-v2.activate_agent('{project_id}', '{agent_name}')",
        "instructions": "Then call get_messages() to retrieve mission"
    }
```

#### ensure_agent() - For Worker Agents (Idempotent)

```python
@mcp.tool()
def ensure_agent(project_id: str, agent_name: str, mission: str) -> Dict:
    """
    Ensure agent exists - get or create (IDEMPOTENT)
    Safe to call multiple times - won't create duplicates
    """
    # Check if agent exists
    existing_job = db.get_active_job(project_id, agent_name)

    if existing_job:
        return {
            "success": True,
            "agent_id": existing_job["id"],
            "status": "existing",
            "message": f"Agent {agent_name} already exists"
        }

    # Create new agent with filtered context
    job_id = db.create_agent_job(
        project_id=project_id,
        agent_name=agent_name,
        job_type=infer_job_type(agent_name),
        mission=mission
    )

    return {
        "success": True,
        "agent_id": job_id,
        "status": "created",
        "message": f"Created agent {agent_name}"
    }
```

#### assign_job() - Give Agents Work (Also Idempotent)

```python
@mcp.tool()
def assign_job(agent_name: str, job_type: str, project_id: str, tasks: List[str]) -> Dict:
    """
    Assign or update job for an agent (IDEMPOTENT)
    Updates existing job or creates new one
    """
    # Check for existing job
    existing_job = db.get_active_job(project_id, agent_name)

    if existing_job:
        # Update existing job
        db.update_job_tasks(existing_job["id"], tasks)
        return {"success": True, "status": "updated"}

    # Create new job
    job_id = db.create_agent_job(
        project_id=project_id,
        agent_name=agent_name,
        job_type=job_type,
        tasks=tasks
    )

    return {"success": True, "status": "created", "job_id": job_id}
```

### 7.2 Message Queue System

**Table:** `mcp_messages`

```sql
CREATE TABLE mcp_messages (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(50) REFERENCES mcp_projects(id),
    from_agent VARCHAR(100) NOT NULL,
    to_agents TEXT[] NOT NULL,              -- PostgreSQL array for multiple recipients
    message_type VARCHAR(50) NOT NULL,      -- broadcast, direct, handoff, status, error, completion
    priority VARCHAR(20) DEFAULT 'normal',  -- low, normal, high, critical
    content TEXT NOT NULL,
    metadata JSONB,
    acknowledged_by TEXT[] DEFAULT '{}',    -- Track who acknowledged
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Message Types

```python
MESSAGE_TYPES = {
    "broadcast": "Message to all agents",
    "direct": "Message to specific agent(s)",
    "handoff": "Context handoff between agents",
    "status": "Status update",
    "error": "Error notification",
    "completion": "Task completion notification"
}
```

#### Priority Levels

```python
PRIORITY_LEVELS = {
    "low": "FYI, no action needed",
    "normal": "Standard message",
    "high": "Needs attention soon",
    "critical": "Immediate action required"
}
```

#### Message Routing with PostgreSQL Arrays

```python
# Send message to multiple agents
send_message(
    from_agent='orchestrator',
    to_agents=['analyzer', 'implementer'],  # PostgreSQL TEXT[]
    content='Start analysis phase',
    message_type='direct',
    priority='high',
    project_id='project_123'
)

# Check acknowledgments
SELECT * FROM mcp_messages
WHERE 'analyzer' = ANY(acknowledged_by)  -- PostgreSQL array contains check
```

#### Acknowledgment Tracking

```python
@mcp.tool()
def acknowledge_message(agent_name: str, message_id: str) -> Dict:
    """Acknowledge receipt of a message"""
    with db.transaction() as cur:
        cur.execute("""
            UPDATE mcp_messages
            SET acknowledged_by = array_append(acknowledged_by, %s)
            WHERE id = %s
            AND NOT (%s = ANY(acknowledged_by))  -- Don't duplicate
        """, (agent_name, message_id, agent_name))

    return {"success": True, "acknowledged": True}
```

### 7.3 Inter-Agent Communication Protocol

**From orchestrator mission (F:/AKE-MCP/server.py, lines 229-238):**

```
MANDATORY AGENT COORDINATION RULES:
✅ Tell user if agents should run in parallel at start or started in order
✅ Tell all agents to acknowledge messages as they read them using acknowledge_message()
✅ Only use handoff() MCP feature upon context limit and moving to agent #2 of same type
✅ Agents should communicate questions/advice to orchestrator who will ask the user
✅ Agents shall communicate status when completed to next agent and report to orchestrator
✅ Agents can start preparing work while waiting for completion message from prior agent

INTER-AGENT COMMUNICATION PROTOCOL:
- Every agent MUST acknowledge messages immediately upon receipt
- Status updates go to: next agent in pipeline + orchestrator
- Questions/blockers go to: orchestrator only (who asks user)
- Handoffs only for: context exhaustion or same-type agent rotation
- Parallel work allowed: agents can prep while waiting for dependencies
```

---

## 8. Orchestrator Prompts & Instructions

### Complete Orchestrator Mission Template

**Location:** `F:/AKE-MCP/server.py` - `generate_orchestrator_mission()` (lines 95-268)

```python
def generate_orchestrator_mission(project_name: str, project_mission: str, product_name: str, agents: list) -> str:
    return f"""
You are the Project Manager and Team Lead for: {project_name}

PROJECT: {project_name}
PRODUCT: {product_name}
INITIAL DESCRIPTION: {project_mission}

YOUR ROLE: Project Manager & Team Lead (NOT CEO)
- You coordinate and lead the team
- You ensure project success through delegation
- The user has final authority on all decisions
- You document everything for transparency

CRITICAL: REQUIRED FIRST STEPS (MUST DO IN ORDER):

1. DISCOVERY PHASE - SERENA FIRST (30% of effort):
   YOU ARE THE PRIMARY USER OF SERENA! Use it to discover intelligence:

   a. USE SERENA MCP FIRST to explore and understand:
      - serena.list_dir("/docs/devlog/", recursive=false) - Recent sessions
      - serena.list_dir("/docs/", recursive=true) - Full documentation structure
      - serena.read_file("CLAUDE.md") - Current context state
      - serena.read_file("CLAUDE.local.md") - Local context
      - serena.get_file_summary() on last 3-5 devlogs - Recent learnings
      - serena.search_files("problem|issue|bug|fix") - Find pain points
      - serena.search_files("pattern|solution|works") - Find successes

   b. THEN read vision using get_vision() - ALL parts
      - First call creates index automatically
      - Read ALL parts: get_vision(1), get_vision(2), etc.
      - Use get_vision_index() to navigate topics

   c. Review product settings with get_product_settings()
      - Note any missing fields and use Serena to find them

   Serena is YOUR research assistant during discovery, not just for other agents!

2. MISSION CREATION (MANDATORY - Based on Serena discoveries):
   ✅ Use intelligence from Serena to create SPECIFIC mission
   ✅ Include problems found, patterns discovered, success criteria
   ✅ Example: "Update CLAUDE.md to fix SQL patterns (from session_X), add vLLM config (from docs/Y), remove deprecated Ollama refs"
   ❌ NEVER create generic mission - use Serena's discoveries
   ❌ NEVER proceed without setting mission - critical failure

3. AGENT ACTIVATION - PROPER FUNCTION USAGE:
   ℹ️ IMPORTANT: Different functions for different purposes!

   FOR ORCHESTRATOR (you):
   - activate_agent() - Triggers immediate discovery and workflow
   - Only used for orchestrator, starts working immediately

   FOR WORKER AGENTS:
   - ensure_agent() - Creates or returns existing worker agent
   - IDEMPOTENT: Safe to call multiple times - won't create duplicates
   - Use this when creating your team members

   WORKFLOW:
   a. You were started with activate_agent() - now START DISCOVERY
   b. After discovery, use ensure_agent() to create worker agents
   c. Use assign_job() to give workers their tasks (also idempotent!)
   d. Send messages to coordinate work

   Example workflow:
   - ensure_agent('project_id', 'doc_analyzer') - Creates/gets analyzer
   - assign_job('doc_analyzer', 'analysis', ...) - Gives them work
   - send_message(['analyzer'], 'Start analysis', 'project_id', from_agent='orchestrator')
   - ALWAYS specify from_agent when sending messages!

4. DELEGATION PLANNING (80% of effort):
   Create your agent pipeline with clear roles:
   - analyzer: For research and analysis tasks
   - implementer: For code creation and updates
   - tester: For validation and quality assurance
   - documenter: For documentation updates

   AGENT MANAGEMENT BEST PRACTICES:
   ✅ UNDERSTANDING ensure_agent() and assign_job() BEHAVIOR:

   BOTH functions are now IDEMPOTENT:
   - ensure_agent(): Ensures agent exists (get or create)
   - assign_job(): Updates existing job or creates new one
   - Both safe to call multiple times - won't create duplicates
   - Clear names convey their idempotent behavior

   ✅ RECOMMENDED WORKFLOW:
   1. project_status('project_id') - See your current team
   2. For any agent: ensure_agent('project', 'analyzer', 'mission')
   3. To give work: assign_job('analyzer', 'analysis', 'project', tasks)
   4. Send coordination messages with send_message()

   📝 WHY CHECK project_status() FIRST?
   - Helps you understand team composition
   - Makes your coordination more intentional
   - Avoids unnecessary activate_agent() calls
   - Clearer delegation strategy

   SERENA ACCESS FOR AGENTS:
   ✅ Tell agents: "You have Serena MCP for file operations"
   ✅ Give specific targets: "Use serena.read_file('CLAUDE.md') to get current state"
   ✅ Bound their scope: "Search only in /docs/devlog/session_X.md for patterns"
   ❌ NEVER let agents explore broadly - you already did that
   Example: "Analyzer: Use serena to read /docs/devlog/session_20240112.md and extract SQL patterns"

   VISION TRANSLATION FOR AGENTS:
   ✅ Extract specific requirements from vision for each agent
   ✅ Give agents concrete instructions, NOT vision references
   ✅ Example: "Use two-phase retrieval with 0.82 threshold" not "see Ch7"
   ❌ NEVER tell agents to "read vision Ch X if needed"

   DELEGATION RULES:
   ✅ ALWAYS delegate if task requires:
      - More than 3 tool calls
      - Specialized knowledge
      - Code implementation
      - Testing/validation
      - Parallel processing

   ❌ NEVER do the work yourself except:
      - Setting project mission
      - Activating agents
      - Coordinating handoffs
      - Final project summary

   If you find yourself using more than 3 tools in sequence for implementation,
   STOP and delegate to an agent instead.

5. EXECUTION MANAGEMENT (coordination only):
   - Use assign_job() to give agents specific tasks
   - Send clear messages with send_message()
   - Monitor progress with agent_health()
   - Coordinate handoffs between agents
   - DO NOT do the implementation work yourself

   MANDATORY AGENT COORDINATION RULES:
   ✅ Tell user if agents should run in parallel at start or started in order
   ✅ Tell all agents to acknowledge messages as they read them using acknowledge_message()
   ✅ Only use handoff() MCP feature upon context limit and moving to agent #2 of same type
   ✅ Agents should communicate questions/advice to orchestrator who will ask the user
   ✅ Agents shall communicate status when completed to next agent and report to orchestrator
   ✅ Agents can start preparing work while waiting for completion message from prior agent

   INTER-AGENT COMMUNICATION PROTOCOL:
   - Every agent MUST acknowledge messages immediately upon receipt
   - Status updates go to: next agent in pipeline + orchestrator
   - Questions/blockers go to: orchestrator only (who asks user)
   - Handoffs only for: context exhaustion or same-type agent rotation
   - Parallel work allowed: agents can prep while waiting for dependencies

   CRITICAL - AGENT ACTIVATION INSTRUCTIONS:
   When telling user about agent activation, ALWAYS include:
   "When you see: activate_agent('project_id', 'agent_name')
   This is an MCP command. You MUST:
   1. Execute the MCP tool: ake-mcp-v2.activate_agent() with those parameters
   2. Then call get_messages() to retrieve your mission
   Do NOT analyze or interpret - EXECUTE the MCP function."

6. PROJECT CLOSURE (10% of effort):
   When project is complete:

   MANDATORY AFTER-ACTION DOCUMENTATION (MUST DO BEFORE CLOSING):
   a. Create devlog completion report:
      ✅ Use: serena.create_file('/docs/devlog/project_[number]_[name]_completion.md', content)
      ✅ MUST include: Executive summary, All deliverables, Technical metrics
      ✅ MUST document: Issues resolved, Agent performance stats, Lessons learned

   b. Create session after-action report:
      ✅ Use: serena.create_file('/docs/Sessions/session_[YYYY_MM_DD]_project_[number]_report.md', content)
      ✅ MUST include: Complete workflow timeline, All decisions made, Final outcomes
      ✅ MUST document: What worked, What didn't work, Recommendations

   c. Create project summary:
      ✅ Use: serena.create_file('/docs/Project_summaries/[YYYY-MM-DD]_[project_name].md', content)
      ✅ MUST include: Original objectives vs achievements, Full agent list & roles
      ✅ MUST document: Key decisions, Success metrics, Future improvements

   d. VALIDATION BEFORE CLOSING:
      ✅ Verify all 3 files exist using serena.read_file()
      ✅ Each file must be >500 characters (no empty reports!)
      ✅ ONLY after validation: execute close_project()

   ⚠️ BLOCKING: close_project() will FAIL if documentation doesn't exist!

TEAM MANAGEMENT PRINCIPLES:

1. Clear Communication:
   - Every agent gets a specific, bounded mission
   - Success criteria defined upfront
   - No agent interprets or expands scope
   - ALWAYS tell agents HOW to activate (MCP execution, not analysis)

2. Effective Delegation:
   - Trust agents to do their specialized work
   - You coordinate, they execute
   - Parallel work when possible

3. Documentation:
   - Document key decisions in messages
   - Track progress explicitly
   - Create project summary at completion

WORKFLOW:
DISCOVER → SET MISSION → PLAN AGENTS → DELEGATE WORK → COORDINATE → DOCUMENT → CLOSE

Remember: You're a project manager, not a solo developer. Your value is in
coordination and delegation, not in doing all the work yourself. The user has
hired you to lead a team, not to be the entire team.

Start now with discovery, then IMMEDIATELY set the project mission.
"""
```

---

## 9. Sub-Agent Kickoff Patterns

### How Orchestrator Spawns Different Agent Types

#### Pattern: ensure_agent() + assign_job() + send_message()

```python
# 1. Ensure agent exists (idempotent)
ensure_agent(
    project_id='proj_123',
    agent_name='researcher',
    mission='Research database migration patterns'
)

# 2. Assign specific job (idempotent)
assign_job(
    agent_name='researcher',
    job_type='research',
    project_id='proj_123',
    tasks=[
        "Search /docs/devlog/ for migration patterns",
        "Read TECHNICAL_ARCHITECTURE.md for current DB schema",
        "Analyze PostgreSQL best practices from vision Ch5",
        "Compile findings into structured report"
    ]
)

# 3. Send activation message
send_message(
    from_agent='orchestrator',
    to_agents=['researcher'],
    content='''Start research phase. Use Serena MCP with these specific targets:
    - serena.search_files("migration|alembic|schema") in /docs/devlog/
    - serena.read_file("TECHNICAL_ARCHITECTURE.md")
    Compile findings and report back to orchestrator.''',
    message_type='direct',
    priority='high',
    project_id='proj_123'
)
```

### Researcher Agent Kickoff

```python
# Orchestrator spawns researcher
ensure_agent('proj_123', 'researcher',
    '''Research authentication patterns:
    1. Use serena.search_files("auth|jwt|api_key") in /api/
    2. Read vision Ch3 (security requirements)
    3. Analyze existing auth implementation
    4. Document findings with code examples''')

assign_job('researcher', 'research', 'proj_123', [
    "Search for auth patterns in /api/",
    "Extract requirements from vision Ch3",
    "Document current vs required auth",
    "Create recommendations report"
])

send_message(
    from_agent='orchestrator',
    to_agents=['researcher'],
    content='Begin auth research. Bounded scope: /api/ directory only. Report findings to orchestrator.',
    message_type='direct',
    priority='high',
    project_id='proj_123'
)
```

### Implementer Agent Kickoff

```python
# Orchestrator spawns implementer
ensure_agent('proj_123', 'implementer',
    '''Implement API key authentication:
    1. Add api_keys table to database (use Alembic)
    2. Create /api/auth/validate endpoint
    3. Add middleware to api/app.py
    4. Update config to enable auth for server mode
    Based on researcher's findings in message #456''')

assign_job('implementer', 'implementation', 'proj_123', [
    "Create Alembic migration for api_keys table",
    "Implement /api/auth/validate endpoint",
    "Add auth middleware to api/app.py",
    "Update config.yaml template for auth settings",
    "Run tests and fix any failures"
])

send_message(
    from_agent='orchestrator',
    to_agents=['implementer'],
    content='''Implement auth based on researcher findings (msg #456).
    Use serena.read_file() to review existing patterns.
    All code must follow CLAUDE.md guidelines.
    Report completion to orchestrator + tester.''',
    message_type='direct',
    priority='high',
    project_id='proj_123'
)
```

### Tester Agent Kickoff

```python
# Orchestrator spawns tester
ensure_agent('proj_123', 'tester',
    '''Test API key authentication:
    1. Create integration tests for /api/auth/validate
    2. Test middleware with valid/invalid keys
    3. Test multi-tenant isolation with auth
    4. Validate config-driven auth enable/disable
    Implementation by implementer in message #789''')

assign_job('tester', 'testing', 'proj_123', [
    "Write integration tests for auth endpoint",
    "Test valid/invalid/expired API keys",
    "Test multi-tenant isolation",
    "Test localhost vs server mode behavior",
    "Run full test suite and report results"
])

send_message(
    from_agent='orchestrator',
    to_agents=['tester'],
    content='''Test auth implementation (implementer msg #789).
    Create tests in tests/integration/test_auth.py
    Follow pytest patterns from existing tests.
    Report: pass/fail + coverage to orchestrator.''',
    message_type='direct',
    priority='high',
    project_id='proj_123'
)
```

### Documenter Agent Kickoff

```python
# Orchestrator spawns documenter
ensure_agent('proj_123', 'documenter',
    '''Document API key authentication:
    1. Update docs/deployment/AUTHENTICATION.md
    2. Add API reference for /api/auth/validate
    3. Update CLAUDE.md with new patterns
    4. Create session memory for this work
    Based on tester results in message #101''')

assign_job('documenter', 'documentation', 'proj_123', [
    "Update deployment guide with auth setup",
    "Document API endpoint in API reference",
    "Add auth patterns to CLAUDE.md",
    "Create session memory with learnings"
])

send_message(
    from_agent='orchestrator',
    to_agents=['documenter'],
    content='''Document completed auth feature.
    Use serena.read_file() to review implementation.
    Follow documentation style from existing docs.
    Include code examples and config snippets.
    Report completion to orchestrator.''',
    message_type='direct',
    priority='normal',
    project_id='proj_123'
)
```

### Handoff Procedures

```python
# When agent reaches context limit
@mcp.tool()
def handoff(from_agent: str, to_agent: str, context: Dict, project_id: str) -> Dict:
    """
    Handoff work between agents (same type, context exhaustion)
    NOT for general coordination - use send_message() for that
    """
    # Mark from_agent as ready_for_handoff
    db.update_job_status(project_id, from_agent, 'ready_for_handoff')

    # Store handoff context
    db.update_job_handoff_context(project_id, from_agent, context)

    # Create/activate to_agent with handoff context
    ensure_agent(project_id, to_agent, f"Continue work from {from_agent}")

    # Send handoff message
    send_message(
        from_agent=from_agent,
        to_agents=[to_agent],
        content=f"Handoff from {from_agent}. Context attached.",
        message_type='handoff',
        priority='critical',
        project_id=project_id,
        metadata=context
    )

    return {"success": True, "handoff_complete": True}
```

---

## 10. Vision Document Management

### Vision Document Structure

**Supports:**
- Single vision file: `vision.md`
- Directory of files: `vision/part1.md, vision/part2.md, ...`

### Automatic Index Creation

**On first `get_vision()` call:**

```python
# First call to get_vision() creates index
index = get_vision_index()  # Returns index, creates if doesn't exist

# Index structure
{
    'total_chunks': 8,
    'chars_per_chunk': 15000,
    'files': [
        {
            'name': 'vision_part1.md',
            'topics': ['Context Management', 'RAG Architecture'],
            'chunks': [1, 2, 3],
            'size': 45000,
            'lines': 1200,
            'char_position': 0,
            'path': '/product/vision/vision_part1.md'
        },
        {
            'name': 'vision_part2.md',
            'topics': ['Agent Coordination', 'Message Queue'],
            'chunks': [4, 5],
            'size': 30000,
            'lines': 800,
            'char_position': 45000,
            'path': '/product/vision/vision_part2.md'
        }
    ]
}
```

### Topic Extraction

**From filenames and chapter headings:**

```python
# Filename patterns
"vision_context_management.md" → topics = ["Context Management"]
"vision_rag_architecture.md" → topics = ["RAG Architecture"]

# Chapter headings in content
"# Agent Coordination\n..." → topics.append("Agent Coordination")
"## Message Queue System\n..." → topics.append("Message Queue System")
```

### Chunk Tracking

```python
# Determine which chunks contain which files
start_char = file_info.get('char_position', 0)
end_char = start_char + file_info['size']

start_chunk = (start_char // chars_per_chunk) + 1
end_chunk = (end_char // chars_per_chunk) + 1
chunks_span = list(range(start_chunk, min(end_chunk + 1, total_chunks + 1)))

# Store in index
file_info['chunks'] = chunks_span  # e.g., [1, 2, 3]
```

### Navigation Tools

```python
# Get index (creates on first call)
@mcp.tool()
def get_vision_index() -> Dict:
    """Get or create vision document index"""
    index = db.get_vision_index(product_id)
    if not index:
        index = create_vision_index(product)  # Auto-create
    return index

# Get specific chunk
@mcp.tool()
def get_vision(chunk_number: int) -> Dict:
    """Get a specific vision chunk by number"""
    vision_content = load_product_vision(product)
    chunks = chunk_text(vision_content, chars_per_chunk=15000)

    if chunk_number < 1 or chunk_number > len(chunks):
        return {"error": f"Invalid chunk. Range: 1-{len(chunks)}"}

    return {
        "chunk": chunk_number,
        "total_chunks": len(chunks),
        "content": chunks[chunk_number - 1],
        "size": len(chunks[chunk_number - 1])
    }
```

### Database Schema for Vision Index

```sql
CREATE TABLE mcp_context_index (
    id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES mcp_products(id),
    index_type VARCHAR(50) NOT NULL,        -- 'vision', 'docs', 'code'
    document_name VARCHAR(200),             -- Filename
    section_name VARCHAR(200),              -- "Chunks 1-3" or "Chapter 5"
    summary TEXT,                           -- Brief summary
    token_count INTEGER,                    -- Estimated tokens
    full_path TEXT,                         -- Full file path
    keywords TEXT[],                        -- PostgreSQL array of topics
    content_hash VARCHAR(32),               -- MD5 for change detection
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_context_index_product ON mcp_context_index(product_id);
CREATE INDEX idx_context_index_type ON mcp_context_index(index_type);
CREATE INDEX idx_context_index_keywords ON mcp_context_index USING GIN(keywords);
```

---

## 11. After-Action Documentation (MANDATORY)

### Three Required Documents Before Project Closure

**From orchestrator mission (F:/AKE-MCP/server.py, lines 240-241):**

#### 1. Devlog Completion Report

**Path:** `/docs/devlog/project_[number]_[name]_completion.md`

```markdown
# Project Completion: [Project Name]

## Executive Summary
[1-2 paragraphs summarizing the project]

## Deliverables
- [x] Feature 1: Description and location
- [x] Feature 2: Description and location
- [ ] Feature 3: Deferred to future (reason)

## Technical Metrics
- **Lines of Code Changed:** 450 additions, 120 deletions
- **Files Modified:** 12 files across 5 directories
- **Test Coverage:** 87% (up from 75%)
- **Performance Impact:** API latency reduced 23%

## Issues Resolved
1. **Issue #42:** Port conflict in server mode
   - Root cause: Hardcoded port binding
   - Solution: Config-driven port selection
   - Validation: Tested on 3 different systems

2. **Issue #58:** Multi-tenant isolation gap
   - Root cause: Missing tenant_key filter in query
   - Solution: Added filter to all queries
   - Validation: Integration tests for isolation

## Agent Performance Stats
- **Researcher:** 35% context used, 3 reports delivered
- **Implementer:** 67% context used, 8 files modified
- **Tester:** 42% context used, 15 tests created (all passing)
- **Documenter:** 28% context used, 4 docs updated

## Lessons Learned
### What Worked
- Dynamic discovery with Serena MCP reduced rework by 40%
- Parallel agent execution saved 2 hours
- Specific missions (not generic) kept agents focused

### What Didn't Work
- Initial implementer mission was too broad
- Tester needed more context about edge cases
- Should have created index before vision reading

## Recommendations
- Use vision index from the start
- Give implementers bounded file scope
- Run testers in parallel with implementation
```

**Validation:**
```python
content = serena.read_file('/docs/devlog/project_3_auth_completion.md')
assert len(content) > 500, "Report too short!"
```

#### 2. Session After-Action Report

**Path:** `/docs/Sessions/session_[YYYY_MM_DD]_project_[number]_report.md`

```markdown
# Session After-Action Report
**Date:** 2025-01-07
**Project:** #3 - API Authentication
**Duration:** 3.5 hours

## Complete Workflow Timeline

### Phase 1: Discovery (45 min)
- 09:00: Orchestrator activated
- 09:05: Serena search for auth patterns → found 3 implementations
- 09:15: Vision Ch3 read → extracted security requirements
- 09:30: Settings review → noted missing auth config
- 09:45: Mission created: "Implement API key auth for server mode"

### Phase 2: Research (30 min)
- 09:50: Researcher spawned
- 10:00: Researcher analyzed existing patterns
- 10:15: Researcher documented JWT vs API key trade-offs
- 10:20: Researcher report delivered to orchestrator

### Phase 3: Implementation (90 min)
- 10:25: Implementer spawned with specific mission
- 10:30: Implementer created Alembic migration
- 11:00: Implementer built /api/auth/validate endpoint
- 11:30: Implementer added middleware
- 12:00: Implementer updated config template

### Phase 4: Testing (45 min)
- 12:05: Tester spawned (parallel with doc work)
- 12:15: Tester created 15 integration tests
- 12:35: Tester found edge case bug → sent to implementer
- 12:45: Implementer fixed bug
- 12:50: All tests passing

### Phase 5: Documentation (30 min)
- 12:10: Documenter spawned (parallel with testing)
- 12:20: Documenter updated deployment guide
- 12:30: Documenter added API reference
- 12:40: Documenter updated CLAUDE.md patterns

## All Decisions Made

### Architecture Decisions
1. **API Key over JWT** (10:15)
   - Rationale: Simpler for server-to-server, no expiry complexity
   - Trade-off: Less granular permissions (accepted for v1)

2. **Middleware Pattern** (11:00)
   - Rationale: Centralized auth, easy to enable/disable
   - Implementation: FastAPI dependency injection

3. **Config-Driven Toggle** (11:30)
   - Rationale: localhost=no auth, server=auth required
   - Implementation: config.yaml security.api_keys.require_for_modes

### Tool Decisions
1. Used Alembic for schema migration (not manual SQL)
2. Used pytest for integration tests (not unittest)
3. Used FastAPI's built-in security utilities

## Final Outcomes

### Completed Deliverables
- ✅ API key authentication system
- ✅ Database schema with api_keys table
- ✅ /api/auth/validate endpoint
- ✅ Auth middleware with config toggle
- ✅ 15 integration tests (100% passing)
- ✅ Complete documentation

### Success Metrics
- **Zero Security Gaps:** Multi-tenant isolation maintained
- **Performance:** <5ms auth overhead
- **Coverage:** 92% test coverage on auth code
- **Compatibility:** Works on localhost + server modes

## What Worked
1. **Dynamic Discovery:** Serena search found existing patterns fast
2. **Specific Missions:** Each agent had bounded, clear scope
3. **Parallel Execution:** Tester + Documenter saved 30 minutes
4. **Message Protocol:** Acknowledgments prevented duplication

## What Didn't Work
1. **Initial Mission Too Broad:** Had to refine implementer scope twice
2. **Vision Reading:** Should have used index from start (wasted 10 min)
3. **Edge Case Discovery:** Tester found bug late (could have been earlier)

## Recommendations for Future Sessions
1. **Always Create Vision Index First:** Use get_vision_index() before reading
2. **Start Testers Earlier:** Parallel with implementation, not after
3. **Bounded File Scope:** Tell implementers exactly which files to modify
4. **Use project_status() First:** Check existing agents before spawning
5. **Acknowledge Messages Immediately:** Prevents coordination confusion
```

**Validation:**
```python
content = serena.read_file('/docs/Sessions/session_2025_01_07_project_3_report.md')
assert len(content) > 500, "Report too short!"
assert "Timeline" in content, "Missing timeline section!"
```

#### 3. Project Summary

**Path:** `/docs/Project_summaries/[YYYY-MM-DD]_[project_name].md`

```markdown
# Project Summary: API Authentication System
**Date:** 2025-01-07
**Project ID:** project_3
**Duration:** 3.5 hours

## Original Objectives
1. Implement API key authentication for server mode
2. Maintain localhost mode without auth (dev convenience)
3. Ensure multi-tenant isolation with auth
4. Create comprehensive tests and documentation

## Achievements
1. ✅ API key authentication fully implemented
2. ✅ Config-driven auth toggle (localhost vs server)
3. ✅ Multi-tenant isolation validated with tests
4. ✅ Complete docs + 15 passing integration tests

## Agent List & Roles

### Orchestrator
- **Role:** Project Manager & Team Lead
- **Key Actions:**
  - Dynamic discovery via Serena MCP (15 min)
  - Vision Ch3 analysis for security requirements
  - Created specific missions for 4 agents
  - Coordinated parallel execution (tester + documenter)
- **Context Used:** 45%
- **Outcome:** Successful coordination, zero scope creep

### Researcher
- **Role:** Auth Pattern Analysis
- **Key Actions:**
  - Searched /api/ for existing auth patterns
  - Analyzed JWT vs API key trade-offs
  - Documented recommendations with code examples
- **Context Used:** 35%
- **Deliverables:** Auth pattern analysis report
- **Outcome:** Clear recommendation → API key approach

### Implementer
- **Role:** Code Implementation
- **Key Actions:**
  - Created Alembic migration for api_keys table
  - Built /api/auth/validate endpoint
  - Added auth middleware to api/app.py
  - Updated config template for auth settings
  - Fixed edge case bug found by tester
- **Context Used:** 67%
- **Deliverables:** Working auth system
- **Outcome:** All requirements met, tests passing

### Tester
- **Role:** Quality Assurance
- **Key Actions:**
  - Created 15 integration tests
  - Tested valid/invalid/expired API keys
  - Found edge case bug (expired key with valid format)
  - Validated multi-tenant isolation
- **Context Used:** 42%
- **Deliverables:** 15 tests (100% passing)
- **Outcome:** Comprehensive test coverage, 1 critical bug found

### Documenter
- **Role:** Documentation
- **Key Actions:**
  - Updated docs/deployment/AUTHENTICATION.md
  - Added API reference for /api/auth/validate
  - Updated CLAUDE.md with auth patterns
  - Created session memory for learnings
- **Context Used:** 28%
- **Deliverables:** 4 documentation files updated
- **Outcome:** Complete, clear documentation

## Key Decisions

### 1. API Key vs JWT
- **Decision:** Use API key authentication
- **Rationale:** Simpler for server-to-server, no token expiry complexity
- **Trade-off:** Less granular permissions (acceptable for v1)
- **Who Decided:** Orchestrator based on researcher analysis

### 2. Config-Driven Auth Toggle
- **Decision:** Auth required only for server/LAN/WAN modes
- **Rationale:** Localhost mode needs dev convenience, no auth
- **Implementation:** config.yaml security.api_keys.require_for_modes
- **Who Decided:** Orchestrator based on vision Ch3 requirements

### 3. Middleware Pattern
- **Decision:** Centralized auth middleware using FastAPI dependency injection
- **Rationale:** Single point of control, easy to enable/disable
- **Alternative Rejected:** Per-endpoint decorators (too scattered)
- **Who Decided:** Implementer with orchestrator approval

## Success Metrics

### Functional Metrics
- ✅ API key validation working (100% test coverage)
- ✅ Multi-tenant isolation maintained
- ✅ Config toggle works (localhost vs server)
- ✅ Performance: <5ms auth overhead

### Quality Metrics
- **Test Coverage:** 92% on auth code
- **Tests Passing:** 15/15 integration tests
- **Documentation:** 100% complete
- **Code Review:** Follows CLAUDE.md standards

### Efficiency Metrics
- **Time:** 3.5 hours (vs 6 hour estimate)
- **Agent Efficiency:** 43% avg context used (healthy)
- **Parallel Execution:** Saved 30 minutes
- **Rework:** Minimal (1 bug fix)

## Future Improvements

### Immediate (Next Sprint)
1. Add API key rotation mechanism
2. Implement key expiry with auto-cleanup
3. Add rate limiting per API key
4. Create admin UI for key management

### Long-term (Future Versions)
1. OAuth2 support for external integrations
2. Role-based permissions per API key
3. Audit logging for all auth events
4. Key usage analytics dashboard

### Process Improvements
1. **Vision Index First:** Always create index before reading (saves 10 min)
2. **Parallel Testing:** Start tester during implementation, not after
3. **Bounded Scope:** Give implementers exact file list upfront
4. **Message Protocol:** Mandate immediate acknowledgment (prevent duplication)
```

**Validation:**
```python
content = serena.read_file('/docs/Project_summaries/2025-01-07_api_authentication.md')
assert len(content) > 500, "Report too short!"
assert "Agent List" in content, "Missing agent section!"
assert "Success Metrics" in content, "Missing metrics!"
```

### Validation Before Project Closure

```python
# MANDATORY: Orchestrator must validate all 3 files exist before close_project()

def validate_documentation_before_closure(project_id: str) -> bool:
    """Validate all after-action docs exist and are substantial"""

    required_files = [
        f'/docs/devlog/project_{project_id}_completion.md',
        f'/docs/Sessions/session_{date.today()}_project_{project_id}_report.md',
        f'/docs/Project_summaries/{date.today()}_{project_name}.md'
    ]

    for file_path in required_files:
        try:
            content = serena.read_file(file_path)
            if len(content) < 500:
                return False, f"File {file_path} too short (<500 chars)"
        except FileNotFoundError:
            return False, f"Required file missing: {file_path}"

    return True, "All documentation validated"

# In orchestrator workflow:
valid, message = validate_documentation_before_closure(project_id)
if not valid:
    return {"error": message, "hint": "Create all 3 required reports first"}

# Only after validation:
close_project(project_id)
```

---

## 12. Database Schema

### Complete Schema from AKE-MCP

**Location:** `F:/AKE-MCP/sql/01_create_new_tables.sql`

```sql
-- Products (Multi-tenant root)
CREATE TABLE mcp_products (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    root_path TEXT NOT NULL,
    vision_path TEXT,
    config_data JSONB,                  -- Architecture, tech_stack, etc.
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projects (Tenant-specific work)
CREATE TABLE mcp_projects (
    id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES mcp_products(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,                    -- User's initial input
    mission TEXT,                        -- Orchestrator's expanded mission
    orchestrator_sequence TEXT[],        -- Ordered agent list
    current_agent VARCHAR(100),
    current_step INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'planning',
    context_used DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(product_id, name)
);

-- Agent Jobs (Work tracking)
CREATE TABLE mcp_agent_jobs (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(50) REFERENCES mcp_projects(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL,      -- 'orchestration', 'analysis', 'implementation', etc.
    mission TEXT,
    status VARCHAR(50) DEFAULT 'created',
    health VARCHAR(20) DEFAULT 'green', -- green/yellow/orange/red
    context_used DECIMAL(5,2) DEFAULT 0.0,
    max_context DECIMAL(5,2) DEFAULT 100.0,
    handoff_context JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, agent_name)
);

-- Messages (Inter-agent communication)
CREATE TABLE mcp_messages (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(50) REFERENCES mcp_projects(id) ON DELETE CASCADE,
    from_agent VARCHAR(100) NOT NULL,
    to_agents TEXT[] NOT NULL,              -- PostgreSQL array
    message_type VARCHAR(50) NOT NULL,      -- broadcast, direct, handoff, status, error, completion
    priority VARCHAR(20) DEFAULT 'normal',  -- low, normal, high, critical
    content TEXT NOT NULL,
    metadata JSONB,
    acknowledged_by TEXT[] DEFAULT '{}',    -- PostgreSQL array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Context Index (Vision navigation)
CREATE TABLE mcp_context_index (
    id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES mcp_products(id) ON DELETE CASCADE,
    index_type VARCHAR(50) NOT NULL,        -- 'vision', 'docs', 'code'
    document_name VARCHAR(200),
    section_name VARCHAR(200),
    summary TEXT,
    token_count INTEGER,
    full_path TEXT,
    keywords TEXT[],                        -- PostgreSQL array
    content_hash VARCHAR(32),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_projects_product ON mcp_projects(product_id);
CREATE INDEX idx_projects_status ON mcp_projects(status);
CREATE INDEX idx_agent_jobs_project ON mcp_agent_jobs(project_id);
CREATE INDEX idx_agent_jobs_status ON mcp_agent_jobs(status);
CREATE INDEX idx_messages_project ON mcp_messages(project_id);
CREATE INDEX idx_messages_to_agents ON mcp_messages USING GIN(to_agents);
CREATE INDEX idx_messages_acknowledged ON mcp_messages USING GIN(acknowledged_by);
CREATE INDEX idx_context_index_product ON mcp_context_index(product_id);
CREATE INDEX idx_context_index_type ON mcp_context_index(index_type);
CREATE INDEX idx_context_index_keywords ON mcp_context_index USING GIN(keywords);

-- Triggers
CREATE OR REPLACE FUNCTION update_project_context_used()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE mcp_projects
    SET context_used = (
        SELECT COALESCE(SUM(context_used), 0)
        FROM mcp_agent_jobs
        WHERE project_id = NEW.project_id
    )
    WHERE id = NEW.project_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_project_context
AFTER INSERT OR UPDATE OF context_used ON mcp_agent_jobs
FOR EACH ROW
EXECUTE FUNCTION update_project_context_used();

CREATE OR REPLACE FUNCTION auto_complete_project()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM mcp_agent_jobs
        WHERE project_id = NEW.project_id
        AND status NOT IN ('completed', 'decommissioned')) = 0
    THEN
        UPDATE mcp_projects
        SET status = 'completed', completed_at = CURRENT_TIMESTAMP
        WHERE id = NEW.project_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_complete_project
AFTER UPDATE OF status ON mcp_agent_jobs
FOR EACH ROW
EXECUTE FUNCTION auto_complete_project();
```

### Key PostgreSQL Features Used

1. **Arrays:** `TEXT[]` for multi-recipient messages and agent sequences
2. **JSONB:** For flexible config data and handoff context
3. **Triggers:** Auto-update project context and status
4. **GIN Indexes:** For array contains queries (`ANY()` operator)
5. **Cascading Deletes:** Clean up related records automatically

---

## 13. MCP Tools Reference

### 20 Essential Tools in 4 Categories

#### Project Management (5 tools)

```python
@mcp.tool()
def create_project(name: str, mission: str, agents: List[str] = None) -> Dict:
    """Create a new project with mission and optional agent sequence"""

@mcp.tool()
def list_projects(status: str = None) -> Dict:
    """List all projects with optional status filter"""

@mcp.tool()
def switch_project(project_id: str) -> Dict:
    """Switch to a different project (activates orchestrator)"""

@mcp.tool()
def close_project(project_id: str) -> Dict:
    """Close/archive a project (requires documentation validation)"""

@mcp.tool()
def project_status(project_id: str) -> Dict:
    """Get detailed project status and agent list"""
```

#### Agent Management (5 tools)

```python
@mcp.tool()
def activate_agent(project_id: str, agent_name: str) -> Dict:
    """Activate agent with immediate discovery (orchestrator only)"""

@mcp.tool()
def ensure_agent(project_id: str, agent_name: str, mission: str) -> Dict:
    """Ensure agent exists - get or create (idempotent)"""

@mcp.tool()
def assign_job(agent_name: str, job_type: str, project_id: str, tasks: List[str]) -> Dict:
    """Assign or update job for agent (idempotent)"""

@mcp.tool()
def handoff(from_agent: str, to_agent: str, context: Dict, project_id: str) -> Dict:
    """Handoff work between agents (context exhaustion)"""

@mcp.tool()
def agent_health(project_id: str, agent_name: str = None) -> Dict:
    """Get agent health status (context usage, status)"""
```

#### Messaging (5 tools)

```python
@mcp.tool()
def send_message(from_agent: str, to_agents: List[str], content: str,
                 message_type: str, priority: str, project_id: str,
                 metadata: Dict = None) -> Dict:
    """Send message to one or more agents"""

@mcp.tool()
def get_messages(agent_name: str, project_id: str, unread_only: bool = True) -> Dict:
    """Get messages for an agent"""

@mcp.tool()
def acknowledge_message(agent_name: str, message_id: str) -> Dict:
    """Acknowledge receipt of a message"""

@mcp.tool()
def complete_message(agent_name: str, message_id: str) -> Dict:
    """Mark message as completed/acted upon"""

@mcp.tool()
def broadcast(from_agent: str, content: str, project_id: str, priority: str = 'normal') -> Dict:
    """Broadcast message to all agents in project"""
```

#### Context & Discovery (5 tools)

```python
@mcp.tool()
def get_vision(chunk_number: int = None) -> Dict:
    """Get vision document chunk (creates index on first call)"""

@mcp.tool()
def get_vision_index() -> Dict:
    """Get vision document index (topics, files, chunks)"""

@mcp.tool()
def get_product_settings() -> Dict:
    """Get product configuration (architecture, tech stack, etc.)"""

@mcp.tool()
def session_info(project_id: str) -> Dict:
    """Get current session context and status"""

@mcp.tool()
def help(tool_name: str = None) -> Dict:
    """Get help for MCP tools"""
```

---

## 14. Implementation Checklist for GiljoAI-MCP

### Phase 1: Database Schema Updates (9 items)

- [ ] **1.1** Add `orchestrator_sequence TEXT[]` to `mcp_projects` table
- [ ] **1.2** Add `current_agent VARCHAR(100)` and `current_step INTEGER` to `mcp_projects`
- [ ] **1.3** Add `mission TEXT` field to `mcp_projects` (separate from description)
- [ ] **1.4** Add `job_type VARCHAR(50)` to `mcp_agent_jobs` (orchestration, analysis, etc.)
- [ ] **1.5** Add `health VARCHAR(20)` to `mcp_agent_jobs` (green/yellow/orange/red)
- [ ] **1.6** Create `mcp_context_index` table for vision navigation
- [ ] **1.7** Update `mcp_messages` table with `acknowledged_by TEXT[]` array
- [ ] **1.8** Add triggers for auto-updating project context and status
- [ ] **1.9** Create GIN indexes on array fields for performance

### Phase 2: Core Class Implementations (7 items)

- [ ] **2.1** Create `ContextManager` class with hierarchical loading
  - Full context for orchestrator (all vision + all config)
  - Filtered context for workers (role-based)
- [ ] **2.2** Implement `_get_filtered_config()` method with role-based filtering
- [ ] **2.3** Create vision chunking system with automatic index creation
- [ ] **2.4** Implement `VisionIndexer` for topic extraction and chunk tracking
- [ ] **2.5** Update `SessionManager` to use hierarchical context loading
- [ ] **2.6** Create message routing with PostgreSQL array support
- [ ] **2.7** Implement health monitoring with context usage thresholds

### Phase 3: MCP Tool Updates (9 items)

- [ ] **3.1** Create `activate_agent()` tool for orchestrator (immediate discovery)
- [ ] **3.2** Create `ensure_agent()` tool for workers (idempotent get-or-create)
- [ ] **3.3** Update `assign_job()` to be idempotent (update or create)
- [ ] **3.4** Implement `get_vision_index()` tool (creates index on first call)
- [ ] **3.5** Implement `get_vision(chunk_number)` tool for chunk reading
- [ ] **3.6** Create `acknowledge_message()` tool with array update
- [ ] **3.7** Create `handoff()` tool for context exhaustion scenarios
- [ ] **3.8** Implement `agent_health()` tool for monitoring
- [ ] **3.9** Update `project_status()` to show orchestrator sequence

### Phase 4: Orchestrator Prompt Creation (7 items)

- [ ] **4.1** Create `generate_orchestrator_mission()` function with full prompt
- [ ] **4.2** Include 30-80-10 effort distribution instructions
- [ ] **4.3** Add "3-tool rule" for delegation vs implementation
- [ ] **4.4** Include Serena MCP discovery workflow (search, read, summarize)
- [ ] **4.5** Add agent spawning instructions (activate vs ensure)
- [ ] **4.6** Include message protocol and acknowledgment requirements
- [ ] **4.7** Add mandatory after-action documentation validation

### Phase 5: Context Management (6 items)

- [ ] **5.1** Implement vision file chunking (15000 chars per chunk)
- [ ] **5.2** Create index with topic extraction from filenames and headings
- [ ] **5.3** Track which chunks contain which files
- [ ] **5.4** Implement config data JSONB schema in products table
- [ ] **5.5** Add role-based config filtering for agents
- [ ] **5.6** Create Serena MCP integration status tracking

### Phase 6: Testing (6 items)

- [ ] **6.1** Test orchestrator activation and discovery workflow
- [ ] **6.2** Test agent spawning (activate vs ensure) with idempotency
- [ ] **6.3** Test hierarchical context loading (orchestrator vs workers)
- [ ] **6.4** Test vision index creation and chunk navigation
- [ ] **6.5** Test message queue with array-based routing and acknowledgments
- [ ] **6.6** Test after-action documentation validation before closure

---

## 15. Code Examples

### Example 1: Orchestrator Discovery Workflow

```python
# F:/AKE-MCP/server.py - Lines 112-132

# DISCOVERY PHASE (30% effort)
def orchestrator_discovery_phase(project_id: str):
    """Orchestrator's dynamic discovery process"""

    # Phase 1: Serena MCP Discovery (Primary)
    recent_sessions = serena.list_dir("/docs/devlog/", recursive=False)
    all_docs = serena.list_dir("/docs/", recursive=True)
    current_context = serena.read_file("CLAUDE.md")
    local_context = serena.read_file("CLAUDE.local.md")

    # Search for pain points and successes
    pain_points = serena.search_files("problem|issue|bug|fix")
    successes = serena.search_files("pattern|solution|works")

    # Phase 2: Vision Reading
    vision_index = get_vision_index()  # Creates index on first call
    total_chunks = vision_index['total_chunks']

    vision_content = []
    for chunk_num in range(1, total_chunks + 1):
        chunk = get_vision(chunk_num)
        vision_content.append(chunk['content'])

    # Phase 3: Settings Review
    settings = get_product_settings()

    # Phase 4: Create SPECIFIC Mission
    mission = f"""
    Based on discoveries:
    1. Fix {len(pain_points)} issues found in recent sessions
    2. Apply {len(successes)} successful patterns
    3. Implement requirements from vision chunks {list(range(1, total_chunks+1))}
    4. Address {len(settings.get('missing_fields', []))} config gaps

    Success criteria:
    - All pain points resolved
    - All tests passing
    - Documentation updated
    """

    # Update project mission
    db.update_project_mission(project_id, mission)

    return mission
```

### Example 2: Hierarchical Context Loading

```python
# F:/AKE-MCP/core/session_manager.py - Lines 205-243

def prepare_agent_context(self, agent_name: str, project_id: str) -> Dict:
    """Prepare context for agent - HIERARCHICAL LOADING"""
    context = {"project": {}, "product": {}}

    # Get project and product
    project = self.db.get_project(project_id)
    product = self.db.get_active_product()

    # Determine if orchestrator
    job = self.db.get_active_job(project_id, agent_name)
    is_orchestrator = (
        agent_name.lower() == "orchestrator" or
        (job and job.get("job_type") == "orchestration")
    )

    if is_orchestrator:
        # ORCHESTRATOR: Gets FULL context
        print("Loading FULL context for orchestrator")

        # Load complete vision
        vision_content = self.load_product_vision(product)
        if vision_content:
            context["product"]["vision"] = vision_content

        # Add ALL config data
        if product.get("config_data"):
            context["product"]["config"] = product["config_data"]

        # Add Serena MCP info
        if product["config_data"].get("serena_mcp_enabled"):
            context["serena_mcp"] = {
                "enabled": True,
                "description": "Serena MCP for code analysis",
                "usage": "Use Serena tools to explore codebase"
            }

    else:
        # WORKER AGENTS: Get FILTERED context
        print(f"Loading FILTERED context for {agent_name}")

        # Vision summary only (not full text)
        context["product"]["vision_summary"] = self._get_vision_summary(product)

        # Role-based config filtering
        context["product"]["relevant_config"] = self._get_filtered_config(
            agent_name, product
        )

        # Add Serena info for all agents
        if product.get("config_data", {}).get("serena_mcp_enabled"):
            context["serena_mcp"] = {
                "enabled": True,
                "description": "Serena MCP available",
                "usage": "Use for bounded file operations"
            }

    return context
```

### Example 3: Idempotent Agent Spawning

```python
# F:/AKE-MCP/server.py

@mcp.tool()
def ensure_agent(project_id: str, agent_name: str, mission: str) -> Dict:
    """
    Ensure agent exists - get or create (IDEMPOTENT)
    Safe to call multiple times - won't create duplicates
    """
    # Check if agent already exists
    existing_job = db.get_active_job(project_id, agent_name)

    if existing_job:
        print(f"Agent {agent_name} already exists, returning existing")
        return {
            "success": True,
            "agent_id": existing_job["id"],
            "status": "existing",
            "message": f"Agent {agent_name} already exists for project {project_id}"
        }

    # Infer job type from agent name
    job_type = infer_job_type(agent_name)
    # 'analyzer' → 'analysis'
    # 'implementer' → 'implementation'
    # 'tester' → 'testing'
    # 'documenter' → 'documentation'

    # Create new agent job
    job_id = db.create_agent_job(
        project_id=project_id,
        agent_name=agent_name,
        job_type=job_type,
        mission=mission,
        status='created'
    )

    # Create session with FILTERED context
    session = session_mgr.create_session(
        agent_name=agent_name,
        project_id=project_id,
        mission=mission,
        job_type=job_type
    )

    print(f"Created new agent {agent_name} with job type {job_type}")
    return {
        "success": True,
        "agent_id": job_id,
        "status": "created",
        "session_id": session["session_id"],
        "message": f"Created agent {agent_name} for project {project_id}"
    }

@mcp.tool()
def assign_job(agent_name: str, job_type: str, project_id: str,
               tasks: List[str]) -> Dict:
    """
    Assign or update job for agent (IDEMPOTENT)
    Updates existing job or creates new one
    """
    # Check for existing job
    existing_job = db.get_active_job(project_id, agent_name)

    if existing_job:
        # Update existing job with new tasks
        db.update_job_tasks(existing_job["id"], tasks)
        print(f"Updated existing job for {agent_name}")
        return {
            "success": True,
            "status": "updated",
            "job_id": existing_job["id"],
            "message": f"Updated job for {agent_name}"
        }

    # Create new job
    job_id = db.create_agent_job(
        project_id=project_id,
        agent_name=agent_name,
        job_type=job_type,
        tasks=tasks
    )

    print(f"Created new job for {agent_name}")
    return {
        "success": True,
        "status": "created",
        "job_id": job_id,
        "message": f"Created job for {agent_name}"
    }
```

### Example 4: Message Queue with Array Routing

```python
# Message sending with PostgreSQL arrays

@mcp.tool()
def send_message(from_agent: str, to_agents: List[str], content: str,
                 message_type: str, priority: str, project_id: str,
                 metadata: Dict = None) -> Dict:
    """Send message to one or more agents"""

    message_id = str(uuid.uuid4())

    with db.transaction() as cur:
        cur.execute("""
            INSERT INTO mcp_messages (
                id, project_id, from_agent, to_agents,
                message_type, priority, content, metadata,
                acknowledged_by
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            message_id,
            project_id,
            from_agent,
            to_agents,  # PostgreSQL TEXT[] array
            message_type,
            priority,
            content,
            json.dumps(metadata) if metadata else None,
            []  # Empty array for acknowledgments
        ))

    return {
        "success": True,
        "message_id": message_id,
        "recipients": to_agents
    }

@mcp.tool()
def acknowledge_message(agent_name: str, message_id: str) -> Dict:
    """Acknowledge receipt of a message"""

    with db.transaction() as cur:
        # Add agent to acknowledged_by array if not already present
        cur.execute("""
            UPDATE mcp_messages
            SET acknowledged_by = array_append(acknowledged_by, %s)
            WHERE id = %s
            AND NOT (%s = ANY(acknowledged_by))  -- Prevent duplicates
        """, (agent_name, message_id, agent_name))

    return {"success": True, "acknowledged": True}

# Query messages for an agent
@mcp.tool()
def get_messages(agent_name: str, project_id: str,
                 unread_only: bool = True) -> Dict:
    """Get messages for an agent"""

    with db.transaction() as cur:
        if unread_only:
            # Get messages not yet acknowledged by this agent
            cur.execute("""
                SELECT id, from_agent, content, message_type, priority, created_at
                FROM mcp_messages
                WHERE project_id = %s
                AND %s = ANY(to_agents)  -- Agent is in recipients
                AND NOT (%s = ANY(acknowledged_by))  -- Not acknowledged yet
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    created_at DESC
            """, (project_id, agent_name, agent_name))
        else:
            # Get all messages for agent
            cur.execute("""
                SELECT id, from_agent, content, message_type, priority, created_at,
                       %s = ANY(acknowledged_by) as acknowledged
                FROM mcp_messages
                WHERE project_id = %s
                AND %s = ANY(to_agents)
                ORDER BY created_at DESC
            """, (agent_name, project_id, agent_name))

        messages = cur.fetchall()

    return {
        "success": True,
        "count": len(messages),
        "messages": messages
    }
```

### Example 5: Vision Index Creation

```python
# F:/AKE-MCP/server.py - Lines 40-93

def create_vision_index(product_id: str, vision_files: List[Dict]) -> Dict:
    """Create searchable index for vision documents"""
    import hashlib
    import uuid

    # Calculate chunking parameters
    total_size = sum(f['size'] for f in vision_files)
    chars_per_chunk = 15000
    total_chunks = (total_size // chars_per_chunk) + 1

    # Clear any existing index
    with db.transaction() as cur:
        cur.execute(
            "DELETE FROM mcp_context_index WHERE product_id = %s AND index_type = 'vision'",
            (product_id,)
        )

        # Create index entries for each file
        for file_info in vision_files:
            # Determine which chunks this file appears in
            start_char = file_info.get('char_position', 0)
            end_char = start_char + file_info['size']

            start_chunk = (start_char // chars_per_chunk) + 1
            end_chunk = (end_char // chars_per_chunk) + 1
            chunks_span = list(range(start_chunk, min(end_chunk + 1, total_chunks + 1)))

            # Extract topics from filename
            filename_topics = extract_topics_from_filename(file_info['name'])

            # Extract topics from chapter headings in content
            content_topics = extract_topics_from_content(file_info.get('content', ''))

            all_topics = list(set(filename_topics + content_topics))

            # Create content hash for change detection
            content_hash = hashlib.md5(file_info['name'].encode()).hexdigest()[:16]

            # Insert index entry
            cur.execute("""
                INSERT INTO mcp_context_index (
                    id, product_id, index_type, document_name, section_name,
                    summary, token_count, full_path, keywords, content_hash,
                    version
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                str(uuid.uuid4()),
                product_id,
                'vision',
                file_info['name'],
                f"Chunks {chunks_span[0]}-{chunks_span[-1]}" if len(chunks_span) > 1
                    else f"Chunk {chunks_span[0]}",
                f"{file_info['lines']} lines covering: {', '.join(all_topics[:3])}",
                file_info['size'] // 4,  # Estimated tokens
                file_info.get('path', ''),
                all_topics,  # PostgreSQL TEXT[] array
                content_hash,
                1
            ))

    return {
        "success": True,
        "total_chunks": total_chunks,
        "files_indexed": len(vision_files),
        "total_topics": len(set(sum([f.get('topics', []) for f in vision_files], [])))
    }

def extract_topics_from_filename(filename: str) -> List[str]:
    """Extract topics from filename patterns"""
    # Remove extension and split by underscores/hyphens
    name = filename.replace('.md', '').replace('.txt', '')
    parts = name.replace('-', '_').split('_')

    # Capitalize and clean
    topics = []
    for part in parts:
        if len(part) > 2:  # Skip short words
            topics.append(part.capitalize())

    return topics

def extract_topics_from_content(content: str) -> List[str]:
    """Extract topics from chapter headings"""
    import re

    topics = []
    # Find markdown headings (# Topic, ## Topic)
    headings = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)

    for heading in headings:
        # Clean and add
        clean_heading = heading.strip()
        if len(clean_heading) > 3:
            topics.append(clean_heading)

    return topics
```

### Example 6: After-Action Validation

```python
# Before closing project, validate all documentation exists

def validate_after_action_documentation(project_id: str, project_name: str) -> tuple:
    """
    Validate all 3 required after-action documents exist and are substantial
    Returns: (success: bool, message: str)
    """
    from datetime import date

    # Construct expected file paths
    project_num = project_id.split('_')[-1]  # Extract number from ID
    today = date.today().strftime('%Y_%m_%d')
    today_dash = date.today().strftime('%Y-%m-%d')

    required_files = {
        "devlog_completion": f"/docs/devlog/project_{project_num}_{project_name}_completion.md",
        "session_report": f"/docs/Sessions/session_{today}_project_{project_num}_report.md",
        "project_summary": f"/docs/Project_summaries/{today_dash}_{project_name}.md"
    }

    MIN_CHARS = 500  # Minimum chars per document

    validation_results = []

    for doc_type, file_path in required_files.items():
        try:
            # Use Serena to read the file
            content = serena.read_file(file_path)

            # Check length
            if len(content) < MIN_CHARS:
                return (False,
                       f"Document {doc_type} exists but too short "
                       f"({len(content)} chars, need {MIN_CHARS}+): {file_path}")

            # Check for required sections based on doc type
            if doc_type == "devlog_completion":
                required_sections = ["Executive Summary", "Deliverables", "Agent Performance"]
                missing = [s for s in required_sections if s not in content]
                if missing:
                    return (False,
                           f"Devlog completion missing sections: {', '.join(missing)}")

            elif doc_type == "session_report":
                required_sections = ["Workflow Timeline", "Decisions Made", "Outcomes"]
                missing = [s for s in required_sections if s not in content]
                if missing:
                    return (False,
                           f"Session report missing sections: {', '.join(missing)}")

            elif doc_type == "project_summary":
                required_sections = ["Agent List", "Success Metrics", "Future Improvements"]
                missing = [s for s in required_sections if s not in content]
                if missing:
                    return (False,
                           f"Project summary missing sections: {', '.join(missing)}")

            validation_results.append(f"✅ {doc_type}: {len(content)} chars")

        except FileNotFoundError:
            return (False, f"Required document missing: {file_path}")
        except Exception as e:
            return (False, f"Error reading {file_path}: {str(e)}")

    return (True, f"All documentation validated:\n" + "\n".join(validation_results))

# In orchestrator workflow before close_project():
valid, message = validate_after_action_documentation(project_id, project_name)

if not valid:
    return {
        "success": False,
        "error": message,
        "hint": """Create all 3 required reports:
        1. /docs/devlog/project_[N]_[name]_completion.md
        2. /docs/Sessions/session_[DATE]_project_[N]_report.md
        3. /docs/Project_summaries/[DATE]_[name].md
        Each must be >500 chars with required sections."""
    }

# Only proceed if validation passes
close_project(project_id)
```

---

## 16. Anti-Patterns to Avoid

### ❌ DON'T: Pre-build Static Contexts

```python
# ❌ WRONG - Loads everything upfront
def bad_orchestrator_start():
    all_vision = load_entire_vision()
    all_docs = load_all_documentation()
    all_code = scan_entire_codebase()
    # Wastes tokens, gives stale info
```

**✅ DO: Dynamic Discovery On-Demand**

```python
# ✅ CORRECT - Discover as needed
def good_orchestrator_start():
    pain_points = serena.search_files("problem|bug")
    specific_vision = get_vision(3)  # Only chunk 3
    relevant_config = get_product_settings()
```

### ❌ DON'T: Create Generic Missions

```python
# ❌ WRONG - Too vague
mission = "Update the documentation"
mission = "Fix the bugs"
mission = "Improve the code"
```

**✅ DO: Create Specific Missions from Discoveries**

```python
# ✅ CORRECT - Specific, actionable
mission = """Update CLAUDE.md based on discoveries:
1. Fix SQL patterns (found in session_20240112.md, lines 45-67)
2. Add vLLM config (from docs/deployment/vllm_setup.md)
3. Remove Ollama refs (serena search found 12 instances in /api/)
4. Validate: All tests pass, config loadable"""
```

### ❌ DON'T: Let Orchestrator Do Implementation

```python
# ❌ WRONG - Orchestrator implementing
orchestrator.read_file('api.py')
orchestrator.edit_file('api.py', changes)
orchestrator.run_tests()
orchestrator.commit_changes()
orchestrator.update_docs()
# > 3 tools in sequence = should delegate!
```

**✅ DO: Delegate to Specialized Agents**

```python
# ✅ CORRECT - Orchestrator delegating
ensure_agent('implementer', 'Update api.py with auth middleware')
assign_job('implementer', 'implementation', project_id, [
    "Add auth middleware to api.py",
    "Run tests",
    "Commit with clear message"
])
send_message(['implementer'], 'Start implementation', ...)
```

### ❌ DON'T: Give Agents Vision References

```python
# ❌ WRONG - Agent has to read vision
mission = "Implement auth. See vision Ch3 for requirements."
mission = "Follow patterns in vision Ch7."
```

**✅ DO: Extract and Give Concrete Instructions**

```python
# ✅ CORRECT - Orchestrator extracts, agent gets specifics
# Orchestrator reads vision Ch3
requirements = extract_from_vision(chapter=3)

# Agent gets concrete instructions
mission = """Implement API key auth with:
- Middleware pattern using FastAPI dependency injection
- API keys table: (id, key_hash, tenant_id, created_at)
- /api/auth/validate endpoint returning {valid: bool, tenant_id: str}
- Config toggle: auth required for server mode only"""
```

### ❌ DON'T: Let Agents Explore Broadly

```python
# ❌ WRONG - Unbounded exploration
mission = "Analyze the codebase and find auth patterns"
mission = "Search for issues and fix them"
# Agent will waste context on broad search
```

**✅ DO: Give Bounded Scope**

```python
# ✅ CORRECT - Specific targets
mission = """Analyze auth patterns:
1. Use serena.read_file('/api/middleware/auth.py')
2. Use serena.search_files('jwt|api_key') in /api/ only
3. Read existing tests in tests/integration/test_auth.py
4. Document findings with code examples
Scope: /api/ directory only"""
```

### ❌ DON'T: Forget Message Acknowledgments

```python
# ❌ WRONG - No acknowledgment tracking
send_message(['implementer'], 'Start work', ...)
# Agent might not see it, duplicates can occur
```

**✅ DO: Enforce Acknowledgment Protocol**

```python
# ✅ CORRECT - Track acknowledgments
send_message(['implementer'], 'Start work', priority='high', ...)

# In agent workflow:
messages = get_messages('implementer', project_id, unread_only=True)
for msg in messages:
    acknowledge_message('implementer', msg['id'])
    # Then process message
```

### ❌ DON'T: Close Project Without Documentation

```python
# ❌ WRONG - Close without validation
close_project(project_id)
# Will fail if docs don't exist
```

**✅ DO: Validate Documentation First**

```python
# ✅ CORRECT - Validate before closing
valid, message = validate_after_action_documentation(project_id, project_name)

if not valid:
    print(f"Cannot close: {message}")
    # Create missing docs
    create_devlog_completion()
    create_session_report()
    create_project_summary()
    # Validate again
    valid, message = validate_after_action_documentation(...)

if valid:
    close_project(project_id)
```

### ❌ DON'T: Use activate_agent() for Workers

```python
# ❌ WRONG - activate_agent() for workers
activate_agent(project_id, 'implementer')  # Triggers discovery!
activate_agent(project_id, 'tester')       # Not idempotent!
```

**✅ DO: Use ensure_agent() for Workers**

```python
# ✅ CORRECT - ensure_agent() for workers
ensure_agent(project_id, 'implementer', mission)  # Idempotent
ensure_agent(project_id, 'tester', mission)       # Get-or-create
```

### ❌ DON'T: Handoff for General Coordination

```python
# ❌ WRONG - handoff() for coordination
handoff('researcher', 'implementer', findings, project_id)
# handoff() is ONLY for context exhaustion!
```

**✅ DO: Use send_message() for Coordination**

```python
# ✅ CORRECT - send_message() for coordination
send_message(
    from_agent='researcher',
    to_agents=['implementer', 'orchestrator'],
    content='Research complete. Findings attached.',
    message_type='completion',
    priority='high',
    project_id=project_id,
    metadata=findings
)

# Use handoff() ONLY when context limit reached
if context_used > 90:
    handoff('implementer_1', 'implementer_2', work_state, project_id)
```

---

## Final Notes

This document captures the complete orchestrator architecture from AKE-MCP. Key takeaways:

1. **Orchestrator = Project Manager**, not solo developer
2. **30-80-10 principle**: Discovery 30%, Delegation 80%, Closure 10%
3. **3-tool rule**: >3 tools in sequence = delegate instead
4. **Dynamic discovery**: Use Serena MCP first, vision second, settings third
5. **Hierarchical context**: Orchestrator gets ALL, workers get FILTERED
6. **Idempotent spawning**: `ensure_agent()` for workers, `activate_agent()` for orchestrator
7. **Specific missions**: Always based on discoveries, never generic
8. **Message protocol**: Acknowledge immediately, coordinate via queue
9. **After-action docs**: 3 mandatory reports >500 chars each
10. **Validation before closure**: Verify docs exist before `close_project()`

**Critical Files from AKE-MCP:**
- `F:/AKE-MCP/server.py` - MCP tools and orchestrator mission (lines 95-268)
- `F:/AKE-MCP/core/session_manager.py` - Context management (lines 200-466)
- `F:/AKE-MCP/core/orchestrator.py` - Agent sequencing and handoffs
- `F:/AKE-MCP/sql/01_create_new_tables.sql` - Complete database schema

Use this document as the definitive guide for implementing the orchestrator in GiljoAI-MCP.
