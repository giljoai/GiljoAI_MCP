"""
Test Suite for ThinClientPromptGenerator Deprecation (Handover 0253 Phase 1)

This module tests the deprecation of generate_execution_prompt() and its
redirection to generate_staging_prompt(). Tests follow strict TDD discipline.

Test Coverage:
1. Deprecation warning logged when generate_execution_prompt() is called
2. generate_execution_prompt() redirects to generate_staging_prompt()
3. generate_staging_prompt() documentation enhanced for universal usage

Author: GiljoAI TDD Implementor Agent
Date: 2025-11-28
Priority: P1 - CRITICAL (Handover 0253)
TDD Phase: RED ❌ (Tests written FIRST, must FAIL initially)
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.mark.asyncio
async def test_generate_execution_prompt_logs_deprecation_warning(
    db_session: AsyncSession, caplog
):
    """
    TEST 1: Deprecation Warning Logged

    BEHAVIOR: When generate_execution_prompt() is called, it should log a
    deprecation warning with structured metadata.

    GIVEN: A valid orchestrator job, project, and database session
    WHEN: generate_execution_prompt() is called
    THEN: A deprecation warning is logged with:
        - Message: "generate_execution_prompt() is deprecated. Use generate_staging_prompt() for universal prompt generation."
        - Level: WARNING
        - Structured metadata: method_called, recommended_method, orchestrator_job_id, project_id

    TDD STATUS: RED ❌ (Expected to FAIL - deprecation not yet implemented)
    """
    # ARRANGE
    tenant_key = "test_tenant_deprecation"

    # Create product
    product = Product(
        id="prod-dep-001",
        name="Deprecation Test Product",
        tenant_key=tenant_key,
        config_data={}
    )
    db_session.add(product)

    # Create user
    user = User(
        id="user-dep-001",
        username="deprecationuser",
        tenant_key=tenant_key,
        field_priority_config={}
    )
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-dep-001",
        name="Deprecation Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Deprecation test description",
        mission="Deprecation test mission",
        context_budget=100000
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator_job = AgentExecution(
        job_id="orch-dep-001",
        agent_name="orchestrator",
        agent_display_name="orchestrator",
        project_id=project.id,
        tenant_key=tenant_key,
        status="working",
        mission="Test orchestrator mission"
    )
    db_session.add(orchestrator_job)
    await db_session.commit()

    # Configure logging capture
    caplog.clear()
    caplog.set_level(logging.WARNING)

    # ACT
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

    # Call deprecated method
    await generator.generate_execution_prompt(
        orchestrator_job_id=orchestrator_job.job_id,
        project_id=project.id,
        claude_code_mode=False
    )

    # ASSERT
    # Check that deprecation warning was logged
    assert any(
        "generate_execution_prompt() is deprecated" in record.message
        and record.levelname == "WARNING"
        for record in caplog.records
    ), "Deprecation warning should be logged at WARNING level"

    # Verify warning message contains recommendation
    deprecation_records = [
        record for record in caplog.records
        if "generate_execution_prompt() is deprecated" in record.message
    ]
    assert len(deprecation_records) > 0, "At least one deprecation warning should be logged"

    warning_record = deprecation_records[0]
    assert "generate_staging_prompt()" in warning_record.message, \
        "Deprecation warning should recommend generate_staging_prompt()"

    # Verify structured logging metadata (if using extra={})
    # This checks that the warning includes context for debugging
    assert hasattr(warning_record, "orchestrator_job_id") or \
           orchestrator_job.job_id in warning_record.message, \
        "Deprecation warning should include orchestrator_job_id in metadata or message"


@pytest.mark.asyncio
async def test_generate_execution_prompt_redirects_to_generate_staging_prompt(
    db_session: AsyncSession
):
    """
    TEST 2: Redirect to generate_staging_prompt()

    BEHAVIOR: generate_execution_prompt() should internally call
    generate_staging_prompt() with correctly mapped parameters.

    GIVEN: A valid orchestrator job and project
    WHEN: generate_execution_prompt() is called
    THEN: It should call generate_staging_prompt() internally
        - orchestrator_job_id → orchestrator_id
        - project_id → project_id
        - claude_code_mode → claude_code_mode
    AND: Return value should be identical to generate_staging_prompt()

    TDD STATUS: RED ❌ (Expected to FAIL - redirect not yet implemented)
    """
    # ARRANGE
    tenant_key = "test_tenant_redirect"

    # Create product
    product = Product(
        id="prod-redirect-001",
        name="Redirect Test Product",
        tenant_key=tenant_key,
        config_data={}
    )
    db_session.add(product)

    # Create user
    user = User(
        id="user-redirect-001",
        username="redirectuser",
        tenant_key=tenant_key,
        field_priority_config={}
    )
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-redirect-001",
        name="Redirect Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Redirect test description",
        mission="Redirect test mission",
        context_budget=100000
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator_job = AgentExecution(
        job_id="orch-redirect-001",
        agent_name="orchestrator",
        agent_display_name="orchestrator",
        project_id=project.id,
        tenant_key=tenant_key,
        status="working",
        mission="Test orchestrator mission"
    )
    db_session.add(orchestrator_job)
    await db_session.commit()

    # ACT
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

    # Call generate_staging_prompt() directly (expected behavior)
    expected_prompt = await generator.generate_staging_prompt(
        orchestrator_id=orchestrator_job.job_id,
        project_id=project.id,
        claude_code_mode=False
    )

    # Call deprecated generate_execution_prompt() (should redirect)
    actual_prompt = await generator.generate_execution_prompt(
        orchestrator_job_id=orchestrator_job.job_id,
        project_id=project.id,
        claude_code_mode=False
    )

    # ASSERT
    # Both methods should return the SAME prompt
    assert actual_prompt == expected_prompt, \
        "generate_execution_prompt() should return identical prompt to generate_staging_prompt()"

    # Verify prompt content is valid (contains staging workflow markers)
    assert "STAGING WORKFLOW" in actual_prompt, \
        "Redirected prompt should contain staging workflow content"
    assert "TASK 1: IDENTITY & CONTEXT VERIFICATION" in actual_prompt, \
        "Redirected prompt should contain Task 1 from staging workflow"


@pytest.mark.asyncio
async def test_generate_staging_prompt_has_enhanced_documentation(
    db_session: AsyncSession
):
    """
    TEST 3: Enhanced generate_staging_prompt() Documentation

    BEHAVIOR: generate_staging_prompt() docstring should clearly state:
    - It is the UNIVERSAL orchestrator prompt generator
    - It works in ALL scenarios (fresh/existing/crashed)
    - It uses the "fetch-first pattern"

    GIVEN: ThinClientPromptGenerator class
    WHEN: Inspecting generate_staging_prompt() method
    THEN: Docstring should contain:
        - "UNIVERSAL" or "universal"
        - "fetch-first pattern" or "fetch-first"
        - "all scenarios" or reference to fresh/existing/crashed

    TDD STATUS: RED ❌ (Expected to FAIL - documentation not yet enhanced)
    """
    # ARRANGE
    # Get the docstring of generate_staging_prompt()
    docstring = ThinClientPromptGenerator.generate_staging_prompt.__doc__

    # ASSERT
    assert docstring is not None, "generate_staging_prompt() should have a docstring"

    # Check for "UNIVERSAL" keyword
    assert "UNIVERSAL" in docstring.upper() or "universal" in docstring.lower(), \
        "Docstring should clearly state this is a UNIVERSAL prompt generator"

    # Check for "fetch-first pattern" reference
    assert "fetch-first" in docstring.lower() or "fetch first" in docstring.lower(), \
        "Docstring should mention the 'fetch-first pattern'"

    # Check for scenario coverage (fresh/existing/crashed/all scenarios)
    scenario_keywords = [
        "all scenarios",
        "fresh",
        "existing",
        "crashed",
        "any scenario",
        "any state"
    ]
    assert any(keyword in docstring.lower() for keyword in scenario_keywords), \
        f"Docstring should mention scenario coverage (one of: {scenario_keywords})"


@pytest.mark.asyncio
async def test_generate_execution_prompt_parameter_mapping_with_claude_code_mode(
    db_session: AsyncSession
):
    """
    TEST 4: Parameter Mapping with claude_code_mode=True

    BEHAVIOR: generate_execution_prompt() should correctly map parameters
    when claude_code_mode=True.

    GIVEN: A valid orchestrator job and project
    WHEN: generate_execution_prompt(claude_code_mode=True) is called
    THEN: generate_staging_prompt(claude_code_mode=True) is called internally
    AND: Returned prompt reflects Claude Code CLI mode

    TDD STATUS: RED ❌ (Expected to FAIL - redirect not yet implemented)
    """
    # ARRANGE
    tenant_key = "test_tenant_claude_code"

    # Create product
    product = Product(
        id="prod-cc-001",
        name="Claude Code Test Product",
        tenant_key=tenant_key,
        config_data={}
    )
    db_session.add(product)

    # Create user
    user = User(
        id="user-cc-001",
        username="claudecodeuser",
        tenant_key=tenant_key,
        field_priority_config={}
    )
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-cc-001",
        name="Claude Code Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Claude Code test description",
        mission="Claude Code test mission",
        context_budget=100000
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator_job = AgentExecution(
        job_id="orch-cc-001",
        agent_name="orchestrator",
        agent_display_name="orchestrator",
        project_id=project.id,
        tenant_key=tenant_key,
        status="working",
        mission="Test orchestrator mission"
    )
    db_session.add(orchestrator_job)
    await db_session.commit()

    # ACT
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

    # Call generate_staging_prompt() directly with claude_code_mode=True
    expected_prompt = await generator.generate_staging_prompt(
        orchestrator_id=orchestrator_job.job_id,
        project_id=project.id,
        claude_code_mode=True
    )

    # Call deprecated generate_execution_prompt() with claude_code_mode=True
    actual_prompt = await generator.generate_execution_prompt(
        orchestrator_job_id=orchestrator_job.job_id,
        project_id=project.id,
        claude_code_mode=True
    )

    # ASSERT
    # Both methods should return the SAME prompt
    assert actual_prompt == expected_prompt, \
        "generate_execution_prompt(claude_code_mode=True) should return identical prompt to generate_staging_prompt(claude_code_mode=True)"

    # Verify prompt reflects Claude Code CLI mode
    assert "Claude Code CLI" in actual_prompt or "claude_code" in actual_prompt.lower(), \
        "Prompt should reflect Claude Code CLI mode when claude_code_mode=True"
