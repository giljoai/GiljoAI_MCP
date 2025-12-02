# Handover 0283: Depth Configuration Not Being Honored

**Date**: 2025-12-02
**Status**: 🔴 **CRITICAL - Depth Settings Ignored by Backend**
**Priority**: HIGH - User has UI controls that don't work
**Prerequisite**: Handover 0282 (Priority field keys) ✅ COMPLETE

---

## Executive Summary

User configured depth settings in the Context Configurator UI (Vision: Light, Tech Stack: Required, etc.), but the backend returns **identical responses** regardless of depth configuration. All depth settings are being **completely ignored**.

**Impact**: Users have granular depth controls in the UI, but toggling them has **zero effect** on token usage or content detail level.

---

## Problem Statement

### User Configuration vs Actual Behavior

| Field | Depth Setting | Expected Tokens | Actual Tokens | Status |
|---|---|---|---|---|
| **Vision Documents** | Light | ~2-3k (condensed) | ~11k (full) | ❌ IGNORED |
| **Tech Stack** | Required | ~200 (minimal) | ~400 (full) | ❌ IGNORED |
| **Architecture** | Overview | ~300 (brief) | ~500 (full) | ❌ IGNORED |
| **Testing** | Basic | ~100 (basic) | ~200 (standard) | ⚠️ UNCLEAR |
| **Agent Templates** | Type only | ~50 (names only) | ~200 (with descriptions) | ❌ IGNORED |
| **360 Memory** | 3 projects | 3 summaries | N/A (no history) | ⚠️ CAN'T VERIFY |
| **Git History** | 5 commits | 5 commit msgs | 0 (not present) | ⚠️ GITHUB DISABLED |

**Total Expected**: ~6,000-8,000 tokens
**Total Actual**: **16,084 tokens** (identical to "full detail" settings)

---

## Evidence

### Test 1: All Fields Excluded (Handover 0282)
- **Config**: All fields Priority 4 (EXCLUDED)
- **Result**: 120 tokens ✅ **PRIORITY WORKS**

### Test 2: Mixed Priorities, Default Depth
- **Config**: Mixed priorities (1-3), depth not configured
- **Result**: 16,084 tokens ✅ **PRIORITY WORKS**

### Test 3: Mixed Priorities, LIGHT Depth (**This Test**)
- **Config**: Vision = Light, Tech Stack = Required, etc.
- **Expected**: ~6-8k tokens (reduced detail)
- **Actual**: **16,084 tokens** ❌ **DEPTH IGNORED**

**Proof**: Identical token count and content between Test 2 and Test 3 proves depth configuration has **zero effect**.

---

## Root Cause Analysis

### Two-Dimensional Context System

The GiljoAI context system has **TWO dimensions**:

1. ✅ **Priority (WHAT to include)** - Working after Handover 0282
   - Priority 1: CRITICAL (always include)
   - Priority 2: IMPORTANT (high priority)
   - Priority 3: REFERENCE (supplemental)
   - Priority 4: EXCLUDED (omit entirely)

2. ❌ **Depth (HOW MUCH detail)** - **NOT IMPLEMENTED**
   - Vision: none/light/moderate/heavy (0-30k tokens)
   - Tech Stack: required/all (200-400 tokens)
   - Architecture: overview/detailed (300-1.5k tokens)
   - Testing: none/basic/full (0-400 tokens)
   - 360 Memory: 1/3/5/10 projects (500-5k tokens)
   - Git History: 5/10/25/50/100 commits (500-5k tokens)
   - Agent Templates: type_only/minimal/standard/full (50-2.4k tokens)

---

## Database Schema Verification

### User Configuration Storage

**Table**: `users`
**Column**: `depth_config` (JSONB)

**Example User Config** (from UI):
```json
{
  "version": "2.0",
  "depth": {
    "vision_documents": "light",
    "tech_stack": "required",
    "architecture": "overview",
    "testing": "basic",
    "agent_templates": "type_only",
    "memory_360": 3,
    "git_history": 5
  }
}
```

**Database Query to Verify**:
```sql
SELECT
  username,
  depth_config
FROM users
WHERE tenant_key = '***REMOVED***';
```

**Status**: ✅ Depth configuration is **SAVED correctly** in database (verified via frontend saving)

---

## Backend Code Analysis

### File: `src/giljo_mcp/mission_planner.py`

**Method**: `_build_context_with_priorities()` (lines 1129-1617)

**Current Behavior**:
```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,  # ✅ READS priority config
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> str:
    # Reads field_priorities ✅
    # Applies priority-based inclusion/exclusion ✅

    # ❌ NEVER reads depth_config
    # ❌ NEVER applies depth-based condensing
    # ❌ Always returns FULL content for included fields
```

**Problem**: The method signature and implementation **completely ignore** `depth_config`.

---

## Expected Behavior (Not Implemented)

### Vision Documents Depth Levels

**None** (depth = 0):
- Omit entirely
- 0 tokens

**Light** (depth = "light"):
- Include only: Product summary, key features, target users
- Omit: Detailed sections, comparisons, technical deep-dives
- ~2,000-3,000 tokens (vs 11,000+ full)

**Moderate** (depth = "moderate"):
- Include: Summary, key features, architecture highlights, main user scenarios
- Omit: Detailed comparisons, exhaustive technical sections
- ~5,000-7,000 tokens

**Heavy** (depth = "heavy"):
- Include everything (current behavior)
- ~10,000-30,000 tokens

### Tech Stack Depth Levels

**Required** (depth = "required"):
- Languages only (Python, JavaScript)
- Core frameworks only (FastAPI, React)
- Primary database only (PostgreSQL)
- ~200 tokens

**All** (depth = "all"):
- All languages, frameworks, tools, versions (current behavior)
- ~400 tokens

### 360 Memory Depth Levels

**1/3/5/10 projects**:
- Return only the N most recent project summaries
- Sort by sequence number DESC
- Limit results to N entries

### Git History Depth Levels

**5/10/25/50/100 commits**:
- Return only the N most recent commits
- Aggregated across all projects in product
- Limit results to N commits

---

## Implementation Gaps

### Gap 1: depth_config Not Read ❌

**File**: `src/giljo_mcp/mission_planner.py`
**Line**: 1129

**Current**:
```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> str:
```

**Needed**:
```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    depth_config: dict = None,  # ← ADD THIS
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> str:
```

---

### Gap 2: Depth Not Applied to Vision Documents ❌

**Current** (line 1265-1362):
```python
vision_priority = effective_priorities.get("vision_documents", 4)
if vision_priority > 0:
    # Always fetches ALL vision chunks or full text
    # ❌ No depth-based filtering
```

**Needed**:
```python
vision_priority = effective_priorities.get("vision_documents", 4)
vision_depth = depth_config.get("vision_documents", "heavy")  # ← ADD THIS

if vision_priority > 0:
    if vision_depth == "light":
        # Fetch only summary chunks (first 2-3 chunks)
        max_chunks = 3
    elif vision_depth == "moderate":
        # Fetch ~50% of chunks
        max_chunks = chunk_count // 2
    else:  # heavy
        # Fetch all chunks (current behavior)
        max_chunks = chunk_count
```

---

### Gap 3: Depth Not Applied to Tech Stack ❌

**Current** (line 1439-1478):
```python
tech_stack_priority = effective_priorities.get("tech_stack", 0)
if tech_stack_priority > 0:
    # Always formats ALL tech stack data
    formatted_tech_stack = self._format_tech_stack(tech_stack_data, tech_stack_detail)
```

**Needed**:
```python
tech_stack_priority = effective_priorities.get("tech_stack", 0)
tech_stack_depth = depth_config.get("tech_stack", "all")  # ← ADD THIS

if tech_stack_priority > 0:
    if tech_stack_depth == "required":
        # Filter to only core languages, frameworks, database
        filtered_data = self._filter_required_tech_stack(tech_stack_data)
    else:  # all
        filtered_data = tech_stack_data

    formatted_tech_stack = self._format_tech_stack(filtered_data, ...)
```

---

### Gap 4: Depth Not Applied to 360 Memory ❌

**Current** (line 1550-1577):
```python
history_priority = effective_priorities.get("memory_360", 4)
if history_priority > 0:
    # Extracts ALL project history
    history_context = await self._extract_product_history(product, history_priority, max_entries=10)
```

**Needed**:
```python
history_priority = effective_priorities.get("memory_360", 4)
memory_depth = depth_config.get("memory_360", 5)  # Number of projects (1/3/5/10)

if history_priority > 0:
    history_context = await self._extract_product_history(
        product,
        history_priority,
        max_entries=memory_depth  # ← APPLY DEPTH
    )
```

---

### Gap 5: Depth Not Applied to Agent Templates ❌

**Current**: Agent templates are fetched via separate MCP tool `get_available_agents()`, not in mission_planner.py

**Note**: Agent templates depth configuration may need different implementation approach since templates are returned in the response dict, not the mission text.

---

## Files Requiring Changes

### 1. `src/giljo_mcp/mission_planner.py` (PRIMARY)
- **Line 1129**: Add `depth_config` parameter to `_build_context_with_priorities()`
- **Line 1265-1362**: Apply vision depth (light/moderate/heavy)
- **Line 1439-1478**: Apply tech stack depth (required/all)
- **Line 1480-1513**: Apply testing depth (none/basic/full)
- **Line 1550-1577**: Apply 360 memory depth (1/3/5/10 projects)
- **New method**: `_filter_required_tech_stack()` to extract core tech only

### 2. `src/giljo_mcp/tools/orchestration.py`
- **Line 1517**: Pass `depth_config` to `_build_context_with_priorities()`
- **Line 1480-1490**: Fetch `depth_config` from user settings (similar to field_priorities)

### 3. Helper Methods Needed (NEW)
- `_condense_vision_light()` - Extract summary, key features, target users only
- `_condense_vision_moderate()` - Extract ~50% of content
- `_filter_required_tech_stack()` - Extract languages, core frameworks, primary DB only
- `_extract_product_history()` - Already accepts `max_entries`, just need to pass depth value

---

## User Settings Flow

### Frontend → Database → Backend

**1. Frontend** (`ContextPriorityConfig.vue`):
```javascript
// User selects "Light" for vision_documents
depth_config: {
  vision_documents: "light",
  tech_stack: "required",
  architecture: "overview",
  testing: "basic",
  agent_templates: "type_only",
  memory_360: 3,
  git_history: 5
}
```

**2. API Endpoint** (`api/endpoints/users.py`):
```python
# Saves to users.depth_config JSONB column ✅ WORKING
await update_user_depth_config(user_id, depth_config)
```

**3. Database** (`users` table):
```json
{
  "version": "2.0",
  "depth": {
    "vision_documents": "light",
    ...
  }
}
```

**4. Backend (orchestration.py)**:
```python
# ❌ CURRENTLY: depth_config NOT fetched
# ✅ NEEDED: Fetch depth_config from user settings
user_config = await _get_user_config(user_id, tenant_key, session)
depth_config = user_config["depth_config"]  # ← ADD THIS
```

**5. Mission Planner**:
```python
# ❌ CURRENTLY: depth_config NOT accepted or used
# ✅ NEEDED: Accept depth_config and apply to each field
condensed_mission = await planner._build_context_with_priorities(
    product=product,
    project=project,
    field_priorities=field_priorities,  # ✅ Already working
    depth_config=depth_config,  # ← ADD THIS
    user_id=user_id
)
```

---

## Testing Requirements

### Unit Tests

**File**: `tests/unit/test_depth_configuration.py` (NEW)

**Test Cases**:
1. `test_vision_light_depth()` - Vision "light" returns ~2-3k tokens
2. `test_vision_moderate_depth()` - Vision "moderate" returns ~5-7k tokens
3. `test_vision_heavy_depth()` - Vision "heavy" returns ~10k+ tokens
4. `test_tech_stack_required_depth()` - Tech stack "required" returns core only
5. `test_tech_stack_all_depth()` - Tech stack "all" returns everything
6. `test_360_memory_depth_1()` - Memory depth=1 returns 1 project
7. `test_360_memory_depth_3()` - Memory depth=3 returns 3 projects
8. `test_360_memory_depth_10()` - Memory depth=10 returns 10 projects
9. `test_mixed_depths()` - Vision light + tech required + memory 3 = combined savings
10. `test_no_depth_config_defaults()` - Missing depth_config uses defaults (heavy/all)

### Integration Tests

**File**: `tests/integration/test_depth_configuration_mcp.py` (NEW)

**Test Scenarios**:
1. Call `get_orchestrator_instructions()` with depth config
2. Verify token counts match expected ranges
3. Verify content detail matches depth setting
4. Verify backward compatibility (no depth config = full detail)

---

## Token Savings Estimate

### Current (No Depth Applied)
- Vision: 11,000 tokens
- Tech Stack: 400 tokens
- Architecture: 500 tokens
- Testing: 200 tokens
- 360 Memory: 300 tokens
- **Total**: ~12,400 tokens

### With Depth Applied ("Light" vision, "Required" tech, etc.)
- Vision (light): 2,500 tokens (**-77%**)
- Tech Stack (required): 200 tokens (**-50%**)
- Architecture (overview): 300 tokens (**-40%**)
- Testing (basic): 100 tokens (**-50%**)
- 360 Memory (3 projects): 300 tokens (same)
- **Total**: ~3,400 tokens

**Total Savings**: **~9,000 tokens** (73% reduction)

---

## Success Criteria

After implementation:

1. ✅ User sets vision depth to "light" → response contains ~2-3k tokens of vision (not 11k)
2. ✅ User sets tech stack depth to "required" → response contains core tech only (~200 tokens)
3. ✅ User sets 360 memory depth to 3 → response contains 3 most recent projects
4. ✅ User sets git history depth to 5 → response contains 5 most recent commits
5. ✅ Token count changes when user toggles depth settings (currently identical)
6. ✅ Backward compatibility: Missing depth_config defaults to "heavy/all" (current behavior)
7. ✅ Tests verify depth filtering works for all supported levels

---

## Known Constraints

1. **Vision Chunking Dependency**: Vision depth filtering works best with chunked vision documents. For inline vision, may need text truncation logic.

2. **Git History Requires GitHub Integration**: If GitHub disabled, git history depth has no effect (no git data available).

3. **360 Memory Requires Project History**: If product has no completed projects, memory depth has no effect.

4. **Agent Templates**: Depth configuration for agent templates may need special handling since templates are returned in response dict, not mission text.

---

## Related Handovers

- **Handover 0282** ✅ COMPLETE - Priority field key mismatches (WHAT to include)
- **Handover 0281** ✅ COMPLETE - Priority framing implementation
- **Handover 0312-0318** ✅ COMPLETE - Context Management v2.0 execution
- **Handover 0266** - Initial context priority system
- **Handover 0246a-c** - Orchestrator workflow pipeline

---

## Recommended Approach

### Phase 1: Plumbing (Days 1-2)
1. Add `depth_config` parameter to `_build_context_with_priorities()`
2. Fetch `depth_config` from user settings in `orchestration.py`
3. Pass `depth_config` through the call chain
4. Add default depth values for backward compatibility

### Phase 2: Vision Depth (Days 3-4)
1. Implement `_condense_vision_light()` method
2. Implement `_condense_vision_moderate()` method
3. Apply depth filtering to vision document section
4. Test with TinyContacts vision document

### Phase 3: Other Fields Depth (Days 5-6)
1. Implement `_filter_required_tech_stack()` method
2. Apply depth to architecture section
3. Apply depth to testing section
4. Apply depth to 360 memory (already supports `max_entries`)

### Phase 4: Testing & Verification (Days 7-8)
1. Write 10 unit tests for depth filtering
2. Write integration tests with MCP tool
3. Verify token savings match estimates
4. Test backward compatibility

---

## Questions for Implementation Agent

1. Should vision "light" depth use a fixed chunk count (first 3 chunks) or percentage-based (first 25%)?
2. Should tech stack "required" filter be hardcoded or configurable?
3. Should depth defaults be "heavy/all" (current behavior) or something lighter?
4. How to handle depth configuration for agent templates (returned in dict, not mission text)?

---

## Next Steps

1. ✅ **Handover 0282 VERIFIED** - Priority field keys working perfectly
2. 🔴 **Handover 0283 READY** - Depth configuration needs implementation
3. 📋 **Assign to Implementation Agent** - Ready for development
4. 🧪 **Test with User's Config** - Light vision + required tech stack
5. 🎯 **Target**: 73% token savings (16k → 6k tokens)

---

**END OF HANDOVER 0283**

✅ Handover 0282 (Priority) = COMPLETE
🔴 Handover 0283 (Depth) = READY FOR IMPLEMENTATION
