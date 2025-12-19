"""
Unit tests for workflow instructions in agent spawn prompts and protocols.

Validates that TodoWrite and progress reporting instructions are present
and correctly formatted in all three layers:
1. Spawn prompt (orchestration.py)
2. Agent protocol (orchestration_service.py)
3. Agent templates (.claude/agents/*.md)

Related to: Handover 0361 Issue 4
"""

import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, Project, AgentTemplate, MCPAgentJob
from src.giljo_mcp.tools.orchestration import spawn_agent_job
from src.giljo_mcp.services.orchestration_service import _generate_agent_protocol
from tests.fixtures.base_fixtures import db_session


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def workflow_tenant():
    """Unique tenant for workflow tests"""
    return f"workflow_tenant_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def workflow_product(db_session, workflow_tenant):
    """Product for workflow testing"""
    product = Product(
        id=str(uuid.uuid4()),
        name=f"WorkflowProd_{uuid.uuid4().hex[:6]}",
        description="Product for workflow instruction testing",
        product_type="backend_service",
        tenant_key=workflow_tenant,
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def workflow_project(db_session, workflow_product, workflow_tenant):
    """Project for workflow testing"""
    project = Project(
        id=str(uuid.uuid4()),
        product_id=workflow_product.id,
        name=f"WorkflowProject_{uuid.uuid4().hex[:6]}",
        description="Test project for workflow instructions",
        status="created",
        tenant_key=workflow_tenant,
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def workflow_template(db_session, workflow_product, workflow_tenant):
    """Active agent template for workflow testing"""
    template = AgentTemplate(
        id=str(uuid.uuid4()),
        name="implementer",
        role="Code Implementation Specialist",
        description="Implements features",
        tenant_key=workflow_tenant,
        product_id=workflow_product.id,
        is_active=True,
        version="1.0.0",
        template_content="# Implementer

Implements code.",
    )
    db_session.add(template)
    await db_session.flush()
    return template
