"""
Test that staging prompt contains no shell commands (Handover 0333).

This test ensures the staging prompt:
1. Does NOT contain shell commands like 'ls'
2. Does NOT reference Windows command equivalents
3. Uses MCP tools for agent discovery instead
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.mark.asyncio
async def test_staging_prompt_no_shell_commands(db_session: AsyncSession):
    """
    Test that staging prompt does not contain shell commands.

    Per Handover 0333, the staging prompt should:
    - NOT include shell commands (ls, grep, find, etc.)
    - NOT reference "Windows equivalent" for shell commands
    - Use get_orchestrator_instructions() MCP tool for agent discovery
    """
    tenant_key = "test-tenant"

    # Create test product
    product = Product(
        id="product-123",
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for prompt generation",
        config_data={
            "tech_stack": {"languages": ["Python 3.11+"], "frameworks": ["FastAPI"]},
            "architecture": {"patterns": ["REST API", "MVC"]}
        }
    )
    db_session.add(product)

    # Create test project
    project = Project(
        id="project-456",
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project",
        description="Test project description",
        mission="Test mission",
        context_budget=200000
    )
    db_session.add(project)
    await db_session.commit()

    # Generate staging prompt
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    prompt = await generator.generate_staging_prompt(
        orchestrator_id="orch-789",
        project_id=project.id,
        claude_code_mode=False
    )

    # Assertions
    assert prompt, "Prompt should not be empty"

    # CRITICAL: No shell commands
    forbidden_patterns = [
        "ls ~/.claude",
        "ls ~",
        "Windows equivalent",
        "Execute: ls",
        "grep",
        "find ~/.claude"
    ]

    for pattern in forbidden_patterns:
        assert pattern not in prompt, (
            f"Staging prompt should NOT contain shell command pattern: '{pattern}'\n"
            f"This violates Handover 0333 requirement for MCP-only agent discovery."
        )

    # REQUIRED: MCP tool reference for instructions
    assert "get_orchestrator_instructions" in prompt, (
        "Staging prompt must reference get_orchestrator_instructions() MCP tool"
    )

    # REQUIRED: Basic identity information
    assert "project-456" in prompt, "Prompt should contain project ID"
    assert tenant_key in prompt, "Prompt should contain tenant key"
    assert "orch-789" in prompt, "Prompt should contain orchestrator ID"


@pytest.mark.asyncio
async def test_staging_prompt_simplified_workflow(db_session: AsyncSession):
    """
    Test that staging prompt uses simplified workflow (not 7-task complex version).

    Per Handover 0333, the simplified prompt should:
    - Be ~50-60 lines (not 200+ lines)
    - Have clear startup sequence
    - Reference get_orchestrator_instructions() for context
    """
    tenant_key = "test-tenant-2"

    # Create test product
    product = Product(
        id="product-abc",
        tenant_key=tenant_key,
        name="Test Product 2",
        description="Another test product"
    )
    db_session.add(product)

    # Create test project
    project = Project(
        id="project-def",
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project 2",
        description="Project requirements here",
        mission="Test mission 2",  # Required field
        context_budget=200000
    )
    db_session.add(project)
    await db_session.commit()

    # Generate staging prompt
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    prompt = await generator.generate_staging_prompt(
        orchestrator_id="orch-xyz",
        project_id=project.id,
        claude_code_mode=True  # Test Claude Code mode
    )

    # Count lines (rough estimate)
    line_count = len(prompt.split('\n'))

    # Should be simplified (not massive 7-task workflow)
    # Allow up to 100 lines for mode-specific instructions
    assert line_count < 100, (
        f"Staging prompt should be simplified (~50-60 lines), got {line_count} lines. "
        "This suggests the old 7-task workflow is still in use."
    )

    # Check for simplified structure
    assert "IDENTITY:" in prompt, "Should have identity section"
    assert "MCP CONNECTION:" in prompt, "Should have MCP connection details"
    assert "STARTUP SEQUENCE:" in prompt or "WORKFLOW:" in prompt, "Should have startup/workflow steps"


@pytest.mark.asyncio
async def test_claude_code_mode_instructions(db_session: AsyncSession):
    """
    Test that Claude Code mode includes proper Task tool instructions.

    Per Handover 0333, Claude Code mode should:
    - Explain Task tool usage
    - Clarify agent_type vs agent_name parameters
    - NOT include shell commands
    """
    tenant_key = "test-tenant-3"

    # Create test product
    product = Product(
        id="product-ghi",
        tenant_key=tenant_key,
        name="Test Product 3",
        description="CC mode test"
    )
    db_session.add(product)

    # Create test project
    project = Project(
        id="project-jkl",
        tenant_key=tenant_key,
        product_id=product.id,
        name="Test Project 3",
        description="CC test project",
        mission="Test mission 3",  # Required field
        context_budget=200000
    )
    db_session.add(project)
    await db_session.commit()

    # Generate staging prompt in Claude Code mode
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    prompt = await generator.generate_staging_prompt(
        orchestrator_id="orch-cc",
        project_id=project.id,
        claude_code_mode=True
    )

    # Should have Claude Code specific instructions
    cc_indicators = [
        "Claude Code CLI",
        "Task tool",
        "agent_display_name",
        "get_agent_mission"
    ]

    for indicator in cc_indicators:
        assert indicator in prompt, (
            f"Claude Code mode prompt should mention '{indicator}'"
        )
