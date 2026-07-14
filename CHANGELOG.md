# Changelog

All notable changes to this project are recorded here. This changelog follows the [Keep a Changelog](https://keepachangelog.com/) convention — entries are grouped by change type (Added / Changed / Fixed / Removed / Security). Internal project IDs appear in parentheses for traceability. Versions follow `MAJOR.MINOR.PATCH[.HOTFIX]` and tags live on the public repository (`giljoai/GiljoAI_MCP`).

## [2.0.0.1] — 2026-07-13

### Fixed

- **Installer no longer fails on non-UTF-8 Windows systems.** The generated `.env` template contained typographic characters that, on machines using a legacy locale (e.g. Windows-1252), were written as bytes the installer could not read back — the very first setup step crashed with a decode error. All installer-generated files are now written explicitly as UTF-8 and the `.env` template is pure ASCII, so installs behave identically on every locale. (INF-9159)

## [2.0.0] — 2026-07-13

### Added

- **Sign in with Google or GitHub.** New Solo accounts can sign up and log in with a Google or GitHub account — no password to remember. Existing password accounts can connect a provider from **Settings → Connected Accounts**, and a provider-linked account can add a password at any time. (BE-1001–BE-1006)

### Changed

- **Simpler self-hosted install — Community Edition now runs over plain HTTP.** The installer no longer asks you to choose HTTP vs HTTPS or set up certificates; localhost and LAN installs serve plain HTTP out of the box. HTTPS is now an optional, post-install upgrade you turn on in **Settings → Network** by providing your own certificate. A public/WAN install prints a clear cleartext warning instead of forcing a certificate. (INF-6241)
- **Network settings show the real server address.** The Admin → Network tab lists the actual IP(s) and port your server responds on, with a one-step bring-your-own-certificate flow; the certificate how-to moved into the in-app guide. (FE-6239)

### Removed

- **Built-in certificate generation removed from the installer.** GiljoAI no longer installs mkcert or generates certificates during setup — bring your own (a public CA, your organization's CA, or a local tool such as mkcert) and add it in Settings → Network. This removes the install-time certificate step, the LAN/WAN HTTPS prompt, and the automatic certificate refresh on IP changes. (INF-6241)

## [1.3.0] — 2026-05-20

### Added

- **Working-time on every agent job.** See at a glance how long each agent has been actively working — live, on the agent card.
- **Native spellcheck across the dashboard.** Project descriptions, missions, and message composition now use your browser's spellcheck.
- **Roomier 360-memory summaries.** Per-entry summary cap raised from 500 to 1,500 characters so longer cross-session learnings survive intact.
- **Customize-prompt panel reordered.** The customize box now sits above the copy button, and your custom text is included in what gets copied.

### Changed

- **Cleaner staging-to-implementation handoff.** When staging finishes, your project sits in a clear *Waiting* state until you click Implement — no flicker, no stale labels, no premature closeout prompts. The implementation kicks off the instant you decide, and the dashboard reflects every transition live.
- **Smoother orchestrator behavior across phases.** One orchestrator per project, transitioning cleanly Working → Waiting → Working → Complete. Replaces an earlier scheme that left phantom rows and confusing statuses.
- **Sharper AI-agent integration.** AI tools connected through MCP get clearer guidance, lighter payloads on routine calls, and cache-aware reads. Day-to-day result: faster, less chatty agent interactions.
- **Projects sorted newest-first by default.** What you most recently touched leads the list.
- **Correct license badge.** README now correctly reads Elastic License 2.0.

### Fixed

- **Closeout button now appears where it should** on implementation-phase projects.
- **Live message-audit modal.** Statuses update in real time instead of freezing at the moment the modal was opened.
- **Cancel popup copy** no longer misleads about hidden projects.
- **Project-open clicks** only fire on the Serial badge, not stray elsewhere on the row.
- **Hidden tasks** no longer leak into the Tasks view.
- **Date filters on project lookups** stopped crashing on certain time-zone edge cases.
- **Setup wizard API-key copy hint** describes what the key is actually for.
- **Codex setup template** escapes special characters safely.
- **Quieter server log.** Heartbeat noise no longer pollutes stdout.
- **Closeout spinner stays visible** during normal memory-write retries instead of flashing transient errors.

### Security

- **Frontend dependencies refreshed:** `dompurify`, `marked`, `axios`, `@sentry/vite-plugin`.
- **Python dependencies refreshed:** `sentry-sdk`, `resend`.

### Removed

- **Legacy `action_required` deprecation fully retired.** Agents that still emit the old tag now get a clear validation error instead of a silent warning.
- **A handful of unused columns and obsolete tests** pruned during the orchestrator refactor.

## [1.2.5] — 2026-05-10

### Added

- **Connect Claude.ai and ChatGPT to your GiljoAI workspace.** Hosted GiljoAI now supports Claude.ai's Custom Connector and ChatGPT's MCP connector. Sign in once through your AI tool of choice and it can orchestrate full development teams through your GiljoAI account — staging projects, launching specialist agents, reading status, and pausing for your input. Built on OAuth 2.1 with full MCP specification conformance. (API-0021, API-0022)
- **Claude Desktop integration for self-hosted installations.** Self-hosted and localhost installations can be wired to Claude Desktop directly via JSON configuration — no public DNS or HTTPS exposure required. The Setup Wizard generates copy-paste-ready snippets for every supported AI tool. (FE-5044)
- **Agents can pause for explicit user approval mid-job.** Long-running specialist agents can now request explicit decisions — "should I proceed with this destructive migration?", "which of these three branches should I implement?" — and the dashboard surfaces the request with the agent's reasoning and clear option buttons. Agents auto-resume the instant you decide. (BE-5029, BE-5059)
- **Task management at parity with projects.** Tasks now have the same agent-tool surface as projects: create, update, list, complete, and fetch context through the same agent-friendly tools. (BE-5053)
- **Cleaner dashboard payloads.** Project lists now support four projection modes — `triage`, `planning`, `audit`, `forensic`. Default mode cuts payload size by roughly 60% for routine status checks while still surfacing what the user needs at a glance. (BE-5042, BE-5048)
- **Optional error tracking.** Self-hosted deployments can opt in to Sentry-based error telemetry by setting a single environment variable. Personally identifying information is scrubbed automatically; team scoping is preserved. (INF-5063)
- **Server capability discovery.** A new well-known endpoint declares which MCP specification versions GiljoAI supports plus high-level capability flags. AI tools can negotiate features automatically without out-of-band coordination. (API-0021h)
- **Privacy and Terms pages on every install.** First-party privacy policy and terms-of-service pages now ship with every installation, routed cleanly through the Setup Wizard. Improved screen-reader announcements on critical dialogs. (INF-5062)

### Changed

- **License switched to Elastic License 2.0.** GiljoAI's source-available license is now ELv2, replacing the prior GiljoAI Community License. ELv2 is a well-established license recognized by legal teams worldwide: it permits internal and commercial use, and only restricts managed-service redistribution and license-key tampering.
- **Faster, calmer dashboard for long sessions.** Background polling was tuned to refresh every 30 seconds (down from every 5) where it was previously running too aggressively. Active operations — job status, agent transitions — still update in real time via WebSocket.
- **Agent handoff prose refreshed.** Built-in agent instructions for handing off to humans are now clearer, more delegated-authority oriented, and aligned with the new approval primitive instead of legacy "blocked" semantics.

### Fixed

- **Toast notification clarity.** Copy-prompt confirmations now describe what the prompt will *do* once pasted — e.g., "Implementation prompt copied. 5 jobs ready to launch." — instead of generic "copied to clipboard" boilerplate. (UI-0002)
- **Notification duration slider now controls timeout.** The Settings → Notifications duration slider was wired to the store but had no effect on actual toast timing. Fixed; the slider now reflects your preference for every toast type. (UI-0003)
- **Auto-fill next serial number in Create Project dialog.** The serial field now suggests the next available number for the chosen project type instead of leaving it blank. (UI-0004)
- **Migration runner no longer stamps backward on restart.** The startup migration check was previously moving the database version pointer backward under certain conditions, causing migrations to replay against already-applied schema and crash. The check now correctly recognizes the modern revision set.
- **Production restarts no longer rewrite the lockfile.** The startup script now uses a read-only npm install path so `package-lock.json` is no longer silently mutated on restart. Prevents lockfile drift on test-server restarts.

### Security

- **Hardened authentication and revocation pathways.** Token lookups and refresh flows now bind on additional identifiers at the query layer, providing defense-in-depth on top of existing tenant isolation. (API-0022)
- **Per-session token revocation.** Issued access tokens can be revoked individually without invalidating the broader user session; revocation propagates to all protected resources within seconds. (API-0022)
- **Stricter audience binding on agent tokens. ⚠ BREAKING.** Tokens presented to the agent-tool boundary must now carry an explicit audience claim. Legacy compatibility for unbound tokens has been removed. Clients holding older tokens must re-authenticate to obtain a properly bound replacement. (API-0022)
- **Improved leak prevention for public-facing files.** New build-time check blocks accidental exposure of internal-network references in public-bound documentation.

### Removed

- **Legacy "blocked" status as a human-in-the-loop signal.** The old pattern of agents setting their own status to "blocked" to request user input is replaced by the proper approval primitive. Self-set "blocked" status is now reserved for genuine error conditions only.

## [1.2.4] — 2026-05-03

### Added

- **Pluggable SMTP email provider.** New `EMAIL_BACKEND` config switch routes transactional email through any SMTP server. (INF-5023)

### Changed

- **BREAKING — minimum Python raised to 3.12.** `pyproject.toml` `requires-python` bumped from `>=3.10` to `>=3.12`. `pip install` on pre-3.12 Python now fails with a `requires-python` resolver error. CI, installer scripts, and docs already required 3.12; this aligns the wheel-build constraint with the existing floor. (INF-5022)
- **Ruff lint target raised to py312.** Lint sweep auto-fixed PEP 604 unions, walrus opportunities, datetime-aware constructions, and ~60 other modernization sites; remaining warnings either fixed manually or carry justified `# noqa` markers. (INF-5020)
- **CI restructured into fast and slow tiers.** Fast checks (lint, secret scan, AI-signature block, pytest, frontend lint+build, vitest) run on every push and PR; the slower installer-integrity matrix runs only on tag pushes matching `v*`. (INF-5024)
- **Project tracking migrated into the MCP server.** New work goes through the `create_project` and `write_360_memory` MCP tools rather than the legacy markdown handover files.

### Fixed

- **Dashboard project list returned stale status values.** The `list_projects` tool now correctly filters across all six project statuses, and a project that changes status reflects in the list within one poll cycle. Regression tests added. (IMP-5026)
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

- **Project status as a typed enum.** Six statuses (`inactive`, `active`, `completed`, `cancelled`, `terminated`, `deleted`) now live in one place — no more drift between backend services, frontend stores, and database CHECK constraints. (BE-5039)
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

- **Multi-layer secrets defense established.** `gitleaks` runs at gitignore, pre-commit, and push-CI stages with a defensive working-tree scan on top.
- **Boundary `gitleaks` gate added to the release pipeline** — last-chance scan before any push. (INF-5018)
- **History rewrite:** stripped HAR files containing PII, including 16 version tags.

### Changed

- **Branch-protection ruleset expanded** with required-check coverage on every push and PR. (INF-5017)
- **Cross-platform installer smoke matrix** (Ubuntu / Windows / macOS) added to CI — caught a real macOS arm64 `greenlet` regression on first run. (INF-5016)

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
