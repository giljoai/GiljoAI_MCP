# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6231 — served agent templates regenerate the MCP bootstrap fresh.

The bug: ``get_agent_mission`` was renamed to ``get_job_mission``, but the
system-owned bootstrap is frozen in ``AgentTemplate.system_instructions`` and
the serve/render path emitted that stored copy verbatim — so downloaded agent
files kept instructing the dead tool. The fix regenerates the bootstrap from the
seed at serve time (renderer + assembler chokepoint). These tests pin that
behavior AT THE SERVE LAYER (bug-fix DoD).
"""

from giljo_mcp.models import AgentTemplate
from giljo_mcp.template_renderer import render_claude_agent, render_gemini_agent, render_generic_agent
from giljo_mcp.template_seeder import _get_mcp_bootstrap_section
from giljo_mcp.tools.agent_template_assembler import AgentTemplateAssembler


# A realistic STALE stored bootstrap: the real system-owned bootstrap text (so it
# carries the marker that flags it as regenerable) but with the pre-rename tool
# name — exactly the shape captured on prod for all 7 served templates.
_STALE_BOOTSTRAP = _get_mcp_bootstrap_section().replace("get_job_mission", "get_agent_mission")


def _stale_template(**overrides) -> AgentTemplate:
    defaults = {
        "name": "implementer",
        "role": "implementer",
        "cli_tool": "claude",
        "description": "Implements features",
        "system_instructions": _STALE_BOOTSTRAP,
        "user_instructions": "Focus on production-grade code.",
        "model": "sonnet",
    }
    defaults.update(overrides)
    return AgentTemplate(**defaults)


class TestRendererServesFreshBootstrap:
    """(a) The Claude renderer heals a stale stored bootstrap."""

    def test_stale_bootstrap_rendered_fresh(self):
        # Precondition: the stored copy really is stale.
        assert "get_agent_mission" in _STALE_BOOTSTRAP
        assert "get_job_mission" not in _STALE_BOOTSTRAP

        result = render_claude_agent(_stale_template())

        assert "get_job_mission" in result
        assert "get_agent_mission" not in result

    def test_clean_bootstrap_renders_job_mission_once(self):
        # (d) Sanity: an already-fresh template still renders get_job_mission
        # exactly once in the (only) bootstrap, with empty role prose.
        template = _stale_template(
            system_instructions=_get_mcp_bootstrap_section(),
            user_instructions="",
        )
        result = render_claude_agent(template)

        assert result.count("get_job_mission") == 1
        assert "get_agent_mission" not in result

    def test_customized_user_instructions_survive(self):
        # (c) Only the bootstrap is regenerated — custom prose is preserved.
        sentinel = "CUSTOM-ROLE-PROSE-DO-NOT-DROP-42"
        result = render_claude_agent(_stale_template(user_instructions=sentinel))

        assert sentinel in result
        assert "get_job_mission" in result
        assert "get_agent_mission" not in result

    def test_non_bootstrap_system_instructions_preserved(self):
        # A row whose system_instructions is NOT the bootstrap (no marker) is
        # emitted verbatim — we only regenerate the system-owned bootstrap.
        custom = "You are a bespoke agent with hand-written instructions."
        result = render_claude_agent(_stale_template(system_instructions=custom))

        assert custom in result


class TestAssemblerServesFreshBootstrap:
    """(b) The serve chokepoint (assembler, used by stage_agent_templates) heals."""

    def setup_method(self):
        self.assembler = AgentTemplateAssembler()

    def test_claude_code_serve_path_healed(self):
        result = self.assembler.assemble([_stale_template()], "claude_code")
        content = result["agents"][0]["content"]

        assert "get_job_mission" in content
        assert "get_agent_mission" not in content

    def test_customization_survives_serve_path(self):
        sentinel = "CUSTOM-ROLE-PROSE-DO-NOT-DROP-42"
        result = self.assembler.assemble([_stale_template(user_instructions=sentinel)], "claude_code")
        content = result["agents"][0]["content"]

        assert sentinel in content
        assert "get_agent_mission" not in content


class TestPlatformParityFreshBootstrap:
    """Every platform the assembler renders heals — no per-platform regression."""

    def test_gemini_renderer_healed(self):
        result = render_gemini_agent(_stale_template(cli_tool="gemini"))
        assert "get_job_mission" in result
        assert "get_agent_mission" not in result

    def test_generic_renderer_healed(self):
        result = render_generic_agent(_stale_template(cli_tool="generic"))
        assert "get_job_mission" in result
        assert "get_agent_mission" not in result
