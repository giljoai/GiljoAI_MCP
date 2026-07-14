# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6049c — launch-command synthesis (string-level, NO real terminals).

Covers the DoD: correct command synthesis per OS for each of the 4 CLI tools, and
— the load-bearing safety property — a seed prompt containing quotes, semicolons,
``$``, backticks and spaces is escaped so it can neither break out of the argument
nor inject a second command. No subprocess is ever spawned (pure string asserts),
so this is parallel-safe with zero DB / env state.
"""

from __future__ import annotations

import pytest

from giljo_mcp.prompts.launch_command_synth import (
    CLI_BINARIES,
    macos_command,
    posix_single_quote,
    pwsh_single_quote,
    resolve_binary,
    synthesize_agent_launch,
    synthesize_launch_commands,
)


# A deliberately hostile seed: every shell metacharacter that could break out.
HOSTILE_SEED = """health_check(); rm -rf /; echo "pwned" $HOME `id` 'quote'"""


@pytest.mark.parametrize(
    "cli_tool,expected_binary",
    [
        ("claude", "claude"),
        ("codex", "codex"),
        ("gemini", "gemini"),
        ("antigravity", "agy"),
    ],
)
def test_binary_mapping_per_tool(cli_tool, expected_binary):
    assert resolve_binary(cli_tool) == expected_binary
    assert CLI_BINARIES[cli_tool] == expected_binary


def test_unknown_and_empty_cli_tool_default_to_claude():
    assert resolve_binary(None) == "claude"
    assert resolve_binary("") == "claude"
    assert resolve_binary("totally-unknown") == "claude"


@pytest.mark.parametrize("cli_tool", ["claude", "codex", "gemini", "antigravity"])
def test_synthesize_emits_all_oses_with_correct_binary(cli_tool):
    spec = {
        "agent": "implementer",
        "cli_tool": cli_tool,
        "job_id": "job-123",
        "seed_prompt": "mcp__giljo_mcp__health_check()",
    }
    result = synthesize_agent_launch(spec)
    binary = CLI_BINARIES[cli_tool]

    assert result["cli_tool"] == cli_tool
    assert result["job_id"] == "job-123"
    assert set(result["commands"]) == {"windows", "linux", "linux_fallback", "macos"}
    # Each per-OS command actually invokes the right binary.
    assert f"Start-Process {binary} " in result["commands"]["windows"]
    assert f"-- {binary} " in result["commands"]["linux"]
    assert f"{binary} " in result["commands"]["linux_fallback"]
    assert f"{binary} " in result["commands"]["macos"]
    # macOS is explicitly flagged unvalidated.
    assert result["macos_validated"] is False


# ---------------------------------------------------------------------------
# Quoting primitives — the security core
# ---------------------------------------------------------------------------


def test_posix_single_quote_neutralizes_embedded_single_quote():
    out = posix_single_quote("a'b")
    # Closed-escaped-reopened: a'b -> 'a'\''b'
    assert out == "'a'\\''b'"


def test_pwsh_single_quote_doubles_embedded_single_quote():
    out = pwsh_single_quote("a'b")
    assert out == "'a''b'"


# ---------------------------------------------------------------------------
# Hostile-seed escaping per OS (the orchestrator's mandated proof)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cli_tool", ["claude", "codex", "gemini", "antigravity"])
def test_hostile_seed_is_escaped_windows(cli_tool):
    cmd = synthesize_agent_launch({"agent": "a", "cli_tool": cli_tool, "job_id": "j", "seed_prompt": HOSTILE_SEED})[
        "commands"
    ]["windows"]
    # The whole seed sits inside ONE PowerShell single-quoted literal; every
    # embedded single quote is doubled, and none survives un-doubled to close it
    # early. Reconstruct the expected literal and assert it is present verbatim.
    assert pwsh_single_quote(HOSTILE_SEED) in cmd
    # BE-6182: -ArgumentList now carries the static autonomy flag, then the quoted
    # seed. The seed is still fully single-quoted (asserted above), so no raw
    # '; rm -rf' separator leaks at the shell layer.
    assert "-ArgumentList " in cmd


@pytest.mark.parametrize("cli_tool", ["claude", "codex", "gemini", "antigravity"])
def test_hostile_seed_is_escaped_posix(cli_tool):
    entry = synthesize_agent_launch({"agent": "a", "cli_tool": cli_tool, "job_id": "j", "seed_prompt": HOSTILE_SEED})[
        "commands"
    ]
    quoted = posix_single_quote(HOSTILE_SEED)
    assert quoted in entry["linux"]
    assert quoted in entry["linux_fallback"]
    # Every literal single-quote in the seed is closed-escaped-reopened, so the
    # argument cannot terminate early.
    assert "'\\''" in quoted


def test_hostile_seed_is_escaped_macos():
    cmd = macos_command("claude", "a", HOSTILE_SEED)
    # The inner double-quotes are backslash-escaped for the AppleScript layer.
    assert '\\"pwned\\"' in cmd
    # The whole osascript script is POSIX single-quoted for the outer shell.
    assert cmd.startswith("osascript -e '")


def test_title_with_special_chars_is_quoted_linux():
    cmd = synthesize_agent_launch({"agent": "weird; name", "cli_tool": "claude", "job_id": "j", "seed_prompt": "x"})[
        "commands"
    ]["linux"]
    assert posix_single_quote("weird; name") in cmd


# ---------------------------------------------------------------------------
# List-level behavior
# ---------------------------------------------------------------------------


def test_synthesize_list_one_entry_per_agent():
    agents = [
        {"agent": "orchestrator", "cli_tool": "claude", "job_id": "o", "seed_prompt": "x"},
        {"agent": "implementer", "cli_tool": "codex", "job_id": "i", "seed_prompt": "y"},
    ]
    out = synthesize_launch_commands(agents)
    assert len(out) == 2
    assert [e["cli_tool"] for e in out] == ["claude", "codex"]


def test_synthesize_empty_list_is_empty():
    assert synthesize_launch_commands([]) == []


# ---------------------------------------------------------------------------
# BE-6182: runnable launch command — autonomy flag + natural-language loaded prompt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cli_tool,binary,flag",
    [
        ("claude", "claude", "--dangerously-skip-permissions"),
        ("codex", "codex", "--dangerously-bypass-approvals-and-sandbox"),
        ("gemini", "gemini", "--yolo"),
        # BE-6205: agy's real autonomy flag (per `agy --help`) is
        # --dangerously-skip-permissions, NOT the wrongly-inferred Gemini --yolo.
        ("antigravity", "agy", "--dangerously-skip-permissions"),
    ],
)
def test_be6182_autonomy_flag_present_in_every_command(cli_tool, binary, flag):
    """BE-6182: every per-OS command carries the harness autonomy flag so the
    launched terminal runs unattended instead of stalling on a permission prompt."""
    from giljo_mcp.prompts.launch_command_synth import autonomy_flag

    assert autonomy_flag(binary) == flag
    cmds = synthesize_agent_launch(
        {"agent": "implementer", "cli_tool": cli_tool, "job_id": "job-1", "seed_prompt": "load your mission"}
    )["commands"]
    for os_name, cmd in cmds.items():
        assert flag in cmd, f"{os_name} command for {cli_tool} must carry the autonomy flag {flag}"


def test_be6182_unknown_binary_emits_no_flag():
    """An unknown binary gets no autonomy flag (safe default — never invent one)."""
    from giljo_mcp.prompts.launch_command_synth import autonomy_flag

    assert autonomy_flag("totally-unknown") == ""


def test_be6182_loaded_prompt_is_natural_language_with_get_job_mission():
    """BE-6182: the launch seed is a NATURAL-LANGUAGE prompt instructing the agent to
    load its mission via get_job_mission(job_id) and execute — not raw tool-call lines."""
    from giljo_mcp.prompts.launch_command_synth import build_loaded_prompt

    prompt = build_loaded_prompt("job-xyz")
    assert "get_job_mission" in prompt, "must instruct loading the mission"
    assert "job-xyz" in prompt, "must thread the real job_id"
    assert "execute" in prompt.lower(), "must instruct executing the mission"
    # Natural language, not a bare tool-call line.
    assert prompt.strip().lower().startswith("you are"), "must read as an instruction, not a tool call"
    assert not prompt.lstrip().startswith("mcp__"), "must NOT be a raw mcp__ tool-call seed"


def test_be6182_windows_command_is_runnable_shape():
    """BE-6182: the Windows command is a runnable Start-Process invocation: the
    binary is the process, the autonomy flag + quoted seed are the arguments."""
    cmd = synthesize_agent_launch(
        {"agent": "a", "cli_tool": "claude", "job_id": "j", "seed_prompt": "load your mission"}
    )["commands"]["windows"]
    assert cmd.startswith("Start-Process claude -ArgumentList "), cmd
    assert "--dangerously-skip-permissions" in cmd
    # The seed remains single-quoted (security property preserved).
    assert pwsh_single_quote("load your mission") in cmd
