# Master Orchestrator Staging Prompt System

**THE HEART OF GILJOAI** - Critical Documentation

**Handover**: 0079
**Date**: 2025-10-31
**Last Updated**: 2025-01-05 (Harmonized)
**Status**: Production Ready (Legacy - see 0088 Thin Client Migration)
**Priority**: MISSION CRITICAL
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../handovers/Simple_Vision.md)** - User journey with "Stage Project" button explanation
- **[start_to_finish_agent_FLOW.md](../handovers/start_to_finish_agent_FLOW.md)** - Technical flow verification (line 1016: Stage Project button calls `/activate` endpoint)
- **[STAGE_PROJECT_FEATURE.md](STAGE_PROJECT_FEATURE.md)** - Current thin-client implementation (Handover 0088)

**Important Terminology**:
- UI displays **"Stage Project"** button
- Backend endpoint: `POST /api/v1/projects/{id}/activate` (not `/stage`)
- See start_to_finish_agent_FLOW.md line 1016: CRITICAL DISCOVERY section

**Agent Job Lifecycle**:
- Initial status: **"waiting"** (not "pending")
- Full lifecycle: waiting → active → working → complete/failed/blocked

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [How It Works](#how-it-works)
4. [Token Budget Management](#token-budget-management)
5. [MCP Integration](#mcp-integration)
6. [Field Priority System](#field-priority-system)
7. [Generated Prompt Structure](#generated-prompt-structure)
8. [Usage Guide](#usage-guide)
9. [Technical Implementation](#technical-implementation)
10. [Troubleshooting](#troubleshooting)
11. [Future Enhancements](#future-enhancements)

---

## Overview

> Legacy Notice (0088 Thin Client Migration): This document describes the legacy “fat prompt” staging approach from Handover 0079. The system has migrated to a thin‑client prompt design that returns a short identity prompt and fetches missions via MCP tools. For current behavior, see `docs/guides/thin_client_migration_guide.md`, `docs/STAGE_PROJECT_FEATURE.md`, and `docs/api/prompts_endpoints.md`.

### Thin Client Endpoint Summary (0088)

- Use `POST /api/prompts/orchestrator` to generate a thin prompt (see `docs/api/prompts_endpoints.md`).
- Orchestrator then calls MCP tools to fetch mission: `get_orchestrator_instructions`, `get_agent_mission`.
- Legacy `GET /api/prompts/staging/{project_id}` is deprecated.

### What Is It?

The **Master Orchestrator Staging Prompt System** is the core intelligence engine that transforms GiljoAI from a collection of components into a production-ready AI agent orchestration platform. It generates comprehensive, token-efficient prompts that enable AI agents to:

1. **Discover context via MCP** (product, vision, priorities, templates)
2. **Create condensed missions** (context prioritization and orchestration)
3. **Select optimal agents** (intelligent allocation, max 8 types)
4. **Coordinate workflows** (multi-agent communication protocols)
5. **Execute within budget** (20K token limit with safety buffer)

### Why It Matters

**Before Handover 0079**:
- Hardcoded 6-line generic prompt
- No context discovery
- No token budget awareness
- No field priority integration
- Clipboard errors with no feedback

**After Handover 0079**:
- Comprehensive 2000-3000 line orchestrator prompt
- MCP-based context discovery (remote-safe)
- 20K token budget with intelligent overflow handling
- Dynamic field priorities (user-configured)
- context prioritization and orchestration via intelligent condensation
- Multi-tool support (Claude Code, Codex, Gemini)
- Production-grade error handling

### Key Features

✅ **MCP-Only Data Access** - Works for LAN/WAN/hosted (no local file reads)
✅ **Dynamic Field Priorities** - User-configured via My Settings → General
✅ **Token Budget Management** - 20K limit (Claude 25K - 5K safety)
✅ **70% Token Reduction** - Intelligent vision document condensation
✅ **Multi-Tool Support** - Claude Code, Codex, Gemini routing
✅ **Max 8 Agent Types** - Enforced system constraint
✅ **Production-Grade** - Comprehensive error handling & logging

---

## Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────────────────┐
│                 USER INTERACTION                         │
│  (Click "Stage Project" in Launch Tab)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FRONTEND (LaunchTab.vue)                    │
│  - Calls API: GET /api/prompts/staging/{project_id}    │
│  - Shows loading state                                   │
│  - Displays token estimate                               │
│  - Copies prompt to clipboard                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           API ENDPOINT (prompts.py)                      │
│  - Validates project & tenant                            │
│  - Initializes OrchestratorPromptGenerator              │
│  - Returns comprehensive prompt                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│     LAYER 1: CONTEXT AGGREGATOR (MCP Discovery)         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ - Fetch product context                          │  │
│  │ - Navigate vision documents (token-aware)        │  │
│  │ - Load field priorities (user-configured)        │  │
│  │ - Catalog agent templates (max 8 types)          │  │
│  │ - Extract product settings                       │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│   LAYER 2: PROMPT TEMPLATE ENGINE (Instruction Gen)     │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Phase 1: Intelligent Discovery (30% effort)      │  │
│  │ Phase 2: Mission Creation (40% effort)           │  │
│  │ Phase 3: Agent Selection (20% effort)            │  │
│  │ Phase 4: Coordination Protocol (10% effort)      │  │
│  │ Phase 5: Execution & Validation                  │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│    LAYER 3: RESPONSE FORMATTER (Output Structuring)     │
│  ┌───────────────────────────────────────────────────┐  │
│  │ - Assemble final prompt (2000-3000 lines)        │  │
│  │ - Calculate token estimate                       │  │
│  │ - Validate budget utilization                    │  │
│  │ - Generate warnings (if needed)                  │  │
│  │ - Return structured JSON response                │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **User Action**: Clicks "Stage Project" button
2. **Frontend**: Makes API call to `/api/prompts/staging/{project_id}`
3. **API Validation**: Checks project exists and belongs to tenant
4. **Context Aggregation**: Fetches all data via MCP-simulated queries
5. **Priority Filtering**: Applies user's field priority settings
6. **Prompt Generation**: Builds 5-phase orchestrator instructions
7. **Token Validation**: Ensures within 20K budget
8. **Response**: Returns comprehensive prompt + metadata
9. **Clipboard**: Copies prompt for user to paste into CLI

---

## How It Works

### Step-by-Step Process

#### 1. Context Discovery (Layer 1)

**What Happens**:
- Fetches project from database (tenant-isolated)
- Loads associated product (if exists)
- Retrieves vision documents (max 5, token-aware)
- Loads field priorities from product config
- Catalogs available agent templates (max 8)
- Extracts product settings (tech stack, features, etc.)

**MCP Tools Simulated**:
```python
# Product Understanding
product = get_product(project_id)

# Vision Documents (token-aware)
vision_index = get_vision_index(product_id)
vision_chunks = [get_vision(product_id, chunk_id) for chunk in priority_chunks]

# Field Priorities (user-configured)
field_priorities = get_context(product_id, field_priorities=true)

# Agent Templates
templates = list_templates(tenant_key)
```

**Result**: `ContextData` object with all aggregated information

#### 2. Prompt Template Generation (Layer 2)

**Phase 1: Intelligent Discovery (30% of effort)**

Generates instructions for orchestrator to use MCP tools:

```
🔍 PHASE 1: INTELLIGENT DISCOVERY (30% of effort)
──────────────────────────────────────────────────

You have access to MCP tools to discover context. Use them STRATEGICALLY:

1️⃣ Product Understanding
   → get_product('product-uuid-123')
   Returns: Tech stack, features, architecture, dependencies

2️⃣ Vision Document Navigation
   → get_vision_index('product-uuid-123')
   Returns: List of 3 vision chunks with topics

   → get_vision('product-uuid-123', chunk_id)
   ⚠️ TOKEN AWARE: Only fetch Priority 1-2 chunks
   ⚠️ BUDGET: Each chunk ~500 tokens, fetch wisely!

3️⃣ Field Priority Configuration
   → get_context('product-uuid-123', field_priorities=true)
   Returns: User's priority settings (1=critical, 2=important, 3-4=optional)

   🎯 PRIORITY 1 FIELDS (MUST INCLUDE): tech_stack, architecture
   🎯 RULE: Only include Priority 1 fields in mission
   🎯 RULE: Include Priority 2 if token budget allows
   🎯 RULE: NEVER include Priority 3-4 (user marked optional)

4️⃣ Available Agent Templates
   → list_templates('tenant-key-abc')
   Returns: 6 agent types you can assign
   ⚠️ LIMIT: Max 8 agent types (hard constraint)
```

**Phase 2: Mission Creation (40% of effort)**

Instructions for creating condensed, token-efficient missions:

```
📝 PHASE 2: MISSION CREATION (40% of effort)
──────────────────────────────────────────────

Based on discovery, create a CONDENSED mission following these patterns:

✅ DO:
- Extract SPECIFIC requirements from vision (not generic)
- Break down into clear, measurable objectives
- Include technical constraints from product settings
- Reference priority fields only
- Target 3,000-5,000 tokens for mission text

❌ DON'T:
- Copy entire vision documents (condense!)
- Include low-priority fields (user doesn't care)
- Create generic missions (be specific!)
- Exceed token budget (agents won't spawn!)

🎯 Mission Format:
"""
MISSION: {concise_title}

OBJECTIVES:
1. {specific_objective_1}
2. {specific_objective_2}
...

TECHNICAL CONTEXT:
- Tech Stack: {from_product_settings}
- Architecture: {from_vision_priority_1}
- Constraints: {from_field_priorities}

SUCCESS CRITERIA:
- {measurable_criterion_1}
- {measurable_criterion_2}
"""
```

**Phase 3: Agent Selection (20% of effort)**

Intelligent agent allocation with token awareness:

```
👥 PHASE 3: AGENT SELECTION (20% of effort)
────────────────────────────────────────────

Select agents using intelligent allocation:

Available Templates: orchestrator, implementer, tester, documenter, analyzer, reviewer

🎯 Selection Rules:
1. Max 8 agent types (system constraint)
2. Match agent capabilities to mission requirements
3. Consider tool routing (Claude Code can spawn sub-agents)
4. Reserve 500 tokens per agent for templates

📊 Token Calculation Per Agent:
- Agent template prompt: ~300 tokens
- Mission context for agent: ~200 tokens
- Tool definitions: ~100 tokens
Total: 500 tokens per agent

Example Selections:
- Simple project: 3-4 agents (implementer, tester, documenter)
- Complex project: 6-8 agents (add analyzer, reviewer, optimizer)
```

**Phase 4: Coordination Protocol (10% of effort)**

Agent communication and workflow patterns:

```
🔄 PHASE 4: COORDINATION PROTOCOL (10% of effort)
──────────────────────────────────────────────────

Establish agent communication patterns:

✅ MANDATORY RULES:
1. All agents MUST acknowledge jobs: acknowledge_job(job_id)
2. Progress reporting: report_progress(job_id, percent, message)
3. Status updates to orchestrator: send_message(to=['orchestrator'], ...)
4. Questions ONLY to orchestrator (not user directly)

📡 MCP Communication Tools:
- send_message(to, message, project_id, from_agent)
- acknowledge_message(message_id)
- get_messages(agent_name, project_id)

🎭 Tool-Specific Workflows:

For Claude Code:
- ONE prompt launches all agents (sub-agent spawning)
- Orchestrator coordinates via internal messages
- Parallel execution supported
```

**Phase 5: Execution & Validation**

Final checklist and launch instructions:

```
⚡ PHASE 5: EXECUTION (Complete your work!)
────────────────────────────────────────────

Now that you have instructions, EXECUTE:

1. Run discovery (MCP calls)
2. Create condensed mission (respecting token budget)
3. Select agents (max 8, within budget)
4. Report back via update_mission('project-id', mission_text)
5. Report agents via select_agents('project-id', agent_list)

🎯 FINAL VALIDATION:
- Total tokens < 20,000? ✓
- Mission includes Priority 1 fields? ✓
- Agent count ≤ 8? ✓
- All agents have assigned missions? ✓
```

#### 3. Token Budget Validation (Layer 3)

**Budget Calculation**:
```python
Total Budget:              20,000 tokens
─────────────────────────────────────────
Orchestrator Reserve:       5,000 tokens (25%)
Agent Templates (6 × 500):  3,000 tokens (15%)
Mission Content Budget:    12,000 tokens (60%)
```

**Warnings Generated**:
- **Over 100%**: `"Token budget exceeded! {total} > {budget}"`
- **90-100%**: `"Token budget critical: {utilization}% utilized"`
- **80-90%**: `"Token budget high: {utilization}% utilized"`
- **< 80%**: No warnings (healthy)

**If Budget Exceeded**:
1. Fetch fewer vision chunks (priority 1 only)
2. Reduce agent count (minimum viable team)
3. Condense mission further
4. Warn user in response

---

## Token Budget Management

### Budget Breakdown

```
┌─────────────────────────────────────────────────┐
│         TOTAL BUDGET: 20,000 TOKENS             │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │  Orchestrator Reserve: 5,000 tokens      │ │
│  │  (Prompt instructions, templates, etc.)  │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │  Agent Templates: 500 × N agents          │ │
│  │  (6 agents = 3,000 tokens)                │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │  Mission Content: Remaining Budget        │ │
│  │  (12,000 tokens for 6 agents)             │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Why 20K?

**Claude's Constraints**:
- Maximum input: 25,000 tokens (sonnet-4-5)
- Safety buffer: 5,000 tokens (20% margin)
- Practical limit: **20,000 tokens**

**Breakdown Rationale**:
- **25% for orchestrator** - Comprehensive instructions (5 phases)
- **15% for agents** - Template prompts (6 agents × 500 tokens)
- **60% for content** - Mission, context, vision chunks

### Token Estimation Formula

```python
# Constants
CHARS_PER_TOKEN = 4  # Standard estimate

# Calculations
prompt_tokens = len(prompt_text) // CHARS_PER_TOKEN
mission_tokens = prompt_tokens - ORCHESTRATOR_RESERVE
agent_tokens = agent_count * PER_AGENT_RESERVE
total_tokens = prompt_tokens + agent_tokens

# Utilization
utilization_percent = (total_tokens / TOTAL_BUDGET) * 100
within_budget = total_tokens <= TOTAL_BUDGET
```

### Budget Optimization Strategies

**If Approaching Limit (80-90%)**:
1. **Reduce vision chunks**: Fetch only Priority 1
2. **Condense mission**: Target 3,000 tokens (not 5,000)
3. **Limit agents**: Use minimum viable team (3-4 agents)

**If Exceeding Limit (>100%)**:
1. **Emergency condensation**: Vision summaries only
2. **Minimal agent set**: Essential agents only (2-3)
3. **Shortened instructions**: Remove examples
4. **User warning**: Display budget exceeded alert

---

## MCP Integration

### Why MCP-Only?

**Problem**: Local file reads don't work for:
- Remote users on LAN/WAN
- Hosted deployments
- Docker containers
- Cloud instances

**Solution**: All data access via MCP tools (database queries)

### MCP Tools Used

#### 1. Product Context

**Tool**: `get_product(project_id)`

**Returns**:
```json
{
  "id": "product-uuid-123",
  "name": "My Product",
  "description": "Product description",
  "config_data": {
    "tech_stack": "Python/FastAPI/PostgreSQL/Vue3",
    "architecture": "Multi-tenant SaaS",
    "features": ["Feature 1", "Feature 2"],
    "dependencies": ["Dep 1", "Dep 2"]
  }
}
```

#### 2. Vision Documents

**Tool**: `get_vision_index(product_id)`

**Returns**:
```json
{
  "chunks": [
    {"id": 1, "topic": "Architecture Overview", "priority": 1},
    {"id": 2, "topic": "Technical Requirements", "priority": 1},
    {"id": 3, "topic": "Nice-to-Have Features", "priority": 3}
  ]
}
```

**Tool**: `get_vision(product_id, chunk_id)`

**Returns**:
```json
{
  "chunk_id": 1,
  "topic": "Architecture Overview",
  "content": "... vision document text ...",
  "tokens": 500
}
```

#### 3. Field Priorities

**Tool**: `get_context(product_id, field_priorities=true)`

**Returns**:
```json
{
  "field_priorities": {
    "tech_stack": 1,      // MUST include
    "architecture": 1,     // MUST include
    "features": 2,         // Include if budget allows
    "dependencies": 2,     // Include if budget allows
    "nice_to_have": 4      // NEVER include
  }
}
```

#### 4. Agent Templates

**Tool**: `list_templates(tenant_key)`

**Returns**:
```json
{
  "templates": [
    {
      "name": "Orchestrator",
      "agent_type": "orchestrator",
      "tool": "claude-code",
      "description": "Project manager and coordinator"
    },
    {
      "name": "Implementer",
      "agent_type": "implementer",
      "tool": "claude-code",
      "description": "Code implementation specialist"
    }
    // ... up to 8 templates
  ]
}
```

### Multi-Tenant Isolation

**Every MCP Call Includes**:
```python
# Tenant key from authenticated user
tenant_key = current_user.tenant_key

# All database queries filter by tenant
product = db.query(Product).filter(
    Product.id == product_id,
    Product.tenant_key == tenant_key  # ← Isolation
).first()
```

**Security Guarantees**:
- ✅ Zero cross-tenant data leakage
- ✅ All queries filtered by tenant_key
- ✅ API authentication required
- ✅ Database-level isolation

---

## Field Priority System

### User Configuration

**Location**: My Settings → General → Field Priorities

**Priority Levels**:
1. **Priority 1** - Critical (ALWAYS included)
2. **Priority 2** - Important (include if budget allows)
3. **Priority 3** - Optional (include if abundant budget)
4. **Priority 4** - Nice-to-have (NEVER included)

### Example Configuration

```json
{
  "field_priorities": {
    "tech_stack": 1,        // Critical: Must know technology
    "architecture": 1,       // Critical: Must understand design
    "features": 2,           // Important: Include if space
    "dependencies": 2,       // Important: Include if space
    "deployment": 3,         // Optional: Skip if tight
    "marketing": 4           // Nice-to-have: Never include
  }
}
```

### How It Works

**Discovery Phase**:
```python
# Fetch user priorities
field_priorities = get_context(product_id, field_priorities=true)

# Filter product context
priority_1_fields = [k for k, v in field_priorities.items() if v == 1]
priority_2_fields = [k for k, v in field_priorities.items() if v == 2]

# Build context (Priority 1 always, Priority 2 if budget allows)
context = {
    field: product.config_data[field]
    for field in priority_1_fields
}

if budget_remaining > threshold:
    context.update({
        field: product.config_data[field]
        for field in priority_2_fields
    })
```

**In Generated Prompt**:
```
🎯 PRIORITY 1 FIELDS (MUST INCLUDE): tech_stack, architecture
🎯 RULE: Only include Priority 1 fields in mission
🎯 RULE: Include Priority 2 if token budget allows
🎯 RULE: NEVER include Priority 3-4 (user marked optional)
```

### Benefits

1. **User Control**: Developers configure what matters
2. **Token Efficiency**: Skip irrelevant context
3. **Budget Optimization**: Intelligent inclusion based on space
4. **Multi-Project**: Different priorities per product

---

## Generated Prompt Structure

### Full Prompt Template

```
ORCHESTRATOR STAGING PROMPT
═══════════════════════════════════════════════════════════

🎯 PROJECT MISSION
──────────────────
Project: {project_name}
Product: {product_name}
Description: {project_description}

📊 YOUR CONTEXT BUDGET
──────────────────────
Total Budget: {total_budget} tokens
Reserved for You: {orchestrator_reserve} tokens (orchestrator overhead)
Per-Agent Reserve: {per_agent_reserve} tokens × {agent_count} = {agent_tokens} tokens
Mission Content Budget: {remaining_budget} tokens

⚠️ CRITICAL: Stay within budget or agents will fail to spawn!

🔍 PHASE 1: INTELLIGENT DISCOVERY (30% of effort)
──────────────────────────────────────────────────
{discovery_instructions}

📝 PHASE 2: MISSION CREATION (40% of effort)
──────────────────────────────────────────────
{mission_instructions}

👥 PHASE 3: AGENT SELECTION (20% of effort)
────────────────────────────────────────────
{agent_selection_instructions}

🔄 PHASE 4: COORDINATION PROTOCOL (10% of effort)
──────────────────────────────────────────────────
{coordination_instructions}

⚡ PHASE 5: EXECUTION (Complete your work!)
────────────────────────────────────────────
{execution_instructions}

═══════════════════════════════════════════════════════════
END ORCHESTRATOR STAGING PROMPT
```

### Example Output

**For 6-Agent Complex Project**:

- **Total Lines**: 2,847 lines
- **Prompt Tokens**: 7,118 tokens
- **Agent Tokens**: 3,000 tokens (6 × 500)
- **Total Tokens**: 10,118 tokens
- **Budget Utilization**: 50.6%
- **Status**: ✅ Healthy

**For 3-Agent Simple Project**:

- **Total Lines**: 1,923 lines
- **Prompt Tokens**: 4,808 tokens
- **Agent Tokens**: 1,500 tokens (3 × 500)
- **Total Tokens**: 6,308 tokens
- **Budget Utilization**: 31.5%
- **Status**: ✅ Excellent

---

## Usage Guide

### For End Users

#### 1. Navigate to Launch Tab

**Path**: Jobs → Launch tab (or Project List → Launch button)

#### 2. Click "Stage Project"

**What Happens**:
1. Toast notification: "Generating comprehensive orchestrator prompt..."
2. API call to `/api/prompts/staging/{project_id}`
3. Prompt generated (< 2 seconds)
4. Toast notification: "Orchestrator prompt copied! (8,500 tokens, 42.5% budget used)"

#### 3. Paste into CLI

**Claude Code**:
```bash
# Paste the comprehensive prompt directly into terminal
# Orchestrator will read the entire prompt and execute
```

**Codex/Gemini**:
```bash
# Paste prompt into Codex/Gemini terminal
# Orchestrator will execute similarly
```

#### 4. Watch Orchestrator Work

**Orchestrator Actions**:
1. Reads prompt instructions
2. Calls MCP tools to discover context
3. Creates condensed mission
4. Selects 3-8 agents
5. Assigns missions to agents
6. Reports back via `update_mission()` and `select_agents()`

#### 5. Review Mission & Agents

**UI Updates**:
- Mission card populates with condensed mission
- Agent cards appear (3-8 agents)
- Launch button becomes enabled

#### 6. Launch Jobs

**Click "Launch Jobs"**:
- Creates jobs for all agents
- Provides copy-paste prompts for each agent
- Agents begin execution

### For Developers

#### Customizing Prompt Generation

**File**: `src/giljo_mcp/prompt_generator.py`

**Modify Phase Instructions**:
```python
def _build_discovery_section(self, context: ContextData, tool: str) -> str:
    """Customize Phase 1: Discovery instructions"""
    # Add custom MCP tool instructions
    # Modify token awareness rules
    # Adjust field priority logic
```

**Adjust Token Budget**:
```python
# In src/giljo_mcp/prompt_generator.py
DEFAULT_TOKEN_BUDGET = 25000  # Increase for Opus
ORCHESTRATOR_RESERVE = 6000   # Increase reserve
PER_AGENT_RESERVE = 600        # Increase per-agent
```

**Add New Tool Support**:
```python
# In _build_coordination_section()
elif tool == "my-new-tool":
    tool_specific = """
For My New Tool:
- Custom workflow instructions
- Tool-specific MCP patterns
"""
```

#### Testing Prompt Generation

**Unit Test Example**:
```python
import pytest
from src.giljo_mcp.prompt_generator import OrchestratorPromptGenerator

@pytest.mark.asyncio
async def test_prompt_generation(db_session):
    generator = OrchestratorPromptGenerator(db_session, "tenant-123")

    result = await generator.generate("project-456", "claude-code")

    assert result["prompt"] is not None
    assert result["token_estimate"] < 20000
    assert result["within_budget"] is True
```

**Integration Test**:
```bash
# Call API endpoint directly
curl -X GET "http://localhost:7272/api/prompts/staging/project-uuid-123?tool=claude-code" \
  -H "Authorization: Bearer {token}"
```

---

## Technical Implementation

### File Structure

```
F:\GiljoAI_MCP/
├── src/giljo_mcp/
│   └── prompt_generator.py          # Core generator (600 lines)
├── api/endpoints/
│   └── prompts.py                   # API endpoint (+100 lines)
├── frontend/src/components/projects/
│   └── LaunchTab.vue                # UI integration (+50 lines)
└── docs/
    └── MASTER_ORCHESTRATOR_PROMPT.md  # This document
```

### Class Architecture

**`OrchestratorPromptGenerator`**:

```python
class OrchestratorPromptGenerator:
    """Main generator class"""

    def __init__(self, db: AsyncSession, tenant_key: str):
        self.db = db
        self.tenant_key = tenant_key
        self.token_budget = 20000
        self.template_manager = UnifiedTemplateManager(db)

    async def generate(self, project_id: str, tool: str) -> Dict[str, Any]:
        """Main entry point"""
        context = await self._gather_context(project_id)
        sections = await self._build_prompt_sections(context, tool)
        final_prompt = self._assemble_prompt(sections, context, tool)
        estimate = TokenEstimate.calculate(final_prompt, len(context.agent_templates))
        return {"prompt": final_prompt, "token_estimate": estimate.total, ...}

    async def _gather_context(self, project_id: str) -> ContextData:
        """Layer 1: Context aggregation"""
        # MCP-simulated queries

    async def _build_prompt_sections(self, context, tool) -> Dict[str, str]:
        """Layer 2: Prompt template generation"""
        # Build 5 phases

    def _assemble_prompt(self, sections, context, tool) -> str:
        """Layer 3: Response formatting"""
        # Combine sections
```

### API Endpoint

**Endpoint**: `GET /api/prompts/staging/{project_id}`

**Query Parameters**:
- `tool` (optional): `claude-code` (default), `codex`, or `gemini`

**Response Schema**:
```json
{
  "prompt": "string (2000-3000 lines)",
  "token_estimate": "integer",
  "budget_utilization": "string (percentage)",
  "context_included": {
    "product_name": "string",
    "project_name": "string",
    "vision_chunk_count": "integer",
    "field_count": "integer",
    "template_count": "integer"
  },
  "warnings": ["array of strings"],
  "tool": "string",
  "estimate_details": {
    "prompt_tokens": "integer",
    "mission_tokens": "integer",
    "agent_tokens": "integer",
    "total_tokens": "integer"
  }
}
```

### Frontend Integration

**Component**: `LaunchTab.vue`

**Method**: `handleStageProject()`

```javascript
async function handleStageProject() {
  stagingInProgress.value = true

  try {
    // Show loading
    toastMessage.value = 'Generating comprehensive orchestrator prompt...'
    showToast.value = true

    // API call
    const response = await window.api.get(`/api/prompts/staging/${props.project.id}`, {
      params: { tool: 'claude-code' }
    })

    const { prompt, token_estimate, budget_utilization, warnings } = response.data

    // Copy to clipboard
    await navigator.clipboard.writeText(prompt)

    // Success feedback
    toastMessage.value = `Orchestrator prompt copied! (${token_estimate} tokens, ${budget_utilization} budget used)`
    showToast.value = true

    emit('stage-project')

  } catch (err) {
    // Error handling
    const errorMsg = err.response?.data?.detail || 'Failed to generate orchestrator prompt'
    toastMessage.value = `Error: ${errorMsg}`
    showToast.value = true
  }
}
```

---

## Troubleshooting

### Common Issues

#### 1. "Project not found or not accessible"

**Cause**: Project doesn't exist or tenant mismatch

**Solution**:
```python
# Check project exists
SELECT id, tenant_key FROM projects WHERE id = 'project-uuid';

# Verify user's tenant matches
SELECT tenant_key FROM users WHERE id = 'user-id';
```

#### 2. "Token budget exceeded"

**Cause**: Too many agents or too much context

**Solutions**:
- Reduce agent count (use 3-4 instead of 6-8)
- Set more fields to Priority 3-4 (skip in mission)
- Reduce vision document count
- Condense project description

#### 3. "Failed to generate orchestrator prompt"

**Cause**: Database connection issue or internal error

**Check Logs**:
```bash
# Backend logs
tail -f logs/giljo_mcp.log | grep "STAGING PROMPT"

# Look for:
# - Database connection errors
# - Template retrieval failures
# - Context aggregation errors
```

#### 4. Clipboard Copy Fails

**Cause**: Browser security restrictions

**Solutions**:
- Use HTTPS (not HTTP)
- Grant clipboard permissions in browser
- Try manual copy-paste from browser console:
  ```javascript
  console.log(response.data.prompt)
  ```

#### 5. Prompt Missing Context

**Cause**: Field priorities set too restrictive

**Check Configuration**:
```sql
SELECT config_data->'field_priorities' FROM products WHERE id = 'product-uuid';
```

**Adjust Priorities**:
- Set critical fields to Priority 1
- Set important fields to Priority 2
- Review token budget utilization

### Performance Issues

#### Slow Prompt Generation (> 5 seconds)

**Causes**:
- Large vision documents (>100 chunks)
- Many agent templates (>20)
- Slow database queries

**Solutions**:
```python
# Add database indexes
CREATE INDEX idx_vision_product ON vision_documents(product_id);
CREATE INDEX idx_templates_tenant ON agent_templates(tenant_key);

# Enable query caching
# Use template cache (already implemented)
```

#### High Memory Usage

**Cause**: Large prompts stored in memory

**Solution**: Stream response instead of buffering:
```python
from fastapi.responses import StreamingResponse

async def generate_streaming():
    prompt = await generator.generate(project_id, tool)
    yield prompt.encode('utf-8')

return StreamingResponse(generate_streaming(), media_type="text/plain")
```

### Debugging Tips

#### Enable Debug Logging

```python
# In src/giljo_mcp/prompt_generator.py
import logging
logging.basicConfig(level=logging.DEBUG)

logger.debug(f"[CONTEXT] Gathered - vision_chunks={len(vision_chunks)}")
logger.debug(f"[TOKEN] Estimate - prompt={prompt_tokens}, agents={agent_tokens}")
```

#### Test Components Independently

```python
# Test context aggregation
context = await generator._gather_context(project_id)
print(f"Context: {context.summary}")

# Test section generation
sections = await generator._build_prompt_sections(context, "claude-code")
print(f"Sections: {sections.keys()}")

# Test token estimation
estimate = TokenEstimate.calculate(final_prompt, 6)
print(f"Tokens: {estimate.total}, Utilization: {estimate.utilization_percent}%")
```

---

## Future Enhancements

### Planned Features

#### 1. Tool Selector in UI

**Current**: Hardcoded to `claude-code`

**Future**: Dropdown to select Claude Code / Codex / Gemini

```vue
<!-- In LaunchTab.vue -->
<v-select
  v-model="selectedTool"
  :items="['claude-code', 'codex', 'gemini']"
  label="AI Tool"
  prepend-icon="mdi-robot"
/>
```

#### 2. Prompt Preview Dialog

**Current**: Prompt immediately copied to clipboard

**Future**: Show preview with sections before copying

```vue
<v-dialog v-model="showPreview" max-width="1200">
  <v-card>
    <v-card-title>Orchestrator Prompt Preview</v-card-title>
    <v-card-text>
      <pre>{{ generatedPrompt }}</pre>
    </v-card-text>
    <v-card-actions>
      <v-btn @click="copyToClipboard">Copy to Clipboard</v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

#### 3. Custom Phase Templates

**Current**: Hardcoded 5-phase structure

**Future**: Allow users to customize phase content

**Implementation**:
```python
# Store custom templates in database
class PromptTemplate(Base):
    id = Column(String, primary_key=True)
    tenant_key = Column(String, nullable=False)
    phase_name = Column(String)  # discovery, mission, agents, etc.
    content_template = Column(Text)

# Load user's custom templates
custom_templates = db.query(PromptTemplate).filter_by(tenant_key=tenant_key).all()
```

#### 4. Token Budget Profiles

**Current**: Fixed 20K budget

**Future**: Configurable budgets per product

```python
# In product settings
product.config_data["token_budget"] = {
    "total": 25000,  # For Opus
    "orchestrator_reserve": 6000,
    "per_agent_reserve": 600
}
```

#### 5. Multi-Language Support

**Current**: English only

**Future**: Generate prompts in user's language

```python
def _build_discovery_section(self, context, tool, language="en"):
    if language == "es":
        return "FASE 1: DESCUBRIMIENTO INTELIGENTE..."
    elif language == "fr":
        return "PHASE 1: DÉCOUVERTE INTELLIGENTE..."
    else:
        return "PHASE 1: INTELLIGENT DISCOVERY..."
```

#### 6. Prompt Analytics

**Current**: No tracking

**Future**: Track prompt usage and effectiveness

```python
class PromptAnalytics(Base):
    id = Column(String, primary_key=True)
    project_id = Column(String)
    generated_at = Column(DateTime)
    token_estimate = Column(Integer)
    actual_tokens_used = Column(Integer)  # Reported by orchestrator
    mission_created = Column(Boolean)
    agents_spawned = Column(Integer)
    success_rate = Column(Float)
```

#### 7. Collaborative Editing

**Current**: Generated prompt is final

**Future**: Allow developers to edit before copying

```vue
<monaco-editor
  v-model="editablePrompt"
  language="markdown"
  :options="{ readOnly: false }"
/>
```

---

## Conclusion

The **Master Orchestrator Staging Prompt System** is the beating heart of GiljoAI. It transforms complex product context into actionable, token-efficient instructions that enable intelligent multi-agent orchestration.

### Key Achievements

✅ **MCP-Only Data Access** - Works everywhere (LAN/WAN/hosted)
✅ **Dynamic Field Priorities** - User-configured, not hardcoded
✅ **20K Token Budget** - Intelligent management with overflow handling
✅ **70% Token Reduction** - Via intelligent condensation
✅ **Multi-Tool Support** - Claude Code, Codex, Gemini
✅ **Production-Grade** - Comprehensive error handling & logging

### Impact

**Before**: 6-line generic placeholder
**After**: 2000-3000 line comprehensive orchestration system

**From clicking "Stage Project" to pasting a production-ready orchestrator prompt: < 2 seconds.**

---

## References

**Related Documentation**:
- [Installation Guide](INSTALLATION_FLOW_PROCESS.md)
- [Architecture Overview](SERVER_ARCHITECTURE_TECH_STACK.md)
- [Agent Template System](AGENT_TEMPLATES_REFERENCE.md)
- [MCP Integration](MCP_OVER_HTTP_INTEGRATION.md)
- [Token Reduction Architecture](vision/TOKEN_REDUCTION_ARCHITECTURE.md)

**Handovers**:
- 0048: Field Priority Configuration
- 0065: Mission Launch Token Counter
- 0073: Static Agent Grid
- **0079: Master Orchestrator Staging Prompt** (this implementation)

**Support**:
- GitHub Issues: https://github.com/anthropics/giljoai-mcp/issues
- Documentation: F:\GiljoAI_MCP\docs\README_FIRST.md

---

**Document Version**: 1.0
**Last Updated**: 2025-10-31
**Author**: GiljoAI Development Team
**Status**: Production Ready
