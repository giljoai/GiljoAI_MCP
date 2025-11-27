# Handover 0248: Context Priority System Repair - Overview & Strategy

**Date**: 2025-11-25
**Status**: Ready for Implementation
**Priority**: CRITICAL
**Estimated Time**: 4-6 days (entire series)
**Dependencies**: None (standalone repair series)
**Series**: 0248 (Parent), 0248a (Plumbing), 0248b (Framing), 0248c (Persistence)
**Implementation Approach**: Clean Slate - Production-grade code from day one

## Executive Summary

The Context Priority System (introduced in Handovers 0312-0316) is currently broken at multiple layers. While the UI allows users to configure field priorities (CRITICAL/IMPORTANT/REFERENCE/EXCLUDE), these priorities have **zero impact** on LLM behavior. This handover series fixes the broken plumbing and implements the Opus 4.5 proposal: **explicit prompt injection** to make priorities actually influence LLM attention.

**The Problem**: Users can configure priorities, but:
1. UI→Backend schema mismatches prevent priorities from being saved correctly
2. MissionPlanner has variable bugs that prevent reading priorities
3. MCP context tools fetch data but don't inject priority framing
4. LLMs see unframed context and ignore priority metadata
5. 360 Memory and execution mode persistence are broken

**The Solution**: Fix plumbing + add priority framing to MCP tool responses.

**Success Criteria**:
- ✅ Priorities flow correctly from UI → Backend → MissionPlanner → MCP Tools
- ✅ MCP tools inject explicit framing (## CRITICAL:, ## IMPORTANT:, etc.)
- ✅ LLMs demonstrably respect priority framing in their responses
- ✅ 360 Memory and execution mode persist correctly

## Vision: Priority Framing for LLM Attention

**Current State** (Broken):
The MCP tools return raw data without any framing to indicate priority levels. LLMs see all context equally.

**Target State** (Fixed):
MCP tools inject explicit framing headers (## CRITICAL:, ## IMPORTANT:, ## REFERENCE:) that guide LLM attention based on user-configured priorities.

## 4-Tier Priority Framing System

### Priority 1: CRITICAL (Always Included)
**Position Strategy**: Injected at **both beginning and end** of context for primacy + recency effect.

### Priority 2: IMPORTANT (High Priority)
**Position Strategy**: Beginning of context (after CRITICAL items).

### Priority 3: REFERENCE (Medium Priority)
**Position Strategy**: Middle of context (after IMPORTANT items).

### Priority 4: EXCLUDE (Never Included)
**Behavior**: MCP tool skips fetching this content entirely.

## Clean Implementation Approach

**Core Principle**: Build it RIGHT from day one - production-grade, commercially-ready code WITHOUT migration complexity, temporary workarounds, or backward compatibility layers.

**What This Means**:
- No "temporary" code that needs cleanup later
- No dual-read fallbacks for migration
- Production-grade error handling from the start
- Comprehensive validation and logging throughout
- Clean, maintainable, testable code

## Series Breakdown

### 0248a: Plumbing Investigation & Repair (2 days)
**Goal**: Fix the broken data flow from UI → Backend → MissionPlanner with production-grade implementations.

**Issues to Fix**:
1. UI→Backend schema mismatch
2. Format drift in field_priority_config structure
3. MissionPlanner reads from correct field (`sequential_history` from day one)

**Deliverable**: Priorities flow correctly from UI to backend with proper validation and error handling.

### 0248b: Priority Framing Implementation (2-3 days)
**Goal**: Add priority framing to all 9 MCP context tools with production-grade quality.

**Implementation**:
1. Create framing_helpers.py with comprehensive validation
2. Update all 9 MCP tools to inject framing with error handling
3. Add user_id parameter to MCP tool signatures
4. Implement position strategy (CRITICAL at beginning + end)
5. Handle malformed entries gracefully

**Deliverable**: MCP tools return framed content with robust error handling and validation.

### 0248c: Persistence & 360 Memory Fixes (1-2 days)
**Goal**: Fix execution mode persistence and verify 360 Memory integration with proper testing.

**Deliverable**: Execution mode persists, 360 Memory confirmed working, comprehensive tests pass.

## Why This Preserves Thin Client Architecture

**Thin Client Principle**: Orchestrator prompts remain ~10 lines.

**How Framing Fits**:
- MCP tools inject framing BEFORE returning data
- Orchestrator sees framed content but doesn't generate framing itself
- Separation of concerns preserved

## Success Metrics

### Plumbing Health (0248a)
- ✅ UI saves priority config without errors
- ✅ GET /api/users/me/context/priorities returns correct structure
- ✅ MissionPlanner reads priorities without variable errors

### Framing Effectiveness (0248b)
- ✅ CRITICAL items appear at beginning AND end of context
- ✅ All 9 MCP tools inject framing based on user priorities
- ✅ Framing templates match specification

### Persistence (0248c)
- ✅ Execution mode toggle survives page refresh
- ✅ 360 Memory sequential_history updates correctly

## Related Handovers

- 0312-0316: Context Management v2.0 (introduced priority system)
- 0088: Thin Client Prompt Generator
- 0135-0139: 360 Memory Management

---

**Status**: Ready for implementation. Proceed to Handover 0248a (Plumbing Investigation & Repair).
