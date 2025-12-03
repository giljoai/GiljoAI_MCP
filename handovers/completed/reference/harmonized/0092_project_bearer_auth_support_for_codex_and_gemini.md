# Project 0092 — Bearer Auth Support for Codex/Gemini (MCP-over-HTTP)
<!-- Harmonized on 2025-11-04; docs updated: AI_TOOL_CONFIGURATION_MANAGEMENT.md and MCP_OVER_HTTP_INTEGRATION.md -->

Document version: 1.0.0
Date: 2025-11-03
Owner: Core Platform

---

## Summary

Added backward-compatible Authorization: Bearer header support to the MCP HTTP endpoint so Codex CLI and Gemini CLI can register the server in URL mode without custom headers. Existing API keys remain the single credential; “Bearer” is just an alternate header for the same key. Claude CLI continues to use `X-API-Key` unchanged.

This change enables remote/laptop clients to integrate via Codex/Gemini with one command while preserving multi-tenant isolation and current API key semantics.

## Goals

- Support Codex/Gemini MCP URL transport which only allows bearer tokens via env var.
- Keep API keys, storage, and validation logic unchanged.
- Maintain full backward compatibility with Claude (`X-API-Key`).
- Update generated commands and docs accordingly.

## Scope of Changes

- Accept `Authorization: Bearer <token>` alongside `X-API-Key: <token>` in MCP endpoint.
- Update command generators (backend + frontend) for Codex/Gemini to use `--bearer-token-env-var`.
- Refresh documentation to note both accepted headers and show new commands.

## Files Modified

- api/endpoints/mcp_http.py:622
  - Accepts `authorization` header.
  - Resolves API key from `X-API-Key` or `Authorization: Bearer`.
  - Reuses existing session/auth logic; no DB changes.

- api/endpoints/ai_tools.py:1
  - Codex config generator outputs bearer env var + `--bearer-token-env-var`.
  - Gemini config generator outputs HTTP + header: `gemini mcp add -t http -H "X-API-Key: ..." <name> <url>`.
  - Instructions updated accordingly.

- frontend/src/utils/configTemplates.js:1
  - Codex template uses bearer env var.
  - Gemini template uses HTTP + header.

- frontend/src/components/AiToolConfigWizard.vue:198
  - Codex prompt uses bearer env var.
  - Gemini prompt uses HTTP + header.

- docs/AI_TOOL_CONFIGURATION_MANAGEMENT.md:1
  - Codex uses bearer env var; Gemini uses HTTP + header.

- docs/MCP_OVER_HTTP_INTEGRATION.md:361
  - “Authentication Headers” now documents both `X-API-Key` and `Authorization: Bearer`.

## Backward Compatibility

- No changes to API key model, format, storage, or issuance.
- Claude CLI flows remain the same using `--header "X-API-Key: ..."`.
- Existing clients using `X-API-Key` continue to work.

## Security & Multi‑Tenant Isolation

- The bearer token is the same API key value; validation path is unchanged.
- Tenant context resolution and session persistence are unaffected.
- Logs and audit remain per `api_key_id` as before.

## Usage — Commands

- Claude CLI (unchanged):
  - `claude mcp add --transport http giljo-mcp http://<server>:7272/mcp --header "X-API-Key: gk_..."`

- Codex CLI:
  - `export GILJO_API_KEY="gk_..."`
  - `codex mcp add --url http://<server>:7272/mcp --bearer-token-env-var GILJO_API_KEY giljo-mcp`

- Gemini CLI:
  - `gemini mcp add -t http -H "X-API-Key: gk_..." giljo-mcp http://<server>:7272/mcp`

Verification:
- `codex mcp list` / `gemini mcp list`
- Curl sanity:
  - `curl -s -X POST http://<server>:7272/mcp -H 'Content-Type: application/json' -H "Authorization: Bearer $GILJO_API_KEY" -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05"},"id":1}'`

## Testing Notes

- Initialize → tools/list → tools/call flows succeed with either header.
- Invalid key returns the same JSON-RPC error as before.
- Sessions created/updated as normal; tenant context preserved.

## Monetization Readiness

- API keys remain the single credential and are SaaS-ready.
- Next steps (incremental, optional):
  - Add usage metering table keyed by `api_key_id`.
  - Enforce rate limits/quotas by plan.
  - Expose usage in dashboard; integrate billing (Stripe) later without auth changes.

## Rollback Plan

- Revert the single MCP endpoint change if required.
- Frontend/command text changes are cosmetic; safe to keep or revert independently.

## Risks & Mitigations

- Risk: Ambiguity from two headers.
  - Mitigation: First prefer `X-API-Key` if present; fall back to Bearer.
- Risk: Client misconfiguration.
  - Mitigation: Updated guides/templates and error messaging to mention both headers.

---

End of Project 0092
