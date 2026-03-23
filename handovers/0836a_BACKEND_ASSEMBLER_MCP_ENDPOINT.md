# Handover 0836a: Backend Assembler + MCP Endpoint

**Date:** 2026-03-22
**Parent:** 0836 (Multi-Platform Agent Template Export)
**Priority:** Critical
**Status:** Not Started
**Edition Scope:** CE
**Branch:** `feature/0836-multi-platform-export`
**Dependencies:** None (can start immediately)

## Pre-Read

Read `handovers/0836_MULTI_PLATFORM_AGENT_EXPORT.md` first — it contains the shared API contract, design doc corrections, and cross-platform requirements.

## Task Summary

Build the `AgentTemplateAssembler` class and register a new `get_agent_templates_for_export` MCP tool. The assembler takes platform-neutral templates from the database and produces correctly formatted output for Claude Code, Codex CLI, or Gemini CLI.

## What to Build

### 1. AgentTemplateAssembler

**New file:** `src/giljo_mcp/tools/agent_template_assembler.py`

A class with one public method: `assemble(templates: list[AgentTemplate], platform: str) -> dict`

Three internal formatters:

**A. Claude Code formatter**
- Wraps existing `render_claude_agent()` from `template_renderer.py`
- Output: markdown with YAML frontmatter
- Frontmatter fields: `name` (role-suffix, lowercase hyphenated), `description`, `model` (default: sonnet), `tools` (hardcoded: `Read, Write, Glob, Grep, Bash, mcp__giljo-mcp__*`), `color` (from `background_color` field)
- Body: `system_instructions` + `user_instructions` + `behavioral_rules` + `success_criteria`
- This should produce output identical to what `render_claude_agent()` produces today — verify with a diff

**B. Gemini CLI formatter**
- Output: markdown with YAML frontmatter (different schema)
- Frontmatter fields: `name` (same naming), `description`, `kind` (always `agent`), `model` (default: gemini-2.5-pro), `max_turns` (default: 50), `tools` (YAML list: `[shell, read_file, write_file, mcp_*]`)
- NO `color` field (Gemini doesn't support it)
- Body: same content as Claude format

**C. Codex CLI formatter**
- Output: structured dict (NOT file content — LLM writes files locally)
- Returns per agent: `agent_name`, `description`, `role`, `developer_instructions` (combined body as string), `suggested_model` (default: gpt-5.2-codex), `suggested_reasoning_effort` (default: medium)
- Also returns `toml_format_reference` — a string documenting the exact TOML schema the LLM should produce

**MCP tool name translation in body content:**
- The `system_instructions` field references `mcp__giljo-mcp__*` (Claude Code convention)
- For Gemini: translate to `giljo-mcp_*` (verify Gemini's actual convention at implementation time — check their docs or test with a connected Gemini CLI)
- For Codex: verify convention at implementation time
- If conventions cannot be confirmed, leave as `mcp__giljo-mcp__*` with a comment — the slim bootstrap instructs agents to call `get_agent_mission()` which delivers the real protocol dynamically

### 2. MCP Tool Registration

**File:** `src/giljo_mcp/tools/tool_accessor.py`

Register `get_agent_templates_for_export` as a new MCP tool.

Parameters: `tenant_key` (str), `platform` (str — one of `claude_code`, `codex_cli`, `gemini_cli`)

Implementation:
1. Query active templates for tenant (reuse existing query pattern from `generate_download_token`)
2. Apply `select_templates_for_packaging()` to cap at 8
3. Call `assembler.assemble(templates, platform)`
4. Return the API contract response (see parent handover for exact JSON schema)

### 3. Platform-Aware ZIP Generation

**File:** `api/endpoints/downloads.py`

Extend `download_agent_templates()` (the direct ZIP endpoint) to accept an optional `platform` query param (default: `claude_code` for backward compatibility).

When platform is specified, use the assembler to format templates instead of hardcoded `render_claude_agent()`.

Also extend `generate_and_stage_download()` (the token-based flow) to accept and forward the platform parameter.

### 4. Assess claude_export.py

**File:** `api/endpoints/claude_export.py`

Read this endpoint. If it's redundant with the assembler path (likely — it writes files directly to disk), mark it as deprecated with a comment. Do not delete it in this handover.

## Testing Requirements

- Unit test: Claude Code formatter output matches existing `render_claude_agent()` output exactly
- Unit test: Gemini formatter produces valid YAML frontmatter with correct fields
- Unit test: Codex formatter returns correct structured dict with all required fields
- Unit test: assembler rejects invalid platform strings
- Integration test: `get_agent_templates_for_export` returns correct response per platform
- Integration test: platform-aware ZIP contains correctly formatted files

## Key Files

| File | Action |
|------|--------|
| `src/giljo_mcp/tools/agent_template_assembler.py` | NEW |
| `src/giljo_mcp/tools/tool_accessor.py` | Add MCP tool registration |
| `src/giljo_mcp/template_renderer.py` | Add `render_gemini_agent()`, `render_codex_agent()` |
| `api/endpoints/downloads.py` | Platform param on ZIP endpoints |
| `api/endpoints/claude_export.py` | Assess, mark deprecated if redundant |
| `tests/` | New test files for assembler + MCP tool |

## Success Criteria

- `get_agent_templates_for_export(platform="claude_code")` returns pre-assembled `.md` files matching current output
- `get_agent_templates_for_export(platform="gemini_cli")` returns pre-assembled `.md` files with Gemini frontmatter
- `get_agent_templates_for_export(platform="codex_cli")` returns structured JSON with TOML format reference
- ZIP downloads work with `?platform=gemini_cli` parameter
- Existing Claude Code export flow unchanged (backward compatible)
- All tests pass, ruff clean
