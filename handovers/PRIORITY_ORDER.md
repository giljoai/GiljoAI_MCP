# Community Edition Launch - Priority Order

Last updated: 2026-03-07

## Completed (This Session)

| ID | Title | Status |
|----|-------|--------|
| 0250 | HTTPS Enablement | Done (`c5443b7d`, `86aa4106`) - needs archiving |
| 0083 | Slash Command Harmonization | Closed - superseded (`133cc473`) |
| 0325 | Tenant Isolation Surgical Fix | Done (Feb 2026) |
| 0765a-s | Perfect Score Sprint (full series) | Done - catalogue needs updating |
| -- | Licensing, branding, Community Edition enforcement | Done (`9dd6e9e8`, `bf2d0ded`, `c3ba7a4a`) |

## Active Priority Queue

| # | ID | Title | Effort | Why |
|---|-----|-------|--------|-----|
| 1 | 0732 | Release Packaging (Docker, GitHub templates, README screenshots, CHANGELOG) | 3-5 hrs | Launch blocker. First impressions. Docker = 2-minute setup for new users. |
| 2 | 0409 | Unified Client Quick Setup (start with Claude Code only) | 4-6 hrs | Reduces onboarding from 6+ steps to copy-paste. Ship Claude path first, Codex/Gemini later. |
| 3 | 0731 | Legacy Code Removal (scoped fresh scan) | 8-12 hrs | Code health before going public. Remove dead code, Ollama refs, stale compat layers. Line refs are stale -- needs re-scan. |
| 4 | 9999 | One-Liner Installation System | 8-12 hrs | curl/bash + irm/iex install scripts. Polish for marketing. Can ship after Docker. |

## Deferred (Not Blocking Launch)

| ID | Title | Effort | Reason |
|----|-------|--------|--------|
| TODO_vision | Vision Summarizer LLM Upgrade | 16-24 hrs | Current Sumy works. Quality improvement, not functional. |
| 0284 | get_available_agents Enhancement | 2-4 hrs | Developer polish. Parked since Dec 2025. |
| 1014 | Security Event Auditing | 8 hrs | Enterprise compliance. No requirement yet. Correctly deferred. |

## Housekeeping (Do Anytime)

- [ ] Archive 0250 to `completed/0250_https_enablement_optional-C.md`
- [ ] Update HANDOVER_CATALOGUE.md: move 0765a-i to completed, mark 0250 done
- [ ] Move reference docs out of root handovers folder to `Reference_docs/`:
  - `TECHNICAL_DEBT_v2.md` (obsolete)
  - `claude_code_agent_teams_integration_review.md`
  - `LOG_ANALYSIS_GUIDE.md`
  - `Agent instructions and where they live.md`
- [ ] Update `handovers/README.md` priority table (currently shows stale 0325/0298)
