# Handover 0316B - Context Condensing Discussion Summary

**Date**: 2025-11-18
**Status**: SUPERSEDED by Handover 0319
**Type**: Architecture Decision / Feature Proposal

---

## ⚠️ SUPERSEDED NOTICE

**This discussion was superseded by Handover 0319 (Context Management v3.0 - Granular Fields).**

The condensing approach (Options B/C) was not implemented. Instead, **Option A (static fields)** was chosen, enhanced with **granular per-field selection** in 0319, which gives users explicit control over individual fields rather than condensed summaries.

**Resolution**: User selected Option A with granular field selection (0319) rather than CPU-based condensing.

---

---

## Session Summary

This session completed **Handover 0316A** (critical alignment fix) and then pivoted to an important architectural discussion about **how depth controls should work**.

---

## Part 1: Completed Work - Handover 0316A

### Problem Solved
User identified critical misalignment after Handover 0316:
- Missing 3 badges in Context Priority Management (Tech Stack, Architecture, Testing)
- Missing 1 depth control in Depth Configuration (Project Context)
- Tools not registered in `context_tools/__init__.py`

### Solution Delivered
**Perfect 9-way alignment achieved:**
```
9 MCP Tools = 9 Priority Badges = 9 Depth Controls = 9 Registered Exports
```

### Files Modified (7 files)
1. `frontend/src/views/UserSettings.vue` - Added 3 missing badges
2. `frontend/src/components/settings/DepthConfiguration.vue` - Added project_context depth control
3. `frontend/src/services/depthTokenEstimator.ts` - Added project_context token estimates
4. `src/giljo_mcp/tools/context_tools/__init__.py` - Registered 3 new tools
5. `tests/integration/test_handover_0316_simple.py` - Fixed failing tests
6. `tests/integration/test_handover_0316_final.py` - Updated to verify 9 tools
7. `handovers/0316a_context_alignment_fix.md` - Documentation

### Git Commit
```
Commit: 5550c18
Message: fix(context): Complete 9-way alignment for context management UI
Status: All tests passing (8/8), frontend builds successfully
```

---

## Part 2: Architectural Discussion - Depth Control Design

### User's Critical Question
> "How do you know what fields you are missing?"

The user identified a fundamental problem with the current field-selection approach: **users can't know what important information they're excluding**.

### Current System Explained

The depth controls are **NOT sliders/truncators**. They are **discrete option selectors**:

| Control Type | Example | How It Works |
|--------------|---------|--------------|
| **Boolean** | `project_context_enabled` | On: fetch all fields. Off: fetch nothing. |
| **Level** | `architecture_depth` | Overview: 2 fields. Detailed: 6 fields. |
| **Numeric** | `git_commits` | Fetch exactly N complete items. |
| **Chunking** | `vision_chunking` | Only vision docs use smart sentence-boundary chunking. |

**Key Point**: No mid-sentence truncation. Everything returned is complete, coherent data.

### The Problem
```python
# User selects: architecture_depth = "overview"
# Returns only:
{
    "primary_pattern": "Microservices",
    "api_style": "RESTful"
}
# User doesn't know security_considerations field even EXISTS!
```

---

## Part 3: Proposed Solutions

### Option 1: Current System (Static Fields)
- **Pros**: Fast, predictable, no processing
- **Cons**: User doesn't know what they're missing

### Option 2: Simple CPU-Based Condensing (RECOMMENDED START)
```python
# User selects: architecture_depth = "overview_condensed"
# Returns ALL fields in condensed form:
{
    "primary_pattern": "Microservices - event-driven",
    "design_patterns": "Repository, Service layer, Factory",
    "api_style": "RESTful + WebSocket",
    "architecture_notes": "FastAPI + PostgreSQL + Vue3...",
    "security": "JWT RS256, rate limiting...",        # NOW VISIBLE!
    "scalability": "Horizontal scaling, pooling..."   # NOW VISIBLE!
}
# ~300 tokens - same budget, but user sees ALL fields exist
```

**CPU Cost**: <5ms per context tool (negligible)
**Implementation**: ~200 lines, 1-2 days

### Option 3: Mission-Aware Reranking (Phase 2)
```python
# Mission: "Fix authentication bug"
# Backend reranks fields by relevance:
{
    "security_considerations": "...",  # RANKED #1 (most relevant to auth)
    "api_style": "...",                # RANKED #2
    "primary_pattern": "...",          # RANKED #3
    ...
}
```

**CPU Cost**: <10ms (keyword matching, no LLM)
**Implementation**: +150 lines, +1 day

### Option 4: LLM Summarization
- **Pros**: Best quality
- **Cons**: ~500ms latency, API costs, complexity
- **Verdict**: Not recommended for now

---

## Comparison Matrix

| Approach | Knows What's Missing? | CPU Cost | Adaptive? | Complexity |
|----------|----------------------|----------|-----------|------------|
| Current (Static) | No | 0ms | No | Low |
| Condensing | Yes (sees all fields) | <5ms | No | Low |
| Reranking | Yes + prioritized | <10ms | Yes | Medium |
| LLM Summary | Yes | ~500ms | Yes | High |

---

## Recommended Implementation Path

### Phase 1: Add Condensed Modes
New depth options:
```python
depth_options = [
    "overview",             # Existing: 2-3 fields, full text
    "overview_condensed",   # NEW: All fields condensed
    "detailed",             # Existing: All fields, full text
    "detailed_condensed",   # NEW: All fields, moderate condensing
]
```

**Effort**: 1-2 days

### Phase 2: Add Mission-Aware Reranking
Optional `mission_context` parameter to MCP tools that reranks fields by relevance.

**Effort**: +1 day

---

## Decision Needed

**User must decide which approach to implement:**

**A)** Keep current system (static fields only)
**B)** Add condensed modes (simple CPU-based sentence truncation)
**C)** Add condensed + reranking (mission-aware field prioritization)
**D)** Something else

**Claude's Recommendation**: Start with **B**, then add **C** in Phase 2.

---

## Technical Details for Condensing

### Simple Sentence-Boundary Truncation
```python
def truncate_to_sentences(text: str, max_tokens: int) -> str:
    """
    Truncate at sentence boundaries, never mid-sentence.
    CPU cost: ~0.5ms (string operations only)
    """
    sentences = text.split('. ')
    result = []
    tokens = 0

    for sentence in sentences:
        sentence_tokens = len(sentence) // 4  # Rough estimate
        if tokens + sentence_tokens > max_tokens:
            break
        result.append(sentence)
        tokens += sentence_tokens

    if len(result) < len(sentences):
        return '. '.join(result) + '...'
    return '. '.join(result)
```

### Field Relevance Scoring (for reranking)
```python
def score_field_relevance(data: dict, mission: str) -> dict:
    """
    Keyword-based relevance scoring. CPU-only, no LLM.
    """
    mission_keywords = mission.lower().split()
    scores = {}

    for field_name, field_value in data.items():
        field_text = f"{field_name} {field_value}".lower()
        matches = sum(1 for kw in mission_keywords if kw in field_text)
        scores[field_name] = matches

    return scores
```

---

## Files to Create (If Implementing)

### Phase 1 (Condensing)
- `src/giljo_mcp/context/condensing.py` - Condensing utilities
- Update all 9 context tools to support `_condensed` modes
- Update `depthTokenEstimator.ts` with new options
- Update `DepthConfiguration.vue` dropdown options

### Phase 2 (Reranking)
- `src/giljo_mcp/context/reranking.py` - Relevance scoring
- Add `mission_context` parameter to MCP tools
- Update orchestrator to pass mission context

---

## Key Insight from Discussion

The current depth system gives users **control** but not **visibility**. Users can exclude fields but don't know what they're excluding.

**Condensing solves this** by showing a 1-sentence summary of EVERY field, so users can see:
1. What fields exist
2. A hint of their content
3. Whether they need to fetch "detailed" mode

---

## Next Steps for Fresh Agent

1. **Get user decision**: A, B, C, or D?
2. **If B or C**: Create implementation plan with TDD approach
3. **Estimate effort**: 2-3 days total
4. **No migrations needed**: This is frontend + backend logic only

---

## Session Context

- **Branch**: master
- **Ahead of origin**: 5 commits (unpushed)
- **Last commit**: 5550c18 (alignment fix)
- **Tests**: All passing
- **Build**: Frontend builds successfully

---

## User's Exact Words

On the problem:
> "how do you know what fields you are missing?"

On potential solution:
> "I am thinking of a very very simplified CPU based reranking method based on the dropdown settings"

On current state:
> "for now i am ok with fields, but I am thinking..."

This indicates the user wants to **explore options** but hasn't committed to implementation yet. Fresh agent should present options clearly and get a decision before proceeding.
