# Orchestrator Context Flow - Single Source of Truth (SSoT)

**Status**: Production Documentation
**Version**: 1.0
**Last Updated**: 2025-11-17
**Last Verified**: 2025-11-17
**Handovers**: 0301, 0302, 0303, 0305, 0306, 0311, 0135-0139, 013B
**Related Documents**: [ORCHESTRATOR.md](ORCHESTRATOR.md), [CONTEXT_MANAGEMENT_SYSTEM.md](CONTEXT_MANAGEMENT_SYSTEM.md), [SERVICES.md](SERVICES.md)

---

## Overview

This document serves as the **Single Source of Truth (SSoT)** for understanding the complete orchestrator context flow in GiljoAI MCP v3.1+. It explains how user-configured context toggle cards translate into orchestrator prompts, how context optimization is achieved (77% reduction from 15K-30K baseline to 3,500 tokens), and how agents receive targeted context based on their specific mission.

**Purpose**: Document the complete end-to-end flow from user setup → orchestrator launch → context building → agent spawning → completion.

**Key Achievement**: **70-77% context optimization** through intelligent toggle-based context extraction and thin client architecture.

---

## The 13 Context Toggle Cards

Users configure 13 context toggle "cards" (fields) in **User Settings → Context Configuration** to control what context is included in orchestrator missions. Each card has a simple on/off toggle plus optional depth controls.

### Toggle States

- **Enabled** (toggle: true): Category is included in context with configured depth
- **Disabled** (toggle: false): Category is excluded from context entirely
- **Priority 1-3 (Minimal)**: Bare minimum context
- **Priority 0 (Exclude)**: Field completely excluded from context

### The 13 Cards (Default Priorities)

| # | Field Path | Label | Default Priority | Token Budget | Detail Level |
|---|------------|-------|------------------|--------------|--------------|
| 1 | `product.name` | **Product Name** | MANDATORY | ~20 tokens | Always included |
| 2 | `product.vision_summary` | **Vision Document** | MANDATORY | ~500 tokens | Always included (chunked if large) |
| 3 | `config_data.tech_stack` | **Tech Stack** | 7 (Moderate) | ~150 tokens | Languages, frameworks, databases |
| 4 | `config_data.architecture` | **Architecture Patterns** | 7 (Moderate) | ~100 tokens | Design patterns, system architecture |
| 5 | `config_data.api_style` | **API Style** | 6 (Abbreviated) | ~50 tokens | REST, GraphQL, etc. |
| 6 | `config_data.design_patterns` | **Design Patterns** | 6 (Abbreviated) | ~50 tokens | Singleton, Factory, etc. |
| 7 | `config_data.features` | **Features** | 7 (Moderate) | ~100 tokens | Product feature list |
| 8 | `config_data.testing_preferences` | **Testing Preferences** | 6 (Abbreviated) | ~50 tokens | Unit/integration test preferences |
| 9 | `product_memory.learnings` | **360 Memory** | 7 (Moderate) | ~600 tokens | Historical project learnings |
| 10 | `git_integration.enabled` | **Git Integration** | TOGGLE | ~250 tokens | Git command instructions |
| 11 | `agent_templates` | **Agent Templates** | 7 (Moderate) | ~200 tokens | Agent role definitions |
| 12 | `serena_mcp_enabled` | **Serena MCP Tools** | 6 (Abbreviated) | ~200 tokens | Symbolic code navigation tools |
| 13 | `codebase_summary` | **Codebase Summary** | 5 (Abbreviated) | ~150 tokens | High-level codebase overview |

**MANDATORY Fields**: Product name and vision summary are always included regardless of user priority settings (500 tokens baseline).

**TOGGLE Fields**: Git Integration is on/off (not priority-based). When enabled, injects git command instructions (~250 tokens).

**Total Default Budget**: ~2,500-3,500 tokens (down from 15K-30K baseline = **77% reduction**)

---

## Complete Orchestrator Workflow

### Initial Setup (User Actions)

**Step 1**: User creates a product
- **Location**: Products view → Create Product button
- **Data**: Product name, vision document (file upload or inline text), config fields (tech stack, architecture, features)
- **Result**: Product created with `config_data` JSONB fields and `product_memory` initialized

**Step 2**: User configures field priorities
- **Location**: User Settings → Field Priorities → Drag-and-drop interface
- **Action**: User drags fields between priority levels (P1/P2/P3) or sets priority 0 to exclude
- **Storage**: `users.field_priority_config` JSONB column
- **Result**: Personalized context preferences saved per user

**Step 3**: User configures integrations
- **Location**: Settings → Integrations tab
- **Actions**:
  - **Git Integration**: Toggle on/off for git command instructions
  - **Serena MCP**: Enable symbolic code navigation tools
  - **360 Memory**: Populated automatically via project closeout
- **Result**: Integration settings stored in `product_memory.git_integration` and user preferences

**Step 4**: User creates a project
- **Location**: Projects view → Create Project button
- **Data**: Project name, description, parent product
- **Validation**: Parent product must be active (single active product enforcement)
- **Result**: Project created and linked to active product

---

### Orchestrator Launch Flow

#### Step 1: User Clicks "Orchestrate Project"

**UI Action**: Dashboard → Projects list → Project card → "Orchestrate" button

**API Call**:
```http
POST /api/v1/orchestration/stage-project
Content-Type: application/json

{
  "project_id": "uuid",
  "tenant_key": "default"
}
```

**Backend Processing** (`OrchestrationService`):
1. **Validate project status**: Must be active, parent product must be active
2. **Create orchestrator job**: Insert row in `mcp_agent_jobs` table
   - `agent_type`: "orchestrator"
   - `status`: "pending"
   - `context_budget`: 200,000 tokens (configurable)
   - `context_used`: 0 tokens (initial)
3. **Stage prompt generation**: Generate thin client prompt (NOT full mission context yet)
4. **Return launch prompt**: User copies prompt and launches Claude Code/Codex/Gemini

**Response**:
```json
{
  "job_id": 123,
  "launch_prompt": "You are an orchestrator for project X. Use get_orchestrator_instructions(job_id=123) to fetch your full mission context.",
  "status": "pending"
}
```

**Key Point**: Full mission context is NOT included in the launch prompt. This is the **thin client architecture** - the prompt is ~10 lines, not 3,000 lines.

---

#### Step 2: Orchestrator MCP Tool Fetches Thin Client Prompt

**Orchestrator Action** (in Claude Code/Codex/Gemini session):

```python
# Orchestrator executes MCP tool
get_orchestrator_instructions(job_id=123, tenant_key="default")
```

**MCP Tool Handler** (`src/giljo_mcp/tools/orchestration.py`):
1. **Fetch job record**: Query `mcp_agent_jobs` where `id=123`
2. **Fetch project**: Query `projects` where `id=job.project_id`
3. **Fetch product**: Query `products` where `id=project.product_id`
4. **Fetch user settings**: Query `users.field_priority_config` for user who launched
5. **Call MissionPlanner**: Build context with priorities
6. **Return full context**: ~3,500 tokens (priority-based extraction)

**MCP Tool Response**:
```json
{
  "mission_context": "<3,500 token context string>",
  "project_id": "uuid",
  "product_id": "uuid",
  "context_budget": 200000,
  "field_toggles_applied": {
    "tech_stack": true,
    "architecture": true,
    "product_memory.learnings": true,
    "codebase_summary": true
  }
}
```

---

#### Step 3: Orchestrator Builds Full Context

**Implementation**: `MissionPlanner._build_fetch_instructions()` method
**File**: `src/giljo_mcp/mission_planner.py` (lines 592-883)

This is where the **13 context toggle cards** translate into actual token-optimized context.

##### 3.1: MANDATORY Section (500 tokens)

**Always included, regardless of user toggle settings**:

```python
context = []

# MANDATORY: Product name (~20 tokens)
context.append(f"# Product: {product.name}")

# MANDATORY: Vision summary (~480 tokens)
vision_summary = self._extract_vision_summary(product)
context.append(f"## Vision\n{vision_summary}")

# MANDATORY: Project description (~50 tokens)
context.append(f"## Project\n{project.description}")

# Running total: ~550 tokens (mandatory baseline)
```

**Token Count**: ~500 tokens (non-negotiable)

---

##### 3.2: Product Vision Section (Chunking) - Priority-Based

**Field**: `product.vision_summary`
**Priority**: MANDATORY (but chunking strategy varies by document size)
**Token Budget**: ~500-1,200 tokens

**Extraction Logic**:
```python
async def _extract_vision_summary(self, product: Product) -> str:
    """
    Extract vision with intelligent chunking for large documents.

    Chunking Strategy:
    - Document < 25K tokens: Include full vision (~500 tokens summary)
    - Document 25K-100K tokens: Chunk into 3-5 semantic chunks, include first chunk + index (~800 tokens)
    - Document > 100K tokens: Chunk into 10+ chunks, include executive summary + index (~1,200 tokens)
    """
    if not product.vision_summary:
        return ""

    # Check document size
    total_tokens = self._count_tokens(product.vision_summary)

    if total_tokens < 25000:
        # Small document: include full summary
        return product.vision_summary

    # Large document: use VisionDocumentChunker (Handover 0305)
    chunks = await self.vision_chunker.chunk_document(
        product.vision_summary,
        max_chunk_size=25000
    )

    # Return first chunk + chunk index
    chunk_index = self._build_chunk_index(chunks)
    return f"{chunks[0].content}\n\n{chunk_index}"
```

**Chunking Example** (JWT authentication project):

**Original Vision Document**: 45,000 tokens (full specification)

**Chunked Context** (~800 tokens):
```markdown
## Vision (Chunk 1 of 3)

**Project**: JWT Authentication System

**Objective**: Build a secure, production-grade authentication system with JWT tokens,
password reset, and 2FA support.

**Key Features**:
- User registration with email verification
- Login with JWT access + refresh tokens
- Password reset via email link
- 2FA with TOTP (Google Authenticator)

**Tech Stack**: Python, FastAPI, PostgreSQL, bcrypt, SendGrid

**Chunk Index**:
- Chunk 1: Overview and objectives (current)
- Chunk 2: Detailed API specifications (25K tokens)
- Chunk 3: Database schema and security requirements (20K tokens)

Use vision_chunk_retrieve(chunk_id=2) to fetch additional chunks as needed.
```

**Token Count**: ~800 tokens (down from 45,000 = **98% reduction per chunk**)

---

##### 3.3: Tech Stack Section - Priority 7 (Moderate)

**Field**: `config_data.tech_stack`
**Default Priority**: 7 (Moderate)
**Token Budget**: ~150 tokens

**Extraction Logic**:
```python
tech_stack_priority = field_toggles.get("config_data.tech_stack", 7)

if tech_stack_priority > 0:
    tech_stack_context = self._extract_tech_stack(
        product.config_data.get("tech_stack", ""),
        priority=tech_stack_priority
    )
    context.append(tech_stack_context)
    tokens_used += self._count_tokens(tech_stack_context)

def _extract_tech_stack(self, tech_stack: str, priority: int) -> str:
    """
    Priority-based tech stack extraction:
    - Priority 10 (full): All details, versions, rationale
    - Priority 7-9 (moderate): Languages, frameworks, databases, key tools
    - Priority 4-6 (abbreviated): Languages and frameworks only
    - Priority 1-3 (minimal): Primary language and framework
    - Priority 0 (exclude): Empty string
    """
    if priority == 0 or not tech_stack:
        return ""

    if priority >= 10:
        # Full: include everything
        return f"## Tech Stack\n{tech_stack}"

    elif priority >= 7:
        # Moderate: extract key components
        lines = tech_stack.split("\n")
        key_components = [
            line for line in lines
            if any(keyword in line.lower()
                   for keyword in ["language", "framework", "database", "backend", "frontend"])
        ]
        return f"## Tech Stack\n" + "\n".join(key_components[:10])

    elif priority >= 4:
        # Abbreviated: languages and frameworks only
        lines = tech_stack.split("\n")
        essential = [
            line for line in lines
            if any(keyword in line.lower() for keyword in ["language", "framework"])
        ]
        return f"## Tech Stack\n" + "\n".join(essential[:5])

    else:
        # Minimal: primary language and framework
        lines = tech_stack.split("\n")
        return f"## Tech Stack\n{lines[0] if lines else ''}"
```

**Example Output** (Priority 7 - Moderate):
```markdown
## Tech Stack

**Backend**: Python 3.11+, FastAPI
**Database**: PostgreSQL 18
**Frontend**: Vue 3, Vuetify 3
**Authentication**: JWT (PyJWT), bcrypt
**Testing**: pytest, pytest-asyncio
```

**Token Count**: ~150 tokens

---

##### 3.4: Config Fields Section - Priority 6-7 (Abbreviated/Moderate)

**Fields**:
- `config_data.architecture` (Priority 7 - Moderate) → ~100 tokens
- `config_data.api_style` (Priority 6 - Abbreviated) → ~50 tokens
- `config_data.design_patterns` (Priority 6 - Abbreviated) → ~50 tokens
- `config_data.features` (Priority 7 - Moderate) → ~100 tokens
- `config_data.testing_preferences` (Priority 6 - Abbreviated) → ~50 tokens

**Extraction Logic** (similar pattern for all config fields):
```python
architecture_priority = field_toggles.get("config_data.architecture", 7)

if architecture_priority > 0:
    architecture = product.config_data.get("architecture", "")
    architecture_context = self._extract_config_field(
        field_name="Architecture Patterns",
        field_value=architecture,
        priority=architecture_priority,
        detail_levels={
            "full": "All architecture details and rationale",
            "moderate": "Key patterns and system design",
            "abbreviated": "Primary architectural approach",
            "minimal": "Architecture type (monolith/microservices/etc.)"
        }
    )
    context.append(architecture_context)
    tokens_used += self._count_tokens(architecture_context)
```

**Example Output** (Priority 7 - Moderate):
```markdown
## Architecture Patterns

**System Design**: Monolithic application with service layer separation
**Patterns**: Repository pattern, dependency injection, async/await
**Database Access**: SQLAlchemy ORM with connection pooling
**API Design**: RESTful endpoints with FastAPI
```

**Token Count**: ~100 tokens per field × 5 fields = **~450 tokens total**

---

##### 3.5: Agent Templates Section - Priority 7 (Moderate)

**Field**: `agent_templates`
**Default Priority**: 7 (Moderate)
**Token Budget**: ~200 tokens

**Extraction Logic**:
```python
templates_priority = field_toggles.get("agent_templates", 7)

if templates_priority > 0:
    templates_context = await self._extract_agent_templates(
        product.id,
        priority=templates_priority
    )
    context.append(templates_context)
    tokens_used += self._count_tokens(templates_context)

async def _extract_agent_templates(self, product_id: str, priority: int) -> str:
    """
    Extract agent template summaries.

    Priority levels:
    - Priority 10 (full): All templates with full content
    - Priority 7-9 (moderate): Template names + role descriptions
    - Priority 4-6 (abbreviated): Template names only
    - Priority 1-3 (minimal): Count of available templates
    - Priority 0 (exclude): Empty string
    """
    if priority == 0:
        return ""

    # Fetch templates from database
    templates = await self.template_cache.get_all_templates(product_id)

    if priority >= 10:
        # Full: include all template content
        return self._format_templates_full(templates)

    elif priority >= 7:
        # Moderate: names + role descriptions
        lines = ["## Available Agent Templates\n"]
        for template in templates:
            lines.append(f"- **{template.name}**: {template.role_description}")
        return "\n".join(lines)

    elif priority >= 4:
        # Abbreviated: names only
        template_names = ", ".join([t.name for t in templates])
        return f"## Agent Templates\n{template_names}"

    else:
        # Minimal: count only
        return f"## Agent Templates\n{len(templates)} templates available"
```

**Example Output** (Priority 7 - Moderate):
```markdown
## Available Agent Templates

- **Implementer**: Writes production-grade code following best practices
- **Tester**: Creates comprehensive test suites (unit, integration, E2E)
- **Refactorer**: Improves code quality and removes technical debt
- **Documenter**: Writes clear, concise documentation
- **Reviewer**: Conducts thorough code reviews and provides feedback
- **Debugger**: Diagnoses and fixes bugs efficiently
```

**Token Count**: ~200 tokens

---

##### 3.6: 360 Memory Section - Priority 7 (Moderate)

**Field**: `product_memory.learnings`
**Default Priority**: 7 (Moderate)
**Token Budget**: ~600 tokens
**Handovers**: 0135-0139 (backend), 0311 (context integration)

**Extraction Logic** (Handover 0311):
```python
learnings_priority = field_toggles.get("product_memory.learnings", 7)

if learnings_priority > 0:
    learnings_context = await self._extract_product_learnings(
        product,
        priority=learnings_priority,
        max_entries=10
    )
    if learnings_context:
        context.append(learnings_context)
        tokens_used += self._count_tokens(learnings_context)

async def _extract_product_learnings(
    self, product: Product, priority: int, max_entries: int = 10
) -> str:
    """
    Extract learnings from product_memory.learnings array.

    Priority-based detail levels:
    - Priority 10 (full): All learnings with summary + outcomes + decisions
    - Priority 7-9 (moderate): Last 5 learnings with summary + outcomes
    - Priority 4-6 (abbreviated): Last 3 learnings with summary only
    - Priority 1-3 (minimal): Last 1 learning with summary only
    - Priority 0 (exclude): Empty string
    """
    if priority == 0 or not product.product_memory:
        return ""

    learnings = product.product_memory.get("learnings", [])
    if not learnings:
        return ""

    # Sort by sequence (most recent first)
    sorted_learnings = sorted(
        learnings, key=lambda x: x.get("sequence", 0), reverse=True
    )

    # Determine entry count based on priority
    if priority >= 10:
        entries = sorted_learnings[:max_entries]  # Up to 10 learnings
    elif priority >= 7:
        entries = sorted_learnings[:5]  # Last 5 learnings
    elif priority >= 4:
        entries = sorted_learnings[:3]  # Last 3 learnings
    else:
        entries = sorted_learnings[:1]  # Last 1 learning

    # Format learnings
    sections = ["## Historical Context (360 Memory)\n"]
    sections.append(
        f"Product has {len(learnings)} previous project(s) in learning history. "
        f"Showing {len(entries)} most recent:\n"
    )

    for entry in entries:
        seq = entry.get("sequence", "?")
        project_name = entry.get("project_name", "Unknown")
        timestamp = entry.get("timestamp", "")[:10]
        summary = entry.get("summary", "")

        sections.append(f"### Learning #{seq} - {project_name} ({timestamp})")
        sections.append(f"{summary}\n")

        # Add outcomes for moderate/full
        if priority >= 7:
            outcomes = entry.get("key_outcomes", [])
            if outcomes:
                sections.append("**Key Outcomes:**")
                for outcome in outcomes:
                    sections.append(f"- {outcome}")
                sections.append("")

        # Add decisions for full only
        if priority >= 10:
            decisions = entry.get("decisions_made", [])
            if decisions:
                sections.append("**Decisions Made:**")
                for decision in decisions:
                    sections.append(f"- {decision}")
                sections.append("")

    sections.append(
        "\n**Note**: Use these learnings to inform decisions, "
        "avoid past mistakes, and build on successful patterns.\n"
    )

    return "\n".join(sections)
```

**Example Output** (Priority 7 - Moderate, 5 learnings):
```markdown
## Historical Context (360 Memory)

Product has 12 previous project(s) in learning history. Showing 5 most recent:

### Learning #12 - JWT Auth System (2025-11-10)
Implemented production-grade JWT authentication with refresh tokens and 2FA support.

**Key Outcomes:**
- 100% test coverage for auth endpoints
- bcrypt password hashing with cost factor 12
- TOTP-based 2FA integration successful
- SendGrid email service integrated

### Learning #11 - User Management Dashboard (2025-10-25)
Built admin dashboard for user CRUD operations with role-based access control.

**Key Outcomes:**
- Vue 3 + Vuetify 3 UI implemented
- Real-time WebSocket updates working
- RBAC enforcement at API level

[...3 more learnings...]

**Note**: Use these learnings to inform decisions, avoid past mistakes, and build on successful patterns.
```

**Token Count**: ~600 tokens (5 learnings with outcomes)

---

##### 3.7: Git Integration Section - TOGGLE (Not Priority-Based)

**Field**: `product_memory.git_integration.enabled`
**Default**: OFF (user toggles in Settings → Integrations)
**Token Budget**: ~250 tokens (fixed)
**Handover**: 013B (Git refactor)

**Extraction Logic**:
```python
git_config = product.product_memory.get("git_integration", {})

if git_config.get("enabled"):
    git_instructions = self._inject_git_instructions(git_config)
    context.append(git_instructions)
    tokens_used += self._count_tokens(git_instructions)

def _inject_git_instructions(self, git_config: dict) -> str:
    """
    Inject git command instructions when Git integration enabled.

    Note: This does NOT fetch commits (CLI agents do that using user's credentials).
    This adds INSTRUCTIONS for agents to run git commands.
    """
    commit_limit = git_config.get("commit_limit", 20)
    default_branch = git_config.get("default_branch", "main")

    instructions = [
        "## Git Integration\n",
        "You have access to git commands for additional historical context. "
        "Use these commands to see recent work:\n",
        "**Recommended Commands**:",
        "```bash",
        "# Recent commit history",
        f"git log --oneline -{commit_limit}",
        "",
        "# Recent changes with author and date",
        'git log --since="1 week ago" --pretty=format:"%h - %s (%an, %ar)"',
        "",
        "# Current branch status",
        "git branch --show-current",
        "git status --short",
        "",
        "# See what changed in recent commits",
        "git show --stat HEAD~5..HEAD",
        "```\n",
        "**Important**: Combine git history with 360 Memory learnings for complete context.\n"
    ]

    return "\n".join(instructions)
```

**Example Output**:
```markdown
## Git Integration

You have access to git commands for additional historical context. Use these commands to see recent work:

**Recommended Commands**:
```bash
# Recent commit history
git log --oneline -20

# Recent changes with author and date
git log --since="1 week ago" --pretty=format:"%h - %s (%an, %ar)"

# Current branch status
git branch --show-current
git status --short

# See what changed in recent commits
git show --stat HEAD~5..HEAD
```

**Important**: Combine git history with 360 Memory learnings for complete context.
```

**Token Count**: ~250 tokens (fixed)

---

##### 3.8: Serena MCP Tools Section - Priority 6 (Abbreviated)

**Field**: `serena_mcp_enabled`
**Default Priority**: 6 (Abbreviated)
**Token Budget**: ~200 tokens

**Extraction Logic**:
```python
serena_priority = field_toggles.get("serena_mcp_enabled", 6)

if serena_priority > 0 and include_serena:
    serena_context = self._inject_serena_tools(priority=serena_priority)
    context.append(serena_context)
    tokens_used += self._count_tokens(serena_context)

def _inject_serena_tools(self, priority: int) -> str:
    """
    Inject Serena MCP symbolic code navigation tool instructions.

    Priority levels:
    - Priority 10 (full): All Serena tools with examples
    - Priority 7-9 (moderate): Core tools with brief descriptions
    - Priority 4-6 (abbreviated): Tool names and purposes only
    - Priority 1-3 (minimal): "Serena MCP available" note
    - Priority 0 (exclude): Empty string
    """
    if priority == 0:
        return ""

    if priority >= 10:
        # Full: all tools with examples
        return SERENA_TOOLS_FULL_REFERENCE  # ~800 tokens

    elif priority >= 7:
        # Moderate: core tools with descriptions
        return """## Serena MCP Tools Available

**Symbolic Code Navigation** (60-90% context prioritization):
- find_symbol(name_path, relative_path) - Find classes, functions, methods
- get_symbols_overview(relative_path) - Get file structure
- find_referencing_symbols(name_path, relative_path) - Find usages
- replace_symbol_body(name_path, relative_path, body) - Edit code symbolically

**Pattern Search**:
- search_for_pattern(substring_pattern, relative_path) - Regex search in codebase

**Important**: Use symbolic tools (find_symbol) instead of reading full files to dramatically reduce unnecessary context streaming and keep agents within healthy token budgets.
"""

    elif priority >= 4:
        # Abbreviated: tool names only
        return """## Serena MCP Tools

Symbolic navigation tools available: find_symbol, get_symbols_overview, find_referencing_symbols,
replace_symbol_body, search_for_pattern. Use these for 60-90% context prioritization.
"""

    else:
        # Minimal: brief note
        return "## Serena MCP Tools\nSymbolic code navigation available for efficient context usage."
```

**Example Output** (Priority 6 - Abbreviated):
```markdown
## Serena MCP Tools

Symbolic navigation tools available: find_symbol, get_symbols_overview, find_referencing_symbols,
replace_symbol_body, search_for_pattern. Use these for 60-90% context prioritization.
```

**Token Count**: ~200 tokens

---

##### 3.9: Codebase Summary Section - Priority 5 (Abbreviated)

**Field**: `codebase_summary`
**Default Priority**: 5 (Abbreviated)
**Token Budget**: ~150 tokens

**Extraction Logic**:
```python
codebase_priority = field_toggles.get("codebase_summary", 5)

if codebase_priority > 0:
    codebase_context = await self._extract_codebase_summary(
        product,
        priority=codebase_priority
    )
    context.append(codebase_context)
    tokens_used += self._count_tokens(codebase_context)

async def _extract_codebase_summary(self, product: Product, priority: int) -> str:
    """
    Extract codebase summary from product context.

    Priority levels:
    - Priority 10 (full): Full directory tree + file counts
    - Priority 7-9 (moderate): Key directories + tech stack
    - Priority 4-6 (abbreviated): High-level structure only
    - Priority 1-3 (minimal): Project type + language
    - Priority 0 (exclude): Empty string
    """
    if priority == 0:
        return ""

    # For now, generate static summary based on tech stack
    # Future: integrate with Serena MCP list_dir() for real codebase structure

    tech_stack = product.config_data.get("tech_stack", "")

    if priority >= 10:
        # Full: detailed structure
        return f"""## Codebase Structure

**Tech Stack**: {tech_stack}

**Directory Structure**:
- src/ - Source code
- tests/ - Test suite
- docs/ - Documentation
- api/ - API endpoints
- frontend/ - Vue 3 frontend

**Key Files**: [To be populated via Serena MCP]
"""

    elif priority >= 7:
        # Moderate: key directories
        return f"""## Codebase Structure

**Tech Stack**: {tech_stack}

**Key Directories**: src/, tests/, api/, frontend/
"""

    elif priority >= 4:
        # Abbreviated: high-level only
        return f"""## Codebase

{tech_stack} - Standard project structure (src/, tests/, api/, frontend/)
"""

    else:
        # Minimal: project type
        primary_lang = tech_stack.split(",")[0] if tech_stack else "Unknown"
        return f"## Codebase\n{primary_lang} project"
```

**Example Output** (Priority 5 - Abbreviated):
```markdown
## Codebase

Python 3.11+, FastAPI - Standard project structure (src/, tests/, api/, frontend/)
```

**Token Count**: ~150 tokens

---

### Step 4: Orchestrator Analyzes Context & Builds Mission Plan

**Internal Processing** (orchestrator AI reasoning):

After receiving the ~3,500 token context from Step 3, the orchestrator performs:

1. **Context Analysis**:
   - Reviews vision document and project description
   - Checks tech stack and architecture patterns
   - Reviews 360 Memory for historical learnings
   - Identifies available agent templates
   - Notes git integration availability and Serena MCP tools

2. **Mission Planning**:
   - Breaks down project into discrete tasks
   - Identifies task dependencies (e.g., DB schema → API → frontend)
   - Selects appropriate agent types for each task
   - Determines task sequencing and parallelization opportunities

3. **Agent Selection** (based on agent templates):
   - **Implementer**: For writing new code (features, APIs, services)
   - **Tester**: For creating test suites (unit, integration, E2E)
   - **Refactorer**: For improving existing code quality
   - **Documenter**: For writing/updating documentation
   - **Reviewer**: For code review tasks
   - **Debugger**: For diagnosing and fixing bugs

4. **Mission Document Generation**:
   - Creates detailed mission document (~5K-10K tokens)
   - Includes task breakdown, dependencies, agent assignments
   - References vision document chunks as needed
   - Incorporates learnings from 360 Memory

**Example Mission Plan** (JWT Auth Project):
```markdown
# Mission Plan: JWT Authentication System

## Mission Overview
Build production-grade JWT authentication system with user registration, login, password reset, and 2FA.

## Task Breakdown

### Phase 1: Database Schema (Implementer)
- Create users table with password_hash, email, is_verified columns
- Create sessions table for refresh token management
- Create 2fa_secrets table for TOTP seeds
**Dependencies**: None
**Estimated Duration**: 2-3 hours

### Phase 2: User Registration (Implementer)
- POST /api/auth/register endpoint
- Email verification via SendGrid
- Password strength validation
**Dependencies**: Phase 1 complete
**Estimated Duration**: 3-4 hours

### Phase 3: Login Endpoint (Implementer)
- POST /api/auth/login endpoint
- JWT access token generation (1 hour expiry)
- Refresh token generation (7 day expiry)
**Dependencies**: Phase 1 complete
**Estimated Duration**: 2-3 hours

### Phase 4: Test Suite (Tester)
- Unit tests for auth service logic
- Integration tests for all endpoints
- E2E tests for full auth flow
**Dependencies**: Phases 2-3 complete
**Estimated Duration**: 4-5 hours

[...additional phases...]

## Success Criteria
- All endpoints return correct status codes
- Test coverage > 80%
- Password hashing uses bcrypt with cost factor 12
- JWT tokens expire correctly
- Email verification flow working
```

**Token Count**: ~8,000 tokens (mission plan)

---

### Step 5: Orchestrator Spawns Agent Jobs

**Orchestrator Action**: Creates agent jobs for each task in mission plan

**MCP Tool Call** (for each agent):
```python
spawn_agent_job(
    agent_type="implementer",
    agent_name="DB Schema Agent",
    mission="Create database schema for JWT auth system...",
    project_id="uuid",
    tenant_key="default"
)
```

**Backend Processing** (`OrchestrationService.spawn_agent_job()`):
1. **Create agent job record**: Insert into `mcp_agent_jobs` table
   - `agent_type`: "implementer"
   - `agent_name`: "DB Schema Agent"
   - `status`: "pending"
   - `spawned_by`: orchestrator job ID (lineage tracking)
   - `mission`: Task-specific mission text (~1,500 tokens)
2. **Generate thin client prompt**: Return launch prompt for user
3. **Emit WebSocket event**: Notify UI of new agent job

**Thin Client Prompt** (returned to orchestrator):
```
DB Schema Agent (Implementer) has been spawned.

Launch in new terminal:
Use get_agent_mission(agent_job_id=456, tenant_key="default") to fetch your mission details.
```

**Key Point**: Agent does NOT receive full context yet. Agent fetches mission via MCP tool (thin client pattern).

---

### Agent Context Re-Prioritization

**Agent Action** (in separate Claude Code/Codex/Gemini session):
```python
get_agent_mission(agent_job_id=456, tenant_key="default")
```

**MCP Tool Handler** (`src/giljo_mcp/tools/agent.py`):
1. **Fetch agent job**: Query `mcp_agent_jobs` where `id=456`
2. **Fetch project + product**: Same as orchestrator
3. **Fetch user priorities**: Same field_priority_config
4. **Call MissionPlanner with AGENT-SPECIFIC priorities**: Re-build context with different token allocation

**Agent-Specific Context Differences**:

| Context Source | Orchestrator Priority | Agent Priority | Rationale |
|----------------|----------------------|----------------|-----------|
| Vision Document | MANDATORY (500 tokens) | MANDATORY (500 tokens) | Same baseline |
| Tech Stack | 7 (Moderate, 150 tokens) | **10 (Full, 300 tokens)** | Agents need detailed tech info |
| Architecture | 7 (Moderate, 100 tokens) | **10 (Full, 200 tokens)** | Agents need design patterns |
| 360 Memory | 7 (Moderate, 600 tokens) | **4 (Abbreviated, 200 tokens)** | Agents focus on current task, not history |
| Git Integration | ON (250 tokens) | **ON (250 tokens)** | Same git instructions |
| Serena MCP | 6 (Abbreviated, 200 tokens) | **10 (Full, 800 tokens)** | Agents need all symbolic tools |
| Codebase Summary | 5 (Abbreviated, 150 tokens) | **10 (Full, 500 tokens)** | Agents need detailed file structure |
| Agent Templates | 7 (Moderate, 200 tokens) | **0 (Excluded)** | Agents don't need template info |

**Agent Context Token Budget**: ~3,200-3,800 tokens (similar to orchestrator, but re-prioritized)

**Why Re-Prioritization**:
- **Orchestrators** need high-level context to plan missions (360 Memory for learning from past, agent templates for selection)
- **Agents** need detailed technical context to execute tasks (full tech stack, full Serena tools, full codebase structure)

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER SETUP (Initial Configuration)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  1. User Creates Product                      │
              │     - Name, vision document, config fields    │
              │     - Tech stack, architecture, features      │
              │     - product_memory initialized (empty)      │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  2. User Configures Field Priorities          │
              │     - Settings → Field Priorities UI          │
              │     - Drag-drop 13 context cards (P1/P2/P3)   │
              │     - Stored in users.field_priority_config   │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  3. User Configures Integrations              │
              │     - Git Integration: Toggle ON/OFF          │
              │     - Serena MCP: Enable symbolic tools       │
              │     - 360 Memory: Auto-populated on closeout  │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  4. User Creates Project                      │
              │     - Name, description, parent product       │
              │     - Project linked to active product        │
              └───────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR LAUNCH (User Clicks "Orchestrate")            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 1: API Call (POST /stage-project)      │
              │     - OrchestrationService.create_job()       │
              │     - Insert mcp_agent_jobs row (pending)     │
              │     - Generate THIN launch prompt (~10 lines) │
              │     - Return job_id + prompt to user          │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 2: Orchestrator MCP Tool Call           │
              │     get_orchestrator_instructions(job_id=123) │
              │                                               │
              │     - Fetch job, project, product records     │
              │     - Fetch user field_priority_config        │
              │     - Call MissionPlanner.build_context()     │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 3: Context Building (Priority-Based)    │
              │                                               │
              │  MANDATORY (500 tokens):                      │
              │  - Product name (~20 tokens)                  │
              │  - Vision summary (~480 tokens)               │
              │                                               │
              │  PRIORITY-BASED (~3,000 tokens):              │
              │  - Vision chunking (P10: 1,200 tokens)        │
              │  - Tech stack (P7: 150 tokens)                │
              │  - Config fields (P6-7: 450 tokens)           │
              │  - 360 Memory (P7: 600 tokens)                │
              │  - Git integration (TOGGLE: 250 tokens)       │
              │  - Agent templates (P7: 200 tokens)           │
              │  - Serena MCP (P6: 200 tokens)                │
              │  - Codebase summary (P5: 150 tokens)          │
              │                                               │
              │  TOTAL: ~3,500 tokens (77% reduction)         │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 4: Orchestrator Analysis & Planning     │
              │     - AI reasoning on ~3,500 token context    │
              │     - Break down project into tasks           │
              │     - Identify dependencies and sequence      │
              │     - Select agent types for each task        │
              │     - Generate mission plan (~8,000 tokens)   │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 5: Agent Job Spawning                   │
              │                                               │
              │  For each task in mission plan:               │
              │    - spawn_agent_job() MCP tool call          │
              │    - Create mcp_agent_jobs row (pending)      │
              │    - Set spawned_by = orchestrator job_id     │
              │    - Generate THIN launch prompt              │
              │    - Return agent_job_id + prompt             │
              │    - Emit WebSocket event (UI update)         │
              └───────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        AGENT EXECUTION (Separate Session)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 6: Agent Fetches Mission                │
              │     get_agent_mission(agent_job_id=456)       │
              │                                               │
              │     - Fetch agent job, project, product       │
              │     - Fetch user field_priority_config        │
              │     - Call MissionPlanner with RE-PRIORITIZED │
              │       context (agent needs tech details)      │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 7: Agent Context Re-Prioritization      │
              │                                               │
              │  AGENT-SPECIFIC PRIORITIES:                   │
              │  - Tech stack: P10 (full, 300 tokens)         │
              │  - Architecture: P10 (full, 200 tokens)       │
              │  - 360 Memory: P4 (abbreviated, 200 tokens)   │
              │  - Serena MCP: P10 (full, 800 tokens)         │
              │  - Codebase: P10 (full, 500 tokens)           │
              │  - Agent templates: P0 (excluded)             │
              │                                               │
              │  TOTAL: ~3,200-3,800 tokens (re-prioritized)  │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 8: Agent Executes Task                  │
              │     - Uses Serena MCP tools for code nav      │
              │     - Writes code / tests / docs              │
              │     - Reports progress via MCP tools          │
              │     - Marks job complete when done            │
              │     - Emits WebSocket event (UI update)       │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 9: Orchestrator Monitors Progress       │
              │     - Check agent status via MCP tools        │
              │     - Spawn next agents when dependencies met │
              │     - Handle failures and re-assignment       │
              │     - Update context_used counter             │
              │     - Trigger succession at 90% capacity      │
              └───────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  Step 10: Project Completion                  │
              │     - All agent jobs succeeded                │
              │     - Orchestrator generates completion report│
              │     - close_project_and_update_memory() call  │
              │     - 360 Memory updated (new learning entry) │
              │     - Project marked complete                 │
              │     - WebSocket event (UI update)             │
              └───────────────────────────────────────────────┘
```

---

## Token Budget Analysis

### Before Optimization (Baseline)

**Traditional Approach** (no priority-based context):
- Full vision document: 5,000-10,000 tokens
- Full tech stack: 500 tokens
- Full config fields: 800 tokens
- Full conversation history: 8,000-15,000 tokens
- Full codebase structure: 2,000 tokens

**Total**: **15,000-30,000 tokens** per mission launch

**Problem**: Context window exhaustion after 5-10 missions, requiring manual restart

---

### After Optimization (Priority-Based + Thin Client)

**GiljoAI MCP Approach** (priority-based context extraction):

| Context Source | Default Priority | Tokens (Moderate) | Tokens (Full) | Tokens (Minimal) |
|----------------|------------------|-------------------|---------------|------------------|
| Product Name | MANDATORY | 20 | 20 | 20 |
| Vision Summary | MANDATORY | 480 | 1,200 | 480 |
| Tech Stack | 7 (Moderate) | 150 | 300 | 50 |
| Architecture | 7 (Moderate) | 100 | 200 | 30 |
| API Style | 6 (Abbreviated) | 50 | 100 | 20 |
| Design Patterns | 6 (Abbreviated) | 50 | 100 | 20 |
| Features | 7 (Moderate) | 100 | 200 | 30 |
| Testing Prefs | 6 (Abbreviated) | 50 | 100 | 20 |
| 360 Memory | 7 (Moderate) | 600 | 1,200 | 100 |
| Git Integration | TOGGLE | 250 | 250 | 250 (if enabled) |
| Agent Templates | 7 (Moderate) | 200 | 500 | 50 |
| Serena MCP | 6 (Abbreviated) | 200 | 800 | 50 |
| Codebase Summary | 5 (Abbreviated) | 150 | 500 | 50 |

**Total (Default Moderate Priorities)**: **~3,500 tokens**
**Total (Maximum Full Priorities)**: **~6,500 tokens**
**Total (Minimum Priorities)**: **~1,500 tokens**

**Token Reduction**: **77% reduction** from baseline (3,500 vs 15,000 tokens)

---

### Thin Client Architecture Impact

**Traditional Fat Client** (full prompt in launch command):
- Launch prompt: 15,000-30,000 tokens
- Agent carries full context from start
- No dynamic priority adjustment

**GiljoAI Thin Client** (prompt fetched via MCP tool):
- Launch prompt: ~100 tokens ("Use get_orchestrator_instructions(job_id=123)")
- Agent fetches context on demand: 3,500 tokens
- Context re-prioritized per agent type
- Total savings: **70-77% context prioritization**

**Additional Benefits**:
1. **Dynamic Prioritization**: User can change priorities mid-project, agents fetch updated context
2. **Multi-Tenant Isolation**: Context fetched from database with tenant_key filtering
3. **Audit Trail**: Every context fetch logged for debugging
4. **Succession Support**: Handover summaries <10K tokens (vs 180K conversation history)

---

## Architecture Notes

### Multi-Tenant Isolation

All context fetching operations enforce multi-tenant isolation:

```python
# MCP tool always requires tenant_key
get_orchestrator_instructions(job_id=123, tenant_key="default")

# Database queries filtered by tenant
job = await session.execute(
    select(AgentJob)
    .where(AgentJob.id == job_id)
    .where(AgentJob.tenant_key == tenant_key)  # Tenant isolation
)

product = await session.execute(
    select(Product)
    .where(Product.id == project.product_id)
    .where(Product.tenant_key == tenant_key)  # Tenant isolation
)
```

**Security**: Zero cross-tenant data leakage - users can only fetch context for their own products/projects.

---

### Service Layer Pattern

Context building uses the **Service Layer** pattern:

```python
# OrchestrationService handles business logic
class OrchestrationService:
    def __init__(self, session: AsyncSession, tenant_key: str):
        self.session = session
        self.tenant_key = tenant_key
        self.mission_planner = MissionPlanner()

    async def get_orchestrator_context(self, job_id: int, user_id: str):
        # Fetch job (tenant-isolated)
        job = await self._get_job(job_id)

        # Fetch project + product (tenant-isolated)
        project = await self._get_project(job.project_id)
        product = await self._get_product(project.product_id)

        # Fetch user toggle config
        user = await self._get_user(user_id)
        field_toggles = user.field_priority_config or DEFAULT_TOGGLES

        # Build fetch instructions based on toggles
        instructions = await self.mission_planner._build_fetch_instructions(
            product, project, field_toggles, user_id, include_serena=True
        )

        return {
            "fetch_instructions": instructions,
            "project_id": str(project.id),
            "product_id": str(product.id),
            "context_budget": job.context_budget,
            "field_toggles_applied": field_toggles
        }
```

**Benefits**:
- Clear separation of concerns (service layer = business logic, repository = data access)
- Testable (can mock session for unit tests)
- Reusable (same service used by MCP tools and API endpoints)

---

### Database Schema

**Key Tables**:

```sql
-- Agent jobs (orchestrators + agents)
CREATE TABLE mcp_agent_jobs (
    id SERIAL PRIMARY KEY,
    agent_type VARCHAR(50) NOT NULL,  -- 'orchestrator' or 'implementer', etc.
    agent_name VARCHAR(255),
    status VARCHAR(50),  -- 'pending', 'active', 'succeeded', 'failed'
    mission TEXT,
    project_id UUID REFERENCES projects(id),
    tenant_key VARCHAR(255),
    context_used INTEGER DEFAULT 0,  -- Token tracking
    context_budget INTEGER DEFAULT 200000,  -- 200K tokens
    spawned_by INTEGER REFERENCES mcp_agent_jobs(id),  -- Lineage
    handover_to INTEGER REFERENCES mcp_agent_jobs(id),  -- Successor
    handover_summary TEXT,  -- Condensed context for successor
    created_at TIMESTAMP DEFAULT NOW()
);

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    vision_summary TEXT,  -- Vision document content
    config_data JSONB,  -- Tech stack, architecture, features, etc.
    product_memory JSONB,  -- 360 Memory + Git integration
    tenant_key VARCHAR(255),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users (field priorities)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR(255),
    email VARCHAR(255),
    field_priority_config JSONB,  -- User's custom priorities
    tenant_key VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    product_id UUID REFERENCES products(id),
    status VARCHAR(50),  -- 'active', 'completed', 'inactive'
    tenant_key VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**JSONB Field Structures**:

```json
// product.config_data
{
  "tech_stack": "Python 3.11+, FastAPI, PostgreSQL 18, Vue 3",
  "architecture": "Monolithic with service layer separation",
  "api_style": "RESTful with FastAPI",
  "design_patterns": "Repository, Dependency Injection, Async/Await",
  "features": "User auth, JWT tokens, Password reset, 2FA",
  "testing_preferences": "pytest, >80% coverage, unit + integration tests"
}

// product.product_memory
{
  "learnings": [
    {
      "sequence": 1,
      "project_id": "uuid",
      "project_name": "JWT Auth System",
      "timestamp": "2025-11-10T12:00:00Z",
      "summary": "Implemented production-grade JWT authentication...",
      "key_outcomes": [
        "100% test coverage for auth endpoints",
        "bcrypt password hashing implemented"
      ],
      "decisions_made": [
        "Use SendGrid for email service",
        "JWT expiry: 1 hour access, 7 day refresh"
      ]
    }
  ],
  "git_integration": {
    "enabled": true,
    "commit_limit": 20,
    "default_branch": "main"
  }
}

// users.field_priority_config
{
  "config_data.tech_stack": 7,
  "config_data.architecture": 7,
  "config_data.api_style": 6,
  "config_data.design_patterns": 6,
  "config_data.features": 7,
  "config_data.testing_preferences": 6,
  "product_memory.learnings": 7,
  "agent_templates": 7,
  "serena_mcp_enabled": 6,
  "codebase_summary": 5
}
```

---

## Related Documentation

### Core Architecture Documents
- [ORCHESTRATOR.md](ORCHESTRATOR.md) - Orchestrator context tracking and succession
- [CONTEXT_MANAGEMENT_SYSTEM.md](CONTEXT_MANAGEMENT_SYSTEM.md) - Context extraction logic
- [SERVICES.md](SERVICES.md) - OrchestrationService API reference
- [SERVER_ARCHITECTURE_TECH_STACK.md](SERVER_ARCHITECTURE_TECH_STACK.md) - System architecture

### Handover Documents (Implementation Details)
- **0300 Series**: Context Management System Implementation
  - [0300 Master](../handovers/0300_context_management_system_implementation.md) - Overall plan
  - [0301](../handovers/0301_fix_priority_mapping_ui_backend.md) - Priority mapping (1-3 → 10/7/4 scale)
  - [0302](../handovers/0302_implement_tech_stack_context_extraction.md) - Tech stack extraction
  - [0303](../handovers/0303_implement_product_config_fields_extraction.md) - Config fields extraction
  - [0305](../handovers/0305_integrate_vision_document_chunking.md) - Vision chunking
  - [0306](../handovers/0306_agent_templates_in_context_string.md) - Agent templates context
  - [0311](../handovers/0311_integrate_360_memory_context.md) - 360 Memory + Git integration

- **360 Memory System** (Handovers 0135-0139):
  - Database schema for `product_memory.learnings`
  - Project closeout MCP tool
  - WebSocket events for real-time updates

- **Git Integration Refactor** (Handover 013B):
  - Simplified toggle (no GitHub API)
  - Git command instruction injection

### User Guides
- [User Settings Guide](user_guides/user_settings_guide.md) - Field priority configuration
- [Orchestrator Succession Guide](user_guides/orchestrator_succession_guide.md) - Context handover workflow

### Developer Guides
- [Thin Client Migration Guide](guides/thin_client_migration_guide.md) - Migrating to thin client architecture
- [Orchestrator Succession Developer Guide](developer_guides/orchestrator_succession_developer_guide.md) - Succession implementation details

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-17 | Initial SSoT document created | Documentation Manager Agent |

---

**Last Updated**: 2025-11-17
**Last Verified**: 2025-11-17
**Status**: ✅ Production Documentation - Single Source of Truth
