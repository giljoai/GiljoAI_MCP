# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for setup_instructions module (Sprint 002e extraction)."""

from giljo_mcp.tools.setup_instructions import build_setup_instructions


def test_claude_code_instructions_contain_download_url():
    """Claude Code instructions include the download URL."""
    url = "https://example.com/download/test"
    result = build_setup_instructions("claude_code", url)
    assert url in result
    assert "~/.claude/" in result


def test_gemini_cli_instructions_contain_download_url():
    """Gemini CLI instructions include the download URL."""
    url = "https://example.com/download/test"
    result = build_setup_instructions("gemini_cli", url)
    assert url in result
    assert "~/.gemini/" in result


def test_codex_cli_instructions_contain_download_url():
    """Codex CLI instructions include the download URL."""
    url = "https://example.com/download/test"
    result = build_setup_instructions("codex_cli", url)
    assert url in result
    assert "~/.codex/" in result


def test_codex_cli_instructions_use_codex_default_model():
    """Codex config registration examples use the supported GiljoAI default model."""
    result = build_setup_instructions("codex_cli", "https://example.com/download/test")

    assert "model = 'gpt-5.3-codex'" in result
    assert "model_reasoning_effort = 'medium'" in result
    assert "model = 'gpt-5.2-codex'" not in result
    assert "model = 'o3'" not in result


def test_generic_instructions_contain_download_url():
    """Generic instructions include the download URL."""
    url = "https://example.com/download/test"
    result = build_setup_instructions("generic", url)
    assert url in result
    assert "platform was not identified" in result
