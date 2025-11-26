# Handover 0248b: Context Priority System - Priority Framing Implementation

**Date**: 2025-11-25
**Status**: Ready for Implementation
**Priority**: CRITICAL
**Estimated Time**: 2-3 days
**Dependencies**: 0248a (Plumbing Investigation & Repair)
**Parent Handover**: 0248 (Context Priority System Repair)

## Executive Summary

With plumbing fixed (0248a), this handover implements the core innovation: **production-grade priority framing injection** in MCP context tools. This makes user-configured priorities actually influence LLM behavior by adding explicit headers to fetched context with comprehensive error handling.

**Current State**: MCP tools return raw data without priority indicators.
**Target State**: MCP tools inject framing based on user priorities with production-grade quality.

**Architecture Alignment**: This handover uses the single rich `sequential_history` field from day one. Each memory entry contains both facts (what we did) and insights (why it matters) in one self-describing structure with built-in priority support.

**Production-Grade Requirements**:
- Comprehensive validation for all inputs
- Graceful handling of malformed entries
- Proper error messages and logging
- Default behavior when priority missing
- No assumptions about data structure

## 4-Tier Framing System

### Priority 1: CRITICAL
Position: Beginning AND end of context (primacy + recency effect).

### Priority 2: IMPORTANT
Position: Beginning of context (after CRITICAL items).

### Priority 3: REFERENCE
Position: Middle of context (after IMPORTANT items).

### Priority 4: EXCLUDE
Behavior: Skip fetching entirely.

## Technical Specification

### Step 1: Create Framing Helpers Module

**File**: src/giljo_mcp/tools/context_tools/framing_helpers.py

Create helpers for:
1. inject_priority_framing() - Add framing template to content
2. get_user_priority() - Fetch user priority configuration

### Step 2: Update MCP Context Tools

Update all 9 tools to:
1. Add user_id parameter
2. Fetch user priority
3. Inject framing before returning

**Tool-Specific Field Names**:
- fetch_product_context.py → product_description
- fetch_vision_document.py → vision_documents
- fetch_tech_stack.py → tech_stack
- fetch_architecture.py → config_data.architecture
- fetch_testing_config.py → config_data.test_methodology
- **fetch_360_memory.py** → memory_360 (maps to sequential_history internally)
- fetch_git_history.py → git_history
- fetch_agent_templates.py → agent_templates
- fetch_project_context.py → project_description

**Critical Note on 360 Memory**: The user-facing field name is `memory_360` or "Project History", which internally maps to `product_memory.sequential_history`. Rich entries include a `priority` field for native framing support.

### Step 3: Position Strategy

CRITICAL items appear twice (beginning + end) for maximum LLM attention.

### Step 4: Rich Entry Framing (360 Memory) - Production-Grade

For `fetch_360_memory`, apply framing to rich sequential_history entries with comprehensive validation:

```python
def apply_rich_entry_framing(entry: Dict[str, Any]) -> str:
    """
    Apply priority framing to rich sequential_history entry.

    Args:
        entry: Rich memory entry from sequential_history

    Returns:
        Formatted string with priority framing

    Raises:
        ValueError: If entry structure is invalid

    Example:
        >>> entry = {"sequence": 12, "project_name": "Auth", "priority": 1}
        >>> framing = apply_rich_entry_framing(entry)
        >>> print("## CRITICAL" in framing)  # True
    """
    # Validation
    required_fields = ["sequence", "project_name", "summary"]
    for field in required_fields:
        if field not in entry:
            logger.error(f"Missing required field: {field}")
            raise ValueError(f"Invalid entry: missing {field}")

    # Extract fields with defaults
    sequence = entry.get("sequence", 0)
    project_name = entry.get("project_name", "Unknown Project")
    summary = entry.get("summary", "No summary available")
    key_outcomes = entry.get("key_outcomes", [])
    decisions_made = entry.get("decisions_made", [])
    priority = entry.get("priority", 3)  # Default to REFERENCE
    significance = entry.get("significance_score", 0.5)

    # Validate types
    if not isinstance(key_outcomes, list):
        logger.warning(f"key_outcomes malformed: {type(key_outcomes)}")
        key_outcomes = []

    if not isinstance(decisions_made, list):
        logger.warning(f"decisions_made malformed: {type(decisions_made)}")
        decisions_made = []

    # Build framing based on priority
    priority_label = {1: "CRITICAL", 2: "IMPORTANT", 3: "REFERENCE"}.get(priority, "REFERENCE")

    framing = f"""
## {priority_label}: Project Memory (Sequence {sequence})
**Project**: {project_name}
**Summary**: {summary}

**Key Outcomes**:
{format_list_safely(key_outcomes)}

**Decisions Made**:
{format_list_safely(decisions_made)}

**Significance**: {significance:.2f}
"""

    logger.debug(f"Applied {priority_label} framing to sequence {sequence}")
    return framing


def format_list_safely(items: List[str]) -> str:
    """Format list with proper handling of empty/invalid data."""
    if not items:
        return "- (None)"

    if not isinstance(items, list):
        logger.warning(f"Expected list, got {type(items)}")
        return "- (Invalid data)"

    try:
        return "\n".join(f"- {item}" for item in items if item)
    except Exception as e:
        logger.error(f"Failed to format list: {e}")
        return "- (Error formatting data)"
```

**Key Points**:
- Comprehensive validation for all fields
- Sensible defaults when fields missing
- Type checking with graceful degradation
- Proper error logging for debugging
- Never crashes on malformed data

## Files to Modify

### New Files
- src/giljo_mcp/tools/context_tools/framing_helpers.py

### Modify Existing (9 MCP Context Tools)
- src/giljo_mcp/tools/context_tools/fetch_product_context.py
- src/giljo_mcp/tools/context_tools/fetch_vision_document.py
- src/giljo_mcp/tools/context_tools/fetch_tech_stack.py
- src/giljo_mcp/tools/context_tools/fetch_architecture.py
- src/giljo_mcp/tools/context_tools/fetch_testing_config.py
- **src/giljo_mcp/tools/context_tools/fetch_360_memory.py** (reads sequential_history)
- src/giljo_mcp/tools/context_tools/fetch_git_history.py
- src/giljo_mcp/tools/context_tools/fetch_agent_templates.py
- src/giljo_mcp/tools/context_tools/fetch_project_context.py

## Testing Criteria

### Unit Tests
- test_inject_priority_framing_critical()
- test_inject_priority_framing_exclude()
- test_get_user_priority()

### Integration Tests
- test_product_context_includes_framing()
- test_vision_document_includes_framing()

### Manual Testing
1. Set product_description to CRITICAL
2. Launch agent
3. Verify framing appears in prompt

## Success Criteria

- ✅ framing_helpers.py created with comprehensive validation
- ✅ All 9 MCP tools updated with error handling
- ✅ Framing injection works for all priority levels
- ✅ CRITICAL items appear at beginning + end
- ✅ fetch_360_memory uses rich entry structure with native priority
- ✅ Graceful handling of malformed entries (no crashes)
- ✅ Proper logging for debugging
- ✅ All tests pass (>80% coverage)
- ✅ Edge case testing (empty data, invalid types, missing fields)

## Implementation Notes

- Token overhead: ~100-200 tokens per framed section
- Default to REFERENCE if priority missing (graceful degradation)
- CRITICAL duplication: 2x tokens but improves LLM attention
- Rich entries (sequential_history) include built-in priority field
- Never crash on invalid data - log and degrade gracefully
- Comprehensive error messages for debugging

## Production-Grade Code Example

```python
# ✅ GOOD - Production-grade framing helper
async def inject_priority_framing(
    content: str,
    priority: int,
    field_name: str,
    user_id: Optional[str] = None
) -> str:
    """
    Inject priority framing headers into content.

    Args:
        content: Raw content to frame
        priority: Priority level (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE, 4=EXCLUDE)
        field_name: Field name for logging
        user_id: Optional user ID for audit trail

    Returns:
        Content with framing headers

    Raises:
        ValueError: If priority invalid or content empty

    Example:
        >>> framed = await inject_priority_framing("Product X", 1, "product_desc")
        >>> print("## CRITICAL" in framed)  # True
    """
    # Validation
    if not content or not isinstance(content, str):
        raise ValueError("Content must be non-empty string")

    if priority not in [1, 2, 3, 4]:
        logger.warning(f"Invalid priority {priority}, defaulting to 3 (REFERENCE)")
        priority = 3

    if priority == 4:  # EXCLUDE
        logger.info(f"Field {field_name} excluded by priority setting")
        return ""

    # Build framing
    priority_labels = {1: "CRITICAL", 2: "IMPORTANT", 3: "REFERENCE"}
    label = priority_labels[priority]

    framed_content = f"""
## {label}: {field_name.replace('_', ' ').title()}

{content}

---
"""

    logger.info(
        f"Applied {label} framing to {field_name} "
        f"(length: {len(content)} chars, user: {user_id})"
    )

    return framed_content
```

## Cross-References

**Integrates With**:
- 0249b: 360 Memory workflow WRITES priority field to rich entries
- 0248b: Priority framing READS priority field from rich entries
- Field naming: User config "memory_360" → Internal field "sequential_history"

**Dependencies**:
- 0248a: Plumbing fixes must complete first
- 0249b: Rich entry structure with priority field (parallel track)

## Next Steps

1. Implement framing_helpers.py
2. Update all 9 MCP tools
3. Special handling for fetch_360_memory (rich entries)
4. Test framing injection
5. Proceed to 0248c

---

**Status**: Ready for implementation after 0248a.
