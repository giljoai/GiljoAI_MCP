# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Platform-specific setup instruction generator.

Sprint 002e: Extracted from tool_accessor.py (module-level function).
Zero coupling to ToolAccessor -- generates install instructions for
bootstrap_setup based on the target CLI platform.
"""

from giljo_mcp.codex_defaults import CODEX_DEFAULT_MODEL, CODEX_DEFAULT_REASONING_EFFORT


def build_setup_instructions(platform: str, download_url: str) -> str:
    """Build a natural-language prompt the LLM will execute to install GiljoAI CLI integration."""
    if platform == "claude_code":
        return (
            "Install the GiljoAI CLI integration. This is a one-time setup.\n\n"
            "Step 1 — Download:\n"
            f"Download: {download_url}\n"
            "Save the zip to a temp location (do NOT extract the whole zip to ~/.claude/ yet).\n\n"
            "Step 2 — Install commands (always overwrite):\n"
            "Extract only the commands/ entries from the zip into ~/.claude/commands/ "
            "(create if needed, overwrite existing).\n\n"
            "Step 3 — Install agents (consent required if any exist):\n"
            "Check if ~/.claude/agents/ contains any .md files.\n"
            "  - If none exist (or the directory is missing): extract agents/* into "
            "~/.claude/agents/ and continue.\n"
            "  - If .md files already exist: ask the user ONCE via AskUserQuestion:\n"
            '      "GiljoAI agent templates already exist in ~/.claude/agents/. '
            "Overwrite with agent templates from the server? Any local edits will be lost. "
            'To preserve them and pick models per agent, cancel and run /gil_get_agents instead."\n'
            "      Options: [Overwrite, Skip agents]\n"
            "    - Overwrite -> extract agents/* into ~/.claude/agents/ (overwrite).\n"
            "    - Skip agents -> do NOT extract agents/*. Tell the user their existing "
            "agent files were preserved.\n\n"
            "Step 4 — Clean up:\n"
            "Delete the downloaded zip.\n\n"
            "Adapt all commands for the OS you are running on.\n\n"
            "Step 5 — Tell the user:\n"
            "Agent templates installed to ~/.claude/agents/ with model: opus by default.\n"
            "Three commands are now available:\n"
            "- /gil_get_agents — install/update GiljoAI agent templates\n"
            "- /gil_add — create tasks/projects from the CLI (try /gil_add --help)\n"
            "- /gil_get — read existing tasks/projects from the CLI\n\n"
            "Restart Claude Code, then run /gil_get_agents to install agent templates.\n"
            "Note: Download link expires in 15 minutes."
        )
    if platform == "gemini_cli":
        return (
            "Install the GiljoAI CLI integration. This is a one-time setup.\n\n"
            "Step 1 — Download:\n"
            f"Download: {download_url}\n"
            "Save the zip to a temp location (do NOT extract the whole zip to ~/.gemini/ yet).\n\n"
            "Step 1a — Install commands (always overwrite):\n"
            "Extract only the commands/ entries from the zip into ~/.gemini/commands/ "
            "(create if needed, overwrite existing).\n\n"
            "Step 1b — Install agents (consent required if any exist):\n"
            "Check if ~/.gemini/agents/ contains any .md files.\n"
            "  - If none exist (or the directory is missing): extract agents/* into "
            "~/.gemini/agents/ and continue.\n"
            "  - If .md files already exist: ask the user ONCE:\n"
            '      "GiljoAI agent templates already exist in ~/.gemini/agents/. '
            "Overwrite with agent templates from the server? Any local edits will be lost. "
            'To preserve them and pick models per agent, cancel and run /gil_get_agents instead."\n'
            "      Options: [Overwrite, Skip agents]\n"
            "    - Overwrite -> extract agents/* into ~/.gemini/agents/ (overwrite).\n"
            "    - Skip agents -> do NOT extract agents/*. Tell the user their existing "
            "agent files were preserved.\n\n"
            "Step 1c — Clean up:\n"
            "Delete the downloaded zip.\n\n"
            "Step 2 — Enable custom agents:\n"
            'Merge {"experimental": {"enableAgents": true}} into ~/.gemini/settings.json '
            "(create if it does not exist). Preserve all existing settings.\n"
            "IMPORTANT — Use a shell command for this step. Your file-write tool may be "
            "sandboxed to the workspace and unable to write to the home directory.\n"
            'Linux/macOS: python3 -c "'
            "import json,pathlib; "
            "p=pathlib.Path.home()/'.gemini'/'settings.json'; "
            "d=json.loads(p.read_text()) if p.exists() else {}; "
            "d.setdefault('experimental',{})['enableAgents']=True; "
            'p.write_text(json.dumps(d,indent=2))"\n'
            'Windows PowerShell: $p="$env:USERPROFILE\\.gemini\\settings.json"; '
            "$d=if(Test-Path $p){Get-Content $p -Raw|ConvertFrom-Json -AsHashtable}else{@{}}; "
            "if(-not $d.ContainsKey('experimental')){$d['experimental']=@{}}; "
            "$d['experimental']['enableAgents']=$true; "
            "$utf8NoBom=New-Object System.Text.UTF8Encoding($false); "
            "[System.IO.File]::WriteAllText($p,($d|ConvertTo-Json -Depth 10),$utf8NoBom)\n\n"
            "Adapt all commands for the OS you are running on.\n\n"
            "Step 3 — Tell the user:\n"
            "Agent templates installed to ~/.gemini/agents/ with model: gemini-3-pro-preview by default.\n"
            "Three commands are now available:\n"
            "- /gil_get_agents — install/update GiljoAI agent templates\n"
            "- /gil_add — create tasks/projects from the CLI (try /gil_add --help)\n"
            "- /gil_get — read existing tasks/projects from the CLI\n\n"
            "Restart Gemini CLI, then run /gil_get_agents to install agent templates.\n"
            "Note: Download link expires in 15 minutes."
        )
    if platform == "generic":
        return (
            "Your platform was not identified. To install GiljoAI agent templates\n"
            "and commands manually:\n\n"
            f"Step 1 — Download: {download_url}\n"
            "Step 2 — Extract the ZIP. It contains:\n"
            "  - agents/ — Markdown files with agent role definitions and system prompts\n"
            "  - commands/ — Reference documents describing available GiljoAI commands\n"
            "Step 3 — Install these files according to your MCP client's documentation\n"
            "  for custom agents and commands/skills.\n\n"
            "For platform-specific setup, visit your GiljoAI server's web interface\n"
            "at Tools -> Connect.\n"
            "Note: Download link expires in 15 minutes."
        )
    # codex_cli
    return (
        "Install the GiljoAI CLI integration. This is a one-time setup.\n\n"
        "Step 1 — Download:\n"
        f"Download: {download_url}\n"
        "Save the zip to a temp location (do NOT extract the whole zip to ~/.codex/ yet).\n\n"
        "Step 1a — Install skills (always overwrite):\n"
        "Extract only the skills/ entries from the zip into ~/.codex/skills/ "
        "(create if needed, overwrite existing).\n\n"
        "Step 1b — Install agents (consent required if any exist):\n"
        "Check if ~/.codex/agents/ contains any gil-*.toml files.\n"
        "  - If none exist (or the directory is missing): extract agents/* into "
        "~/.codex/agents/ and set AGENTS_INSTALLED=true.\n"
        "  - If gil-*.toml files already exist: ask the user ONCE:\n"
        '      "GiljoAI agent templates already exist in ~/.codex/agents/. '
        "Overwrite with agent templates from the server? Any local edits will be lost. "
        'To preserve them and pick models per agent, cancel and run $gil-get-agents instead."\n'
        "      Options: [Overwrite, Skip agents]\n"
        "    - Overwrite -> extract agents/* into ~/.codex/agents/ and set "
        "AGENTS_INSTALLED=true.\n"
        "    - Skip agents -> do NOT extract agents/*. Set AGENTS_INSTALLED=false and "
        "tell the user their existing agent files were preserved.\n\n"
        "Step 1c — Clean up:\n"
        "Delete the downloaded zip.\n\n"
        "Step 2 — Enable interactive menus:\n"
        "Read ~/.codex/config.toml (create if it does not exist).\n"
        "Under the [features] section, ensure these flags are set:\n"
        "  default_mode_request_user_input = true\n"
        "  multi_agent = true\n"
        "If [features] already exists, merge — do NOT remove existing flags.\n"
        "CRITICAL: Use a TOML parser to read-then-merge. Never overwrite config.toml.\n"
        "Back up config.toml before writing.\n"
        "Sandbox fallback: If your file-write tool cannot write outside the workspace, "
        "use a shell command instead: cp -p ~/.codex/config.toml ~/.codex/config.toml.bak "
        '&& python3 -c "import tomllib,pathlib; '
        "p=pathlib.Path.home()/'.codex'/'config.toml'; "
        "t=p.read_text() if p.exists() else ''; "
        "tomllib.loads(t) if t.strip() else None; "
        "t+='\\n[features]\\ndefault_mode_request_user_input = true\\nmulti_agent = true\\n' "
        "if '[features]' not in t else t; "
        'p.write_text(t); tomllib.loads(p.read_text())"\n'
        "IMPORTANT — Windows BOM trap: Use your built-in write_file tool if available. "
        "If you must use PowerShell: $utf8NoBom = New-Object System.Text.UTF8Encoding($false); "
        "[System.IO.File]::WriteAllText($path, $content, $utf8NoBom). "
        "Do NOT use Set-Content, Out-File, or [System.Text.Encoding]::UTF8 (all add BOM).\n\n"
        "Adapt all commands for the OS you are running on.\n\n"
        "Step 3 — Register agent templates:\n"
        "Skip this entire step if AGENTS_INSTALLED=false (user chose Skip agents in Step 1b) — "
        "existing registrations stay in place.\n"
        "Otherwise: the ZIP extracted agent files to ~/.codex/agents/ (e.g. gil-analyzer.toml, "
        "gil-implementer.toml). Each one MUST be registered in config.toml.\n"
        "For each gil-*.toml file in the agents/ directory, add a section:\n"
        "  [agents.gil-{name}]\n"
        "  config_file = 'agents/gil-{name}.toml'\n"
        f"  model = '{CODEX_DEFAULT_MODEL}'\n"
        f"  model_reasoning_effort = '{CODEX_DEFAULT_REASONING_EFFORT}'\n"
        "  nickname_candidates = ['gil-{name}']\n"
        "Where {name} is the agent name from the filename (without gil- prefix and .toml).\n"
        "Preserve any existing non-GiljoAI [agents.*] entries.\n"
        "Use the same TOML parser read-then-merge approach from Step 2.\n"
        "If sandboxed, use the same shell fallback: back up, append, validate.\n\n"
        "Step 4 — Tell the user:\n"
        "Three skills are now available:\n"
        "- $gil-get-agents — install/update GiljoAI agent templates\n"
        "- $gil-add — create tasks/projects from the CLI (try $gil-add --help)\n"
        "- $gil-get — read existing tasks/projects from the CLI\n\n"
        "Restart Codex CLI, then run $gil-get-agents to install agent templates.\n"
        "Note: Download link expires in 15 minutes."
    )
