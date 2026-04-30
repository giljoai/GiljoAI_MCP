# Changelog

All notable changes to this project are recorded here. Versions follow `MAJOR.MINOR.PATCH[.HOTFIX]` and tags live on the public repository (`giljoai/GiljoAI_MCP`).

## [Unreleased]

_No pending work yet — v1.2.1+ entries will land here._

## [1.2.0] — 2026-04-29

The first minor-version release since the v1.1 line, consolidating six weeks of installer hardening, dependency cleanup, and dashboard polish into a single public cut. If you've been running v1.1.9.5, this upgrade is recommended — especially on Windows.

### Installers, fixed for real

- **Windows install now works on stock PowerShell 5.1.** Earlier Windows installs could fail with cryptic parser errors before reaching the wizard; `install.ps1` is now ASCII-clean and parses correctly under every PowerShell version that ships with Windows 10 / 11.
- **macOS Apple Silicon installs are more resilient.** A new floor on the `greenlet` dependency plus an explicit fail-fast guard prevents the long silent hangs that some early Apple Silicon users saw when binary wheels weren't yet published for a new Python release.
- **Linux first-run no longer crashes** on the elevation-guidance step. A path edge case that produced `ValueError` on stock Ubuntu has been fixed.

### Dashboard polish

- **"Tools → Connect"** replaces the old "Settings → Integrations" naming throughout the dashboard. Same feature, clearer mental model: one place to connect Claude Code, Cursor, and other tooling.
- **Welcome wizard** now offers a starter-template card on step 4 so new users can get to a working agent setup with a single click.

### Agent skills bundle (v1.1.11)

- **`/gil_add` gained a Read mode**, so you can pull a project's context or status by alias without opening the dashboard. Add mode is unchanged.
- **Faster, cheaper agent context fetches.** Agents now fetch only the context they need rather than pulling the full bundle every time — meaningfully fewer tokens per multi-step run.
- **Cleaner predecessor handling.** Multi-agent handovers now auto-detect whether you're handing off or being handed to, removing a class of "wrong context" agent runs.
- The dashboard will show a "skills bundle out of date" banner when you load v1.2.0 for the first time — that's expected. Run `giljo_setup` (or pull the latest skills via the dashboard) to upgrade your local CLI skills to v1.1.11.

### Under the hood

- Frontend toolchain is back on a stable, broadly-tested vite line. Vite 8 was briefly trialed but pulled back when its new bundler stack proved unstable on macOS and Windows under real installer conditions; the upgrade will return once that stack ships a stable 1.0.
- Frontend builds now require Node 22 (matching what most current distributions ship by default).
- Updated dependencies: `vue`, `postcss`, `greenlet` — all routine patch / minor bumps.
- Repository housekeeping: legacy distribution-tarball scripts removed (the hosted installer at `giljo.ai/install.ps1` and `giljo.ai/install.sh` is the only supported install path). Security policy document rewritten to accurately reflect current supported versions.

### Notes for upgraders

- Tagged as `v1.2.0-rc.1` first; promoted to `v1.2.0` after a soak window.
- No database schema changes vs v1.1.9.5. Routine `git pull` + restart is sufficient.
- If you're upgrading from v1.1.9.4 or earlier, you'll also pick up the security-foundation work that landed in v1.1.9.5 (four-layer secrets defense, hardened CI). No action required on your end.

## [1.1.9.5] — 2026-04-29

Security foundation release. Public repo brought from "no protections" to a full four-layer secrets defense in one session.

- Three-layer secrets defense established (gitignore + pre-commit `gitleaks` + push-CI `gitleaks` on private; defensive working-tree `gitleaks` on public)
- Boundary `gitleaks` gate added to `export_ce.sh` and `export_ce_dev.sh` (INF-5018) — last-chance scan after SaaS-strip and before push to public
- Private repo migrated to PRIMARY CI gate with branch-protection ruleset (9 required checks); public CI slimmed to a 6-check smoke set (INF-5017)
- Cross-platform installer smoke matrix (Ubuntu / Windows / macOS) added to private CI (INF-5016) — caught a real macOS arm64 `greenlet` regression on first run
- History rewrite: stripped HAR files (containing PII) from both repos including 16 version tags
- Bulk cleanup: 19 stale branches deleted per repo (Dependabot + abandoned dev branches)

## [1.1.9.4] — 2026-04-28

- Frontend deps train: `cryptography` 47, `numpy` 2.2.6 (with `sumy` LSA verified), `vite` 8 *(reverted in [Unreleased] — see above)*
- Linux installer fix: `Path.relative_to` `ValueError` in `display_elevation_guide`

## [1.1.9.3] and earlier

Earlier release notes are not archived in this changelog. See the public repo Releases page (`https://github.com/giljoai/GiljoAI_MCP/releases`) and the git history for prior version detail.

---

[Unreleased]: https://github.com/giljoai/GiljoAI_MCP/compare/v1.2.0...dev/v1.2.0
[1.2.0]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.2.0
[1.1.9.5]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.1.9.5
[1.1.9.4]: https://github.com/giljoai/GiljoAI_MCP/releases/tag/v1.1.9.4
