"""
Integration Test for Agent Templates in Full Context Workflow (Handover 0306)

This test validates the end-to-end integration of agent templates in orchestrator
context generation, from product creation to final prompt generation.

Workflow:
1. Create product with agent templates
2. Create project linked to product
3. Configure user field priorities
4. Generate orchestrator prompt
5. Verify agent templates appear in correct position with correct detail level
6. Verify token accounting and section ordering

Author: GiljoAI Development Team
Date: 2025-11-17
Priority: P2 - MEDIUM
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, Product, Project, User
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.mark.asyncio
async def test_agent_templates_in_full_context_workflow(db_session: AsyncSession):
    """
    INTEGRATION: Agent templates appear correctly in full context generation workflow

    GIVEN: A product with agent templates, project, and user with field priorities
    WHEN: Generating full orchestrator context
    THEN: Agent templates appear in correct position with correct detail level
    AND: Token accounting includes agent template content
    AND: Section ordering is correct (Memory → Git → Agents → Role → Tools)
    """
    # ARRANGE - Create full product ecosystem
    tenant_key = "integration_test_tenant"

    # Step 1: Create product
    product = Product(
        id="prod-integration",
        name="Integration Test Product",
        tenant_key=tenant_key,
        config_data={
            "tech_stack": {
                "languages": ["Python", "TypeScript"],
                "backend": "FastAPI",
                "frontend": "Vue 3",
                "database": "PostgreSQL",
            },
            "architecture": {"pattern": "Service Layer", "api_style": "REST"},
        },
        product_memory={
            "learnings": [
                {"summary": "Previous project insight 1", "type": "architecture"},
                {"summary": "Previous project insight 2", "type": "testing"},
            ],
            "context": {"objectives": ["Build scalable API", "Maintain >80% test coverage"]},
            "git_integration": {"enabled": True, "default_branch": "main", "commit_limit": 20},
        },
    )
    db_session.add(product)

    # Step 2: Create agent templates for the product
    agent_templates_data = [
        {
            "name": "implementer",
            "role": "Backend implementation specialist",
            "description": "Implements backend features using Python and FastAPI",
            "meta_data": {
                "capabilities": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"],
                "expertise": ["API design", "database schema", "service layer architecture"],
                "typical_tasks": [
                    "Implement features",
                    "Write service methods",
                    "Create API endpoints",
                    "Design database schemas",
                ],
            },
        },
        {
            "name": "tester",
            "role": "Quality assurance specialist",
            "description": "Writes comprehensive tests for backend and integration",
            "meta_data": {
                "capabilities": ["pytest", "integration testing", "test-driven development"],
                "expertise": ["Test suite design", "coverage analysis", "edge case identification"],
                "typical_tasks": [
                    "Write unit tests",
                    "Create integration tests",
                    "Validate functionality",
                    "Review test coverage",
                ],
            },
        },
        {
            "name": "frontend_implementer",
            "role": "Frontend implementation specialist",
            "description": "Builds user interfaces using Vue 3",
            "meta_data": {
                "capabilities": ["Vue 3", "TypeScript", "Vuetify", "Component design"],
                "expertise": ["UI/UX implementation", "State management", "Component architecture"],
                "typical_tasks": [
                    "Build Vue components",
                    "Implement UI features",
                    "Integrate with backend APIs",
                    "Ensure responsive design",
                ],
            },
        },
    ]

    for template_data in agent_templates_data:
        template = AgentTemplate(
            tenant_key=tenant_key,
            product_id=product.id,
            name=template_data["name"],
            role=template_data["role"],
            category="role",
            description=template_data["description"],
            system_instructions=f"System instructions for {template_data['name']}",
            meta_data=template_data["meta_data"],
            is_active=True,
        )
        db_session.add(template)

    # Step 3: Create user with field priority configuration
    user = User(
        id="user-integration",
        username="integration_user",
        tenant_key=tenant_key,
        field_priority_config={
            "agent_templates": 2,  # Summary detail level
            "tech_stack.languages": 1,
            "tech_stack.backend": 1,
            "architecture.pattern": 1,
        },
    )
    db_session.add(user)

    # Step 4: Create project
    project = Project(
        id="proj-integration",
        name="Integration Test Project",
        product_id=product.id,
        tenant_key=tenant_key,
        description="This is an integration test project to validate agent templates in context generation workflow.",
        mission="Integration test mission",
        context_budget=150000,
    )
    db_session.add(project)

    await db_session.commit()

    # ACT - Generate orchestrator prompt
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_key)
    result = await generator.generate(
        project_id=project.id, user_id=user.id, field_priorities=user.field_priority_config
    )

    thin_prompt = result["thin_prompt"]
    estimated_tokens = result["estimated_prompt_tokens"]

    # ASSERT - Verify complete integration

    # 1. Agent templates section exists
    assert "## Available Agents" in thin_prompt, "Agent templates section should be present in context"

    # 2. All three agent templates appear
    assert "implementer" in thin_prompt.lower(), "Implementer agent should be present"
    assert "tester" in thin_prompt.lower(), "Tester agent should be present"
    assert "frontend_implementer" in thin_prompt.lower() or "frontend implementer" in thin_prompt.lower(), (
        "Frontend implementer agent should be present"
    )

    # 3. Priority 2 detail level (capabilities present, expertise/tasks absent)
    assert "**Capabilities**:" in thin_prompt or "Capabilities:" in thin_prompt, (
        "Priority 2 should include capabilities"
    )
    assert "**Expertise**:" not in thin_prompt and "Expertise:" not in thin_prompt, (
        "Priority 2 should NOT include expertise"
    )
    assert "**Typical Tasks**:" not in thin_prompt and "Typical Tasks:" not in thin_prompt, (
        "Priority 2 should NOT include typical tasks"
    )

    # 4. Section ordering verification
    # Expected order: IDENTITY → MCP CONNECTION → 360 Memory → Git → Agents → YOUR ROLE → TOOLS
    identity_index = thin_prompt.find("IDENTITY:")
    mcp_index = thin_prompt.find("MCP CONNECTION:")
    memory_index = thin_prompt.find("## 360 Memory System")
    git_index = thin_prompt.find("## Git Integration")
    agents_index = thin_prompt.find("## Available Agents")
    role_index = thin_prompt.find("YOUR ROLE:")
    tools_index = thin_prompt.find("MCP TOOLS AVAILABLE")

    # Verify identity → mcp → memory
    assert identity_index < mcp_index, "IDENTITY should come before MCP CONNECTION"
    assert mcp_index < memory_index, "MCP CONNECTION should come before 360 Memory"

    # Verify memory → git → agents (git may be absent if disabled)
    if git_index > 0:  # Git integration is enabled
        assert memory_index < git_index, "360 Memory should come before Git Integration"
        assert git_index < agents_index, "Git Integration should come before Agent Templates"
    else:
        assert memory_index < agents_index, "360 Memory should come before Agent Templates"

    # Verify agents → role → tools
    assert agents_index < role_index, "Agent Templates should come before YOUR ROLE"
    assert role_index < tools_index, "YOUR ROLE should come before MCP TOOLS AVAILABLE"

    # 5. Token accounting
    assert estimated_tokens > 0, "Estimated tokens should be greater than zero"
    assert estimated_tokens > 100, "Context should include substantial content (>100 tokens)"

    # 6. 360 Memory integration
    assert "Product has 2 previous project learnings" in thin_prompt or "previous project learnings" in thin_prompt, (
        "360 Memory should reference product learnings"
    )

    # 7. Git integration (enabled in product_memory)
    assert "git log" in thin_prompt.lower() or "git integration" in thin_prompt.lower(), (
        "Git integration should be present (enabled in product config)"
    )

    # 8. Multi-tenant isolation (verify tenant_key in prompt)
    assert tenant_key in thin_prompt, "Tenant key should appear in prompt for MCP tool calls"

    # 9. Project identity
    assert project.name in thin_prompt, "Project name should appear in prompt"
    assert "Integration Test Project" in thin_prompt, "Full project name should be present"

    # SUCCESS - All integration checks passed
