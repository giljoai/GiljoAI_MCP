# Community Edition Launch - Priority Order

Last updated: 2026-03-09

## Completed

| ID | Title | Status |
|----|-------|--------|
| 0250 | HTTPS Enablement | Done (`c5443b7d`, `86aa4106`). Archived. |
| 0083 | Slash Command Harmonization | Closed - superseded (`133cc473`) |
| 0325 | Tenant Isolation Surgical Fix | Done (Feb 2026) |
| 0765a-s | Perfect Score Sprint (full series) | Done - 67 commits, 8.35/10 score |
| -- | Licensing, branding, Community Edition enforcement | Done (`9dd6e9e8`, `bf2d0ded`, `c3ba7a4a`) |
| 0732 | CE Release Packaging | Done - CHANGELOG updated, convention violations fixed, requirements.txt aligned |
| 0771 | Edition Isolation Architecture | Done - 10 deliverables, Edition Isolation Guide, SaaS scaffold, pre-commit hook |
| 0731 | Legacy Code Removal | SUPERSEDED - resolved by 0745/0765 sprints |
| 0409 | Unified Client Quick Setup | DEFERRED - all underlying UI components already exist |
| ~~9999~~ | ~~One-Liner Installation System~~ | DELETED - website directs to GitHub; `python startup.py` is the install path |

## CE Launch Status

**All launch-blocking handovers are COMPLETE.** No active work items remain for CE launch.

## Deferred (Post-Launch)

| ID | Title | Effort | Reason |
|----|-------|--------|--------|
| TODO_vision | Vision Summarizer LLM Upgrade | 16-24 hrs | Current Sumy works. Quality improvement, not functional. |
| 1014 | Security Event Auditing | 8 hrs | Enterprise compliance. No requirement yet. |
| 0409 | Unified Client Quick Setup | 2-3 hrs | All UI components exist. Revisit if user feedback indicates friction. |

## Recently Completed (moved from Deferred)

| ID | Title | Completed | Notes |
|----|-------|-----------|-------|
| 0732b | README Screenshots | 2026-03-14 | Screenshots captured manually by user. Archived to `completed/0732b_readme_screenshots-C.md`. |

## Retired

| ID | Title | Reason |
|----|-------|--------|
| 0284 | get_available_agents Enhancement | Architecture evolved past this. Archived. |
| TECHNICAL_DEBT_v2 | Technical Debt Register (Oct 2025) | Deleted 2026-03-09. Replaced by `techdebt_march_2026.md`. |

## Housekeeping Done (2026-03-09)

- [x] Archive 0250 to `completed/0250_https_enablement_optional-C.md`
- [x] Archive 0732 to `completed/0732_release_packaging_sprint-C.md`
- [x] Archive 0771 to `completed/0771_EDITION_ISOLATION_ARCHITECTURE-C.md`
- [x] Archive 0284 to `completed/0284_address_get_available_agents-DEFERRED-C.md`
- [x] Archive 0409 to `completed/0409_unified_client_quick_setup-DEFERRED-C.md`
- [x] Delete `claude_code_agent_teams_integration_review.md` (one-off analysis, no future reference value)
- [x] Move `Handover_report_feb.md` to `Reference_docs/`
- [x] Update HANDOVER_CATALOGUE.md with all status changes
- [x] `TECHNICAL_DEBT_v2.md` deleted and replaced by `techdebt_march_2026.md` (198 lines vs 2720)
- [ ] Move remaining reference docs to `Reference_docs/`: `LOG_ANALYSIS_GUIDE.md`, `Agent instructions and where they live.md`, `Code_quality_prompt.md`
- [ ] Update `handovers/README.md` priority table

---

## Forward-Looking Planning

This document served as the **CE launch checklist** and is now complete. For post-launch planning, branch transition prep, and the feature roadmap, see:

**[ROADMAP.md](./ROADMAP.md)** -- the active forward-looking planning document.
