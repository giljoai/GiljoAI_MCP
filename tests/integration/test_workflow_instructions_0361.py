"""
Integration tests for Handover 0361 Issue 4: Agent Workflow Instructions.

Validates that TodoWrite and progress reporting instructions are present
in all three layers:
1. Spawn prompt (orchestration.py)
2. Agent protocol (orchestration_service.py)  
3. Agent templates (.claude/agents/*.md)

This ensures agents receive consistent, mandatory workflow guidance.
"""

import uuid
import pytest
import pytest_asyncio
from pathlib import Path

from src.giljo_mcp.models import Product, Project, AgentTemplate
from src.giljo_mcp.tools.orchestration import spawn_agent_job
from src.giljo_mcp.services.orchestration_service import _generate_agent_protocol
from tests.fixtures.base_fixtures import db_session


@pytest_asyncio.fixture
async def workflow_tenant():
    return f"wf_tenant_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def workflow_product(db_session, workflow_tenant):
    product = Product(
        id=str(uuid.uuid4()),
        name=f"WorkflowProd_{uuid.uuid4().hex[:6]}",
        description="Product for workflow instruction testing",
        tenant_key=workflow_tenant,
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def workflow_project(db_session, workflow_product, workflow_tenant):
    project = Project(
        id=str(uuid.uuid4()),
        product_id=workflow_product.id,
        name=f"WorkflowProject_{uuid.uuid4().hex[:6]}",
        description="Test project for workflow instructions",
        mission="Test mission for workflow validation",
        status="created",
        tenant_key=workflow_tenant,
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def workflow_template(db_session, workflow_product, workflow_tenant):
    template = AgentTemplate(
        id=str(uuid.uuid4()),
        name="implementer",
        role="Code Implementation Specialist",
        description="Implements features",
        tenant_key=workflow_tenant,
        product_id=workflow_product.id,
        is_active=True,
        version="1.0.0",
        template_content="Test template",
    )
    db_session.add(template)
    await db_session.flush()
    return template


class TestWorkflowInstructionsAllLayers:
    @pytest.mark.asyncio
    async def test_layer1_spawn_prompt_has_workflow_requirements(
        self, db_session, workflow_project, workflow_tenant, workflow_template
    ):
        result = await spawn_agent_job(
            agent_type="implementer",
            agent_name="implementer",  # Must match template name
            mission="Test mission",
            project_id=str(workflow_project.id),
            tenant_key=workflow_tenant,
            session=db_session,
        )

        assert result["success"] is True
        prompt = result.get("agent_prompt", "")
        assert "WORKFLOW REQUIREMENTS" in prompt
        assert "MANDATORY" in prompt
        assert "TodoWrite" in prompt

    def test_layer2_protocol_has_mandatory_todowrite(self):
        protocol = _generate_agent_protocol(
            job_id=str(uuid.uuid4()),
            tenant_key="test_tenant",
            agent_name="test-agent",
        )

        assert "MANDATORY" in protocol
        assert "TodoWrite" in protocol
        phase1 = protocol.split("### Phase 2")[0]
        assert "TodoWrite" in phase1

    def test_layer3_templates_have_workflow_protocol(self):
        agent_dir = Path(".claude/agents")
        templates = list(agent_dir.glob("*.md"))

        assert len(templates) == 12

        for template_file in templates:
            content = template_file.read_text(encoding="utf-8")
            assert "Workflow Protocol (MANDATORY)" in content, (
                f"{template_file.name} missing workflow protocol"
            )
            assert "TodoWrite" in content
            assert "in_progress" in content
            assert "completed" in content
