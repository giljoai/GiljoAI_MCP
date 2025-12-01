# Serena MCP Configuration Guide

**Status**: Production Ready
**Last Updated**: 2025-11-30
**Implementation**: Handover 0267
**Configuration Entry Point**: `config.yaml`

---

## Quick Reference

### Enable Serena MCP Instructions

**File**: `F:\GiljoAI_MCP\config.yaml`

**Setting**:
```yaml
features:
  serena_mcp:
    use_in_prompts: true
```

**Status**: Currently enabled in production

---

## What Serena MCP Does

Serena MCP is a code discovery and navigation tool that helps orchestrators and agents:

- **Navigate code symbolically** instead of reading entire files
- **Find specific code** by symbol name (classes, methods, functions)
- **Locate all usages** of a symbol across the codebase
- **Understand structure** without full file reads
- **Save tokens**: 80-90% reduction in code context tokens

### Example Token Savings

Without Serena:
```
Read entire AuthService class: 500 tokens
Read entire UserModel class: 400 tokens
Read entire database module: 800 tokens
Total: 1,700 tokens
```

With Serena:
```
get_symbols_overview for src/: 50 tokens
find_symbol for auth service methods: 40 tokens
find_referencing_symbols for UserModel: 30 tokens
Total: 120 tokens (93% reduction!)
```

---

## Configuration Options

### System-Wide (Recommended)

**Location**: `config.yaml`

```yaml
features:
  serena_mcp:
    use_in_prompts: true  # Enable/disable globally
```

**Scope**: Affects all orchestrators and agents system-wide

**Change Required**: Restart system to reload config

**Advantages**:
- Simple to manage
- Consistent across all projects/users
- No database overhead
- Appropriate for developer tool

---

## How It Works

### 1. Configuration Reading

```
Orchestrator starts → Reads config.yaml → Checks features.serena_mcp.use_in_prompts
```

### 2. Instruction Generation

```
If enabled:
  → SerenaInstructionGenerator creates comprehensive instructions
  → Includes tool list, examples, best practices
  → Instructions prepended to orchestrator mission
```

### 3. Agent Propagation

```
Orchestrator mission includes Serena instructions
  → Agents inherit instructions when spawned
  → Agents know which Serena tools are available
  → Agents can use tools effectively
```

### 4. Context Building

```
MissionPlanner._build_context_with_priorities(include_serena=True)
  → Fetches codebase context via Serena tools
  → Appends to mission sections
  → Tracks token usage
```

---

## Available Serena Tools

### Navigation Tools

- **get_symbols_overview** - High-level view of symbols in a file
- **find_symbol** - Find specific symbol by name
- **find_referencing_symbols** - Find all usages of a symbol

### Search Tools

- **search_for_pattern** - Search for text patterns in code
- **find_file** - Find files matching pattern

### Utility Tools

- **list_dir** - List directory contents
- **get_symbols_overview** - Symbol inspection

### Memory Tools

- **read_memory** - Access 360 memory
- **write_memory** - Store learned context
- **list_memories** - Browse knowledge base

---

## Usage Patterns

### Pattern 1: Understand File Structure

```python
# FIRST: Get overview of file
symbols = await get_symbols_overview(relative_path="src/app.py")

# Then: Read specific symbols
app_class = await find_symbol(
    name_path_pattern="App",
    relative_path="src/app.py",
    include_body=True
)
```

### Pattern 2: Find Code by Functionality

```python
# Find all auth-related symbols
auth_symbols = await find_symbol(
    name_path_pattern="authenticate",  # Substring matching
    substring_matching=True,
    relative_path="src/"
)
```

### Pattern 3: Understand Relationships

```python
# Find where a function is used
usages = await find_referencing_symbols(
    name_path="authenticate_user",
    relative_path="src/auth.py"
)

# Result: All places that call this function
```

### Pattern 4: Complex Pattern Search

```python
# Find all class definitions with specific pattern
classes = await search_for_pattern(
    substring_pattern=r"class\s+\w+\(.*Service\):",  # Classes ending in Service
    paths_include_glob="src/**/*.py",
    relative_path="src/"
)
```

---

## When to Enable/Disable

### Enable Serena (`use_in_prompts: true`)

**Recommended when**:
- You have large codebases (>100 files)
- You want to optimize token usage
- You need precise code navigation
- Agents need to understand code structure
- Cost optimization is important

**Default**: ENABLED in production

### Disable Serena (`use_in_prompts: false`)

**Consider disabling when**:
- Serena MCP server is unavailable
- You have very small codebases (<10 files)
- You prefer agents to read full files
- You're debugging (easier to read raw code)
- Testing different approaches

**How to disable**:
```yaml
features:
  serena_mcp:
    use_in_prompts: false
```

Then restart:
```bash
python startup.py
```

---

## Monitoring & Logging

### Check If Serena Is Enabled

Look for logs when orchestrator starts:

```
[SERENA] Enabled for orchestrator <orchestrator-id>
```

Or:

```
[SERENA] Disabled (use_in_prompts: false)
```

### Monitor Serena Usage

In logs during orchestrator execution:

```
[SERENA] Injected Serena instructions into orchestrator mission
[SERENA] Serena codebase context: 234 tokens (MANDATORY when enabled)
```

### Debug Missing Serena

If Serena instructions missing from mission:

1. Check config.yaml:
   ```bash
   grep -A 2 "serena_mcp:" config.yaml
   ```

2. Check logs for errors:
   ```bash
   grep "\[SERENA\]" logs/giljo_mcp.log
   ```

3. Verify config is valid YAML:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

---

## Best Practices

### For Orchestrators

1. **Always start with overview**:
   ```
   get_symbols_overview(relative_path=".") to understand project
   ```

2. **Use find_symbol for precise navigation**:
   ```
   Don't read entire files - find specific symbols
   ```

3. **Ask agents to use Serena**:
   ```
   "Use get_symbols_overview to understand structure first"
   ```

### For Agents

1. **Prefer Serena tools over file reads**:
   ```
   Serena tools: 50-100 tokens
   File read: 500-1000 tokens
   ```

2. **Use tool combinations**:
   ```
   get_symbols_overview → find_symbol → find_referencing_symbols
   ```

3. **Follow symbolic workflow**:
   ```
   1. Overview (file structure)
   2. Find (locate specific code)
   3. Read (only needed code)
   4. Modify (make changes)
   5. Verify (check references)
   ```

---

## Troubleshooting

### Serena Instructions Missing

**Problem**: Orchestrator mission doesn't include Serena instructions

**Solutions**:
1. Check `config.yaml` has `serena_mcp.use_in_prompts: true`
2. Restart system: `python startup.py`
3. Check logs for `[SERENA]` entries
4. Verify no exceptions in try/except block

### Serena Tools Not Working

**Problem**: Agents can't call Serena tools

**Solutions**:
1. Verify Serena MCP server running
2. Check MCP tool registration in `src/giljo_mcp/tools/`
3. Verify tool names: `mcp__serena__<tool_name>`
4. Check agent has MCP access enabled

### Configuration Not Taking Effect

**Problem**: Changed config.yaml but Serena still off

**Solutions**:
1. Restart application: `python startup.py`
2. Config is loaded at startup, not dynamically
3. Check you edited correct `config.yaml` (in project root)
4. Validate YAML syntax

---

## Technical Details

### Configuration Reading

**Location**: `src/giljo_mcp/tools/orchestration.py:1400`

```python
include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
```

**Behavior**:
- Reads config.yaml at orchestrator startup
- Defaults to `False` if key missing
- Logs status for audit trail
- Graceful degradation if config unavailable

### Instruction Generation

**Class**: `SerenaInstructionGenerator` in `src/giljo_mcp/prompt_generation/serena_instructions.py`

**Methods**:
- `generate_instructions()` - Full instructions with caching
- `generate_for_agent()` - Agent-specific instructions
- Detail levels: minimal, summary, full

**Features**:
- In-memory caching (avoid regeneration)
- Token-aware generation
- Agent-type specific guidance
- Markdown formatted output

### Context Integration

**Function**: `MissionPlanner._build_context_with_priorities(include_serena=True)`

**Steps**:
1. Accept `include_serena` parameter
2. Fetch Serena context if enabled
3. Append to mission sections
4. Track token usage
5. Return complete mission

---

## Related Documentation

- [CLAUDE.md - Serena MCP Section](CLAUDE.md#serena-mcp-code-discovery)
- [Handover 0267 - Implementation Details](handovers/completed/0267_add_serena_mcp_instructions-C.md)
- [Handover 0265 - Investigation Report](handovers/0265_orchestrator_context_investigation.md)
- [Serena MCP Official Docs](https://serena-mcp.docs/)

---

## Configuration Reference

### Complete Serena Config Block

```yaml
features:
  # ... other features ...

  serena_mcp:
    use_in_prompts: true    # Enable Serena instructions in orchestrator/agent missions

  # Related features
  git_integration:
    enabled: true           # Git history integration (separate from Serena)
    use_in_prompts: true    # Include git commits in missions
```

### Default Values

| Setting | Default | Type |
|---------|---------|------|
| `use_in_prompts` | `true` | boolean |
| Scope | System-wide | N/A |
| Restart required | Yes | N/A |
| Database overhead | None | N/A |

---

## Support & Questions

### Common Questions

**Q: Does Serena cost extra?**
A: No, Serena MCP is built-in and has no additional cost.

**Q: Can I disable Serena for specific projects?**
A: Currently no - it's system-wide. Per-project control could be added via `Product.config_data` if needed.

**Q: How much does Serena save?**
A: Typically 80-90% token reduction for code navigation tasks vs. full file reads.

**Q: Is Serena always available?**
A: Yes, if the Serena MCP server is running. Configuration controls whether instructions are included.

**Q: Can I use Serena tools even if `use_in_prompts: false`?**
A: Yes - the setting only controls whether instructions are injected. Tools still work via MCP.

---

## Summary

- **Configuration**: `features.serena_mcp.use_in_prompts` in `config.yaml`
- **Default**: Enabled (`true`)
- **Scope**: System-wide (all orchestrators/agents)
- **Purpose**: Optimize token usage by enabling symbolic code navigation
- **Impact**: 80-90% token reduction for code analysis
- **Change**: Restart required
- **Status**: Production ready and tested

**Recommended**: Keep Serena enabled for optimal performance.
