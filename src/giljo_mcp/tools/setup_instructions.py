# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Platform-specific setup instruction generator.

Sprint 002e: Extracted from tool_accessor.py (module-level function).
Zero coupling to ToolAccessor -- generates install instructions for
bootstrap_setup based on the target CLI platform.
"""


def build_setup_instructions(platform: str, download_url: str) -> str:
    """Build a natural-language prompt the LLM will execute to install GiljoAI CLI integration."""
    if platform == "claude_code":
        return (
            "Install the GiljoAI CLI skills. This is a one-time setup.\n\n"
            "Step 1 — Download and extract:\n"
            f"Download: {download_url}\n"
            "Extract to: ~/.claude/ (create if needed, overwrite existing)\n"
            "Delete the downloaded zip.\n\n"
            "Adapt all commands for the OS you are running on.\n\n"
            "Step 2 — Tell the user:\n"
            "Skills installed to user-level (~/.claude/commands/).\n"
            "Two commands are now available:\n"
            "- /gil_get_agents — pull agent templates for your active product\n"
            "- /gil_add — add tasks and projects from the CLI (try /gil_add --help)\n\n"
            "Restart Claude Code, then run /gil_get_agents to install agent templates.\n"
            "Note: Download link expires in 15 minutes."
        )
    if platform == "gemini_cli":
        return (
            "Install the GiljoAI CLI skills. This is a one-time setup.\n\n"
            "Step 1 — Download and extract:\n"
            f"Download: {download_url}\n"
            "Extract to: ~/.gemini/ (create if needed, overwrite existing)\n"
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
            "Skills installed to user-level (~/.gemini/commands/).\n"
            "Two commands are now available:\n"
            "- /gil_get_agents — pull agent templates for your active product\n"
            "- /gil_add — add tasks and projects from the CLI (try /gil_add --help)\n\n"
            "Restart Gemini CLI, then run /gil_get_agents to install agent templates.\n"
            "Note: Download link expires in 15 minutes."
        )
    if platform == "generic":
        return (
            "Your platform was not identified. To install GiljoAI skills manually:\n\n"
            f"Step 1 — Download: {download_url}\n"
            "Step 2 — Extract the ZIP. It contains:\n"
            "  - commands/ — Slash command reference documents\n"
            "Step 3 — Install these files according to your MCP client's documentation\n"
            "  for commands/skills.\n"
            "Step 4 — Use the appropriate get-agents command to pull agent templates.\n\n"
            "For platform-specific setup, visit your GiljoAI server's web interface\n"
            "at Settings -> Integrations.\n"
            "Note: Download link expires in 15 minutes."
        )
    # codex_cli
    return (
        "Install the GiljoAI CLI skills. This is a one-time setup.\n\n"
        "Step 1 — Download and extract:\n"
        f"Download: {download_url}\n"
        "Extract to: ~/.codex/ (create if needed, overwrite existing)\n"
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
        "Step 3 — Tell the user:\n"
        "Skills installed to user-level (~/.codex/skills/).\n"
        "Two skills are now available:\n"
        "- $gil-get-agents — pull agent templates for your active product\n"
        "- $gil-add — add tasks and projects from the CLI (try $gil-add --help)\n\n"
        "Use $gil-get-agents to pull agent templates for your product.\n"
        "Note: Download link expires in 15 minutes."
    )
