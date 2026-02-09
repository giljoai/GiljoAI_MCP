"""
Test Suite for Agent Templates in Context String (Handover 0306)

This module tests the integration of agent templates into orchestrator context strings
using the ThinClientPromptGenerator. Tests follow strict TDD discipline.

Test Coverage:
1. Agent templates appear in context string (section presence & ordering)
2. Priority levels control detail (Priority 1/2/3/Unassigned)
3. Token accounting includes agent template tokens
4. Multi-tenant isolation (templates scoped by tenant_key)
5. Default priority behavior (Priority 2 when no user config)

Author: GiljoAI Development Team
Date: 2025-11-17
Priority: P2 - MEDIUM

Updated: 2026-02-08 (0730 series)
- Removed context_budget from Project (not a valid field)
- Added Organization creation for User.org_id NOT NULL constraint (0424j)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, Product, Project, User
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


async def create_test_org(session: AsyncSession, tenant_key: str) -> Organization:
    """Helper to create an organization for test users (0424j: User.org_id NOT NULL)."""
    org = Organization(
        tenant_key=tenant_key,
        name=f"Test Org {tenant_key}",
        slug=f"test-org-{tenant_key.replace('_', '-')}",
        is_active=True,
    )
    session.add(org)
    await session.flush()
    return org


@pytest.mark.asyncio
async def test_thin_prompt_contains_core_structure(db_session: AsyncSession):
    """
    BEHAVIOR: Thin prompt contains essential orchestrator structure

    Updated 0730 series: Thin prompts do NOT embed agent templates inline.
    Agent templates are fetched via MCP tool get_orchestrator_instructions().

    GIVEN: A product with a project
    WHEN: Generating thin prompt
    THEN: Prompt contains IDENTITY, MCP CONNECTION, YOUR ROLE, and WORKFLOW sections
    AND: Prompt references get_orchestrator_instructions for context fetching
    """
    # ARRANGE
    tenant_key = "test_tenant"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key)

    # Create product
    product = Product(id="prod-001", name="Test Product", tenant_key=tenant_key, config_data={})
    db_session.add(product)

    # Create user with field priority config
    user = User(
        id="user-001",
        username="testuser",
        tenant_key=tenant_key,
        org_id=org.id,  # 0424j: User.org_id NOT NULL
        field_priority_config={
            "agent_templates": 2,  # High Priority
            "tech_stack.languages": 1,
            "codebase_summary": 2,
        },
    )
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-001",
        name="Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Test project description",
        mission="Test project mission",
    )
    db_session.add(project)

    # Create agent templates (stored in DB, fetched via MCP tools at runtime)
    templates_data = [
        {
            "name": "implementer",
            "role": "Backend implementation specialist",
            "description": "Implements backend features",
            "meta_data": {
                "capabilities": ["Python", "FastAPI", "SQLAlchemy"],
                "expertise": ["API design", "database schema"],
                "typical_tasks": ["Implement features", "write service methods"],
            },
        },
        {
            "name": "tester",
            "role": "Quality assurance specialist",
            "description": "Writes and runs tests",
            "meta_data": {
                "capabilities": ["pytest", "integration testing"],
                "expertise": ["Test suite design", "coverage analysis"],
                "typical_tasks": ["Write unit tests", "create integration tests"],
            },
        },
        {
            "name": "documenter",
            "role": "Documentation specialist",
            "description": "Creates documentation",
            "meta_data": {
                "capabilities": ["Markdown", "technical writing"],
                "expertise": ["User guides", "API documentation"],
                "typical_tasks": ["Write docs", "create tutorials"],
            },
        },
    ]

    for template_data in templates_data:
        template = AgentTemplate(
            tenant_key=tenant_key,
            product_id=product.id,
            name=template_data["name"],
            role=template_data["role"],
            category="role",
            description=template_data["description"],
            system_instructions=f"System instructions for {template_data['name']}",
            meta_data=template_data["meta_data"],
        )
        db_session.add(template)

    await db_session.commit()

    # ACT
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(
        project_id=project.id, user_id=user.id, field_priorities=user.field_priority_config
    )
    thin_prompt = result["thin_prompt"]

    # ASSERT - Core structure present (Handover 0315: thin prompt architecture)
    assert "IDENTITY:" in thin_prompt, "IDENTITY section missing from thin prompt"
    assert "MCP CONNECTION:" in thin_prompt, "MCP CONNECTION section missing from thin prompt"
    assert "YOUR ROLE:" in thin_prompt, "YOUR ROLE section missing from thin prompt"

    # Verify MCP tool reference for context fetching (NOT inline agent templates)
    assert "get_orchestrator_instructions" in thin_prompt, (
        "Thin prompt should reference get_orchestrator_instructions MCP tool for context fetching"
    )

    # Verify section ordering: IDENTITY -> MCP CONNECTION -> YOUR ROLE
    identity_index = thin_prompt.find("IDENTITY:")
    mcp_index = thin_prompt.find("MCP CONNECTION:")
    role_index = thin_prompt.find("YOUR ROLE:")

    assert identity_index < mcp_index < role_index, (
        "Sections should be ordered: IDENTITY -> MCP CONNECTION -> YOUR ROLE"
    )


@pytest.mark.asyncio
async def test_thin_prompt_is_concise(db_session: AsyncSession):
    """
    BEHAVIOR: Thin prompt is designed to be concise (~600 tokens)

    Updated 0730 series: Agent template priority handling moved to MCP tools.
    The thin prompt itself does NOT vary based on agent_templates priority.
    Priority filtering happens when orchestrator calls get_orchestrator_instructions().

    GIVEN: Agent templates with full metadata
    WHEN: Generating thin prompt with various priority settings
    THEN: Thin prompt remains concise (MCP tool references, not inline content)
    AND: All priorities produce similar token counts (templates fetched at runtime)
    """
    # ARRANGE
    tenant_key = "test_tenant_priority"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key)

    # Create product
    product = Product(id="prod-priority", name="Priority Test Product", tenant_key=tenant_key, config_data={})
    db_session.add(product)

    # Create user (will update field_priority_config for each test case)
    user = User(id="user-priority", username="priorityuser", tenant_key=tenant_key, org_id=org.id, field_priority_config={})
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-priority",
        name="Priority Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Priority test description",
        mission="Priority test mission",
    )
    db_session.add(project)

    # Create agent template with full metadata
    template = AgentTemplate(
        tenant_key=tenant_key,
        product_id=product.id,
        name="implementer",
        role="Backend implementation specialist",
        category="role",
        description="Full metadata template",
        system_instructions="System instructions",
        meta_data={
            "capabilities": ["Python", "FastAPI"],
            "expertise": ["API design", "database schema"],
            "typical_tasks": ["Implement features", "write service methods"],
        },
    )
    db_session.add(template)
    await db_session.commit()

    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

    # TEST: Thin prompt should be concise regardless of priority settings
    # (Agent templates NOT embedded inline - fetched via MCP tools)
    user.field_priority_config = {"agent_templates": 1}  # Priority 1
    await db_session.commit()

    result_p1 = await generator.generate(
        project_id=project.id, user_id=user.id, field_priorities=user.field_priority_config
    )

    # Thin prompt should NOT contain inline agent template content
    # (Agent details are fetched via get_orchestrator_instructions at runtime)
    thin_prompt = result_p1["thin_prompt"]

    # Verify thin prompt is concise (target ~600 tokens = ~2400 chars)
    assert len(thin_prompt) < 5000, f"Thin prompt should be concise, got {len(thin_prompt)} chars"

    # Verify it references MCP tool for context fetching instead of embedding inline
    assert "get_orchestrator_instructions" in thin_prompt, (
        "Thin prompt should reference get_orchestrator_instructions for context fetching"
    )

    # Verify agent template metadata NOT embedded inline
    # (capabilities, expertise, typical_tasks should NOT appear in thin prompt)
    assert "API design" not in thin_prompt, "Agent expertise should NOT be embedded in thin prompt"
    assert "Implement features" not in thin_prompt, "Agent typical_tasks should NOT be embedded in thin prompt"


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
    tenant_key = "test_tenant_tokens"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key)

    # Create product
    product = Product(id="prod-tokens", name="Token Test Product", tenant_key=tenant_key, config_data={})
    db_session.add(product)

    # Create user
    user = User(id="user-tokens", username="tokenuser", tenant_key=tenant_key, org_id=org.id, field_priority_config={})
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-tokens",
        name="Token Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Token test description",
        mission="Token test mission",
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
    result = await generator.generate(
        project_id=project.id, user_id=user.id, field_priorities={"agent_templates": 1}
    )

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
    # Tenant A setup
    tenant_a_key = "tenant_a"

    # Create organizations for both tenants (0424j: User.org_id NOT NULL)
    org_a = await create_test_org(db_session, tenant_a_key)

    product_a = Product(id="prod-a", name="Tenant A Product", tenant_key=tenant_a_key, config_data={})
    db_session.add(product_a)

    user_a = User(
        id="user-a", username="tenant_a_user", tenant_key=tenant_a_key, org_id=org_a.id, field_priority_config={"agent_templates": 2}
    )
    db_session.add(user_a)

    project_a = Project(
        id="proj-a",
        name="Tenant A Project",
        product_id=product_a.id,
        tenant_key=tenant_a_key,
        description="Tenant A description",
        mission="Tenant A mission",
    )
    db_session.add(project_a)

    # Tenant A agent template (stored in DB, fetched via MCP at runtime)
    template_a = AgentTemplate(
        tenant_key=tenant_a_key,
        product_id=product_a.id,
        name="tenant_a_agent",
        role="Tenant A Specialist",
        category="role",
        description="Tenant A exclusive agent",
        system_instructions="Tenant A system instructions",
        meta_data={"capabilities": ["Tenant A Skill"]},
    )
    db_session.add(template_a)

    # Tenant B setup
    tenant_b_key = "tenant_b"
    product_b = Product(id="prod-b", name="Tenant B Product", tenant_key=tenant_b_key, config_data={})
    db_session.add(product_b)

    # Tenant B agent template (should NOT appear in Tenant A's context)
    template_b = AgentTemplate(
        tenant_key=tenant_b_key,
        product_id=product_b.id,
        name="tenant_b_agent",
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
        project_id=project_a.id, user_id=user_a.id, field_priorities=user_a.field_priority_config
    )
    thin_prompt = result_a["thin_prompt"]

    # ASSERT - Thin prompt contains Tenant A's project
    assert "Tenant A Project" in thin_prompt, "Thin prompt should contain project name"

    # Tenant B content should NOT appear (multi-tenant isolation)
    assert "Tenant B Project" not in thin_prompt, "Tenant B's project should NOT appear in Tenant A's thin prompt"
    assert "Tenant B Product" not in thin_prompt, "Tenant B's product should NOT appear in Tenant A's thin prompt"

    # Note: Agent templates are NOT embedded inline - they are fetched via MCP tools
    # Tenant isolation for agent templates is tested in MCP tool tests, not thin prompt tests


@pytest.mark.asyncio
async def test_thin_prompt_works_without_field_priorities(db_session: AsyncSession):
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
    tenant_key = "test_tenant_default"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key)

    # Create product
    product = Product(id="prod-default", name="Default Priority Product", tenant_key=tenant_key, config_data={})
    db_session.add(product)

    # Create user with NO field_priority_config (should use defaults)
    user = User(
        id="user-default",
        username="defaultuser",
        tenant_key=tenant_key,
        org_id=org.id,  # 0424j: User.org_id NOT NULL
        field_priority_config=None,  # No custom config
    )
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-default",
        name="Default Priority Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Default priority test description",
        mission="Default priority test mission",
    )
    db_session.add(project)

    # Create agent template with full metadata (stored in DB, fetched via MCP)
    template = AgentTemplate(
        tenant_key=tenant_key,
        product_id=product.id,
        name="implementer",
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

    # ACT - Generate thin prompt without providing field_priorities
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=None,  # No custom priorities - should use defaults
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
    assert "Default Priority Project" in thin_prompt, "Project name should appear in thin prompt"

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
    tenant_key = "test_tenant_notes_bug"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key)

    # Create product
    product = Product(id="prod-notes-bug", name="Notes Bug Test Product", tenant_key=tenant_key, config_data={})
    db_session.add(product)

    # Create user
    user = User(id="user-notes-bug", username="notesbuguser", tenant_key=tenant_key, org_id=org.id, field_priority_config={})
    db_session.add(user)

    # Create project with description
    project_description = "This is the project description field that should appear in context"
    project = Project(
        id="proj-notes-bug",
        name="Notes Bug Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description=project_description,
        mission="Test mission for notes bug",
    )
    db_session.add(project)
    await db_session.commit()

    # ACT - Generate context (should NOT raise AttributeError on project.notes)
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(project_id=project.id, user_id=user.id, field_priorities={})
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
