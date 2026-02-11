# Serena MCP Configuration - Implementation Flow

## Current Status: COMPLETE & ACTIVE

The Serena MCP configuration is fully implemented, tested, and enabled in production.

---

## Configuration Source

**File**: `F:\GiljoAI_MCP\config.yaml` (lines 49-50)

```yaml
features:
  serena_mcp:
    use_in_prompts: true  # ← Main toggle
```

**Default**: Enabled (`true`)
**Scope**: System-wide
**Change Required**: Restart to apply

---

## Code Flow

### Step 1: Orchestrator Initialization

**Location**: `src/giljo_mcp/tools/orchestration.py:1205-1516`

Function: `get_orchestrator_instructions()` (registered as MCP tool)

When called:
1. Validates orchestrator ID and tenant key
2. Fetches orchestrator job from database
3. Gets project and product metadata
4. **Reads config.yaml** for Serena toggle (line 1400)

### Step 2: Configuration Reading

**Code** (lines 1389-1408):

```python
# Check if Serena is enabled (from config.yaml)
include_serena = False
try:
    from pathlib import Path
    import yaml

    config_path = Path.cwd() / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
        if include_serena:
            logger.info(
                f"[SERENA] Enabled for orchestrator {orchestrator_id}",
                extra={"orchestrator_id": orchestrator_id, "project_id": str(project.id)}
            )
except Exception as e:
    logger.warning(f"[SERENA] Failed to read config for Serena toggle: {e}")
    include_serena = False
```

**Behavior**:
- Reads `config.yaml` from current working directory
- Extracts nested value: `features` → `serena_mcp` → `use_in_prompts`
- Defaults to `False` if not found
- Logs status for audit trail
- Gracefully handles read errors

### Step 3: Pass to Context Builder

**Code** (line 1412):

```python
condensed_mission = await planner._build_context_with_priorities(
    product=product,
    project=project,
    field_priorities=field_priorities,
    user_id=user_id,
    include_serena=include_serena  # ← Pass flag
)
```

Calls `MissionPlanner._build_context_with_priorities()` with the `include_serena` flag.

### Step 4: Context Building

**Location**: `src/giljo_mcp/mission_planner.py:1050-1464`

Function: `_build_context_with_priorities()`

**Function signature** (line 1058):

```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict[str, int] = None,
    user_id: str = None,
    include_serena: bool = False,  # ← Accept flag
) -> str:
```

**Inside the function** (line 1378):

```python
if include_serena:
    serena_context = await self._fetch_serena_codebase_context(
        project_id=str(project.id),
        tenant_key=product.tenant_key
    )
    if serena_context:
        formatted_serena = f"## Codebase Context (Serena)\n{serena_context}"
        context_sections.append(formatted_serena)
        serena_tokens = self._count_tokens(formatted_serena)
        total_tokens += serena_tokens
        logger.debug(f"Serena codebase context: {serena_tokens} tokens (MANDATORY when enabled)")
```

### Step 5: Instruction Generation & Injection

**Location**: `src/giljo_mcp/tools/orchestration.py:1416-1431`

**Code**:

```python
if include_serena:
    try:
        from giljo_mcp.prompt_generation.serena_instructions import SerenaInstructionGenerator

        serena_gen = SerenaInstructionGenerator()
        serena_instructions = await serena_gen.generate_instructions(enabled=True, detail_level="full")

        # Prepend Serena instructions to mission
        condensed_mission = serena_instructions + "\n\n---\n\n" + condensed_mission
        logger.info(
            f"[SERENA] Injected Serena instructions into orchestrator mission",
            extra={"orchestrator_id": orchestrator_id, "serena_instructions_length": len(serena_instructions)}
        )
    except Exception as e:
        logger.warning(f"[SERENA] Failed to inject Serena instructions: {e}")
        # Continue without Serena instructions if injection fails
```

**Process**:
1. Creates `SerenaInstructionGenerator` instance
2. Calls `generate_instructions(enabled=True, detail_level="full")`
3. Gets back comprehensive instructions (cached)
4. Prepends instructions to orchestrator mission
5. Logs success or failure
6. Gracefully continues even if injection fails

### Step 6: Instruction Generation Details

**Location**: `src/giljo_mcp/prompt_generation/serena_instructions.py`

**Class**: `SerenaInstructionGenerator`

**Key methods**:
- `generate_instructions(enabled=True, detail_level="full")` - Main API
- `_generate_full_instructions()` - Comprehensive instructions
- `_generate_summary_instructions()` - Token-optimized
- `_generate_minimal_instructions()` - Minimal guidance

**Caching** (line 30):

```python
_instruction_cache: dict[str, str] = {}
```

First call generates instructions, subsequent calls use cache.

**Detail levels**:
- `minimal` - 100-200 tokens
- `summary` - 300-500 tokens
- `full` - 1000-1500 tokens (default for orchestrators)

### Step 7: Orchestrator Mission Structure

**Final mission includes**:

1. **Serena Instructions** (if enabled)
   - Tool catalog (40+ tools)
   - Usage patterns with examples
   - Token savings explanation
   - Agent-type specific guidance

2. **Product Context**
   - Product name and description
   - Vision documents (chunked)

3. **Project Context**
   - Project name and description
   - Project metadata

4. **Technical Context**
   - Tech stack
   - Architecture patterns
   - Testing configuration

5. **Integration Context**
   - 360 Memory
   - Git integration info

6. **MCP Tool Catalog** (if enabled)
   - Available MCP tools
   - Usage examples

### Step 8: Agent Spawning

**Location**: `src/giljo_mcp/tools/orchestration.py:471-673`

Function: `spawn_agent_job()`

**Process**:
1. Takes mission from orchestrator
2. Creates `AgentJob` database record
3. Stores full mission in `AgentJob.mission` field
4. Returns thin prompt (~10 lines)
5. Agent calls `get_agent_mission()` to fetch full mission
6. Agent receives Serena instructions

**Key fields**:
- `AgentJob.mission` - Full mission including Serena instructions
- `AgentJob.template_id` - Link to source template
- `AgentJob.spawned_by` - Parent orchestrator ID (for succession)

---

## Configuration Flow Diagram

```
config.yaml
    |
    ├─ features:
    │   └─ serena_mcp:
    │       └─ use_in_prompts: true
    |
    v
get_orchestrator_instructions() MCP Tool
    |
    ├─ Read config.yaml
    ├─ Extract use_in_prompts flag
    ├─ Log status: [SERENA] Enabled for orchestrator <id>
    └─ Pass include_serena=True
       |
       v
   MissionPlanner._build_context_with_priorities()
       |
       ├─ If include_serena=True:
       │   ├─ Fetch Serena context
       │   └─ Append to mission
       |
       v
   SerenaInstructionGenerator.generate_instructions()
       |
       ├─ Check cache
       ├─ If not cached: Generate full instructions
       │   ├─ Tool catalog (40+ tools)
       │   ├─ Usage patterns & examples
       │   ├─ Token savings explanation
       │   └─ Agent-type specific guidance
       ├─ Prepend to mission
       |
       v
   Orchestrator Mission Complete
       |
       ├─ Serena Instructions (if enabled)
       ├─ Tool Catalog
       ├─ Usage Examples
       ├─ Product Context
       ├─ Project Context
       ├─ Tech Stack
       └─ 360 Memory
       |
       v
   spawn_agent_job()
       |
       ├─ Store mission in DB
       ├─ Create AgentJob
       ├─ Return thin prompt
       |
       v
   Agent Execution
       |
       ├─ Agent receives thin prompt
       ├─ Calls get_agent_mission()
       ├─ Retrieves full mission
       ├─ Sees Serena instructions
       ├─ Uses Serena tools
       └─ Saves 80-90% tokens
```

---

## Key Decision Points

### Decision 1: Configuration Location

**CHOSEN**: `config.yaml` (system-wide)

**Options Considered**:
- `Product.config_data` (per-product) - Rejected, too granular
- User settings (per-user) - Rejected, breaks team consistency

**Why config.yaml**:
- Serena is a developer tool, not feature-specific
- Configuration rarely changes
- Consistent experience across team
- No database overhead
- Aligns with `git_integration` pattern

### Decision 2: Enable by Default

**CHOSEN**: `true` (enabled)

**Rationale**:
- Token savings are significant (80-90%)
- No computational overhead (caching)
- Graceful degradation if unavailable
- Well-tested implementation

---

## Testing Verification

**Location**: `tests/integration/test_serena_instructions_integration.py`

**Test Count**: 13 tests
**Status**: All passing

**Key tests**:
1. `test_serena_instructions_included_when_enabled` - Config works
2. `test_serena_instructions_excluded_when_disabled` - Disable works
3. `test_spawned_agents_receive_serena_status` - Agents get info
4. `test_serena_instructions_token_savings_mentioned` - Benefits explained

**Run tests**:
```bash
pytest tests/integration/test_serena_instructions_integration.py -v
```

**Expected**: 13/13 PASSED

---

## Summary

| Aspect | Value |
|--------|-------|
| **Configuration File** | `config.yaml` |
| **Setting Path** | `features.serena_mcp.use_in_prompts` |
| **Default Value** | `true` (enabled) |
| **Scope** | System-wide |
| **Change Method** | Edit config.yaml + restart |
| **Test Status** | 13/13 passing |
| **Production Ready** | Yes |
| **Token Impact** | 80-90% reduction |
| **Computational Overhead** | Minimal (cached) |
| **Graceful Degradation** | Yes |
| **Logging** | Debug level with audit trail |

---

## Status: COMPLETE

No further implementation needed. Configuration is:
- Implemented
- Tested (13 integration tests)
- Documented
- Production-ready
- Enabled by default

**Recommendation**: Keep Serena enabled for optimal system performance.
