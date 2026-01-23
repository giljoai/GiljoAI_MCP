"""
Test orchestrator template seeding and self-identity retrieval.

Handover 0431: Verify orchestrator template can be seeded and retrieved via
fetch_context(categories=["self_identity"], agent_name="orchestrator").
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_seeder import seed_tenant_templates
from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity


class TestOrchestratorSeeding:
    """Test orchestrator template seeding workflow"""

    @pytest.mark.asyncio
    async def test_orchestrator_template_is_seeded(
        self, db_session, test_tenant_key
    ):
        """Verify orchestrator template is seeded to database"""
        # Seed templates
        seeded = await seed_tenant_templates(
            session=db_session,
            tenant_key=test_tenant_key
        )

        # Verify seeding occurred
        assert seeded > 0, "Templates should have been seeded"

        # Query for orchestrator template
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == test_tenant_key,
            AgentTemplate.role == "orchestrator"
        )
        result = await db_session.execute(stmt)
        orchestrator = result.scalar_one_or_none()

        # Assert orchestrator exists
        assert orchestrator is not None, "Orchestrator template should exist in database"
        assert orchestrator.role == "orchestrator"
        assert orchestrator.name == "orchestrator-coordinator"
        assert orchestrator.is_active is True

    @pytest.mark.asyncio
    async def test_get_self_identity_finds_orchestrator(
        self, db_session, test_tenant_key
    ):
        """Verify get_self_identity() can retrieve orchestrator template"""
        # Seed templates
        await seed_tenant_templates(
            session=db_session,
            tenant_key=test_tenant_key
        )

        # Fetch self-identity
        result = await get_self_identity(
            agent_name="orchestrator-coordinator",
            tenant_key=test_tenant_key,
            session=db_session
        )

        # Verify result structure
        assert result["source"] == "self_identity"
        assert "data" in result
        assert "metadata" in result

        # Verify data fields
        data = result["data"]
        assert data["name"] == "orchestrator-coordinator"
        assert data["role"] == "orchestrator"
        assert len(data["system_instructions"]) > 0
        assert len(data["user_instructions"]) > 0

        # Verify no error in metadata
        assert "error" not in result["metadata"]

    @pytest.mark.asyncio
    async def test_orchestrator_still_protected_from_updates(self):
        """Verify orchestrator remains protected from user modifications"""
        from api.endpoints.templates.crud import _is_system_managed_role

        # Verify protection check
        assert _is_system_managed_role("orchestrator") is True
        assert _is_system_managed_role("implementer") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
