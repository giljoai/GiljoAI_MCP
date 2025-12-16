# Handover 0347: Context Field Dynamic Tier Assignment Fix

**Date**: 2025-12-15
**Status**: COMPLETED
**Type**: Bug Fix (Regression)
**Severity**: High - 4 of 8 context fields broken
**Commit**: `ef5b834c`

---

## Summary

Fixed regression introduced by handover 0347b (commit `fbf74f21`) where 4 context fields stopped appearing in orchestrator context output despite being configured via UI toggles.

**Root Cause**: Hardcoded priority checks (`== 1` or `== 2`) instead of dynamic tier assignment (`in [1, 2, 3]`).

**Impact**: product_core, tech_stack, architecture, and testing fields never appeared unless set to exact hardcoded priority values.

**Secondary Bug**: Testing field also had key mismatch - code looked for `testing` but database stores under `test_config`.

---

## End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Vue 3 + Vuetify)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  My Settings → Context Tab                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Priority Configuration (What to Fetch)                               │    │
│  │ ┌──────────────────┬────────────┬──────────────┐                    │    │
│  │ │ Field            │ Toggle     │ Dropdown     │                    │    │
│  │ ├──────────────────┼────────────┼──────────────┤                    │    │
│  │ │ Product Core     │ [ON/OFF]   │ [1|2|3]      │                    │    │
│  │ │ Tech Stack       │ [ON/OFF]   │ [1|2|3]      │                    │    │
│  │ │ Architecture     │ [ON/OFF]   │ [1|2|3]      │                    │    │
│  │ │ Testing          │ [ON/OFF]   │ [1|2|3]      │                    │    │
│  │ │ Vision Documents │ [ON/OFF]   │ [1|2|3]      │                    │    │
│  │ │ 360 Memory       │ [ON/OFF]   │ [1|2|3]      │                    │    │
│  │ │ Git History      │ [ON/OFF]   │ [1|2|3]      │                    │    │
│  │ │ Agent Templates  │ [ON/OFF]   │ [1|2|3]      │                    │    │
│  │ └──────────────────┴────────────┴──────────────┘                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│                         PUT /api/users/me/context                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI + SQLAlchemy)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL: users table                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ context_priority_config (JSONB)     context_depth_config (JSONB)    │    │
│  │ {                                   {                               │    │
│  │   "product_core": 2,                  "vision_documents": "light",  │    │
│  │   "tech_stack": 2,                    "memory_360": 5,              │    │
│  │   "architecture": 3,                  "git_history": 10,            │    │
│  │   "testing": 3,                       "agent_templates": "type_only"│    │
│  │   ...                               }                               │    │
│  │ }                                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Products table (config_data JSONB):                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ {                                                                   │    │
│  │   "test_config": {           // NOTE: "test_config" NOT "testing"   │    │
│  │     "quality_standards": "", // Can be blank                        │    │
│  │     "strategy": "Hybrid",                                           │    │
│  │     "frameworks": "pytest 7.4+...",                                 │    │
│  │     "coverage_target": 85                                           │    │
│  │   },                                                                │    │
│  │   "tech_stack": {...},                                              │    │
│  │   "architecture": {...}                                             │    │
│  │ }                                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP TOOLS (Orchestrator Fetches)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  get_orchestrator_instructions(orchestrator_id, tenant_key)                  │
│  └─► src/giljo_mcp/tools/orchestration.py                                   │
│      └─► MissionPlanner._build_context_with_priorities()                    │
│                    │                                                         │
│                    ▼                                                         │
│  src/giljo_mcp/mission_planner.py (lines 1649-1719)                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ For EACH context field:                                              │    │
│  │   1. Get priority from effective_priorities                          │    │
│  │   2. Check if priority in [1, 2, 3] (toggle ON)                     │    │
│  │   3. Build content with correct field names                          │    │
│  │   4. Call _add_to_tier_by_priority(builder, field, priority, content)│    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT (JSON Response)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  {                                                                           │
│    "priority_map": {                                                        │
│      "critical": ["project_description", "agent_templates", "memory_360"],  │
│      "important": ["product_core", "tech_stack", "vision_documents"],       │
│      "reference": ["architecture", "testing"]                               │
│    },                                                                       │
│    "critical": {...},                                                       │
│    "important": {...},                                                      │
│    "reference": {...}                                                       │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## UI Model (Critical Understanding)

```
┌─────────────────────────────────────────────────────────────┐
│ My Settings → Context Tab                                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Field Name          │ Toggle    │ Dropdown                 │
│  ────────────────────┼───────────┼────────────────────────  │
│  Product Core        │ [ON/OFF]  │ [Critical|Important|Ref] │
│  Tech Stack          │ [ON/OFF]  │ [Critical|Important|Ref] │
│  Architecture        │ [ON/OFF]  │ [Critical|Important|Ref] │
│  Testing             │ [ON/OFF]  │ [Critical|Important|Ref] │
│  Vision Documents    │ [ON/OFF]  │ [Critical|Important|Ref] │
│  360 Memory          │ [ON/OFF]  │ [Critical|Important|Ref] │
│  Git History         │ [ON/OFF]  │ [Critical|Important|Ref] │
│  Agent Templates     │ [ON/OFF]  │ [Critical|Important|Ref] │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Priority Mapping**:
| UI State | Priority Value | Tier |
|----------|----------------|------|
| Toggle OFF | 4 | EXCLUDED |
| Toggle ON + Critical | 1 | critical |
| Toggle ON + Important | 2 | important |
| Toggle ON + Reference | 3 | reference |

**Rule**: When toggle is ON, field MUST appear in the tier specified by dropdown.

---

## The Bug (Primary)

### Broken Pattern (4 fields):
```python
# Only includes if priority == EXACT VALUE
if tech_stack_priority == 1:  # Fails when dropdown is 2 or 3!
    builder.add_critical("tech_stack")
```

### Working Pattern (already fixed in 4 other fields):
```python
# Includes for ANY non-excluded priority
if vision_priority in [1, 2, 3]:
    self._add_to_tier_by_priority(builder, "vision_documents", vision_priority, content)
```

### Affected Fields

| Field | Old Check | Default Priority | Behavior |
|-------|-----------|------------------|----------|
| product_core | `== 1` | 1 | Only appeared at Critical |
| tech_stack | `== 1` | 2 | **NEVER appeared** (default 2, check 1) |
| architecture | `== 2` | 2 | Only appeared at Important |
| testing | `== 2` | 2 | Only appeared at Important |

---

## The Bug (Secondary): Testing Field Key Mismatch

After the initial fix, `testing` field still wasn't appearing. Investigation revealed:

| Issue | Problem |
|-------|---------|
| Key mismatch | Code looked for `testing`, database stores `test_config` |
| Field mismatch | Code used `methodology`, database has `strategy`, `frameworks`, `quality_standards` |

### Database Structure (Product.config_data):
```json
{
  "test_config": {
    "quality_standards": "",
    "strategy": "Hybrid",
    "frameworks": "pytest 7.4+...",
    "coverage_target": 85
  }
}
```

---

## The Fix

**File**: `src/giljo_mcp/mission_planner.py` (lines 1649-1719)

### Before (Broken):
```python
if product_core_priority == 1:
    builder.add_critical("product_core")
    builder.add_critical_content("product_core", {...})

if tech_stack_priority == 1 and product.config_data:
    builder.add_critical("tech_stack")
    builder.add_critical_content("tech_stack", tech_stack_data)

if arch_priority == 2 and product.config_data:
    builder.add_important("architecture")
    builder.add_important_content("architecture", {...})

if testing_priority == 2 and product.config_data:
    testing_data = product.config_data.get("testing", {})  # WRONG KEY!
    if testing_data:
        testing_content = {
            "methodology": testing_data.get("methodology", ""),  # WRONG FIELD!
            "coverage_target": testing_data.get("coverage_target", 80),
            ...
        }
        builder.add_important("testing")
```

### After (Fixed):
```python
# Product Core - Dynamic tier assignment
if product_core_priority in [1, 2, 3]:  # Process unless EXCLUDED (4)
    product_core_content = {
        "name": product.name,
        "description": product.description or "",
        "tenant_key": product.tenant_key
    }
    self._add_to_tier_by_priority(builder, "product_core", product_core_priority, product_core_content)

# Tech Stack - Dynamic tier assignment
if tech_stack_priority in [1, 2, 3] and product.config_data:
    # ... normalization logic preserved ...
    if tech_stack_data:
        self._add_to_tier_by_priority(builder, "tech_stack", tech_stack_priority, tech_stack_data)

# Architecture - Dynamic tier assignment
if arch_priority in [1, 2, 3] and product.config_data:
    arch_text = product.config_data.get("architecture", "")
    if arch_text:
        arch_content = {
            "summary": arch_text[:500] + "..." if len(arch_text) > 500 else arch_text,
            "fetch_tool": "fetch_architecture(product_id)",
            "detail_level": "condensed"
        }
        self._add_to_tier_by_priority(builder, "architecture", arch_priority, arch_content)

# Testing Configuration - FIXED KEY AND FIELDS
# Note: Database stores testing data under "test_config" key
testing_priority = effective_priorities.get("testing", 2)
if testing_priority in [1, 2, 3] and product.config_data:  # Process unless EXCLUDED (4)
    testing_data = product.config_data.get("test_config", {})  # CORRECT KEY
    # Check if any testing fields have content
    has_testing_content = any([
        testing_data.get("quality_standards"),
        testing_data.get("strategy"),
        testing_data.get("frameworks"),
        testing_data.get("coverage_target")
    ])
    if testing_data and has_testing_content:
        testing_content = {
            "quality_standards": testing_data.get("quality_standards", ""),  # CORRECT FIELD
            "strategy": testing_data.get("strategy", ""),                     # CORRECT FIELD
            "frameworks": testing_data.get("frameworks", ""),                 # CORRECT FIELD
            "coverage_target": testing_data.get("coverage_target", 80),
            "fetch_tool": "fetch_testing_config(product_id)",
            "detail_level": "condensed"
        }
        self._add_to_tier_by_priority(builder, "testing", testing_priority, testing_content)
```

---

## Verification

### Test Configuration:
| Field | Toggle | Dropdown | Expected Tier |
|-------|--------|----------|---------------|
| product_core | ON | Important (2) | important |
| tech_stack | ON | Important (2) | important |
| architecture | ON | Reference (3) | reference |
| testing | ON | Reference (3) | reference |
| vision_documents | ON | Important (2) | important |
| memory_360 | ON | Critical (1) | critical |
| agent_templates | ON | Critical (1) | critical |

### Final Result (After All Fixes):
```json
{
  "priority_map": {
    "critical": ["project_description", "agent_templates", "memory_360"],
    "important": ["product_core", "tech_stack", "vision_documents"],
    "reference": ["architecture", "testing"]
  }
}
```

### Testing Field Content (Verified Working):
```json
{
  "testing": {
    "_priority_frame": {
      "level": 3,
      "tier": "reference",
      "label": "REFERENCE",
      "instruction": "REFERENCE: 'testing' is available for deeper context. Fetch on-demand when needed.",
      "action": "FETCH_IF_NEEDED",
      "skip_allowed": true
    },
    "quality_standards": "",
    "strategy": "Hybrid",
    "frameworks": "pytest 7.4+ (backend unit and integration tests)...",
    "coverage_target": 85,
    "fetch_tool": "fetch_testing_config(product_id)",
    "detail_level": "condensed"
  }
}
```

---

## Claude Code CLI Mode vs Multi-Terminal Mode

### Two Execution Modes

| Aspect | Claude Code CLI Mode | Multi-Terminal Mode |
|--------|---------------------|---------------------|
| Terminals | 1 (orchestrator uses Task tool) | N (one per agent) |
| Agent Spawning | `Task(subagent_type="{agent_type}")` | User copies each agent's prompt |
| Play Button (>) | Only orchestrator gets implementation prompt | Each agent card has play button |
| Target Users | Claude Code users | Other AI tools (no Task tool) |

### Claude Code CLI Mode: STRICT agent_type Enforcement

**CRITICAL RULE**: `agent_type` is the SINGLE SOURCE OF TRUTH for Task tool calling.

| Term | Purpose | Example |
|------|---------|---------|
| `agent_type` | Template filename for Task tool | `"implementer"` → `.claude/agents/implementer.md` |
| `agent_name` | Display label for UI/messages ONLY | `"Backend Implementer"` |

**Forbidden Patterns** (will fail):
```python
Task(subagent_type="Backend Implementer")  # Creative name
Task(subagent_type="frontend-impl")         # Hyphenated variation
Task(subagent_type="IMPLEMENTER")           # Case mismatch
```

**Required Pattern**:
```python
Task(subagent_type="implementer")  # Exact template name
```

---

## Agent Templates Depth Configuration

Only TWO depth options exist:

| Depth | Behavior |
|-------|----------|
| **type_only** | Type, name, brief description + strict type matching |
| **full** | Use MCP fetch tool to get complete agent configurations |

### Full Depth Mode

When `agent_templates` depth is `full`, provide MCP fetch instructions instead of inline content:

```json
{
  "agent_templates": {
    "depth": "full",
    "instruction": "Fetch complete agent configurations via MCP before spawning",
    "fetch_tool": "get_available_agents(tenant_key, active_only=True, include_full_config=True)",
    "note": "User has custom agent configurations - honor their settings"
  }
}
```

---

## Related Commits

| Commit | Description |
|--------|-------------|
| `fbf74f21` | 0347b JSON refactor - **introduced regression** |
| `eb11cbcd` | Partial fix for vision_documents, memory_360, agent_templates, git_history |
| `ef5b834c` | **This fix**: Complete fix for product_core, tech_stack, architecture, testing + test_config key fix |

---

## Files Modified

- `src/giljo_mcp/mission_planner.py` - Lines 1649-1719

---

## Key Helper Method

```python
def _add_to_tier_by_priority(self, builder, field_name, priority, content):
    """Add field to correct tier based on priority value."""
    if priority == 1:
        builder.add_critical(field_name)
        builder.add_critical_content(field_name, content)
    elif priority == 2:
        builder.add_important(field_name)
        builder.add_important_content(field_name, content)
    elif priority == 3:
        builder.add_reference(field_name)
        builder.add_reference_content(field_name, content)
```

---

## Lessons Learned

1. **Pattern Consistency**: When refactoring, ensure all similar code paths follow the same pattern
2. **Regression Testing**: Priority/toggle combinations need explicit test coverage
3. **UI-Backend Contract**: The "toggle + dropdown" UI model must be documented and enforced in code
4. **Field Name Alignment**: Database field names must match code expectations (test_config vs testing)
5. **Complete Testing**: After fixing one bug, verify all related functionality works

---

## Test Command

```bash
# Verify fix via MCP tool
mcp__giljo-mcp__get_orchestrator_instructions(
    orchestrator_id="<valid-orchestrator-id>",
    tenant_key="<tenant-key>"
)
```

Check that `priority_map` contains all toggled-ON fields in their correct tiers.

---

## Serena Memory Updated

Memory file `0347_context_field_dynamic_tier_fix` created with quick reference for future sessions.
