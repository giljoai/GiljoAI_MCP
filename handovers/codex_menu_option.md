# Codex CLI's `request_user_input` and the plan mode constraint

**Codex CLI's `request_user_input` was originally locked to Plan mode only, but PR #12735 (merged February 25, 2026) extended it to Default mode behind a config flag.** The tool presents structured multiple-choice questions — not free-text prompts — and the model cannot programmatically switch itself into Plan mode. This design created friction that sparked over a dozen GitHub issues and eventually forced OpenAI to relax the restriction. Claude Code and Gemini CLI both ship similar tools with fewer mode constraints, reflecting a broader consensus that agent-initiated clarification should not require a special operating mode.

---

## The tool presents structured menus, not text prompts

The `request_user_input` tool is defined in `codex-rs/protocol/src/request_user_input.rs` and handled in `codex-rs/core/src/tools/handlers/request_user_input.rs`. It accepts **1–3 questions**, each with required parameters:

- **`id`** (string): unique identifier for correlating answers
- **`header`** (string): short label displayed above the question
- **`question`** (string): the full question text
- **`options`** (array, **required and non-empty**): each option has a `label` and `description`
- **`isSecret`** (bool): marks the answer as sensitive
- **`isOther`** (bool): the handler **force-sets this to `true`** on every question, guaranteeing a "None of the above" free-text escape hatch

The tool returns a `RequestUserInputResponse` — a `HashMap<String, RequestUserInputAnswer>` where each answer is a `Vec<String>`, serialized as JSON. This is explicitly a **popup/select UI** in the TUI, not inline chat text. Every question must include predefined options; calling the tool without options returns the error `"request_user_input requires non-empty options for every question"`. The tool description is dynamically generated to reflect which modes it supports: *"Request user input for one to three short questions and wait for the response. This tool is only available in {allowed_modes}."*

---

## The Plan mode restriction and how it was relaxed

The availability check lives in one function in the handler file:

```rust
fn request_user_input_is_available(mode: ModeKind, default_mode_request_user_input: bool) -> bool {
    mode.allows_request_user_input()
        || (default_mode_request_user_input && mode == ModeKind::Default)
}
```

**Before PR #12735** (v0.93 through roughly v0.97), `allows_request_user_input()` returned `true` only for `ModeKind::Plan`. Calling the tool in Default or Code mode produced the error *"request_user_input is unavailable in {mode_name} mode"*. The tool's system-prompt description explicitly stated it was Plan-only, and the Plan mode template (`codex-rs/core/templates/collaboration_mode/plan.md`) instructed the model to *"strongly prefer using the request_user_input tool to ask any questions"* with *"meaningful multiple-choice options."*

**After PR #12735** (merged February 25, 2026), a new config flag `default_mode_request_user_input` within `CollaborationModesConfig` unlocks the tool in Default mode. The Default mode instructions were updated to **prefer assumptions first** and use `request_user_input` only when a question is truly unavoidable — a deliberate contrast with Plan mode, where clarifying questions are the primary workflow. In non-interactive sessions (`codex exec`), both `request_user_input` and the related `ask_user_question` are stripped from the toolset entirely to prevent indefinite hangs.

---

## The model cannot switch itself into Plan mode

Only the human user can toggle collaboration modes. Three mechanisms exist, all user-initiated:

- **`/plan` slash command** (PR #10103, v0.93.0): types `/plan` optionally followed by a prompt; blocked while a task is running
- **`Shift+Tab`** in the TUI composer: cycles between Plan and Default mode
- **TUI mode picker**: graphical mode selector

The Plan mode template is unambiguous: *"You are in Plan Mode until a developer message explicitly ends it. Plan Mode is not changed by user intent, tone, or imperative language."* Mode state is stored in the `TurnContext` and set by the TUI/system layer. The model receives a `<collaboration_mode>` developer message indicating the current mode but **cannot emit such messages**. No tool exists for programmatic mode switching — the template explicitly warns that `update_plan` (a checklist/TODO tool) *"does not enter or exit Plan Mode."*

A persistent bug cluster (Issues #10185, #9997, #10565, #14029) demonstrates the corollary: after switching Plan → Default, the model sometimes continues behaving as if in Plan mode because stale prompt context lingers. The model genuinely cannot detect or control its own mode — it can only read the instructions it was given.

---

## Subagents and workarounds hit real limits

**Issue #13289** ("Forked Subagents Using request_user_input") documents the most significant practical problem: subagents spawned two layers deep invoke `request_user_input`, but no human is present to respond, causing the session to hang indefinitely. The proposed fix is to set `default_mode_request_user_input = false` for all subagents, ensuring the tool is only available to the top-level agent that has a human at the keyboard.

Before the official Plan mode existed, the community developed a **custom prompt workaround** (Discussion #4760): creating `~/.codex/prompts/plan.md` with instructions to plan first and wait for approval, then invoking `/plan` as a prompt alias. This simulated planning behavior but lacked the structured `request_user_input` UI.

Other workarounds include toggling Shift+Tab to unstick mode-switching bugs and ending/resuming sessions when user input fails to register (Issue #8651). **No workaround exists to call `request_user_input` from a mode where it is disabled** — the handler performs a hard runtime check and returns an error string to the model, not a soft warning.

---

## The community pushed hard for this change

The restriction generated substantial friction across **at least seven issues**:

- **#10384** ("Make request_user_input available in code mode") — the canonical issue, filed February 2, 2026, became the duplicate target for all subsequent requests
- **#11266** ("Enable clarifying questions in normal mode") — initially closed as "not planned," which triggered backlash
- **#11536** drew the critical distinction that prompting alone *"cannot reproduce the Plan-mode popup/select experience"* — the tool provides a fundamentally different UI from chat text
- **#11892** and others piled on with the same request

UX issues compounded the frustration: **#12524** and **#13478** reported that no notification fires when `request_user_input` is waiting, so users miss that the agent is blocked. **#10734** found that plan mode breaks entirely after context compaction. **Discussion #11717** proposed custom collaboration modes with configurable tool access, reflecting demand for more granular control than the binary Plan/Default split.

---

## Claude Code and Gemini CLI take a less restrictive approach

All three major coding CLIs now ship agent-initiated user input tools, but Codex CLI's original mode restriction was the most constraining.

**Claude Code's `AskUserQuestion`** (since v2.0.21) supports **1–4 questions** with 2–4 multiple-choice options each, plus free-text fallback and optional HTML previews. It operates through the SDK's `canUseTool` callback with a **60-second timeout** — if the user doesn't respond, Claude assumes denial and tries another approach. The tool works in all modes (including plan mode) but is **explicitly unavailable in subagents** spawned via the Task tool, mirroring the problem Codex CLI encountered in Issue #13289.

**Gemini CLI's `ask_user`** is the most feature-rich, supporting three question types: `choice` (multiple-choice with multi-select), `text` (free-form with placeholder), and `yesno` (confirmation). It allows **1–4 questions per call** and renders through a dedicated `AskUserDialog` UI component. Google designed it explicitly to complement Plan mode — their blog stated it lets *"the agent pause its research and ask you targeted questions"* rather than making assumptions. Gemini CLI also offers collaborative plan editing via `Ctrl+X` and automatic model routing (Pro for planning, Flash for execution).

The key architectural difference: **both Claude Code and Gemini CLI make their user-input tools available outside plan mode by default.** Codex CLI was the only one that originally hard-locked the tool to a single mode, creating a gap between what the model could do (ask structured questions) and when it was allowed to do so (only during planning). PR #12735 partially closed this gap, but the Default mode instructions still discourage use, and the subagent problem remains unresolved.

---

## Conclusion

The `request_user_input` story reveals a tension in coding agent design: **structured user input is too useful to confine to a single mode, but too disruptive to allow everywhere.** Codex CLI's original Plan-only restriction was architecturally clean but practically frustrating — developers wanted clarifying questions during implementation, not just planning. The February 2026 relaxation via `default_mode_request_user_input` was a pragmatic compromise, but the subagent hang problem (Issue #13289) shows that mode-level gating alone is insufficient. The deeper question — whether the *agent* or the *system* should decide when to ask questions — remains open across all three platforms, with each making different tradeoffs between agent autonomy and user control.