# Changelog

All notable changes to this project are recorded here. This changelog follows the [Keep a Changelog](https://keepachangelog.com/) convention — entries are grouped by change type (Added / Changed / Fixed / Removed / Security). Internal project IDs appear in parentheses for traceability. Versions follow `MAJOR.MINOR.PATCH[.HOTFIX]` and tags live on the public repository (`giljoai/GiljoAI_MCP`).

## [Unreleased]

### Added

- **Declare MCP spec-version conformance.** New `mcp_spec_versions_supported` custom claim on `/.well-known/oauth-authorization-server`, plus a new public `GET /.well-known/mcp-server-info` endpoint returning `{spec_versions, capabilities, server_name, server_version}`. Declared: `2025-03-26`, `2025-06-18` (default), `2025-11-25` (PARTIAL — CIMD deferred). A 20-test regression suite locks the declaration to CI; full audit and drift-tracking process in [docs/CONFORMANCE.md](docs/CONFORMANCE.md). (API-0021h)
- **Agent-parity MCP tools for tasks.** New tools `update_task`, `update_task_status`, `complete_task`, and `list_tasks` (summary/full modes). `fetch_context` now accepts `categories=["tasks"]`.
- **OAuth token revocation endpoint (RFC 7009).** New `POST /api/oauth/revoke` revokes access and refresh tokens idempotently. Public clients may revoke their own tokens without separate authentication per RFC 7009 §2.1. `MCPAuthMiddleware` enforces revocation on every protected request via an in-process TTL cache (60s positive / 5s negative, tenant-keyed). Refresh-token revocation flips the entire token family per RFC 6749 §10.4. CE migration `ce_0022_oauth_revoked_tokens` adds the revocation ledger. (API-0022)
- **Per-token revocation identity on access JWTs.** Every issued access JWT now carries a `jti` claim (uuid4 hex) so individual tokens can be revoked without invalidating the broader session. (API-0022)

### Changed

- **Task taxonomy unified.** `tasks.category` (freewrite string) replaced with `tasks.task_type_id` foreign key to the renamed `taxonomy_types` table (was `project_types`). REST path `/api/v1/project-types` → `/api/v1/taxonomy-types`. On upgrade, tasks whose old `category` value did not exact-match a taxonomy abbreviation or label arrive untyped — re-tag via the TasksView Type dropdown or via the `update_task` tool. CE migrations apply the rename, FK backfill, and legacy-column drop; all idempotent.
- **BREAKING — `/mcp` hard-rejects JWTs missing an `aud` claim.** The legacy warn-and-accept transition path is removed. Tokens lacking `aud`, or whose `aud` does not include the configured resource, are rejected with `401 Unauthorized` + `WWW-Authenticate` header instead of being silently accepted with a log warning. Every fresh token issued since API-0021d Phase 2 carries a client-asserted `aud`, so legacy compatibility can sunset cleanly. Clients still presenting aud-less tokens must re-authenticate to obtain a properly audience-bound JWT. (API-0022)
- **`oauth_authorization_codes.scope` server default canonicalized.** The Postgres column default moved from the historical `'mcp'` value to the post-API-0021b canonical `'mcp:read mcp:write'` form via CE migration `ce_0021_oauth_codes_scope_default`. The ORM-side default was already canonical; this aligns the schema. (API-0022)

### Security

- **Public-doc leak guardrail.** New pre-commit check blocks RFC 1918 IPs, internal hostnames, and absolute drive-letter paths from being committed to public-bound files. Allowlist: `127.0.0.1`, `::1`, `0.0.0.0`, `localhost`, and the RFC 5737 / RFC 3849 documentation prefixes. Prevents the class of leakage that surfaced in earlier releases.
- **OAuth lookup defense-in-depth.** Refresh-token and authorization-code service-layer lookups now bind on `client_id` in addition to the existing `token_hash` / `code` predicate. `oauth_clients.client_id` is a UUIDv4 primary key (globally unique across tenants), so the additional predicate makes every lookup cross-tenant-isolated at the query layer rather than relying solely on downstream guard checks. Honors the CLAUDE.md "every database query filters by tenant_key — no exceptions" rule. (API-0022 — folds API-0024)

## [1.2.4] — 2026-05-03

### Added

- **Pluggable SMTP email provider.** New `EMAIL_BACKEND` config switch lets self-hosted SaaS deployments route email through any SMTP server instead of the Resend default. (INF-5023)

### Changed

- **BREAKING — minimum Python raised to 3.12.** `pyproject.toml` `requires-python` bumped from `>=3.10` to `>=3.12`. `pip install` on pre-3.12 Python now fails with a `requires-python` resolver error. CI, installer scripts, and docs already required 3.12; this aligns the wheel-build constraint with the existing floor. (INF-5022)
- **Ruff lint target raised to py312.** Lint sweep auto-fixed PEP 604 unions, walrus opportunities, datetime-aware constructions, and ~60 other modernization sites; remaining warnings either fixed manually or carry justified `# noqa` markers. (INF-5020)
- **CI tier-separated.** Private-repo CI restructured into two tiers: a fast tier of eight checks running on every push and PR (gitleaks, ruff, AI-signature block, CE/SaaS boundary, SaaS table refs, pytest, frontend lint+build, vitest), and a slower installer-integrity matrix that runs only on tag pushes matching `v*`. The public CE-export script runs the integrity check locally before push so installer regressions are caught before reaching the public repo. (INF-5024)
- **Project tracking migrated into the MCP server.** New work goes through the `create_project` and `write_360_memory` MCP tools rather than the legacy markdown handover files.

### Fixed

- **Dashboard project list returned stale status values.** The `list_projects` tool now correctly filters across all eight project statuses, and a project that changes status reflects in the list within one poll cycle. Regression tests added. (IMP-5026)
- **`create_project` MCP tool: type validation restored.** Unknown `project_type` values now raise `ValidationError` with the structured `valid_types` list (abbreviation, label, color) in the error context. Omitted `project_type` returns the same hint in the success response. (IMP-5027)
- **System-update banner copy.** Bell-icon notification dropped the redundant "re-run `/giljo_setup`" line (the skills-drift banner already covers that). Both the bell notification and the dashboard update banner now say "restart your server" instead of the older `python update.py` wording.

### Removed

- **Deprecated `deploy_lan_windows.ps1` script.** Pre-unified-installer artifact (2025-10) fully obsoleted by the current `install.ps1` flow. (INF-5021)

## [1.2.3] — 2026-05-03

### Security

- **Removed default password fallback in user creation.** `UserService.create_user` no longer silently substitutes a literal default when no password is supplied. The admin endpoint now forwards the user-provided password, and the service treats the absence of a password as an explicit error. (SEC-5009)

### Changed

- **Skills-version drift banner simplified.** Replaces the previous per-user tracking model. The earlier design tracked three pieces of state for what is fundamentally one comparison: "did the bundled `SKILLS_VERSION` move past the version we last announced?" The new endpoint `/api/notifications/check-skills-version` returns `{current, announced, drift_detected, message}` with no per-user state. Per-version dismissal continues via localStorage. Banner switched from informational blue to brand-yellow warning for better contrast and semantic correctness. The 30-day post-login reminder loop was dropped. Edition-aware copy: CE says "run `/giljo_setup` then `git pull`"; demo/saas says just "run `/giljo_setup`". (IMP-5024)

## [1.2.2] — 2026-05-01

### Added

- **Project status as a typed enum.** Eight statuses (`active`, `inactive`, `staging`, `paused`, `completed`, `cancelled`, `terminated`, `archived`) now live in one place — no more drift between backend services, frontend stores, and database CHECK constraints. (BE-5039)
- **New REST endpoint `GET /api/v1/project-statuses/`** exposes the canonical list with labels, color tokens, and lifecycle flags. The frontend reads from this, never from a hardcoded array.
- **Version-consistency check (`scripts/check_version_consistency.py`).** `VERSION` is the single source of truth; `pyproject.toml`, `frontend/package.json`, `package-lock.json`, `__init__.py` fallback, and the latest `CHANGELOG.md` entry must all match. Wired into pre-commit and the release pipeline.

### Changed

- **Installers hardened on every supported path.** All four install paths now work on stock systems with no manual prep: Windows `install.ps1` (verified on stock PowerShell 5.1 + Windows 11), Windows `install.py` direct (Node.js auto-installs via `winget` when missing), Linux `install.sh` (verified on stock Ubuntu / Debian / WSL), Linux `install.py` direct (`python3-venv` detection via an actual `ensurepip` probe). The "please restart your shell" banner now only fires on Windows where it is actually needed. (INF-5014)
- **`ProjectStatus` enum is backwards compatible.** `ProjectStatus` inherits from `str`, so every existing `project.status == "active"` comparison still works. Callers adopt the enum at their own pace.

### Notes for upgraders

- No database schema rollback path. The status-enum migration is one-way; if you need to back out, restore from a pre-upgrade backup.
- **macOS not validated this release.** The CI smoke matrix runs `install.py` on macOS-latest, but no end-to-end real-box test was performed. Track as a known gap.

## [1.2.1] — 2026-04-30

### Changed

- **BREAKING — `list_projects` MCP tool default behavior.** No longer returns completed or cancelled projects by default. Pass `include_completed=true` to retrieve archived projects. Agents running `list_projects()` with no arguments will now see only active and inactive projects.

### Added

- **New filter parameters on `list_projects`:** `status` (single or comma-separated), `project_type`, `taxonomy_alias_prefix`, `created_after`, `created_before`, `completed_after`, `completed_before`, `include_completed`, and `hidden` (tri-state: `"true"` / `"false"` / `""` for no filter).
- **`hidden` field exposed in every row** regardless of filter. The `hidden` column is a UI declutter flag, not an agent-visibility gate. Agents always see hidden and non-hidden projects alike unless `hidden=true|false` is passed explicitly.

### Notes

- **Legacy backward-compat.** Callers using `status_filter="all"` continue to work; that value implies `include_completed=True` and is honored when the new `status` param is unset.
- **REST endpoint unchanged.** `GET /api/projects/` (used by the dashboard) was not modified — only the MCP-tool-facing path changed.

## [1.2.0] — 2026-04-29

First minor-version release since the v1.1 line, consolidating six weeks of installer hardening, dependency cleanup, and dashboard polish into a single public cut. If you have been running v1.1.9.5, this upgrade is recommended — especially on Windows.

### Fixed

- **Windows install now works on stock PowerShell 5.1.** Earlier Windows installs could fail with cryptic parser errors before reaching the wizard; `install.ps1` is now ASCII-clean and parses correctly under every PowerShell version that ships with Windows 10 / 11.
- **macOS Apple Silicon installs are more resilient.** A new floor on the `greenlet` dependency plus an explicit fail-fast guard prevents long silent hangs that some early Apple Silicon users saw when binary wheels were not yet published for a new Python release.
- **Linux first-run no longer crashes** on the elevation-guidance step. A path edge case that produced `ValueError` on stock Ubuntu has been fixed.

### Changed

- **"Tools → Connect"** replaces the old "Settings → Integrations" naming throughout the dashboard. Same feature, clearer mental model: one place to connect Claude Code, Cursor, and other tooling.
- **Welcome wizard** now offers a starter-template card on step 4 so new users can get to a working agent setup with a single click.
- **Frontend builds now require Node 22** (matching what most current distributions ship by default).
- **Vite line stabilized.** Vite 8 was briefly trialed but pulled back when its new bundler stack proved unstable on macOS and Windows under real installer conditions; the upgrade will return once that stack ships a stable 1.0.

### Added (agent skills bundle v1.1.11)

- **`/gil_add` gained a Read mode**, so you can pull a project's context or status by alias without opening the dashboard. Add mode is unchanged.
- **Faster, cheaper agent context fetches.** Agents now fetch only the context they need rather than pulling the full bundle every time — meaningfully fewer tokens per multi-step run.
- **Cleaner predecessor handling.** Multi-agent handovers now auto-detect whether you are handing off or being handed to, removing a class of "wrong context" agent runs.

### Removed

- **Legacy distribution-tarball scripts.** The hosted installer at `giljo.ai/install.ps1` and `giljo.ai/install.sh` is the only supported install path.

### Notes for upgraders

- Tagged as `v1.2.0-rc.1` first; promoted to `v1.2.0` after a soak window.
- No database schema changes vs v1.1.9.5. Routine `git pull` + restart is sufficient.
- If you are upgrading from v1.1.9.4 or earlier, you will also pick up the security-foundation work that landed in v1.1.9.5 (four-layer secrets defense, hardened CI). No action required.
- The dashboard will show a "skills bundle out of date" banner when you load v1.2.0 for the first time — this is expected. Run `/giljo_setup` (or pull the latest skills via the dashboard) to upgrade your local CLI skills to v1.1.11.

## [1.1.9.5] — 2026-04-29

### Security

- **Four-layer secrets defense established.** Three layers in private (gitignore + pre-commit `gitleaks` + push-CI `gitleaks`), defensive working-tree `gitleaks` in public.
- **Boundary `gitleaks` gate added to CE export pipeline** — last-chance scan after SaaS-strip and before push to public. (INF-5018)
- **History rewrite:** stripped HAR files containing PII from both repos, including 16 version tags.

### Changed

- **Private repo migrated to PRIMARY CI gate** with branch-protection ruleset (9 required checks); public CI slimmed to a 6-check smoke set. (INF-5017)
- **Cross-platform installer smoke matrix** (Ubuntu / Windows / macOS) added to private CI — caught a real macOS arm64 `greenlet` regression on first run. (INF-5016)

### Removed

- **Bulk branch cleanup:** 19 stale branches deleted per repo (Dependabot and abandoned dev branches).

## [1.1.9.4] — 2026-04-28

### Changed

- **Frontend dependency train.** Bumped `cryptography` to 47 and `numpy` to 2.2.6 (with the summarization library verified against the new numpy). Vite 8 was attempted and reverted (see [1.2.0] notes).

### Fixed

- **Linux installer:** `Path.relative_to` `ValueError` in `display_elevation_guide`.

## [1.1.9.3] and earlier

Earlier release notes are not archived in this changelog. See the public repo Releases page (`https://github.com/giljoai/GiljoAI_MCP/releases`) and the git history for prior version detail.

---

[Unreleased]: https://github.com/giljoai/GiljoAI_MCP/compare/v1.2.0...dev/v1.2.0
[1.2.0]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.2.0
[1.1.9.5]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.1.9.5
[1.1.9.4]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.1.9.4
