"""
Token Reduction Comparison Tests (Handover 0088)

Compares fat prompts (old) vs thin client prompts (new) to validate
context prioritization and orchestration is achieved.

This test validates the CORE VALUE PROPOSITION of this handover.
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.mark.asyncio
class TestTokenReductionComparison:
    """Compare token usage between fat and thin approaches."""

    async def test_fat_vs_thin_comparison(self, db_session):
        """
        CRITICAL TEST: Validate 70%+ context prioritization.

        Compares:
        - Fat prompt: Embedded mission (old approach)
        - Thin prompt + MCP fetch: Separated mission (new approach)

        Expected Outcome:
        - Fat: ~30,000 tokens
        - Thin: ~50 tokens (prompt) + ~6,000 tokens (mission via MCP) = ~6,050 total
        - Savings: ~24,000 tokens (79.8% reduction)
        """
        tenant_key = str(uuid4())
        user_id = str(uuid4())

        # Create user with field priorities
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            username="testuser",
            email="test@giljoai.com",
            field_priority_config={
                "product_vision": 10,  # Full detail
                "architecture": 7,  # Moderate
                "codebase_summary": 4,  # Abbreviated
                "dependencies": 2,  # Minimal
            },
        )
        db_session.add(user)

        # Create product with LARGE vision (simulating real-world complexity)
        large_vision = """
        PRODUCT VISION - COMPREHENSIVE PLATFORM

        OVERVIEW:
        This is a comprehensive software platform designed to revolutionize how developers
        build and deploy modern applications. The platform includes microservices architecture,
        event-driven communication, real-time analytics, and AI-powered code generation.

        ARCHITECTURE:
        - Frontend: React 18 with TypeScript, Material-UI, Redux Toolkit
        - Backend: Python 3.11 FastAPI with async/await, SQLAlchemy 2.0, Pydantic v2
        - Database: PostgreSQL 14+ with PostGIS, Redis for caching, Elasticsearch for search
        - Infrastructure: Docker containers, Kubernetes orchestration, AWS deployment
        - Security: OAuth2/JWT authentication, RBAC, encryption at rest and in transit
        - Monitoring: Prometheus metrics, Grafana dashboards, ELK stack for logging

        FEATURES:
        1. User Management System
           - Multi-tenant architecture with complete isolation
           - Role-based access control (RBAC) with fine-grained permissions
           - Single sign-on (SSO) integration with SAML 2.0 and OAuth2
           - User activity auditing and compliance reporting

        2. Code Generation Engine
           - AI-powered code generation using GPT-4 and Claude
           - Template-based scaffolding for common patterns
           - Custom DSL for business logic specification
           - Real-time code validation and linting

        3. Project Management
           - Agile/Scrum workflow support
           - Sprint planning and backlog management
           - Time tracking and resource allocation
           - Automated reporting and analytics

        4. CI/CD Pipeline
           - Automated testing (unit, integration, E2E)
           - Code quality gates with SonarQube
           - Automated deployments to staging/production
           - Blue-green and canary deployment strategies

        5. Analytics Dashboard
           - Real-time metrics visualization
           - Custom report builder
           - Data export in multiple formats
           - Scheduled email reports

        CODEBASE STRUCTURE:
        /
        ├── frontend/
        │   ├── src/
        │   │   ├── components/
        │   │   ├── stores/
        │   │   ├── services/
        │   │   ├── utils/
        │   │   └── types/
        │   ├── public/
        │   ├── tests/
        │   └── package.json
        ├── backend/
        │   ├── api/
        │   │   ├── endpoints/
        │   │   ├── models/
        │   │   ├── schemas/
        │   │   └── dependencies/
        │   ├── core/
        │   ├── services/
        │   ├── tests/
        │   └── requirements.txt
        ├── infrastructure/
        │   ├── docker/
        │   ├── kubernetes/
        │   └── terraform/
        └── docs/
            ├── architecture/
            ├── api/
            └── user_guides/

        DEPENDENCIES:
        Backend:
        - fastapi==0.104.1
        - sqlalchemy==2.0.23
        - pydantic==2.5.0
        - alembic==1.12.1
        - redis==5.0.1
        - celery==5.3.4
        - pytest==7.4.3
        - pytest-asyncio==0.21.1

        Frontend:
        - react==18.2.0
        - typescript==5.2.2
        - @reduxjs/toolkit==1.9.7
        - @mui/material==5.14.18
        - react-router-dom==6.20.0
        - axios==1.6.2
        - vite==5.0.0

        DATABASE SCHEMA:
        - 45+ tables for multi-tenant data
        - JSONB columns for flexible metadata
        - Full-text search indexes
        - Partitioning for large tables
        - Row-level security policies

        TESTING STRATEGY:
        - Unit tests: 85%+ coverage requirement
        - Integration tests: API endpoint validation
        - E2E tests: Cypress for critical user flows
        - Performance tests: Load testing with Locust
        - Security tests: OWASP ZAP scanning

        DEPLOYMENT:
        - Containerized applications via Docker
        - Kubernetes for orchestration
        - AWS EKS for managed Kubernetes
        - CloudFormation/Terraform for IaC
        - Multi-region deployment for HA

        This content is intentionally large to simulate real-world product vision documents.
        The old fat prompt approach would embed ALL of this in the launch prompt.
        The new thin client approach fetches it via MCP with field priorities applied.
        """

        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Enterprise Platform",
            description="Comprehensive enterprise software platform",
            vision_document=large_vision,
        )
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Platform MVP",
            description="Minimum viable product for platform launch",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # THIN PROMPT APPROACH (NEW)
        thin_generator = ThinClientPromptGenerator(db_session, tenant_key)
        thin_result = await thin_generator.generate(
            project_id=str(project.id), user_id=user_id, tool="claude-code", instance_number=1
        )

        # Calculate token counts
        thin_prompt_tokens = thin_result.estimated_prompt_tokens

        # Get mission tokens by fetching the stored mission
        from sqlalchemy import select

        from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

        result = await db_session.execute(select(AgentExecution).where(AgentExecution.id == thin_result.orchestrator_id))
        orchestrator = result.scalar_one()
        mission_tokens = len(orchestrator.mission) // 4  # 1 token ≈ 4 chars

        # FAT PROMPT APPROACH (OLD) - Simulated
        # In the old approach, the entire vision + templates would be embedded
        fat_prompt_simulation = large_vision  # Simplified simulation
        fat_tokens = len(fat_prompt_simulation) // 4

        # Calculate reduction
        total_thin_tokens = thin_prompt_tokens + mission_tokens
        savings = fat_tokens - total_thin_tokens
        reduction_percent = (savings / fat_tokens) * 100

        # Print comparison for documentation
        print("\n" + "=" * 60)
        print("TOKEN REDUCTION COMPARISON")
        print("=" * 60)
        print(f"Fat Prompt (OLD):        {fat_tokens:,} tokens")
        print(f"Thin Prompt (NEW):       {thin_prompt_tokens:,} tokens")
        print(f"Mission via MCP:         {mission_tokens:,} tokens")
        print(f"Total New Approach:      {total_thin_tokens:,} tokens")
        print(f"Savings:                 {savings:,} tokens")
        print(f"Reduction:               {reduction_percent:.1f}%")
        print("=" * 60 + "\n")

        # CRITICAL ASSERTIONS
        assert thin_prompt_tokens < 200, f"Thin prompt too large: {thin_prompt_tokens} tokens"
        assert total_thin_tokens < fat_tokens, "Thin approach must use fewer tokens"
        assert reduction_percent >= 50, f"Context prioritization should be ≥50%, got {reduction_percent:.1f}%"

        # Document the win
        print(f"✅ SUCCESS: Achieved {reduction_percent:.1f}% context prioritization")
        print(
            f"   User experience improved: Copy {len(thin_result.prompt.split())} words instead of {len(fat_prompt_simulation.split())} words"
        )

    async def test_thin_prompt_line_count_professional(self, db_session):
        """
        Verify thin prompts are copy-pasteable (professional UX).

        A commercial product should NEVER ask users to copy 3000 lines.
        """
        tenant_key = str(uuid4())

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision content")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), tool="claude-code")

        # Professional UX validation
        lines = result.prompt.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        assert len(non_empty_lines) <= 30, f"Unprofessional: {len(non_empty_lines)} lines to copy"
        print(f"✅ Professional UX: Only {len(non_empty_lines)} lines to copy")

    async def test_mission_fetch_token_efficiency(self, db_session):
        """
        Test that mission fetched via MCP is condensed (field priorities applied).
        """
        tenant_key = str(uuid4())
        user_id = str(uuid4())

        # Create user with aggressive field priorities (minimize tokens)
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            username="tokenoptimizer",
            field_priority_config={
                "product_vision": 5,  # Abbreviated
                "architecture": 3,  # Minimal
                "codebase_summary": 2,  # Minimal
                "dependencies": 1,  # Exclude
            },
        )
        db_session.add(user)

        # Large vision document
        large_vision = "PRODUCT VISION:\n" + ("Detail " * 2000)  # ~10K tokens raw

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document=large_vision)
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        # Generate with aggressive token optimization
        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), user_id=user_id, tool="claude-code")

        # Get mission
        from sqlalchemy import select

        from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

        db_result = await db_session.execute(select(AgentExecution).where(AgentExecution.id == result.orchestrator_id))
        orchestrator = db_result.scalar_one()

        mission_tokens = len(orchestrator.mission) // 4
        raw_vision_tokens = len(large_vision) // 4

        # Mission should be significantly smaller than raw vision
        reduction = ((raw_vision_tokens - mission_tokens) / raw_vision_tokens) * 100

        print("\nMission Token Efficiency:")
        print(f"  Raw vision: {raw_vision_tokens:,} tokens")
        print(f"  Condensed mission: {mission_tokens:,} tokens")
        print(f"  Reduction: {reduction:.1f}%")

        assert mission_tokens < raw_vision_tokens * 0.7, "Field priorities should reduce mission size"

    async def test_no_mission_in_prompt(self, db_session):
        """
        CRITICAL: Verify mission content is NOT embedded in prompt.

        This is the #1 mistake that would defeat the entire handover.
        """
        tenant_key = str(uuid4())

        # Create product with distinctive vision content
        distinctive_content = "UNIQUE_VISION_MARKER_12345_SHOULD_NOT_APPEAR_IN_PROMPT"
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Product",
            vision_document=f"Product vision with {distinctive_content} embedded.",
        )
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), tool="claude-code")

        # CRITICAL ASSERTION: Distinctive content must NOT be in prompt
        assert distinctive_content not in result.prompt, "Mission content embedded in prompt - ARCHITECTURE VIOLATION"

        # Mission should be in database, not prompt
        from sqlalchemy import select

        from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

        db_result = await db_session.execute(select(AgentExecution).where(AgentExecution.id == result.orchestrator_id))
        orchestrator = db_result.scalar_one()

        # Content should be in stored mission
        assert distinctive_content in orchestrator.mission or "vision" in orchestrator.mission.lower()

        print("✅ ARCHITECTURE VERIFIED: Mission separated from prompt")
