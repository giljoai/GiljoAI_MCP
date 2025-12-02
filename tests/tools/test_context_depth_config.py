"""
Test suite for context orchestration depth configuration (Handover 0281 Phase 3).

Tests the depth config implementation for:
- Vision document chunking (light/moderate/heavy)
- 360 Memory pagination (1/3/5/10 projects)
- Git commit limiting (5/15/25 commits)
- Agent template detail levels (minimal/standard/full)

Test-Driven Development (TDD) Approach:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Optimize and clean up
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, List, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.products import VisionDocument
from src.giljo_mcp.models.context import MCPContextIndex
from src.giljo_mcp.models.templates import AgentTemplate


# ============================================================================
# Phase 3: Depth Config Implementation Tests (Handover 0281)
# ============================================================================


@pytest.mark.asyncio
class TestVisionDocumentDepthControl:
    """Test vision document chunking depth control (Task 3.1)."""

    async def test_vision_chunking_light_returns_exactly_2_chunks(self, db_session: AsyncSession):
        """
        GIVEN a product with 6 vision document chunks in database
        WHEN _fetch_vision_documents() is called with depth="light"
        THEN exactly 2 chunks should be returned (light = 2 chunks)
        """
        from src.giljo_mcp.tools.orchestration import _fetch_vision_documents

        # Setup: Create product with 6 vision chunks
        tenant_key = str(uuid4())
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product with vision"
        )
        db_session.add(product)
        await db_session.commit()

        # Create vision document
        vision_doc = VisionDocument(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            document_name="Primary Vision",
            document_type="vision",
            vision_document="Test vision content",
            storage_type="inline",
            chunked=True,
            chunk_count=6
        )
        db_session.add(vision_doc)
        await db_session.commit()

        # Create 6 chunks
        for i in range(6):
            chunk = MCPContextIndex(
                id=str(uuid4()),
                tenant_key=tenant_key,
                vision_document_id=vision_doc.id,
                chunk_content=f"Chunk {i+1} content",
                chunk_number=i+1,
                total_chunks=6,
                context_type="vision_document"
            )
            db_session.add(chunk)
        await db_session.commit()

        # Act: Fetch with depth="light"
        result = await _fetch_vision_documents(
            product_id=product.id,
            depth="light",
            tenant_key=tenant_key,
            db=db_session
        )

        # Assert: Exactly 2 chunks
        assert len(result) == 2, "Light depth should return exactly 2 chunks"
        assert all(isinstance(chunk, dict) for chunk in result)
        assert all("chunk_content" in chunk for chunk in result)

    async def test_vision_chunking_moderate_returns_exactly_4_chunks(self, db_session: AsyncSession):
        """
        GIVEN a product with 6 vision document chunks
        WHEN _fetch_vision_documents() is called with depth="moderate"
        THEN exactly 4 chunks should be returned
        """
        from src.giljo_mcp.tools.orchestration import _fetch_vision_documents

        # Setup: Create product with 6 vision chunks
        tenant_key = str(uuid4())
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product"
        )
        db_session.add(product)
        await db_session.commit()

        vision_doc = VisionDocument(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            document_name="Primary Vision",
            document_type="vision",
            vision_document="Test content",
            storage_type="inline",
            chunked=True,
            chunk_count=6
        )
        db_session.add(vision_doc)
        await db_session.commit()

        for i in range(6):
            chunk = MCPContextIndex(
                id=str(uuid4()),
                tenant_key=tenant_key,
                vision_document_id=vision_doc.id,
                chunk_content=f"Chunk {i+1}",
                chunk_number=i+1,
                total_chunks=6,
                context_type="vision_document"
            )
            db_session.add(chunk)
        await db_session.commit()

        # Act
        result = await _fetch_vision_documents(
            product_id=product.id,
            depth="moderate",
            tenant_key=tenant_key,
            db=db_session
        )

        # Assert
        assert len(result) == 4, "Moderate depth should return exactly 4 chunks"

    async def test_vision_chunking_heavy_returns_exactly_6_chunks(self, db_session: AsyncSession):
        """
        GIVEN a product with 6 vision chunks
        WHEN depth="heavy"
        THEN return all 6 chunks
        """
        from src.giljo_mcp.tools.orchestration import _fetch_vision_documents

        tenant_key = str(uuid4())
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product"
        )
        db_session.add(product)
        await db_session.commit()

        vision_doc = VisionDocument(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            document_name="Vision",
            document_type="vision",
            vision_document="Content",
            storage_type="inline",
            chunked=True,
            chunk_count=6
        )
        db_session.add(vision_doc)
        await db_session.commit()

        for i in range(6):
            chunk = MCPContextIndex(
                id=str(uuid4()),
                tenant_key=tenant_key,
                vision_document_id=vision_doc.id,
                chunk_content=f"Chunk {i+1}",
                chunk_number=i+1,
                total_chunks=6,
                context_type="vision_document"
            )
            db_session.add(chunk)
        await db_session.commit()

        result = await _fetch_vision_documents(
            product_id=product.id,
            depth="heavy",
            tenant_key=tenant_key,
            db=db_session
        )

        assert len(result) == 6, "Heavy depth should return all 6 chunks"

    async def test_vision_chunking_none_returns_empty_list(self, db_session: AsyncSession):
        """
        GIVEN a product with vision chunks
        WHEN depth="none"
        THEN return empty list
        """
        from src.giljo_mcp.tools.orchestration import _fetch_vision_documents

        tenant_key = str(uuid4())
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product"
        )
        db_session.add(product)
        await db_session.commit()

        result = await _fetch_vision_documents(
            product_id=product.id,
            depth="none",
            tenant_key=tenant_key,
            db=db_session
        )

        assert result == [], "None depth should return empty list"


@pytest.mark.asyncio
class TestMemoryPagination:
    """Test 360 Memory pagination (Task 3.2)."""

    async def test_memory_pagination_returns_exactly_3_projects(self, db_session: AsyncSession):
        """
        GIVEN a product with 10 project history entries
        WHEN _fetch_360_memory() is called with depth=3
        THEN exactly 3 most recent projects returned in reverse chronological order
        """
        from src.giljo_mcp.tools.orchestration import _fetch_360_memory

        # Setup: Create product with 10 sequential history entries
        tenant_key = str(uuid4())
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            product_memory={
                "sequential_history": [
                    {"sequence": i, "summary": f"Project {i}", "timestamp": f"2025-11-{i:02d}T10:00:00Z"}
                    for i in range(1, 11)
                ]
            }
        )
        db_session.add(product)
        await db_session.commit()

        # Act
        result = await _fetch_360_memory(
            product_id=product.id,
            depth=3,
            tenant_key=tenant_key,
            db=db_session
        )

        # Assert
        assert len(result) == 3, "Depth=3 should return exactly 3 projects"
        # Verify reverse chronological (most recent first)
        assert result[0]["sequence"] > result[1]["sequence"]
        assert result[1]["sequence"] > result[2]["sequence"]

    async def test_memory_pagination_returns_exactly_1_project(self, db_session: AsyncSession):
        """
        GIVEN 10 project history entries
        WHEN depth=1
        THEN return exactly 1 most recent project
        """
        from src.giljo_mcp.tools.orchestration import _fetch_360_memory

        tenant_key = str(uuid4())
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            product_memory={
                "sequential_history": [
                    {"sequence": i, "summary": f"Project {i}"}
                    for i in range(1, 11)
                ]
            }
        )
        db_session.add(product)
        await db_session.commit()

        result = await _fetch_360_memory(
            product_id=product.id,
            depth=1,
            tenant_key=tenant_key,
            db=db_session
        )

        assert len(result) == 1, "Depth=1 should return exactly 1 project"


@pytest.mark.asyncio
class TestGitCommitLimiting:
    """Test git history commit limiting (Task 3.3)."""

    async def test_git_commit_limiting_returns_exactly_5_commits(self, db_session: AsyncSession):
        """
        GIVEN a product with 25 commits in product_memory
        WHEN _fetch_git_history() is called with depth=5
        THEN exactly 5 most recent commits returned
        """
        from src.giljo_mcp.tools.orchestration import _fetch_git_history

        tenant_key = str(uuid4())

        # Create commits across multiple projects
        commits = [
            {"commit_hash": f"abc{i:03d}", "message": f"Commit {i}", "timestamp": f"2025-11-{i%28+1:02d}T10:00:00Z"}
            for i in range(25)
        ]

        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            product_memory={
                "git_integration": {"enabled": True, "repo_url": "https://github.com/test/repo"},
                "sequential_history": [
                    {"sequence": i, "git_commits": commits[i:i+3] if i < 23 else commits[i:]}
                    for i in range(0, 25, 3)
                ]
            }
        )
        db_session.add(product)
        await db_session.commit()

        result = await _fetch_git_history(
            product_id=product.id,
            depth=5,
            tenant_key=tenant_key,
            db=db_session
        )

        assert len(result) == 5, "Depth=5 should return exactly 5 commits"
        assert all("timestamp" in commit for commit in result)

    async def test_git_commit_limiting_returns_empty_when_disabled(self, db_session: AsyncSession):
        """
        GIVEN a product with git integration disabled
        WHEN _fetch_git_history() is called
        THEN return empty list
        """
        from src.giljo_mcp.tools.orchestration import _fetch_git_history

        tenant_key = str(uuid4())
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            product_memory={
                "git_integration": {"enabled": False},
                "sequential_history": []
            }
        )
        db_session.add(product)
        await db_session.commit()

        result = await _fetch_git_history(
            product_id=product.id,
            depth=15,
            tenant_key=tenant_key,
            db=db_session
        )

        assert result == [], "Git disabled should return empty list"


@pytest.mark.asyncio
class TestAgentTemplateDetailControl:
    """Test agent template detail levels (Task 3.4)."""

    async def test_agent_template_detail_minimal_returns_names_only(self, db_session: AsyncSession):
        """
        GIVEN 5 agent templates
        WHEN depth="minimal"
        THEN return only name + agent_type fields (~400 tokens)
        """
        from src.giljo_mcp.tools.orchestration import _fetch_agent_templates

        tenant_key = str(uuid4())

        # Create 5 agent templates
        templates = ["orchestrator", "implementer", "tester", "reviewer", "documenter"]
        for tmpl in templates:
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                name=tmpl,
                role=f"{tmpl.title()} Agent",
                description=f"This is the {tmpl} agent with detailed description",
                expertise=f"Expert in {tmpl} tasks",
                constraints=f"Must follow {tmpl} constraints",
                is_active=True
            )
            db_session.add(template)
        await db_session.commit()

        result = await _fetch_agent_templates(
            tenant_key=tenant_key,
            depth="minimal",
            db=db_session
        )

        assert len(result) == 5, "Should return all 5 templates"
        for template in result:
            assert "name" in template
            assert "role" in template
            assert "description" not in template, "Minimal should exclude description"
            assert "expertise" not in template, "Minimal should exclude expertise"

    async def test_agent_template_detail_standard_includes_descriptions(self, db_session: AsyncSession):
        """
        GIVEN 5 agent templates
        WHEN depth="standard"
        THEN return name + role + description (~1,200 tokens)
        """
        from src.giljo_mcp.tools.orchestration import _fetch_agent_templates

        tenant_key = str(uuid4())

        templates = ["orchestrator", "implementer", "tester"]
        for tmpl in templates:
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                name=tmpl,
                role=f"{tmpl.title()}",
                description=f"Description for {tmpl}",
                expertise=f"Expertise in {tmpl}",
                is_active=True
            )
            db_session.add(template)
        await db_session.commit()

        result = await _fetch_agent_templates(
            tenant_key=tenant_key,
            depth="standard",
            db=db_session
        )

        assert len(result) == 3
        for template in result:
            assert "name" in template
            assert "role" in template
            assert "description" in template, "Standard should include description"
            assert "expertise" not in template, "Standard should exclude expertise"

    async def test_agent_template_detail_full_includes_all_fields(self, db_session: AsyncSession):
        """
        GIVEN 5 agent templates
        WHEN depth="full"
        THEN return complete template with all fields (~2,400 tokens)
        """
        from src.giljo_mcp.tools.orchestration import _fetch_agent_templates

        tenant_key = str(uuid4())

        templates = ["orchestrator", "implementer"]
        for tmpl in templates:
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                name=tmpl,
                role=f"{tmpl.title()}",
                description=f"Description for {tmpl}",
                expertise=f"Expertise in {tmpl}",
                constraints=f"Constraints for {tmpl}",
                is_active=True
            )
            db_session.add(template)
        await db_session.commit()

        result = await _fetch_agent_templates(
            tenant_key=tenant_key,
            depth="full",
            db=db_session
        )

        assert len(result) == 2
        for template in result:
            assert "name" in template
            assert "role" in template
            assert "description" in template
            assert "expertise" in template or "constraints" in template, "Full should include complete details"
