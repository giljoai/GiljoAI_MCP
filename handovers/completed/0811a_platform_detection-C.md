# 0811a Research: #50 — Platform Detection cmd.exe vs GNU bash

**Handover ID:** 0811a
**Type:** Research / Triage
**Status:** COMPLETE
**Verdict:** VALID BUG (Low Priority, P3/E1)
**Completed:** 2026-03-06
**Commit:** `f665c861`
**Edition Scope:** CE

---

## Original Claim

#50: "Platform detection cmd.exe vs GNU bash — Windows timeout vs sleep confusion" (P2, E1)

## Verdict: VALID BUG (Low Priority)

`protocol_builder.py` embeds incorrect platform-specific shell commands. It tells agents to use Windows cmd.exe `timeout /t N /nobreak` when detecting Windows, but Claude Code on Windows runs in Git Bash where `sleep` works and `timeout` does NOT.

Practical impact is minimal: LLMs detect their shell, 0804b removed prescriptive polling, sub-agents never need sleep. The entire STEP 0 block is ~60 wasted tokens per prompt.

## Problematic Locations

1. `protocol_builder._build_ch2_startup()` lines 576-582 — Orchestrator STEP 0 incorrect `timeout` for Windows
2. `protocol_builder._generate_agent_protocol()` lines 236-240 — Sub-agent Phase 1 identical incorrect reference

## Non-Problematic

- `thin_prompt_generator.py` line 148: generic `sleep` reference (OK)
- `AgentTipsDialog.vue`: says "bash sleep" explicitly (correct)
- `slash_command_templates.py`: correctly says Unix paths work everywhere

## Fix Applied

Removed platform detection blocks from both locations in commit `f665c861`. Replaced with one-liner about Unix commands. Saves ~60 tokens per prompt.

---

**Chain log:** `handovers/0808_tier2_chain_log.json`
