# Handover 0841: Slash Command Optimization (/gil_add)

**Date:** 2026-03-26
**From Agent:** Orchestrator
**To Agent:** Next Session
**Priority:** Low
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Rewrite `/gil_add` slash command from 343 lines (~3,500 tokens) to ~40 lines (~500 tokens). The current file scripts the entire conversational flow verbatim, but Claude only needs the routing rules, tool names, parameter schemas, and valid values. The MCP tool definitions (already loaded via server connection) provide the rest.

## Context

- Slash commands are Claude Code-only (static `.md` files in `~/.claude/commands/`)
- They are NOT dynamic across platforms — Codex CLI and Gemini CLI have separate systems (0836 series)
- The file is injected as the full prompt on every invocation — zero prior context
- Keep it local (no MCP round-trips) but slim

## Current Problem

The 343-line file includes:
- ~80 lines of interactive mode with verbatim prompt templates Claude doesn't need
- ~40 lines of triplicated success confirmation templates
- ~25 lines of error handling scripts
- ~20 lines of embedded help text

Claude can generate conversational prompts and error messages from rules + valid values. It doesn't need a script.

## Proposed Slim Version (~40 lines)

```markdown
# /gil_add — Add task or project to GiljoAI

## Routing
- **Task**: technical debt, TODOs, bugs, improvements -> `create_task` MCP tool
- **Project**: actionable work items, features, initiatives -> `create_project` MCP tool

## Task parameters
- title (required), description, category (frontend|backend|database|api|testing|devops|documentation|security|performance|general), priority (low|medium|high|critical)

## Project parameters
- name (required), description, project_type (optional label)

## Behavior
- If input is clear, route directly. If ambiguous, ask: task or project?
- If no flags, analyze conversation context to suggest title/description
- On success: show type, title, ID, and "View in GiljoAI dashboard"
- On error: show what's wrong and how to fix
```

## Implementation Plan

1. Back up current `~/.claude/commands/gil_add.md`
2. Write slim version
3. Test: `/gil_add fix the login bug` (should route to task)
4. Test: `/gil_add implement OAuth support` (should route to project)
5. Test: `/gil_add` with no args (should enter interactive mode)
6. Test: `/gil_add --help` (should show usage)
7. Update the server-side slash command export (`/api/download/slash-commands`) to ship the slim version

## Also Consider

- Review ALL slash commands in `~/.claude/commands/` for similar bloat
- The server exports these via `FileStaging.stage_slash_commands()` — update the source templates
- Source templates likely in `src/giljo_mcp/slash_commands/` or similar

## Success Criteria

- [ ] `/gil_add` works identically with ~500 tokens instead of ~3,500
- [ ] All routing scenarios tested (task, project, ambiguous, no args, --help)
- [ ] Server-side export updated to ship slim version
- [ ] No regression in MCP tool calls
