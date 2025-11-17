# Handover 0314: Implement Per-Source Depth Controls

**Status**: Not Started
**Tool**: Claude Code (CLI) - Requires database schema change, backend, and frontend
**Estimated Time**: 4-5 days
**Created**: 2025-11-17
**Assignee**: Database Expert + TDD Implementor Agents

## Executive Summary

Implement per-source depth controls to allow granular token management independent of priority. Based on v2.0 architecture from Handover 0312.

## Scope

**Database Changes**:
1. Add `depth_config` JSONB column to `users` table
2. Create migration script (idempotent)

**Backend Changes**:
1. Add depth_config CRUD endpoints
2. Update `mission_planner.py` to use depth settings
3. Implement depth-specific extraction logic for 6 sources

**Frontend Changes**:
1. Add "Context Depth" tab to UserSettings.vue
2. Create depth configuration table (6 rows, different controls per source)
3. Add token calculator (display-only, no enforcement)

**Per-Source Depth Controls**:
- Vision Document: [None | Light | Moderate | Heavy] chunking
- 360 Memory: [Last 1 | 3 | 5 | 10] projects
- Git History: [Last 1 | 3 | 5 | 10] commits
- Agent Templates: [Title Only | Full Description]
- Tech Stack: [Summary | Full]
- Architecture: [Summary | Full] + checkbox for Serena codebase

**Files Modified**:
- `src/giljo_mcp/models.py` (add depth_config column)
- `src/giljo_mcp/mission_planner.py` (use depth_config)
- `frontend/src/views/UserSettings.vue` (add depth tab)
- `api/endpoints/users.py` (depth_config CRUD)
- `install.py` (migration for depth_config column)

**Estimated Time**: 4-5 days

## TDD Implementation Plan

**Phase 1: Database Migration (RED)**
- Test depth_config column exists
- Test default depth_config applied to new users
- Test depth_config validation (valid values only)

**Phase 2: Backend Depth Logic (GREEN)**
- Test depth controls applied correctly per source
- Test token calculator accuracy
- Test graceful degradation (missing depth_config)

**Phase 3: Frontend UI (GREEN)**
- Test depth configuration table renders
- Test depth changes saved to backend
- Test token calculator updates in real-time

## Dependencies

**Requires**: Handover 0313 (Priority System) complete
**Blocks**: Handover 0315 (MCP Thin Client)

## Success Criteria

- [ ] depth_config column added to users table
- [ ] 6 depth controls configurable in UI
- [ ] Token calculator shows estimated total
- [ ] Depth settings persist across sessions
- [ ] All tests passing (>80% coverage)
- [ ] Migration is idempotent (safe for fresh installs + upgrades)
