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
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, Product, Project, User
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.mark.asyncio
async def test_agent_templates_included_in_context_string(db_session: AsyncSession):
    """
    BEHAVIOR: Agent templates are formatted and included in orchestrator context string

    GIVEN: A product with 3 agent templates (implementer, tester, documenter)
    WHEN: Generating orchestrator context with agent_templates priority = 2
    THEN: Context string contains "## Available Agents" section with all 3 agents
    AND: Section appears after "MCP CONNECTION" and before "MCP TOOLS AVAILABLE"
    """
    # ARRANGE
    tenant_key = "test_tenant"

    # Create product
    product = Product(
        id="prod-001",
        name="Test Product",
        tenant_key=tenant_key,
        config_data={}
    )
    db_session.add(product)

    # Create user with field priority config
    user = User(
        id="user-001",
        username="testuser",
        tenant_key=tenant_key,
        field_priority_config={
            "agent_templates": 2,  # High Priority
            "tech_stack.languages": 1,
            "codebase_summary": 2
        }
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
        context_budget=100000
    )
    db_session.add(project)

    # Create agent templates
    templates_data = [
        {
            "name": "implementer",
            "role": "Backend implementation specialist",
            "description": "Implements backend features",
            "meta_data": {
                "capabilities": ["Python", "FastAPI", "SQLAlchemy"],
                "expertise": ["API design", "database schema"],
                "typical_tasks": ["Implement features", "write service methods"]
            }
        },
        {
            "name": "tester",
            "role": "Quality assurance specialist",
            "description": "Writes and runs tests",
            "meta_data": {
                "capabilities": ["pytest", "integration testing"],
                "expertise": ["Test suite design", "coverage analysis"],
                "typical_tasks": ["Write unit tests", "create integration tests"]
            }
        },
        {
            "name": "documenter",
            "role": "Documentation specialist",
            "description": "Creates documentation",
            "meta_data": {
                "capabilities": ["Markdown", "technical writing"],
                "expertise": ["User guides", "API documentation"],
                "typical_tasks": ["Write docs", "create tutorials"]
            }
        }
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
            meta_data=template_data["meta_data"]
        )
        db_session.add(template)

    await db_session.commit()

    # ACT
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=user.field_priority_config
    )
    thin_prompt = result["thin_prompt"]

    # ASSERT
    # Agent templates section should be present
    assert "## Available Agents" in thin_prompt, "Agent templates section missing from context"

    # All three agent names should appear (case-insensitive)
    assert "implementer" in thin_prompt.lower(), "Implementer agent missing from context"
    assert "tester" in thin_prompt.lower(), "Tester agent missing from context"
    assert "documenter" in thin_prompt.lower(), "Documenter agent missing from context"

    # Verify section ordering: agents should appear after MCP CONNECTION
    mcp_index = thin_prompt.find("MCP CONNECTION")
    agents_index = thin_prompt.find("## Available Agents")
    assert mcp_index < agents_index, "Agent templates should appear after MCP CONNECTION section"

    # Agents should appear before "YOUR ROLE" section
    role_index = thin_prompt.find("YOUR ROLE:")
    assert agents_index < role_index, "Agent templates should appear before YOUR ROLE section"


@pytest.mark.asyncio
async def test_agent_template_detail_respects_priority_levels(db_session: AsyncSession):
    """
    BEHAVIOR: Agent template detail level varies based on field priority

    GIVEN: Agent templates with full metadata (role, capabilities, expertise, tasks)
    WHEN: Generating context with different priority levels (1, 2, 3, unassigned)
    THEN: Detail level matches priority tier (full, summary, names-only, excluded)

    Priority Levels:
    - Priority 1 (Full): Role, capabilities, expertise, typical tasks
    - Priority 2 (Summary): Role and capabilities only
    - Priority 3 (Names): Name and role only
    - Unassigned (None): Section excluded entirely
    """
    # ARRANGE
    tenant_key = "test_tenant_priority"

    # Create product
    product = Product(
        id="prod-priority",
        name="Priority Test Product",
        tenant_key=tenant_key,
        config_data={}
    )
    db_session.add(product)

    # Create user (will update field_priority_config for each test case)
    user = User(
        id="user-priority",
        username="priorityuser",
        tenant_key=tenant_key,
        field_priority_config={}
    )
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-priority",
        name="Priority Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Priority test description",
        mission="Priority test mission",
        context_budget=100000
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
            "typical_tasks": ["Implement features", "write service methods"]
        }
    )
    db_session.add(template)
    await db_session.commit()

    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

    # TEST CASE 1: Priority 1 (Full Detail)
    user.field_priority_config = {"agent_templates": 1}
    await db_session.commit()

    result_p1 = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=user.field_priority_config
    )
    context_p1 = result_p1["thin_prompt"]

    # Priority 1 should include ALL details
    assert "**Capabilities**:" in context_p1 or "Capabilities:" in context_p1, \
        "Priority 1 should include capabilities"
    assert "**Expertise**:" in context_p1 or "Expertise:" in context_p1, \
        "Priority 1 should include expertise"
    assert "**Typical Tasks**:" in context_p1 or "Typical Tasks:" in context_p1, \
        "Priority 1 should include typical tasks"

    # TEST CASE 2: Priority 2 (Summary - Capabilities Only)
    user.field_priority_config = {"agent_templates": 2}
    await db_session.commit()

    result_p2 = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=user.field_priority_config
    )
    context_p2 = result_p2["thin_prompt"]

    # Priority 2 should include capabilities but NOT expertise or typical tasks
    assert "**Capabilities**:" in context_p2 or "Capabilities:" in context_p2, \
        "Priority 2 should include capabilities"
    assert "**Expertise**:" not in context_p2 and "Expertise:" not in context_p2, \
        "Priority 2 should NOT include expertise"
    assert "**Typical Tasks**:" not in context_p2 and "Typical Tasks:" not in context_p2, \
        "Priority 2 should NOT include typical tasks"

    # TEST CASE 3: Priority 3 (Names and Roles Only)
    user.field_priority_config = {"agent_templates": 3}
    await db_session.commit()

    result_p3 = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=user.field_priority_config
    )
    context_p3 = result_p3["thin_prompt"]

    # Priority 3 should show agent name/role but NO detailed metadata
    assert "implementer" in context_p3.lower(), "Priority 3 should include agent name"
    assert "**Capabilities**:" not in context_p3 and "Capabilities:" not in context_p3, \
        "Priority 3 should NOT include capabilities"

    # TEST CASE 4: Unassigned (Excluded)
    user.field_priority_config = {"agent_templates": None}
    await db_session.commit()

    result_unassigned = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=user.field_priority_config
    )
    context_unassigned = result_unassigned["thin_prompt"]

    # Unassigned priority should completely exclude the section
    assert "## Available Agents" not in context_unassigned, \
        "Unassigned priority should exclude agent templates section entirely"


@pytest.mark.asyncio
async def test_agent_template_token_accounting(db_session: AsyncSession):
    """
    BEHAVIOR: Agent template tokens are counted and included in budget calculations

    GIVEN: Context with agent templates and other sections
    WHEN: Calculating total context tokens
    THEN: Agent template tokens are included in the total count
    AND: Context with agents has more tokens than without agents
    """
    # ARRANGE
    tenant_key = "test_tenant_tokens"

    # Create product
    product = Product(
        id="prod-tokens",
        name="Token Test Product",
        tenant_key=tenant_key,
        config_data={}
    )
    db_session.add(product)

    # Create user
    user = User(
        id="user-tokens",
        username="tokenuser",
        tenant_key=tenant_key,
        field_priority_config={}
    )
    db_session.add(user)

    # Create project
    project = Project(
        id="proj-tokens",
        name="Token Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Token test description",
        mission="Token test mission",
        context_budget=100000
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
            "typical_tasks": ["Implement features", "write service methods", "create endpoints"]
        }
    )
    db_session.add(template)
    await db_session.commit()

    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)

    # ACT - Generate context WITH agent templates (Priority 1)
    user.field_priority_config = {"agent_templates": 1}
    await db_session.commit()

    result_with_agents = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=user.field_priority_config
    )
    context_with_agents = result_with_agents["thin_prompt"]
    tokens_with = result_with_agents["estimated_prompt_tokens"]

    # ACT - Generate context WITHOUT agent templates (Unassigned)
    user.field_priority_config = {"agent_templates": None}
    await db_session.commit()

    result_without_agents = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=user.field_priority_config
    )
    context_without_agents = result_without_agents["thin_prompt"]
    tokens_without = result_without_agents["estimated_prompt_tokens"]

    # ASSERT
    # Context with agents should have more tokens
    assert tokens_with > tokens_without, \
        f"Context with agents ({tokens_with} tokens) should exceed context without agents ({tokens_without} tokens)"

    # Difference should be meaningful (at least 50 tokens for full detail agent template)
    token_difference = tokens_with - tokens_without
    assert token_difference >= 50, \
        f"Agent template should add at least 50 tokens (actual difference: {token_difference} tokens)"

    # Verify agent section is present in with-agents context
    assert "## Available Agents" in context_with_agents, \
        "Context with agents should contain agent section"

    # Verify agent section is absent in without-agents context
    assert "## Available Agents" not in context_without_agents, \
        "Context without agents should not contain agent section"


@pytest.mark.asyncio
async def test_multi_tenant_agent_template_isolation(db_session: AsyncSession):
    """
    BEHAVIOR: Agent templates respect tenant boundaries

    GIVEN: Two products from different tenants with different agent templates
    WHEN: Generating context for Tenant A's project
    THEN: Only Tenant A's agent templates appear in context (not Tenant B's)
    """
    # ARRANGE
    # Tenant A setup
    tenant_a_key = "tenant_a"
    product_a = Product(
        id="prod-a",
        name="Tenant A Product",
        tenant_key=tenant_a_key,
        config_data={}
    )
    db_session.add(product_a)

    user_a = User(
        id="user-a",
        username="tenant_a_user",
        tenant_key=tenant_a_key,
        field_priority_config={"agent_templates": 2}
    )
    db_session.add(user_a)

    project_a = Project(
        id="proj-a",
        name="Tenant A Project",
        product_id=product_a.id,
        tenant_key=tenant_a_key,
        description="Tenant A description",
        mission="Tenant A mission",
        context_budget=100000
    )
    db_session.add(project_a)

    # Tenant A agent template
    template_a = AgentTemplate(
        tenant_key=tenant_a_key,
        product_id=product_a.id,
        name="tenant_a_agent",
        role="Tenant A Specialist",
        category="role",
        description="Tenant A exclusive agent",
        system_instructions="Tenant A system instructions",
        meta_data={"capabilities": ["Tenant A Skill"]}
    )
    db_session.add(template_a)

    # Tenant B setup
    tenant_b_key = "tenant_b"
    product_b = Product(
        id="prod-b",
        name="Tenant B Product",
        tenant_key=tenant_b_key,
        config_data={}
    )
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
        meta_data={"capabilities": ["Tenant B Skill"]}
    )
    db_session.add(template_b)

    await db_session.commit()

    # ACT - Generate context for Tenant A
    generator_a = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_a_key)
    result_a = await generator_a.generate(
        project_id=project_a.id,
        user_id=user_a.id,
        field_priorities=user_a.field_priority_config
    )
    context_a = result_a["thin_prompt"]

    # ASSERT
    # Tenant A's agent should be present
    assert "tenant_a_agent" in context_a.lower() or "Tenant A Specialist" in context_a, \
        "Tenant A's agent template should appear in Tenant A's context"

    # Tenant B's agent should NOT be present (multi-tenant isolation)
    assert "tenant_b_agent" not in context_a.lower(), \
        "Tenant B's agent should NOT appear in Tenant A's context (tenant isolation violated)"
    assert "Tenant B Specialist" not in context_a, \
        "Tenant B's agent role should NOT appear in Tenant A's context"


@pytest.mark.asyncio
async def test_default_priority_for_agent_templates(db_session: AsyncSession):
    """
    BEHAVIOR: Agent templates default to Priority 2 when user has no custom config

    GIVEN: A new user with no field_priority_config set
    WHEN: Generating orchestrator context
    THEN: Agent templates are included with Priority 2 detail level (summary)
    AND: Capabilities are shown but NOT expertise or typical tasks
    """
    # ARRANGE
    tenant_key = "test_tenant_default"

    # Create product
    product = Product(
        id="prod-default",
        name="Default Priority Product",
        tenant_key=tenant_key,
        config_data={}
    )
    db_session.add(product)

    # Create user with NO field_priority_config (should use defaults)
    user = User(
        id="user-default",
        username="defaultuser",
        tenant_key=tenant_key,
        field_priority_config=None  # No custom config
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
        context_budget=100000
    )
    db_session.add(project)

    # Create agent template with full metadata
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
            "typical_tasks": ["Implement features", "write service methods"]
        }
    )
    db_session.add(template)
    await db_session.commit()

    # ACT - Generate context without providing field_priorities
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities=None  # No custom priorities - should use defaults
    )
    context = result["thin_prompt"]

    # ASSERT
    # Agent templates should be included (not excluded)
    assert "## Available Agents" in context, \
        "Agent templates should be included by default (not excluded)"

    # Default is Priority 2 (summary) - should include role and capabilities
    assert "implementer" in context.lower() or "Backend implementation specialist" in context, \
        "Default priority should show agent name/role"

    # Priority 2 should include capabilities
    assert "**Capabilities**:" in context or "Capabilities:" in context or \
           "Python" in context or "FastAPI" in context, \
        "Default Priority 2 should include capabilities"

    # Priority 2 should NOT include expertise or typical tasks (full detail)
    assert "**Expertise**:" not in context and "Expertise:" not in context, \
        "Default Priority 2 should NOT include expertise (full detail)"
    assert "**Typical Tasks**:" not in context and "Typical Tasks:" not in context, \
        "Default Priority 2 should NOT include typical tasks (full detail)"


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
    
    # Create product
    product = Product(
        id="prod-notes-bug",
        name="Notes Bug Test Product",
        tenant_key=tenant_key,
        config_data={}
    )
    db_session.add(product)
    
    # Create user
    user = User(
        id="user-notes-bug",
        username="notesbuguser",
        tenant_key=tenant_key,
        field_priority_config={}
    )
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
        context_budget=100000
    )
    db_session.add(project)
    await db_session.commit()
    
    # ACT - Generate context (should NOT raise AttributeError on project.notes)
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(
        project_id=project.id,
        user_id=user.id,
        field_priorities={}
    )
    thin_prompt = result["thin_prompt"]
    
    # ASSERT
    # Should not raise AttributeError (test passes if we get here)
    assert thin_prompt is not None, "Thin prompt should be generated without errors"
    
    # Project description should appear in context
    assert project_description in thin_prompt or "project description" in thin_prompt.lower(), \
        "Project description should appear in context string"
    
    # Should contain PROJECT CONTEXT section
    assert "PROJECT CONTEXT" in thin_prompt, "Context should contain PROJECT CONTEXT section"
