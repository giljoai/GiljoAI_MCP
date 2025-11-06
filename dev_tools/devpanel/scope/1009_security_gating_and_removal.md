# 1009 – Security, Gating, and Removal

Objective
- Ensure the Developer Panel is strictly dev-only, gated, auditable, and easy to remove.

Controls
- Route Gate: Only mount `/developer` when `ENABLE_DEVPANEL=true`.
- Network Gate: Enforce localhost (127.0.0.1) access and deny external origins.
- Auth Gate: Require authenticated session or a dev-only API key (if configured).
- Edit Gate: Config editing only when `ALLOW_DEVPANEL_EDIT=true` + role check.

Auditing
- Log all panel requests to `logs/devpanel_audit.log` (user, action, time, IP).
- Log config diffs (redacted) with reason.

Removal Plan
- Disable env flags; remove `devpanel.db`; restart API.
- Keep code behind a feature flag and/or dev branch; exclude from production builds.

Pen Test Checklist
- Verify no write path reaches main DB under any condition.
- Verify SSRF/CORS protection and token scopes.
- Verify WS events cannot be forged via panel endpoints.

Estimate / Owner
- 0.5–1 day; Backend + DevOps.
