# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test Suite for Agent Templates in Context String - Core Structure and Conciseness

Split from test_thin_client_prompt_generator_agent_templates.py during test reorganization.
Tests core prompt structure (sections, ordering) and conciseness behavior.

Original module: Handover 0306
Updated: 0730 series (thin prompt architecture, MCP tool-based context fetching)
"""

import random
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, Product, Project, User
from src.giljo_mcp.models.auth import UserFieldPriority
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from tests.services.conftest import create_test_org


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
    unique_id = str(uuid4())[:8]
    tenant_key = f"test_tenant_{unique_id}"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key, unique_id)

    # Create product
    product = Product(
        id=str(uuid4()),
        name=f"Test Product {unique_id}",
        tenant_key=tenant_key,
    )
    db_session.add(product)

    # Create user (0840d: field_priority_config replaced by user_field_priorities table)
    user = User(
        id=str(uuid4()),
        username=f"testuser_{unique_id}",
        tenant_key=tenant_key,
        org_id=org.id,  # 0424j: User.org_id NOT NULL
    )
    db_session.add(user)

    # Insert field priority rows (0840d: replaces field_priority_config JSONB)
    for category in ["agent_templates", "tech_stack"]:
        db_session.add(
            UserFieldPriority(
                user_id=user.id,
                tenant_key=tenant_key,
                category=category,
                enabled=True,
            )
        )

    # Create project
    project = Project(
        id=str(uuid4()),
        name=f"Test Project {unique_id}",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Test project description",
        mission="Test project mission",
        series_number=random.randint(1, 999999),
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
    field_toggles = {"agent_templates": True, "tech_stack": True}
    result = await generator.generate(project_id=project.id, user_id=user.id, field_toggles=field_toggles)
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
    unique_id = str(uuid4())[:8]
    tenant_key = f"test_tenant_priority_{unique_id}"

    # Create organization for user (0424j: User.org_id NOT NULL)
    org = await create_test_org(db_session, tenant_key, unique_id)

    # Create product
    product = Product(
        id=str(uuid4()),
        name=f"Priority Test Product {unique_id}",
        tenant_key=tenant_key,
    )
    db_session.add(product)

    # Create user (0840d: field_priority_config removed)
    user = User(
        id=str(uuid4()),
        username=f"priorityuser_{unique_id}",
        tenant_key=tenant_key,
        org_id=org.id,
    )
    db_session.add(user)

    # Create project
    project = Project(
        id=str(uuid4()),
        name=f"Priority Test Project {unique_id}",
        product_id=product.id,
        tenant_key=tenant_key,
        description="Priority test description",
        mission="Priority test mission",
        series_number=random.randint(1, 999999),
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

    # TEST: Thin prompt should be concise regardless of toggle settings
    # (Agent templates NOT embedded inline - fetched via MCP tools)
    # 0840d: Insert field priority row instead of setting JSONB
    db_session.add(
        UserFieldPriority(
            user_id=user.id,
            tenant_key=tenant_key,
            category="agent_templates",
            enabled=True,
        )
    )
    await db_session.commit()

    field_toggles_p1 = {"agent_templates": True}
    result_p1 = await generator.generate(project_id=project.id, user_id=user.id, field_toggles=field_toggles_p1)

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
