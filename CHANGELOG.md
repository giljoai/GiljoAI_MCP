# Changelog

All notable changes to this project are recorded here. This changelog follows the [Keep a Changelog](https://keepachangelog.com/) convention — entries are grouped by change type (Added / Changed / Fixed / Removed / Security). Versions follow `MAJOR.MINOR.PATCH[.HOTFIX]` and tags live on the public repository (`giljoai/GiljoAI_MCP`).

## [2.0.1] — 2026-07-15

### Security

- **Session-sensitive account fields now require a live browser session.** Email, password, and recovery-PIN changes (and API-key minting) can no longer be driven by an API key alone — they demand the stronger login context.
- **Cross-tenant hardening pass.** WebSocket connections are no longer discoverable across tenants, task references are verified to belong to your tenant before use, and hosted SaaS pins the Host header against origin spoofing.
- **Log and telemetry hygiene.** Lifecycle tokens no longer appear in access logs; error reporting scrubs transactions, query strings, and local variables; and token masking gained a sanitize barrier that closes the remaining public CodeQL log-injection findings.
- **Password checks fail closed** if the hashing backend misbehaves, instead of falling through.
- **CI security-tooling floors raised** — semgrep ≥1.169, pip-audit ≥2.10.

### Changed

- **Backups and exports are now schema-driven.** Account backups, checkpoints, and the GDPR data export derive their coverage automatically from the database schema — new features are captured in backups by construction, and a CI guard fails the build if any table is ever neither captured nor deliberately excluded. Backup files are version-stamped, and older backup files restore cleanly.
- **Message Hub tabs renamed:** "Project Comms" is now **Project threads** and "Town Square" is now **General threads**.
- **Dependency refresh:** FastAPI 0.139, MCP SDK 1.28, Vite 8.1.4, Vuetify 4.1.5, dompurify, marked, eslint, prettier, Sentry SDKs, and js-yaml 5.

### Fixed

- **Account restore could fail or silently drop Message Hub data.** Backups now capture hub threads, participants, and read state; restores of current accounts work again, and older backup files restore with every message kept.
- **The "Messages Waiting" badge is back on the implementation page** — lost in the Message Hub migration — and now updates live as agents receive and read messages.
- **Signed-in sessions no longer hang after a failed token refresh**; all queued requests settle cleanly and you land on the login page.
- **Project closeout could deadlock** when an orchestrator was never staged; force-close now frees it, and all-complete states route to closeout.
- **MCP tool errors fixed:** `list_tasks` with `due_before`, `update_task` with `due_date`, `get_context` with a string depth, and password-reset flows during partial test runs no longer return internal errors.
- **Passwords longer than 72 bytes are rejected with a clear message** instead of a server error.
- **The Admin/Owner badge no longer displays on hosted SaaS** (meaningless on single-user accounts).
- **The frontend test suite runs clean on Windows checkouts under Node 24.**

## [2.0.0.2] — 2026-07-14

### Security

- **Log-forging protection completed across the backend.** Every place where user- or agent-supplied text reaches a log line now strips newline and control characters, so nobody can forge fake log entries. This finishes a convention already present in about half the codebase and closes the CodeQL log-injection findings from the public security audit.
- **The public health endpoint no longer reveals internal error details.** During a database or cache outage, anonymous callers of `/health` now see a generic status; full diagnostic detail moved to the server logs and the authenticated system-status endpoint.
- **Startup lock file is now readable by its owner only**, preventing other local users on a shared machine from interfering with startup coordination.

### Fixed

- **Vision-document import tuned for accuracy.** Rewritten extraction prompting and roundtrip fixes make importing a vision document produce cleaner, more faithful results.
- **Vision-analysis wizard no longer gets stuck on "Analyzing".** A polling fallback and a hardened completion path keep the wizard moving even if a realtime update is missed.
- **Vision analysis now fills in the Codebase Folder automatically** when it can determine the project path, with a user-visible way to skip it.
- **Quieter dev server output.** Dropped a harmless "config.yaml not found" log line that appeared on every normal start.

### Removed

- **Operator-only dev tools no longer ship in Community Edition.** The `dev_tools/` utilities (internal control panel and reset scripts) were operator tooling, not product features.

## [2.0.0.1] — 2026-07-13

### Fixed

- **Installer no longer fails on non-UTF-8 Windows systems.** The generated `.env` template contained typographic characters that, on machines using a legacy locale (e.g. Windows-1252), were written as bytes the installer could not read back — the very first setup step crashed with a decode error. All installer-generated files are now written explicitly as UTF-8 and the `.env` template is pure ASCII, so installs behave identically on every locale.

## [2.0.0] — 2026-07-13

### Added

- **Chain projects — link projects and run them back to back.** Select several projects, link them into a chain with a shared chain mission, and a dedicated conductor stages each one, launches it, watches progress, and advances to the next as each completes. Per-project review checkpoints and a firm human-in-the-loop halt before implementation keep you in control, and the Jobs view follows the whole run live.
- **Work from chat-based AI tools and web coding agents — not just terminal CLIs.** The server now identifies the connected AI tool on every connection and adapts its instructions to what that tool can actually do (terminals, file access, subagents); web coding agents can hand work across pull requests, and setup gained presets for Antigravity, Codex, and generic MCP clients.
- **Message Hub — a built-in messaging center for you and your agents.** Conversation threads bind to projects and jobs, agents post under their own identity with user and agent messages rendered distinctly, and the Jobs view opens each job's thread directly. Agent coordination now flows through server threads instead of local handoff files.
- **Sign in with Google or GitHub.** New Solo accounts can sign up and log in with a Google or GitHub account — no password to remember. Existing password accounts can connect a provider from **Settings → Connected Accounts**, and a provider-linked account can add a password at any time.
- **Fully self-service Solo subscriptions (SaaS).** Subscribe monthly or yearly from the dashboard through a secure embedded checkout, switch plans, cancel or resume, and open your billing portal for invoices and receipts; payment failures and cancellations now trigger clear lifecycle emails. Signup records your acceptance of the Terms, and you are asked to re-accept when they materially change.
- **Roadmap pane.** A dedicated view that keeps upcoming work ordered — agents maintain it as they plan, you can edit and reorder entries, and the Projects list can sort in roadmap order.
- **Search your 360 memory.** A new Memory browser with full-text search across cross-session learnings, plus a `search_memory` tool so agents can look up prior learnings mid-run.
- **Trash and recover.** Deleted threads, tasks, vision documents, and agent templates now land in a recoverable trash with scheduled purge instead of vanishing. Separately, hiding a project is now called **Archived**, and search can find archived projects and tasks.
- **Account backups and restore (SaaS).** Nightly encrypted snapshots to durable storage, plus Danger Zone controls to download your latest backup, create a restore point on demand, or request a restore — and restores preserve your API keys so integrations keep working.
- **Complete, automated account deletion (SaaS).** Deleting your account now auto-cancels an active subscription, offers an immediate-deletion option, and purges everything including backups; dormant deletion requests get a warning at 11 months and are fully removed after a year, with hash-verified deletion receipts retained for compliance.
- **Public status page (SaaS).** Service health and incident history are now published on a public status page linked from the app footer.
- **New agent tools and supervision controls.** Agents gained `stage_project`, `implement_project`, `launch_implementation`, `start_chain_run`, `diagnose_project_state`, and `search_memory`; server-enforced tool profiles (core/standard/full) bound what each connection may call. On the dashboard, you can now request automatic agent check-ins on an interval and tune the silence threshold in Settings.
- **Manage your own credentials.** Change your password and recovery PIN from your profile (recovery PIN: Community Edition), and hosted accounts can change their sign-in email with confirm-before-switch verification and notifications to both addresses (SaaS).

### Changed

- **Execution modes simplified.** Six overlapping execution modes collapsed to two, with the right harness resolved automatically at runtime from the connected tool and shown as a read-only "detected" chip. Headless running is now an explicit account-level toggle, implementation launches default to a human-in-the-loop gate, and the dashboard auto-follows a headless run live in the Jobs pane.
- **Product creation is AI-first.** Attach one or more vision documents and run vision analysis to fill in the product profile — analysis is now the default path (with a create-blank escape), documents are stored in the database instead of by file path, and completing analysis is what unlocks staging.
- **Simpler self-hosted install — Community Edition now runs over plain HTTP.** The installer no longer asks you to choose HTTP vs HTTPS or set up certificates; localhost and LAN installs serve plain HTTP out of the box. HTTPS is now an optional, post-install upgrade you turn on in **Settings → Network** by providing your own certificate. A public/WAN install prints a clear cleartext warning instead of forcing a certificate.
- **Faster dashboard and API across the board.** Project lists paginate, filter, search, and sort in SQL; the frontend dedupes requests and pauses background polling in hidden tabs; hot backend paths (auth hashing, email sends, exports) moved off the event loop; repeated-query hotspots were batched and indexed; and connected AI tools receive much smaller instruction payloads per call. Long sessions and large workspaces feel it most.
- **Refreshed look and feel.** The UI moved to Vuetify 4 / Material Design 3, the four top banners unified onto one accessible style, agent colors are driven by design tokens everywhere, Tools → Connect and onboarding were redesigned, and the Projects list gained a compact view.
- **Connecting AI tools is clearer.** Guided per-tool connect flows with copy-ready snippets, an OAuth-first connect step during first run on hosted accounts (SaaS), a streamlined API-key flow for Community Edition, working CLI OAuth sign-in via loopback redirect, and stay-signed-in through rotating refresh tokens.
- **The notification bell is now database-backed.** Notifications persist across sessions and devices, project notifications deep-link to the project, and previously scattered banners consolidated onto one notification service — including API-key expiry reminders.
- **The in-app user guide covers the whole product.** Expanded to full end-user coverage and made edition-aware, so Community Edition and hosted users each see the chapters that apply to them.
- **Network settings show the real server address.** The Admin → Network tab lists the actual IP(s) and port your server responds on, with a one-step bring-your-own-certificate flow; the certificate how-to moved into the in-app guide.
- **Minimum PostgreSQL is now 16 (18 recommended) (Community Edition).** Installs on PostgreSQL versions 14 or 15 should upgrade the database server before updating.
- **Projects can be marked superseded** with a link to their successor, keeping history navigable without deleting anything.

### Fixed

- **Live updates are far more resilient.** Fixed a WebSocket reconnect storm and a cold-start realtime outage, added heartbeat supervision and per-tenant fan-out isolation, reconnect now re-arms when your machine wakes or comes back online, and the MCP transport was hardened against repeated-request storms and oversized payloads from connected clients.
- **Dashboard navigation no longer stalls,** and after a server update the app recovers from stale cached assets on its own instead of erroring until a hard refresh.
- **Serial numbers stopped jumping to five digits.** The counter no longer counts soft-deleted rows, and historical oversized serials are tolerated instead of erroring.
- **Stuck projects can always be recovered.** Deactivate now resets a never-launched orchestrator, unstage/re-stage releases the execution-mode lock and clears the stale mission, promoting a task to a project no longer deactivates your active project, and refreshing agent templates preserves your edits (reset restores the shipped defaults).
- **Installer and first-run hardening on every platform.** Re-running the installer is now safe and idempotent with a new `--repair` mode and unattended option; installs extract atomically and pin dependencies to the shipped versions; Windows fixes cover PATH refresh and store-alias/prompt hangs; Linux waits out apt locks and guards WSL paths (including browser auto-open); fresh-install defects in taxonomy seeding and first-admin creation were fixed; and the Cookie Domain Whitelist setting is now actually enforced.
- **The landing page's "Forgot your password?" link works again (SaaS).** It previously dead-ended instead of opening the reset flow.

### Security

- **Credential changes now end live sessions.** Changing or resetting a password — including the first-login password set — evicts all live sessions and refresh tokens, deactivating an account closes its WebSockets immediately, a server-side revocation epoch supports forced logout, and access tokens rotate on refresh.
- **Stronger sign-in and credential protection.** Per-account login lockout, failed-auth throttling on the API-key and WebSocket paths, a higher password-hashing cost, and uniform auth errors that do not reveal whether an account exists. New API keys use a stronger storage format, the key-count cap was removed, and expiring keys trigger bell reminders.
- **Tenant isolation enforced in depth.** Bulk updates and deletes now pass through the tenant guard automatically, tenant-scoped models are registration-checked at boot and fail loudly if wiring is missing, MCP tool authorization fails closed, and a permanent cross-tenant isolation test gate runs in CI.
- **Boundary validation and rate limiting hardened.** Agent-supplied input is validated at the MCP boundary with sanitized error responses, structured JSONB payloads are validated at every write, the rate limiter is atomic under concurrency and proxy-aware, and OAuth token-endpoint errors now conform to RFC 6749.
- **Dependency refresh across the stack.** Backend framework pins cleared known CVEs, all high-severity npm advisories were resolved, and routine frontend and backend dependency bumps landed throughout the window.

### Removed

- **Built-in statistical summarizer removed.** Document and memory summaries are now produced by your connected AI agent instead of a bundled algorithm — better summaries and a lighter install (the sumy/NLTK dependency chain is gone).
- **Separate demo edition retired.** Its landing page and flows were folded into the hosted Solo tier; the only editions are Community Edition and hosted SaaS.
- **Built-in certificate generation removed from the installer.** GiljoAI no longer installs mkcert or generates certificates during setup — bring your own (a public CA, your organization's CA, or a local tool such as mkcert) and add it in Settings → Network. This removes the install-time certificate step, the LAN/WAN HTTPS prompt, and the automatic certificate refresh on IP changes.
- **Dead weight deleted.** Dozens of unused REST routes, three low-value MCP tools, retired setup-wizard remnants, and the old OpenClaw preset (superseded by the Antigravity/Codex/generic MCP presets) were removed.

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

- **Connect Claude.ai and ChatGPT to your GiljoAI workspace.** Hosted GiljoAI now supports Claude.ai's Custom Connector and ChatGPT's MCP connector. Sign in once through your AI tool of choice and it can orchestrate full development teams through your GiljoAI account — staging projects, launching specialist agents, reading status, and pausing for your input. Built on OAuth 2.1 with full MCP specification conformance.
- **Claude Desktop integration for self-hosted installations.** Self-hosted and localhost installations can be wired to Claude Desktop directly via JSON configuration — no public DNS or HTTPS exposure required. The Setup Wizard generates copy-paste-ready snippets for every supported AI tool.
- **Agents can pause for explicit user approval mid-job.** Long-running specialist agents can now request explicit decisions — "should I proceed with this destructive migration?", "which of these three branches should I implement?" — and the dashboard surfaces the request with the agent's reasoning and clear option buttons. Agents auto-resume the instant you decide.
- **Task management at parity with projects.** Tasks now have the same agent-tool surface as projects: create, update, list, complete, and fetch context through the same agent-friendly tools.
- **Cleaner dashboard payloads.** Project lists now support four projection modes — `triage`, `planning`, `audit`, `forensic`. Default mode cuts payload size by roughly 60% for routine status checks while still surfacing what the user needs at a glance.
- **Optional error tracking.** Self-hosted deployments can opt in to Sentry-based error telemetry by setting a single environment variable. Personally identifying information is scrubbed automatically; team scoping is preserved.
- **Server capability discovery.** A new well-known endpoint declares which MCP specification versions GiljoAI supports plus high-level capability flags. AI tools can negotiate features automatically without out-of-band coordination.
- **Privacy and Terms pages on every install.** First-party privacy policy and terms-of-service pages now ship with every installation, routed cleanly through the Setup Wizard. Improved screen-reader announcements on critical dialogs.

### Changed

- **License switched to Elastic License 2.0.** GiljoAI's source-available license is now ELv2, replacing the prior GiljoAI Community License. ELv2 is a well-established license recognized by legal teams worldwide: it permits internal and commercial use, and only restricts managed-service redistribution and license-key tampering.
- **Faster, calmer dashboard for long sessions.** Background polling was tuned to refresh every 30 seconds (down from every 5) where it was previously running too aggressively. Active operations — job status, agent transitions — still update in real time via WebSocket.
- **Agent handoff prose refreshed.** Built-in agent instructions for handing off to humans are now clearer, more delegated-authority oriented, and aligned with the new approval primitive instead of legacy "blocked" semantics.

### Fixed

- **Toast notification clarity.** Copy-prompt confirmations now describe what the prompt will *do* once pasted — e.g., "Implementation prompt copied. 5 jobs ready to launch." — instead of generic "copied to clipboard" boilerplate.
- **Notification duration slider now controls timeout.** The Settings → Notifications duration slider was wired to the store but had no effect on actual toast timing. Fixed; the slider now reflects your preference for every toast type.
- **Auto-fill next serial number in Create Project dialog.** The serial field now suggests the next available number for the chosen project type instead of leaving it blank.
- **Migration runner no longer stamps backward on restart.** The startup migration check was previously moving the database version pointer backward under certain conditions, causing migrations to replay against already-applied schema and crash. The check now correctly recognizes the modern revision set.
- **Production restarts no longer rewrite the lockfile.** The startup script now uses a read-only npm install path so `package-lock.json` is no longer silently mutated on restart. Prevents lockfile drift on test-server restarts.

### Security

- **Hardened authentication and revocation pathways.** Token lookups and refresh flows now bind on additional identifiers at the query layer, providing defense-in-depth on top of existing tenant isolation.
- **Per-session token revocation.** Issued access tokens can be revoked individually without invalidating the broader user session; revocation propagates to all protected resources within seconds.
- **Stricter audience binding on agent tokens. ⚠ BREAKING.** Tokens presented to the agent-tool boundary must now carry an explicit audience claim. Legacy compatibility for unbound tokens has been removed. Clients holding older tokens must re-authenticate to obtain a properly bound replacement.
- **Improved leak prevention for public-facing files.** New build-time check blocks accidental exposure of internal-network references in public-bound documentation.

### Removed

- **Legacy "blocked" status as a human-in-the-loop signal.** The old pattern of agents setting their own status to "blocked" to request user input is replaced by the proper approval primitive. Self-set "blocked" status is now reserved for genuine error conditions only.

## [1.2.4] — 2026-05-03

### Added

- **Pluggable SMTP email provider.** New `EMAIL_BACKEND` config switch routes transactional email through any SMTP server.

### Changed

- **BREAKING — minimum Python raised to 3.12.** `pyproject.toml` `requires-python` bumped from `>=3.10` to `>=3.12`. `pip install` on pre-3.12 Python now fails with a `requires-python` resolver error. CI, installer scripts, and docs already required 3.12; this aligns the wheel-build constraint with the existing floor.
- **Ruff lint target raised to py312.** Lint sweep auto-fixed PEP 604 unions, walrus opportunities, datetime-aware constructions, and ~60 other modernization sites; remaining warnings either fixed manually or carry justified `# noqa` markers.
- **CI restructured into fast and slow tiers.** Fast checks (lint, secret scan, AI-signature block, pytest, frontend lint+build, vitest) run on every push and PR; the slower installer-integrity matrix runs only on tag pushes matching `v*`.
- **Project tracking migrated into the MCP server.** New work goes through the `create_project` and `write_360_memory` MCP tools rather than the legacy markdown handover files.

### Fixed

- **Dashboard project list returned stale status values.** The `list_projects` tool now correctly filters across all six project statuses, and a project that changes status reflects in the list within one poll cycle. Regression tests added.
- **`create_project` MCP tool: type validation restored.** Unknown `project_type` values now raise `ValidationError` with the structured `valid_types` list (abbreviation, label, color) in the error context. Omitted `project_type` returns the same hint in the success response.
- **System-update banner copy.** Bell-icon notification dropped the redundant "re-run `/giljo_setup`" line (the skills-drift banner already covers that). Both the bell notification and the dashboard update banner now say "restart your server" instead of the older `python update.py` wording.

### Removed

- **Deprecated `deploy_lan_windows.ps1` script.** Pre-unified-installer artifact (2025-10) fully obsoleted by the current `install.ps1` flow.

## [1.2.3] — 2026-05-03

### Security

- **Removed default password fallback in user creation.** `UserService.create_user` no longer silently substitutes a literal default when no password is supplied. The admin endpoint now forwards the user-provided password, and the service treats the absence of a password as an explicit error.

### Changed

- **Skills-version drift banner simplified.** Replaces the previous per-user tracking model. The earlier design tracked three pieces of state for what is fundamentally one comparison: "did the bundled `SKILLS_VERSION` move past the version we last announced?" The new endpoint `/api/notifications/check-skills-version` returns `{current, announced, drift_detected, message}` with no per-user state. Per-version dismissal continues via localStorage. Banner switched from informational blue to brand-yellow warning for better contrast and semantic correctness. The 30-day post-login reminder loop was dropped. Edition-aware copy: CE says "run `/giljo_setup` then `git pull`"; demo/saas says just "run `/giljo_setup`".

## [1.2.2] — 2026-05-01

### Added

- **Project status as a typed enum.** Six statuses (`inactive`, `active`, `completed`, `cancelled`, `terminated`, `deleted`) now live in one place — no more drift between backend services, frontend stores, and database CHECK constraints.
- **New REST endpoint `GET /api/v1/project-statuses/`** exposes the canonical list with labels, color tokens, and lifecycle flags. The frontend reads from this, never from a hardcoded array.
- **Version-consistency check (`scripts/check_version_consistency.py`).** `VERSION` is the single source of truth; `pyproject.toml`, `frontend/package.json`, `package-lock.json`, `__init__.py` fallback, and the latest `CHANGELOG.md` entry must all match. Wired into pre-commit and the release pipeline.

### Changed

- **Installers hardened on every supported path.** All four install paths now work on stock systems with no manual prep: Windows `install.ps1` (verified on stock PowerShell 5.1 + Windows 11), Windows `install.py` direct (Node.js auto-installs via `winget` when missing), Linux `install.sh` (verified on stock Ubuntu / Debian / WSL), Linux `install.py` direct (`python3-venv` detection via an actual `ensurepip` probe). The "please restart your shell" banner now only fires on Windows where it is actually needed.
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
- **Boundary `gitleaks` gate added to the release pipeline** — last-chance scan before any push.
- **History rewrite:** stripped HAR files containing PII, including 16 version tags.

### Changed

- **Branch-protection ruleset expanded** with required-check coverage on every push and PR.
- **Cross-platform installer smoke matrix** (Ubuntu / Windows / macOS) added to CI — caught a real macOS arm64 `greenlet` regression on first run.

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

[2.0.1]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v2.0.1
[2.0.0.2]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v2.0.0.2
[2.0.0.1]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v2.0.0.1
[2.0.0]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v2.0.0
[1.3.0]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.3.0
[1.2.5]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.2.5
[1.2.4]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.2.4
[1.2.3]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.2.3
[1.2.2]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.2.2
[1.2.1]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.2.1
[1.2.0]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.2.0
[1.1.9.5]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.1.9.5
[1.1.9.4]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.1.9.4
