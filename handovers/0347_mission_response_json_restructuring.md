# Handover: 0347 - Mission Response JSON Restructuring

**Date:** 2025-12-14 (Updated from YAML to JSON approach)
**From Agent:** Orchestrator
**To Agent:** TDD Implementor
**Priority:** High
**Estimated Complexity:** 6-8 hours
**Status:** Ready for Implementation

---

## Architecture Decision: JSON over YAML

**Original Plan:** Use YAML for mission field formatting
**Revised Plan:** Use nested JSON structures

**Rationale:**
- MCP protocol already uses JSON - no need for YAML inside JSON
- Claude parses JSON just as easily as YAML
- No double parsing (JSON response → YAML content)
- Native to Python dicts - simpler implementation
- Better tooling/validation support

**The goal remains the same:** Priority framing, token reduction (21K → 1.5K), fetch-on-demand pointers.

---

## Sub-Project Breakdown

### Dependency Graph

```
0347a (JSON Builder) ──┬──> 0347b (MissionPlanner Refactor) ──┬──> 0347d (Agent Templates Depth)
                       │                                       │
                       │                                       └──> 0347e (Vision Doc 4-Level)
                       │
0347c (Response Fields) ✅ DONE ────────────────────────────────────> 0347f (Integration Testing)
```

### Sub-Project Summary

| ID | Name | Dependencies | Effort | Status |
|----|------|--------------|--------|--------|
| **0347a** | JSON Context Builder | None | 1.5h | Ready |
| **0347b** | MissionPlanner JSON Refactor | 0347a | 3h | Ready |
| **0347c** | Response Fields Enhancement | None | 2h | **COMPLETE** |
| **0347d** | Agent Templates Depth Toggle | 0347b | 2h | Ready |
| **0347e** | Vision Document 4-Level Depth | 0347b | 3h | Ready |
| **0347f** | Integration & E2E Testing | All above | 2h | Ready |

---

## Problem Statement

The `get_orchestrator_instructions` MCP tool returns a `mission` field containing ~21,000 tokens of markdown-concatenated context. This is inefficient:

1. Inlines all context regardless of priority
2. Buries priority in markdown headers (`## CRITICAL: ...`)
3. Forces Claude to parse unstructured text
4. Includes full vision docs even when user selects "light" depth

---

## Solution: Structured JSON with Priority Framing

Replace markdown blob with nested JSON structure:

```json
{
  "mission": {
    "priority_map": {
      "critical": ["product_core", "tech_stack"],
      "important": ["architecture", "testing", "agent_templates"],
      "reference": ["vision_documents", "memory_360", "git_history"]
    },
    "critical": {
      "product_core": {
        "name": "TinyContacts",
        "type": "Contact management application",
        "key_features": ["Photo uploads", "Date tracking", "Tags", "Fuzzy search"]
      },
      "tech_stack": {
        "languages": ["Python 3.11+", "TypeScript 5.0+"],
        "backend": ["FastAPI", "SQLAlchemy"],
        "frontend": ["React 18", "Tailwind CSS"],
        "database": {"dev": "SQLite", "prod": "PostgreSQL"}
      }
    },
    "important": {
      "architecture": {
        "pattern": "Modular monolith with service layer",
        "api": "REST + OpenAPI 3.0",
        "fetch_details": "fetch_architecture()"
      },
      "testing": {
        "target": "80% coverage",
        "approach": "TDD"
      },
      "agent_templates": {
        "discovery_tool": "get_available_agents()",
        "note": "Fetch agent details on-demand"
      }
    },
    "reference": {
      "vision_documents": {
        "available": true,
        "depth_setting": "moderate",
        "estimated_tokens": 12500,
        "summary": "40K word product vision - UX, specs, benefits",
        "fetch_tool": "fetch_vision_document(page=N)"
      },
      "memory_360": {
        "projects": 3,
        "status": "3 completed projects in history",
        "fetch_tool": "fetch_360_memory(limit=5)"
      },
      "git_history": {
        "commits": 25,
        "fetch_tool": "fetch_git_history(limit=25)"
      }
    }
  },
  "mission_format": "json"
}
```

**Token Impact:** 93% reduction (21,000 → ~1,500 tokens)

---

## 0347a: JSON Context Builder

**File:** `src/giljo_mcp/json_context_builder.py`

**Purpose:** Utility class to build structured JSON context with priority tiers.

```python
class JSONContextBuilder:
    """Builds structured JSON context with priority framing."""

    def __init__(self):
        self.critical_fields: list[str] = []
        self.important_fields: list[str] = []
        self.reference_fields: list[str] = []
        self.critical_content: dict = {}
        self.important_content: dict = {}
        self.reference_content: dict = {}

    def add_critical(self, field_name: str) -> None:
        """Add field to CRITICAL priority tier."""

    def add_important(self, field_name: str) -> None:
        """Add field to IMPORTANT priority tier."""

    def add_reference(self, field_name: str) -> None:
        """Add field to REFERENCE priority tier."""

    def add_critical_content(self, field_name: str, content: Any) -> None:
        """Add content for CRITICAL field."""

    def add_important_content(self, field_name: str, content: Any) -> None:
        """Add content for IMPORTANT field."""

    def add_reference_content(self, field_name: str, content: Any) -> None:
        """Add content for REFERENCE field."""

    def build(self) -> dict:
        """Build the complete JSON structure."""
        return {
            "priority_map": {
                "critical": self.critical_fields,
                "important": self.important_fields,
                "reference": self.reference_fields
            },
            "critical": self.critical_content,
            "important": self.important_content,
            "reference": self.reference_content
        }

    def estimate_tokens(self) -> int:
        """Estimate token count (1 token ~ 4 chars of JSON)."""
        import json
        return len(json.dumps(self.build())) // 4
```

**Tests:** `tests/services/test_json_context_builder.py`

---

## 0347b: MissionPlanner JSON Refactor

**File:** `src/giljo_mcp/mission_planner.py`

**Change:** Refactor `_build_context_with_priorities()` to use JSONContextBuilder instead of markdown string concatenation.

**Before (markdown):**
```python
context_sections = []
context_sections.append(f"## CRITICAL: {content}")
return "\n\n".join(context_sections)  # ~21K tokens
```

**After (JSON):**
```python
from .json_context_builder import JSONContextBuilder

builder = JSONContextBuilder()
builder.add_critical("product_core")
builder.add_critical_content("product_core", {...})
return builder.build()  # ~1.5K tokens
```

---

## 0347c: Response Fields Enhancement - COMPLETE

Already implemented. Adds 6 guidance fields using nested dicts (no YAML):
- `post_staging_behavior`
- `required_final_action`
- `multi_terminal_mode_rules`
- `error_handling`
- `agent_spawning_limits`
- `context_management`

---

## 0347d: Agent Templates Depth Toggle

**No YAML changes needed.** This feature controls whether agent templates return:
- "type_only": Minimal metadata (~50 tokens/agent)
- "full": Complete template content (~2000 tokens/agent)

Implementation uses JSON responses.

---

## 0347e: Vision Document 4-Level Depth

**No YAML changes needed.** The 4 levels (Optional/Light/Medium/Full) control:
- What content is inlined in the JSON response
- Fetch tool pointers for on-demand retrieval

---

## 0347f: Integration & E2E Testing

**Updated scope:** Test JSON structure instead of YAML parsing.

Tests:
- `test_mission_is_dict_not_string` - Mission field is nested dict
- `test_priority_map_present` - Priority map in response
- `test_critical_fields_inline` - Critical content embedded
- `test_reference_has_fetch_tools` - Reference sections have pointers
- `test_token_count_under_2000` - Token reduction achieved

---

## Success Criteria

- [ ] JSONContextBuilder class implemented with tests
- [ ] MissionPlanner returns dict instead of markdown string
- [ ] Response includes `"mission_format": "json"`
- [ ] Priority map clearly defines CRITICAL/IMPORTANT/REFERENCE
- [ ] Total mission tokens < 2,000 (down from 21,000)
- [ ] All existing tests pass (no regressions)
- [ ] Coverage >80% for new code

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/giljo_mcp/json_context_builder.py` | JSON context builder utility |
| `tests/services/test_json_context_builder.py` | Unit tests |

## Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/mission_planner.py` | Use JSONContextBuilder in `_build_context_with_priorities()` |
| `src/giljo_mcp/tools/orchestration.py` | Add `mission_format: json` to response |

---

## Migration from YAML Approach

**Reverted commits:**
- `ffaa8795` - YAML context builder (reverted)
- `7a34b80d` - MissionPlanner YAML refactor (reverted)

**Backup branch:** `backup-0347-yaml-approach` (can restore if needed)

**Key differences:**
| Aspect | YAML Approach | JSON Approach |
|--------|--------------|---------------|
| Output format | YAML string inside JSON | Nested JSON dict |
| Parsing | JSON → YAML string → parse YAML | JSON only |
| Dependencies | PyYAML required | None (stdlib json) |
| Complexity | Higher | Lower |
| MCP native | No | Yes |

---

## Execution Order

1. **0347a** - Create JSONContextBuilder (1.5h)
2. **0347b** - Refactor MissionPlanner (3h)
3. **0347d + 0347e** - Depth toggles (parallel, 2h each)
4. **0347f** - Integration testing (2h)

**Note:** 0347c is already complete and doesn't need changes.
