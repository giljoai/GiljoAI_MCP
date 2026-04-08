# Code Standards

These standards apply to all contributions to GiljoAI MCP. They reflect lessons from production use and keep the codebase consistent as the contributor base grows.

---

## Code Discipline: Fold, Don't Reinvent

Before writing new code, check whether the functionality already exists. This project has a mature service layer — use it.

**Existing services to know about:**
- **Service layer** (`src/giljo_mcp/services/`) — Business logic lives here, not in endpoints or tools
- **WebSocket events** (`api/websocket_manager.py`) — Real-time updates use the existing broadcast system
- **AgentJobManager** — Agent lifecycle management
- **TenantManager** — Tenant filtering (never write manual WHERE clauses for tenant isolation)
- **UnifiedTemplateManager** — Template operations
- **ProductMemoryRepository** — Memory entries (not raw JSONB manipulation)

**The discipline:**
1. **Search before you build.** Check if the functionality already exists in a service, repository, or utility.
2. **Extend, don't duplicate.** Add a method to an existing service rather than creating a new module.
3. **Root-cause fixes only.** If something is broken, find out why and fix that. No workarounds.
4. **Leave the codebase cleaner than you found it.** If you touch a file and see dead code, clean it up.

---

## Quality Gate

### Pre-Commit Checks

Before every commit, verify:

1. **Zero lint issues**: `ruff check src/ api/` must pass clean
2. **Exception-based error handling**: All Python layers raise exceptions on error — never `return {"success": False, ...}`
3. **Tenant isolation**: Every database query filters by `tenant_key` (security-critical, no exceptions)
4. **No dead code**: If you add a method, it must be called. If you remove a caller, remove the method.
5. **No commented-out code**: Delete it. Git has the history.
6. **Pre-commit hooks must pass**: Do not use `--no-verify`

### Function and Class Size

- No function exceeds 200 lines without explicit justification
- No class exceeds 1000 lines — split into focused modules

### No Placeholder Data

- No `random.randint()` or fabricated values in production code paths
- If real data is unavailable: return null, raise an exception, or mark as "not yet implemented" — never fabricate

---

## Database Write Discipline

All writes to domain entities flow through the owning service. No direct `setattr` on ORM models from tools, endpoints, or sibling services.

1. **Single validated write path per entity.** Product writes go through `ProductService.update_product()`. The same principle applies to every domain entity.
2. **Field allowlists, not `hasattr`.** Service methods that accept dynamic fields must use an explicit allowlist. `hasattr(model, field)` is not a security gate.
3. **JSONB validators are mandatory.** Every JSONB column with a known schema must have a Pydantic model in `jsonb_validators.py`, called at the service write boundary.
4. **Agent input is untrusted.** MCP tool parameters (`src/giljo_mcp/tools/`) come from AI agents. Validate type, enforce max length, and check enum membership before reaching the service layer. DB constraints produce 500s — validate at the application layer for clean 422 responses.

---

## Endpoint Security

- Every API router must inject `Depends(get_current_active_user)` for authentication
- Admin-only endpoints must additionally check user role
- Only explicitly public endpoints (login, health check, frontend config) may skip auth

---

## Frontend Standards

- **Design reference:** `frontend/design-system-sample-v2.html` is the authoritative UI/brand guide. Open it in a browser before any frontend styling work.
- Shared logic goes in `composables/` — do not duplicate utility functions across components
- Use Vuetify theme variables for colors — no `!important` CSS overrides unless compensating for a verified framework bug
- **Dialog anatomy:** All modals use `.dlg-header` / `.dlg-footer` from `main.scss`. Never use `v-card-title` or `v-card-actions` for dialog chrome.
- **Borders:** Never use CSS `border` on rounded elements. Use the `smooth-border` class from `main.scss` (box-shadow inset approach).
- **Agent colors:** Use `getAgentColor()` or CSS `var(--agent-*-primary)` — never hardcode hex values. Colors are defined in `design-tokens.scss` and `agentColors.js`.
- **Accessibility baseline:** WCAG AA contrast (4.5:1), color-blind safe palettes, keyboard navigability for all interactive elements.

### Frontend Tests

Tests live in `frontend/tests/` using Vitest + @vue/test-utils + @pinia/testing. Run with `npm run test:run` from `frontend/`. Add tests for new components.

---

## Cross-Platform

Always use `pathlib.Path()` for file operations:

```python
# Correct
from pathlib import Path
config_path = Path.cwd() / "config.yaml"

# Wrong — hardcoded OS path
config_path = "F:\\GiljoAI_MCP\\config.yaml"
```
