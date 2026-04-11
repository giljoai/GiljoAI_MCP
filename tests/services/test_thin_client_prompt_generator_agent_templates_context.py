# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test Suite for Agent Templates in Context String - Token Estimation, Tenant Isolation, and Defaults

Split from test_thin_client_prompt_generator_agent_templates.py during test reorganization.
Tests token accounting, multi-tenant isolation, default priority behavior, and regression cases.

Original module: Handover 0306
Updated: 0730 series (thin prompt architecture, MCP tool-based context fetching)
Updated: 2026-02-08 (Organization creation for User.org_id NOT NULL constraint)
Updated: 2026-02-09 (UUID fix for test entity conflicts)
"""

import random
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, Product, Project, User
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from tests.services.conftest import create_test_org


@pytest.mark.asyncio
async def test_thin_prompt_token_estimation(db_session: AsyncSession):
    """
    BEHAVIOR: Token estimation is provided for thin prompts

    Updated 0730 series: Agent templates NOT embedded in thin prompt.
    Token count reflects thin prompt structure only (not inline templates).

    GIVEN: A project setup
    WHEN: Generating thin prompt
    THEN: estimated_prompt_tokens is reasonable (~600 tokens target)
    AND: Token count is consistent regardless of agent template priority
    """
    # ARRANGE
    unique_id = str(uuid4())[:8]
    tenant_key = f"test_tenant_tokens_{unique_id}"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key, unique_id)

    # Create product
    product = Product(
        id=str(uuid4()),
        name=f"Token Test Product {unique_id}",
        tenant_key=tenant_key,
    )
    db_session.add(product)

    # Create user (0840d: field_priority_config removed)
    user = User(
        id=str(uuid4()),
        username=f"tokenuser_{unique_id}",
        tenant_key=tenant_key,
        org_id=org.id,
    )
    db_session.add(user)

    # Create project
    project = Project(
        id=str(uuid4()),
        name=f"Token Test Project {unique_id}",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Token test description",
        mission="Token test mission",
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)

    # Create agent template with substantial content
    template = AgentTemplate(
        tenant_key=tenant_key,
        product_id=product.id,
        name="implementer",
        role="Backend implementation specialist",
        category="role",
        description="Template for token accounting test",
        system_instructions="Detailed system instructions for token accounting",
        meta_data={
            "capabilities": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"],
            "expertise": ["API design", "database schema", "service layer architecture"],
            "typical_tasks": ["Implement features", "write service methods", "create endpoints"],
        },
    )
    db_session.add(template)
    await db_session.commit()

    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

    # ACT - Generate thin prompt
    result = await generator.generate(project_id=project.id, user_id=user.id, field_toggles={"agent_templates": True})

    # ASSERT
    # Token estimation should be provided
    assert "estimated_prompt_tokens" in result, "Response should include estimated_prompt_tokens"
    tokens = result["estimated_prompt_tokens"]

    # Thin prompt should be around 600-1000 tokens (not 3500+ like old fat prompts)
    assert 200 < tokens < 1500, f"Thin prompt should be ~600 tokens, got {tokens}"

    # Verify thin_prompt is present
    assert "thin_prompt" in result, "Response should include thin_prompt"
    assert len(result["thin_prompt"]) > 0, "thin_prompt should not be empty"


@pytest.mark.asyncio
async def test_thin_prompt_includes_project_context(db_session: AsyncSession):
    """
    BEHAVIOR: Thin prompt includes project context inline

    Updated 0730 series: Agent templates NOT embedded inline (fetched via MCP).
    However, core project context IS included in thin prompt for efficiency.

    GIVEN: Two products from different tenants
    WHEN: Generating thin prompt for Tenant A's project
    THEN: Thin prompt contains Tenant A's project name
    AND: Thin prompt does NOT contain Tenant B's project details
    """
    # ARRANGE
    unique_id_a = str(uuid4())[:8]
    unique_id_b = str(uuid4())[:8]

    # Tenant A setup
    tenant_a_key = f"tenant_a_{unique_id_a}"

    # Create organizations for both tenants (0424j: User.org_id NOT NULL)
    org_a = await create_test_org(db_session, tenant_a_key, unique_id_a)

    product_a = Product(
        id=str(uuid4()),
        name=f"Tenant A Product {unique_id_a}",
        tenant_key=tenant_a_key,
    )
    db_session.add(product_a)

    user_a = User(
        id=str(uuid4()),
        username=f"tenant_a_user_{unique_id_a}",
        tenant_key=tenant_a_key,
        org_id=org_a.id,
    )
    db_session.add(user_a)

    project_a = Project(
        id=str(uuid4()),
        name=f"Tenant A Project {unique_id_a}",
        product_id=product_a.id,
        tenant_key=tenant_a_key,
        description="Tenant A description",
        mission="Tenant A mission",
        series_number=random.randint(1, 999999),
    )
    db_session.add(project_a)

    # Tenant A agent template (stored in DB, fetched via MCP at runtime)
    template_a = AgentTemplate(
        tenant_key=tenant_a_key,
        product_id=product_a.id,
        name=f"tenant_a_agent_{unique_id_a}",
        role="Tenant A Specialist",
        category="role",
        description="Tenant A exclusive agent",
        system_instructions="Tenant A system instructions",
        meta_data={"capabilities": ["Tenant A Skill"]},
    )
    db_session.add(template_a)

    # Tenant B setup
    tenant_b_key = f"tenant_b_{unique_id_b}"
    product_b = Product(
        id=str(uuid4()),
        name=f"Tenant B Product {unique_id_b}",
        tenant_key=tenant_b_key,
    )
    db_session.add(product_b)

    # Tenant B agent template (should NOT appear in Tenant A's context)
    template_b = AgentTemplate(
        tenant_key=tenant_b_key,
        product_id=product_b.id,
        name=f"tenant_b_agent_{unique_id_b}",
        role="Tenant B Specialist",
        category="role",
        description="Tenant B exclusive agent",
        system_instructions="Tenant B system instructions",
        meta_data={"capabilities": ["Tenant B Skill"]},
    )
    db_session.add(template_b)

    await db_session.commit()

    # ACT - Generate thin prompt for Tenant A
    generator_a = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_a_key)
    result_a = await generator_a.generate(
        project_id=project_a.id, user_id=user_a.id, field_toggles={"agent_templates": True}
    )
    thin_prompt = result_a["thin_prompt"]

    # ASSERT - Thin prompt contains Tenant A's project
    assert f"Tenant A Project {unique_id_a}" in thin_prompt, "Thin prompt should contain project name"

    # Tenant B content should NOT appear (multi-tenant isolation)
    assert f"Tenant B Project {unique_id_b}" not in thin_prompt, (
        "Tenant B's project should NOT appear in Tenant A's thin prompt"
    )
    assert f"Tenant B Product {unique_id_b}" not in thin_prompt, (
        "Tenant B's product should NOT appear in Tenant A's thin prompt"
    )

    # Note: Agent templates are NOT embedded inline - they are fetched via MCP tools
    # Tenant isolation for agent templates is tested in MCP tool tests, not thin prompt tests


@pytest.mark.asyncio
async def test_thin_prompt_works_without_field_toggles(db_session: AsyncSession):
    """
    BEHAVIOR: Thin prompt generation works when user has no field_priority_config

    Updated 0730 series: Agent templates NOT embedded inline.
    Priority handling happens in MCP tools, not thin prompt generation.

    GIVEN: A new user with no field_priority_config set
    WHEN: Generating thin prompt
    THEN: Thin prompt is generated successfully
    AND: Prompt contains core structure (IDENTITY, MCP CONNECTION, YOUR ROLE)
    """
    # ARRANGE
    unique_id = str(uuid4())[:8]
    tenant_key = f"test_tenant_default_{unique_id}"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key, unique_id)

    # Create product
    product = Product(
        id=str(uuid4()),
        name=f"Default Priority Product {unique_id}",
        tenant_key=tenant_key,
    )
    db_session.add(product)

    # Create user with no field priority rows (should use defaults)
    # 0840d: field_priority_config column removed; absence of rows = defaults
    user = User(
        id=str(uuid4()),
        username=f"defaultuser_{unique_id}",
        tenant_key=tenant_key,
        org_id=org.id,  # 0424j: User.org_id NOT NULL
    )
    db_session.add(user)

    # Create project
    project_name = f"Default Priority Project {unique_id}"
    project = Project(
        id=str(uuid4()),
        name=project_name,
        product_id=product.id,
        tenant_key=tenant_key,
        description="Default priority test description",
        mission="Default priority test mission",
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)

    # Create agent template with full metadata (stored in DB, fetched via MCP)
    template = AgentTemplate(
        tenant_key=tenant_key,
        product_id=product.id,
        name=f"implementer_{unique_id}",
        role="Backend implementation specialist",
        category="role",
        description="Default priority test template",
        system_instructions="System instructions",
        meta_data={
            "capabilities": ["Python", "FastAPI"],
            "expertise": ["API design", "database schema"],
            "typical_tasks": ["Implement features", "write service methods"],
        },
    )
    db_session.add(template)
    await db_session.commit()

    # ACT - Generate thin prompt without providing field_toggles
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_toggles=None,  # No custom toggles - should use defaults
    )
    thin_prompt = result["thin_prompt"]

    # ASSERT
    # Thin prompt should be generated successfully
    assert thin_prompt is not None, "Thin prompt should be generated"
    assert len(thin_prompt) > 0, "Thin prompt should not be empty"

    # Core structure should be present
    assert "IDENTITY:" in thin_prompt, "IDENTITY section should be present"
    assert "MCP CONNECTION:" in thin_prompt, "MCP CONNECTION section should be present"
    assert "YOUR ROLE:" in thin_prompt, "YOUR ROLE section should be present"

    # Project name should appear in prompt
    assert project_name in thin_prompt, "Project name should appear in thin prompt"

    # MCP tool reference should be present (for fetching context including agent templates)
    assert "get_orchestrator_instructions" in thin_prompt, (
        "Thin prompt should reference get_orchestrator_instructions for fetching context"
    )


@pytest.mark.asyncio
async def test_project_description_not_notes_in_context_string(db_session: AsyncSession):
    """
    BEHAVIOR: Thin prompt generator should use project.description not project.notes

    REGRESSION TEST for Bug #1: AttributeError 'Project' object has no attribute 'notes'

    GIVEN: A project with a description field
    WHEN: Generating orchestrator context
    THEN: Context string includes project description (NOT project.notes which doesn't exist)
    AND: No AttributeError is raised
    """
    # ARRANGE
    unique_id = str(uuid4())[:8]
    tenant_key = f"test_tenant_notes_bug_{unique_id}"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key, unique_id)

    # Create product
    product = Product(
        id=str(uuid4()),
        name=f"Notes Bug Test Product {unique_id}",
        tenant_key=tenant_key,
    )
    db_session.add(product)

    # Create user (0840d: field_priority_config removed)
    user = User(
        id=str(uuid4()),
        username=f"notesbuguser_{unique_id}",
        tenant_key=tenant_key,
        org_id=org.id,
    )
    db_session.add(user)

    # Create project with description
    project_description = "This is the project description field that should appear in context"
    project = Project(
        id=str(uuid4()),
        name=f"Notes Bug Test Project {unique_id}",
        product_id=product.id,
        tenant_key=tenant_key,
        description=project_description,
        mission="Test mission for notes bug",
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()

    # ACT - Generate context (should NOT raise AttributeError on project.notes)
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(project_id=project.id, user_id=user.id, field_toggles={})
    thin_prompt = result["thin_prompt"]

    # ASSERT
    # Should not raise AttributeError (test passes if we get here)
    assert thin_prompt is not None, "Thin prompt should be generated without errors"

    # Project description should appear in context
    assert project_description in thin_prompt or "project description" in thin_prompt.lower(), (
        "Project description should appear in context string"
    )

    # Should contain PROJECT CONTEXT section
    assert "PROJECT CONTEXT" in thin_prompt, "Context should contain PROJECT CONTEXT section"
