# ADR-010 — Execution-mode collapse: two axes (topology + harness)

**Status:** Accepted (2026-07-04)
**Scope:** Backend architecture / orchestration identity / edition isolation (Both). Read **before** touching `execution_mode`, the platform registry, per-CLI prose rendering, staging/implementation prompt routing, or harness detection.

## Context

`projects.execution_mode` historically held SIX values — `multi_terminal`, `claude_code_cli`, `codex_cli`, `gemini_cli`, `antigravity_cli`, `generic_mcp` — that **conflated two independent things**:

1. **Topology** — does one human watch a fleet of terminals (`multi_terminal`), or does one orchestrator session manage its workers (all the others)? This is a genuine, user-declared project choice.
2. **Harness identity** — *which* CLI/agent app is driving the session (Claude Code / Codex / Gemini / Antigravity / opencode / something else). This determines spawn syntax, wake/reactivation prose, launch commands, and autonomy flags.

Conflating them forced a **user** to declare their harness up front (`claude_code_cli` vs `codex_cli` …), which is fragile: the picker had to enumerate every CLI, a new CLI (opencode) had no value to pick, and the declared value silently drifted from the harness that actually connected. Meanwhile the MCP `initialize` handshake already carries the real harness in `clientInfo` (captured + persisted since INF-8003d), so the harness never needed to be declared at all.

Evidence (3-agent census, 2026-07-04): ~155 branch sites, but ~95 were plain boolean `subagent` vs `multi_terminal` checks that survive unchanged, and ~33 of the per-CLI sites were mechanical registry-dict lookups whose *key source* changes, not their shape. The DB needs **no migration** (`projects.execution_mode` is a nullable `String(20)` with no CHECK; `sequence_runs.execution_mode` a `String(50)` with no CHECK; validation is app-layer, registry-derived).

## Decision

**Split `execution_mode` onto two orthogonal axes.**

### Axis 1 — TOPOLOGY (user-declared, 2 values)

`execution_mode` collapses to exactly **`multi_terminal`** and **`subagent`**. This stays the project column and the UI choice (two pills). "Multi-Terminal" is permanent (standing CHT-0058 ruling). The registry exposes these as `MODES`.

### Axis 2 — HARNESS (runtime-resolved, never declared)

Which CLI drives the session — `claude-code` / `codex` / `gemini` / `antigravity` / `opencode`, plus the `generic` fail-safe floor — is **resolved at runtime** from the `clientInfo` sent at MCP `initialize` (`harness_from_client_info`), stamped on the session (`session_data['resolved_harness']`), and read back through the ONE precedence helper `effective_harness()`. The registry exposes the per-harness knowledge (spawn syntax, launcher binary, template locations, export token, autonomy flag) as `HARNESSES`.

### Precedence rule (the one new design decision)

For **harness-specific RENDERING**, **DETECTED beats DECLARED**: a concrete detected harness wins over a legacy declared CLI token, which is only a *hint* used when detection is absent. Topology is 100% declared, never detected. (For the orthogonal harness PRESET axis — `web_sandbox` / `desktop_app` / `chat`, INF-8003e — the existing DECLARED-beats-DETECTED rule stays; the flip is HARNESS-only.)

### Fail-safe floor

Unknown / absent / ambiguous `clientInfo` → the `generic` harness → the **universal subagent prose** (a rich PREFERRED/FALLBACK/FLOOR ladder: spawn a terminal per agent, else use your harness's in-process subagent mechanism, else self-adopt as a verified last resort). Detection *sharpens* the CLIs that send a rich `clientInfo` (claude-code, opencode today); the universal prose *carries* every other and every future harness. Both halves matter; neither over-claims.

### Security framing (load-bearing)

Harness detection drives **rendering only** — spawn syntax, wake prose, launch commands, autonomy flags. It is **NEVER** an authentication or authorization signal; auth stays tenant/scope-based. `clientInfo` is client-supplied and trivially spoofable; a wrong detection degrades ergonomics only and the declared hint can correct it.

## Tolerance policy (data-facing DoD — no migration, option (a): code tolerates the old shape)

The 5 legacy tokens live in prod + CE self-hoster DBs **forever**. They are never rewritten. Instead:

- `VALID_EXECUTION_MODES` = `{multi_terminal, subagent}` governs **new writes** (the UI).
- `LEGACY_MODE_ALIASES` = the old 5 tokens; `ACCEPTED_EXECUTION_MODES` = the union, accepted at **every validation boundary** (project update, sequence-run create/update, chain tools, `stage_project`) so a stored legacy row never hard-fails.
- `normalize_execution_mode()` folds any token onto the 2 modes (`multi_terminal`→`multi_terminal`; NULL→NULL; everything else→`subagent`). Read sites display/branch through the normalizer (or `is_subagent_mode()`); stored values are never mutated.
- A stored legacy `*_cli` token still functions as a **harness hint** through `effective_harness()` (e.g. a legacy `claude_code_cli` project with no detection still renders the Claude block).
- `stage_project`'s public MCP `mode` param keeps accepting `multi_terminal | subagent | claude | codex | gemini | antigravity`; the per-CLI tokens map to `subagent` + a harness hint. The agent-facing contract never breaks.
- Statistics `GROUP BY execution_mode` folds legacy rows into `subagent` through the normalizer (display-only).

## Consequences

- **UI shrinks** to two pills; the per-CLI picker is gone. The Template Manager `cli_tool` picker is a **separate per-agent axis** and is untouched. A read-only "detected: &lt;harness&gt;" chip exposes the resolved harness.
- **Registry** splits `PLATFORMS` → `MODES` (2) + `HARNESSES` (5, incl. opencode as a first-class row using the BE-9015 verified `cmd /k opencode --prompt` launch). Export vocabulary (`EXPORT_*`) is untouched. `Platform` remains only for the harness PRESET rows.
- **Golden re-baseline** (owner-blessed): the S1–S4 render golden moves to a `mode×harness` key scheme. `multi_terminal` renders stay byte-identical (the collapse never touches the human-driven path); the `_be6209f_golden_multi_terminal.txt` fixture is byte-stable.
- **Teams-readiness (ADR-009):** unaffected — no per-user assumption is introduced; `execution_mode` is a project attribute scoped by `tenant_key` as before.

## Fallback

Zero DB migrations anywhere in the chain, so every fallback is pure code. Fallback branch `backup/pre-mode-collapse` + tag `pre-mode-collapse-20260704` on origin; per-phase rollback = `git revert -m 1 <merge-sha>`. The per-milestone commits (registry → backend sweep → FE → prose → ADR → golden) are the revert grain.

## References

- Chain: BE-9035a (drift fixes + clientInfo harvest) → BE-9035b (harness resolver + DETECTED tier) → BE-9035c (this collapse). BE-9036 = SDK-GA-gated successor.
- `src/giljo_mcp/platform_registry.py` — `MODES`, `HARNESSES`, `normalize_execution_mode`, `effective_harness`, `harness_from_client_info`.
- ADR-009 (tenancy invariant); INF-8003e (harness PRESET axis, orthogonal).
