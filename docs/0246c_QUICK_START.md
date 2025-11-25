# Handover 0246c - Quick Start Guide

**Updated**: 2025-11-24
**Focus**: Dynamic Agent Discovery & Token Reduction
**Status**: READY FOR IMPLEMENTATION
**Timeline**: 2 days

---

## The Challenge in 30 Seconds

**Problem**: Orchestrator prompts waste 142 tokens (24%) embedding static agent templates.

**Solution**: Create MCP tool for dynamic discovery, remove embedded templates.

**Result**: 594 → 450 tokens (25% reduction, 144 tokens saved per instance)

---

## Before vs After

### Current State (Inefficient)

```
Orchestrator Prompt: 594 tokens

Core Instructions: 452 tokens ← Essential
Agent Templates: 142 tokens   ← WASTE!
  ├── implementer: 28 tokens
  ├── tester: 26 tokens
  ├── reviewer: 29 tokens
  ├── documenter: 31 tokens
  └── analyzer: 28 tokens
```

### Target State (Optimized)

```
Orchestrator Prompt: 450 tokens

Core Instructions: 450 tokens ← All essential
Discovery Instruction: "Use get_available_agents() to discover agents"

No embedded templates!
```

---

## What to Build

### 4 Phases, 2 Days

**Phase 1: Create MCP Tool** (2-3 hours)
- File: `src/giljo_mcp/tools/agent_discovery.py`
- Function: `get_available_agents()`
- Returns: Agents with version metadata

**Phase 2: Remove Embedding** (1-2 hours)
- File: `src/giljo_mcp/prompt_generators/thin_prompt_generator.py`
- Delete: `_format_agent_templates()` method
- Result: Templates removed from prompt

**Phase 3: Register Tool** (30 minutes)
- File: `src/giljo_mcp/tools/__init__.py`
- Action: Register `get_available_agents` in MCP tools

**Phase 4: Update Instructions** (1 hour)
- File: `src/giljo_mcp/tools/orchestration.py`
- Update: Remove templates from response

---

## Documentation Roadmap

### Where to Find What

**Quick Reference** (This File)
- Where to look, what to do

**Implementation Guide**
- File: `F:\GiljoAI_MCP\docs\HANDOVER_0246c_IMPLEMENTATION_GUIDE.md`
- Use: During active coding
- Contains: Step-by-step instructions, code examples, checklist

**Primary Handover**
- File: `F:\GiljoAI_MCP\handovers\0246c_dynamic_agent_discovery_token_reduction.md`
- Use: Complete reference, edge cases, testing details
- Contains: Full specification, 4 phases, testing strategy

**Documentation Index**
- File: `F:\GiljoAI_MCP\docs\HANDOVER_0246c_DOCUMENTATION_INDEX.md`
- Use: Navigation hub, finding specific sections
- Contains: Document map, quick reference sections

---

## Getting Started (5 Steps)

### Step 1: Understand the Problem (10 min)
Read: `HANDOVER_0246c_UPDATE_SUMMARY.md` (first 50 lines)

### Step 2: Review Implementation Plan (15 min)
Read: `HANDOVER_0246c_IMPLEMENTATION_GUIDE.md` (Lines 1-100)

### Step 3: Write Tests First (TDD) (2 hours)
Create: `tests/unit/test_agent_discovery.py`
Reference: `HANDOVER_0246c_IMPLEMENTATION_GUIDE.md` (Testing section)

### Step 4: Implement Phases 1-4 (4-5 hours)
Follow: `HANDOVER_0246c_IMPLEMENTATION_GUIDE.md` (Phase sections)
Code Examples: Complete with all details

### Step 5: Verify & Commit (1 hour)
Checklist: `HANDOVER_0246c_IMPLEMENTATION_GUIDE.md` (Verification section)
Commit: See primary handover (Git Commit Template)

---

## Success Metrics

### When You're Done

- Orchestrator prompt: **450 tokens** (was 594)
- Tests: **All passing** (>80% coverage)
- Files: **Created (3) + Modified (3)**
- Time: **2 days** of implementation

---

## Key Files

| File | Purpose | Read |
|------|---------|------|
| `HANDOVER_0246c_IMPLEMENTATION_GUIDE.md` | Step-by-step guide | During coding |
| `0246c_dynamic_agent_discovery_token_reduction.md` | Complete spec | For details |
| `HANDOVER_0246c_DOCUMENTATION_INDEX.md` | Navigation | For finding sections |
| `HANDOVER_0246c_UPDATE_SUMMARY.md` | Task overview | At start |

---

## The Architecture

### How It Works (After Implementation)

```
OLD: Embedded Templates
  Orchestrator Prompt (594 tokens)
  ├── Core Instructions (452)
  └── Templates (142) ← Embedded

NEW: Dynamic Discovery
  Orchestrator Prompt (450 tokens)
  ├── Core Instructions (450)
  └── Discovery instruction
       ↓
     Orchestrator calls: get_available_agents()
       ↓
     MCP Tool returns: Agent list with metadata
       ↓
     Orchestrator: Uses agents as needed
```

### What Changes

| Component | Before | After |
|-----------|--------|-------|
| Prompt size | 594 tokens | 450 tokens |
| Template embedding | Yes | No |
| Discovery method | Embedded | MPC tool call |
| Token savings | 0% | 25% |

---

## Common Questions

**Q: Why remove embedded templates?**
A: Static data shouldn't be in prompts. Templates are static (never change per-project) yet embedded in EVERY orchestrator prompt. Moving to on-demand MCP tool saves 144 tokens per instance.

**Q: How does the orchestrator get agents now?**
A: Via MCP tool: `get_available_agents()`. When orchestrator needs agents, it calls this tool instead of using embedded data.

**Q: Will this break existing code?**
A: No. Templates still available via MCP tool. Only the prompt embedding is removed.

**Q: How do I verify it works?**
A: Compare token counts before and after. Before: ~594, After: <495 (target 450).

---

## Verification Checklist

Before marking complete:

- [ ] `get_available_agents()` created in `src/giljo_mcp/tools/agent_discovery.py`
- [ ] `_format_agent_templates()` removed from prompt generator
- [ ] MCP tool registered in `src/giljo_mcp/tools/__init__.py`
- [ ] `get_orchestrator_instructions()` updated to remove templates
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Prompt token count verified: <495 tokens
- [ ] Coverage >80% on new code
- [ ] No breaking changes
- [ ] Git commit created with descriptive message

---

## Quick Reference: File Locations

All absolute paths (Windows format):

**Primary Handover**:
```
F:\GiljoAI_MCP\handovers\0246c_dynamic_agent_discovery_token_reduction.md
```

**Implementation Guide**:
```
F:\GiljoAI_MCP\docs\HANDOVER_0246c_IMPLEMENTATION_GUIDE.md
```

**Documentation Index**:
```
F:\GiljoAI_MCP\docs\HANDOVER_0246c_DOCUMENTATION_INDEX.md
```

**Session Memory**:
```
F:\GiljoAI_MCP\docs\sessions\2025-11-24_handover_0246c_refocus.md
```

---

## Next: Start Implementation

1. Read: `HANDOVER_0246c_UPDATE_SUMMARY.md` (5 min)
2. Read: `HANDOVER_0246c_IMPLEMENTATION_GUIDE.md` (20 min)
3. Create: Tests (TDD RED phase) (2 hours)
4. Implement: Phases 1-4 (4-5 hours)
5. Verify: Token count and tests (1 hour)

**Total Time**: ~2 days

**Status**: Ready to start now!

---

**Document Version**: 1.0
**Date**: 2025-11-24
**Quality**: Production-Grade
