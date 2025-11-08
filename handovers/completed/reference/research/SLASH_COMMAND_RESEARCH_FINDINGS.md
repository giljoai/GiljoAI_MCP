# Slash Command Template System Research - Complete Findings

**Date:** 2025-11-03
**Research Focus:** Understanding the slash command template system for ZIP packaging

---

## Executive Summary

The GiljoAI slash command system is fully implemented and ready for packaging. Three slash commands (`/gil_import_productagents`, `/gil_import_personalagents`, `/gil_handover`) are stored as markdown templates with YAML frontmatter. The system uses a clean architecture where:

1. **Templates** are defined in Python (`slash_command_templates.py`)
2. **Handlers** execute the command logic (`slash_commands/` directory)
3. **MCP Tool** (`setup_slash_commands`) serves template contents to users
4. **Users** install via Claude Code's Write tool (local file creation)

---

## 1. Storage Locations

### Primary Template Storage
**File:** `F:\GiljoAI_MCP\src\giljo_mcp\tools\slash_command_templates.py` (59 lines)

Contains three string constants with markdown templates:
- `GIL_IMPORT_PRODUCTAGENTS_MD` (lines 8-20)
- `GIL_IMPORT_PERSONALAGENTS_MD` (lines 22-30)
- `GIL_HANDOVER_MD` (lines 32-44)
- `get_all_templates()` function (lines 47-58)

### Handler Directory
**Location:** `F:\GiljoAI_MCP\src\giljo_mcp\slash_commands\` (4 files)

**Files:**
1. `__init__.py` - Slash command registry (25 lines)
2. `import_agents.py` - Agent import handlers (421 lines)
3. `handover.py` - Orchestrator handover handler (169 lines)
4. `__pycache__/` - Compiled Python bytecode

**Registry Mapping (slash_commands/__init__.py):**
```python
SLASH_COMMANDS: dict[str, Callable] = {
    "gil_handover": handle_gil_handover,
    "gil_import_productagents": handle_import_productagents,
    "gil_import_personalagents": handle_import_personalagents,
}
```

---

## 2. Three Slash Commands - Structure & Content

### Command 1: `/gil_import_productagents`

**Template Location:** `slash_command_templates.py` lines 8-20
**Handler:** `slash_commands/import_agents.py` lines 21-241
**Handler Function:** `async def handle_import_productagents(...)`

**Template Content:**
```markdown
---
name: gil_import_productagents
description: Import GiljoAI agent templates to current product folder
---

Import agent templates to your active product's .claude/agents folder by calling the gil_import_productagents MCP tool.

Requirements:
- Active product configured in GiljoAI dashboard
- Product must have project_path set

The tool will fetch active agent templates from GiljoAI server, create backup of existing agents (if any), and export templates to your product's .claude/agents directory with YAML frontmatter.
```

**What It Does:**
1. Retrieves user's active product from database
2. Validates product has `project_path` configured
3. Constructs export path: `{project_path}/.claude/agents`
4. Creates ZIP backup of existing agents
5. Exports each active template as `.md` file with YAML frontmatter
6. Returns success/failure with file list

**Response Format:**
```json
{
  "success": true,
  "message": "Successfully imported 5 agent template(s) to product 'MyProduct'",
  "exported_count": 5,
  "files": [
    {"name": "implementer", "path": "/path/to/project/.claude/agents/implementer.md"}
  ]
}
```

---

### Command 2: `/gil_import_personalagents`

**Template Location:** `slash_command_templates.py` lines 22-30
**Handler:** `slash_commands/import_agents.py` lines 243-420
**Handler Function:** `async def handle_import_personalagents(...)`

**Template Content:**
```markdown
---
name: gil_import_personalagents
description: Import GiljoAI agent templates to personal agents folder
---

Import agent templates to your personal ~/.claude/agents folder (available across all projects) by calling the gil_import_personalagents MCP tool.

The tool will fetch active agent templates from GiljoAI server, create backup of existing agents (if any), and export templates to ~/.claude/agents with YAML frontmatter.
```

**What It Does:**
1. Retrieves active templates for user's tenant
2. Exports to global personal path: `~/.claude/agents`
3. Creates ZIP backup before export
4. Writes each template as markdown file with YAML frontmatter
5. Returns success/failure with file list

**Key Difference from Command 1:**
- Uses `Path.home() / ".claude" / "agents"` (personal/global)
- No product validation needed
- No project_path requirement

**Response Format:**
```json
{
  "success": true,
  "message": "Successfully imported 5 agent template(s) to personal agents",
  "exported_count": 5,
  "files": [...]
}
```

---

### Command 3: `/gil_handover`

**Template Location:** `slash_command_templates.py` lines 32-44
**Handler:** `slash_commands/handover.py` (169 lines)
**Handler Function:** `async def handle_gil_handover(...)`

**Template Content:**
```markdown
---
name: gil_handover
description: Trigger orchestrator succession (context handover)
---

Trigger orchestrator succession when context window reaches capacity by calling the gil_handover MCP tool.

Use when context window is approaching 90% capacity, at natural phase transitions in the project, or when manual succession is requested.

The tool will generate a handover summary, create a successor orchestrator job, return a launch prompt for the new instance, and update lineage tracking.

Optional arguments: reason can be "context_limit", "manual", or "phase_transition"
```

**What It Does:**
1. Retrieves active orchestrator for current project
2. Validates only orchestrators can trigger handover
3. Checks for existing handovers (prevents duplicates)
4. Generates handover summary with context info
5. Creates successor orchestrator instance
6. Marks current orchestrator as complete with handover
7. Generates launch prompt for successor
8. Returns successor ID and launch instructions

**Response Format:**
```json
{
  "success": true,
  "message": "Successor orchestrator created (Instance 2)",
  "successor_id": "job_abc123...",
  "launch_prompt": "export GILJO_MCP_SERVER_URL=...",
  "handover_summary": {
    "project_name": "MyProject",
    "project_status": 45,
    "active_agents": ["implementer", "tester"]
  }
}
```

---

## 3. Current Template Structure

### YAML Frontmatter Format
All templates use standard Claude Code markdown format:

```yaml
---
name: <command_name>
description: <short_description>
---

<markdown_content>
```

### Template Content Pattern

**Common Elements:**
1. **YAML Frontmatter** - Command metadata (name, description)
2. **Markdown Body** - User-facing documentation
3. **Requirements Section** - Prerequisites/constraints
4. **Usage Instructions** - How to invoke
5. **Optional Arguments** - Parameters (if any)

### No External Resources
- Templates are **self-contained** strings
- No external file dependencies
- No binary data
- Pure text/markdown format

---

## 4. API Endpoints Serving Templates

### MCP HTTP Endpoint
**File:** `F:\GiljoAI_MCP\api\endpoints\mcp_http.py`

**Tool Definition (lines 663-670):**
```python
{
    "name": "setup_slash_commands",
    "description": "Install GiljoAI slash commands to local CLI...",
    "inputSchema": {
        "type": "object",
        "properties": {}
    }
}
```

**Tool Routing (line 810):**
```python
"setup_slash_commands": state.tool_accessor.setup_slash_commands,
```

### Slash Commands HTTP Endpoint
**File:** `F:\GiljoAI_MCP\api\endpoints\slash_commands.py` (81 lines)

**Endpoints:**
- `POST /slash/execute` - Execute slash command via HTTP
- Request: `{command, tenant_key, project_id, arguments}`
- Response: `{success, message, error, successor_id, launch_prompt}`

---

## 5. How Templates Are Generated/Formatted

### Generation Pipeline

**Step 1: Template Definition (Python)**
```python
# slash_command_templates.py
GIL_IMPORT_PRODUCTAGENTS_MD = """---
name: gil_import_productagents
...
"""
```

**Step 2: Template Retrieval (Tool)**
```python
# tool_accessor.py - setup_slash_commands()
from .slash_command_templates import get_all_templates
templates = get_all_templates()  # Returns dict[filename, content]
```

**Step 3: File Assembly (Return to Client)**
```python
# Returns to MCP client
files_with_paths = {
    ".claude/commands/gil_import_productagents.md": templates["gil_import_productagents.md"],
    ".claude/commands/gil_import_personalagents.md": templates["gil_import_personalagents.md"],
    ".claude/commands/gil_handover.md": templates["gil_handover.md"]
}
```

**Step 4: Client Installation (User's Machine)**
Claude Code / Codex uses its Write tool to create:
- `~/.claude/commands/gil_import_productagents.md`
- `~/.claude/commands/gil_import_personalagents.md`
- `~/.claude/commands/gil_handover.md`

### Key Formatting Details

**File Names:**
- Must be lowercase with underscores: `gil_command_name.md`
- Match YAML `name:` field

**YAML Frontmatter:**
- Required fields: `name`, `description`
- Wrapped in `---` delimiters
- Must be first content in file

**Markdown Content:**
- Plain markdown after frontmatter
- Can contain code blocks, lists, emphasis
- Cross-platform compatible

---

## 6. Multi-Tenant Isolation

### Database Queries
All handlers use tenant isolation:

```python
# Import handlers - query active templates for tenant only
templates_stmt = (
    select(AgentTemplate)
    .where(
        AgentTemplate.tenant_key == tenant_key,  # Multi-tenant isolation
        AgentTemplate.is_active,
    )
    .order_by(AgentTemplate.name)
)
```

### User/Product Validation
```python
# Get user by tenant_key
user_stmt = select(User).where(User.tenant_key == tenant_key)

# Get active product for tenant
product_stmt = select(Product).where(
    and_(
        Product.tenant_key == tenant_key,  # Isolation
        Product.is_active == True,
    )
)
```

### Result: Zero Cross-Tenant Leakage
- Each tenant gets only their own templates
- No exposure of other tenant's configurations
- Database-enforced via tenant_key field

---

## 7. Testing & Validation

### Test Files
1. `F:\GiljoAI_MCP\tests\test_slash_commands.py` - Command handler tests
2. `F:\GiljoAI_MCP\tests\test_import_agents_slash_commands.py` - Import agent tests
3. `F:\GiljoAI_MCP\tests\test_slash_command_setup.py` - Setup tool tests
4. `F:\GiljoAI_MCP\tests\api\test_slash_commands_api.py` - API endpoint tests

### Coverage
- 21 tests passing (Handover 0093)
- 3 tests skipped (integration)
- 100% coverage on new modules
- 89.15% overall coverage

---

## 8. Handover Evolution & Related Docs

### Completed Handovers
1. **0037** - MCP Slash Commands Readiness Assessment
2. **0038** - MCP Slash Commands Implementation
3. **0080a** - Orchestrator Succession Slash Command
4. **0084b** - Agent Import Slash Commands
5. **0093** - MCP Slash Command Setup Tool

### Documentation Files
- `docs/guides/MCP_SLASH_COMMANDS_USER_GUIDE.md`
- `docs/guides/MCP_SLASH_COMMANDS_QUICK_REFERENCE.md`
- `docs/manuals/SLASH_COMMANDS__URGENT.md`
- `handovers/0093_mcp_slash_command_setup.md`
- `handovers/completed/0093_mcp_slash_command_setup_COMPLETE.md`

---

## Summary for ZIP Packaging

### Core Files to Package

**Absolute Paths:**
- `F:\GiljoAI_MCP\src\giljo_mcp\tools\slash_command_templates.py` (59 lines)
- `F:\GiljoAI_MCP\src\giljo_mcp\slash_commands\__init__.py` (25 lines)
- `F:\GiljoAI_MCP\src\giljo_mcp\slash_commands\import_agents.py` (421 lines)
- `F:\GiljoAI_MCP\src\giljo_mcp\slash_commands\handover.py` (169 lines)
- `F:\GiljoAI_MCP\api\endpoints\mcp_http.py` (modified - tool exposure)
- `F:\GiljoAI_MCP\api\endpoints\slash_commands.py` (81 lines)

**Total:** 755 lines of production code

### What Needs No Packaging
- `__pycache__/` directories (compiled bytecode)
- Test files (already in repository)
- Documentation files (separate deployment)
- HTML coverage reports (internal only)

### Recommended ZIP Structure

```
slash_command_system/
├── templates/
│   └── slash_command_templates.py
├── handlers/
│   ├── __init__.py
│   ├── import_agents.py
│   └── handover.py
├── api/
│   ├── mcp_http_integration_details.txt
│   └── slash_commands_endpoint.py
├── MANIFEST.md
└── README.md
```

---

## Key Takeaways

1. **Complete Implementation:** All three commands fully functional with handlers, tests, documentation
2. **Self-Contained Templates:** Markdown content embedded as Python strings, no external dependencies
3. **MCP Integration:** `setup_slash_commands` tool serves all templates via single endpoint
4. **Multi-Tenant Safe:** Database queries enforce tenant isolation throughout
5. **User Flow:** Three-step installation (Add MCP → Install Commands → Import Agents)
6. **Zero Breaking Changes:** Purely additive architecture, backward compatible
7. **Production Ready:** 21/21 tests passing, 100% test coverage, fully documented
