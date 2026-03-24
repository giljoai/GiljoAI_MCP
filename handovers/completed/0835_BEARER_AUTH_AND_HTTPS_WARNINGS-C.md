# Handover 0835: Bearer Auth Migration & HTTPS Contextual Warnings

**Date:** 2026-03-22
**From Agent:** Claude Code Session
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 2-3 Hours
**Status:** Complete
**Edition Scope:** CE

## Task Summary

Migrate MCP tool configuration prompts from `X-API-Key` header to `Authorization: Bearer` (MCP spec-aligned, future-proof for SaaS OAuth). Add contextual HTTPS warnings in three places so users enabling HTTPS understand the extra CLI tool configuration required (specifically Gemini CLI's Node.js cert trust issue).

## Context

- Server already accepts both `X-API-Key` and `Authorization: Bearer` (mcp_http.py:1142-1189)
- All 3 CLIs support Bearer tokens natively
- Gemini CLI (Node.js) rejects self-signed mkcert certs — requires `NODE_EXTRA_CA_CERTS` env var
- HTTP is the default (no cert issues) — HTTPS is opt-in for power users
- This is pre-CE-launch cleanup (April 5 deadline)

## Implementation Plan

### Part 1: Migrate wizard to Authorization: Bearer

**Frontend (`AiToolConfigWizard.vue`):**
- `claudePrompt()` → `--header "Authorization: Bearer ${apiKey}"`
- `geminiPrompt()` → `-H "Authorization: Bearer ${apiKey}"`
- `codexPrompt()` → already uses `--bearer-token-env-var` (no change)
- `openclawPrompt()` → already uses `Authorization: Bearer` (no change)
- Default fallback → update to Bearer format

**Backend (`api/endpoints/ai_tools.py`):**
- `get_claude_code_config()` → Bearer header
- `get_gemini_config()` → Bearer header
- `get_codex_config()` → no change

### Part 2: HTTPS contextual warnings (3 places)

1. **AiToolConfigWizard.vue** — when Gemini selected AND `window.location.protocol === 'https:'`, show prerequisite alert with `NODE_EXTRA_CA_CERTS` command
2. **NetworkSettingsTab.vue** — when HTTPS is toggled on, show note about CLI tool cert configuration
3. **install.py** — when user enables HTTPS, print note about CLI tool requirements

## Success Criteria

- Wizard outputs `Authorization: Bearer` for Claude and Gemini
- Gemini HTTPS warning appears only when ssl_enabled AND tool=gemini
- NetworkSettingsTab shows CLI cert note when HTTPS enabled
- install.py prints CLI cert advisory when HTTPS selected
- All existing tests pass

## Implementation Summary

### What Was Built
- Wizard outputs `Authorization: Bearer` for Claude and Gemini (Codex already used env var, OpenClaw already used Bearer)
- Gemini + HTTPS conditional warning in wizard with `NODE_EXTRA_CA_CERTS` command
- CLI cert note in NetworkSettingsTab when HTTPS is enabled
- **Protocol toggle re-attach warning** — when HTTPS is toggled on/off, user is warned to remove and re-add MCP tools with step-by-step instructions
- HTTPS advisory in install.py during HTTPS setup
- 4 integration tests, all passing

### Key Files Modified (6)
- `frontend/src/components/AiToolConfigWizard.vue` — Bearer prompts + Gemini HTTPS warning
- `frontend/src/components/settings/tabs/NetworkSettingsTab.vue` — CLI cert note + re-attach warning
- `api/endpoints/ai_tools.py` — Bearer format in config generators
- `install.py` — HTTPS advisory text
- `handovers/HANDOVER_CATALOGUE.md` — catalogue entry
- `tests/integration/test_bearer_auth_migration.py` — new, 4 tests

### Status
Complete. 20 integration tests passing (16 from 0834 + 4 new). No lint regressions.
