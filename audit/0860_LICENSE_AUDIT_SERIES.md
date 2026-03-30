# Handover 0860: Code Provenance & License Compliance Audit (Series Coordinator)

**Date:** 2026-03-30
**From Agent:** Claude Opus 4.6 orchestrator
**To Agent:** Orchestrator-gated chain (0860a-d)
**Priority:** CRITICAL — gates CE public launch April 5, 2026
**Status:** Not Started
**Edition Scope:** Both (CE + SaaS, with different severity thresholds)

---

## Task Summary

Run a two-layer license and code provenance audit against the entire GiljoAI MCP codebase before Community Edition public launch. Layer 1 (ScanCode Toolkit) scans for license headers and dependency licenses. Layer 2 (SCANOSS) scans for code snippets matching known open source. Findings are triaged per-edition: CE distributes source (strict), SaaS never distributes (relaxed for GPL, still strict for AGPL).

**Authoritative spec:** `handovers/CODE_PROVENANCE_LICENSE_AUDIT.md` — all agents MUST read this before starting. It contains triage rules, expected false positives, and output format requirements.

**Owner review required:** Patrik must personally review all BLOCK and REVIEW items. No agent resolves findings.

---

## Series Structure (Orchestrator-Gated v3)

| Phase | ID | Title | Color | Est. | Parallel? |
|-------|-----|-------|-------|------|-----------|
| 1 | 0860a | Tool Installation + Dependency License Scan | #4CAF50 | 30 min | No (first) |
| 2 | 0860b | ScanCode Source Scanning | #2196F3 | 2-3h | Yes (with 0860c) |
| 3 | 0860c | SCANOSS Snippet Scanning | #9C27B0 | 1-2h | Yes (with 0860b) |
| 4 | 0860d | Findings Consolidation + Audit Summary | #FF9800 | 30 min | No (last) |

**Execution mode:** Orchestrator-Gated (v3). Agents STOP after completing. Orchestrator reviews chain log, adjusts downstream handovers, then spawns next.

**Branch:** `feature/0860-license-audit`

**Chain log:** `prompts/0860_chain/chain_log.json`

**Output directory:** `audit/` (gitignored — large JSON scan results stay local, only .md summaries committed)

---

## Critical Rules

1. **Do NOT resolve findings.** Document and stop. Resolution decisions belong to the project owner.
2. **Do NOT rewrite matched code.** Even if SCANOSS flags a GPL snippet, the agent documents it — it does not rewrite.
3. **AGPL is BLOCK for BOTH editions.** If found anywhere, mark as CRITICAL in chain log immediately.
4. **GPL is BLOCK for CE, SAFE for SaaS** (under no-distribution assumption). Document in both BLOCK and TRACK registers.
5. **Read the spec** (`handovers/CODE_PROVENANCE_LICENSE_AUDIT.md`) before starting ANY phase.
