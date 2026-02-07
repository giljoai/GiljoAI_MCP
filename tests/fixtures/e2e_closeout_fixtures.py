"""
E2E Closeout Workflow Test Fixtures

Creates test data in the database for E2E closeout workflow testing.
This script can be run standalone or imported as a fixture.

Usage:
    python tests/fixtures/e2e_closeout_fixtures.py

Requirements:
    - PostgreSQL database running
    - Database credentials in config.yaml or environment variables
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.tenant import TenantManager


class E2ECloseoutFixtures:
    """
    E2E Closeout Workflow Test Fixtures

    Creates consistent test data for E2E closeout workflow testing:
    - Test user with known credentials
    - Test product (active)
    - Test project (active)
    - 3 completed agent jobs
    """

    # Test user credentials (consistent across tests)
    TEST_EMAIL = "test@example.com"
    TEST_PASSWORD = "testpassword"
    TEST_USERNAME = "testuser"
    TEST_TENANT_PREFIX = "e2e-test"

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize fixture creator.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.tenant_manager = TenantManager()

    async def create_all_fixtures(self, session: AsyncSession) -> dict:
        """
        Create all E2E test fixtures.

        Returns:
            dict: Created fixtures (user, product, project, agents)
        """
        # Generate unique tenant for this test run
        tenant_key = self.tenant_manager.generate_tenant_key(project_name="E2E Test")

        # Create test user
        user = await self._create_test_user(session, tenant_key)

        # Create test product
        product = await self._create_test_product(session, tenant_key)

        # Create test project
        project = await self._create_test_project(session, tenant_key, product.id)

        # Create 3 completed agents
        agents = await self._create_test_agents(session, tenant_key, project.id)

        await session.commit()

        return {
            "user": user,
            "product": product,
            "project": project,
            "agents": agents,
            "tenant_key": tenant_key,
        }

    async def _create_test_user(self, session: AsyncSession, tenant_key: str) -> User:
        """
        Create test user with known credentials.

        Args:
            session: Database session
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            User: Created user instance
        """
        # Check if user already exists
        stmt = select(User).where(User.email == self.TEST_EMAIL)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Update tenant_key and password if different (for test isolation and consistency)
            password_hash = bcrypt.hash(self.TEST_PASSWORD)
            needs_update = False

            if existing_user.tenant_key != tenant_key:
                existing_user.tenant_key = tenant_key
                needs_update = True

            # Always update password to ensure it matches expected test password
            if existing_user.password_hash != password_hash:
                existing_user.password_hash = password_hash
                needs_update = True

            if needs_update:
                await session.flush()
                print(f"[OK] Test user updated: {self.TEST_EMAIL}")
            else:
                print(f"[OK] Test user already exists: {self.TEST_EMAIL}")
            return existing_user

        # Hash password using bcrypt (same as production)
        password_hash = bcrypt.hash(self.TEST_PASSWORD)

        # Create new user
        user = User(
            username=self.TEST_USERNAME,
            email=self.TEST_EMAIL,
            password_hash=password_hash,
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            full_name="Test User",
            created_at=datetime.now(timezone.utc),
        )

        session.add(user)
        await session.flush()  # Flush to get user.id

        print(f"[OK] Created test user: {self.TEST_EMAIL}")
        print(f"  - Username: {self.TEST_USERNAME}")
        print(f"  - Password: {self.TEST_PASSWORD}")
        print(f"  - Tenant: {tenant_key}")
        print("  - Role: developer")

        return user

    async def _create_test_product(self, session: AsyncSession, tenant_key: str) -> Product:
        """
        Create test product.

        Args:
            session: Database session
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Product: Created product instance
        """
        # Check if product already exists for this tenant
        stmt = select(Product).where(Product.tenant_key == tenant_key, Product.name == "Test Product")
        result = await session.execute(stmt)
        existing_product = result.scalar_one_or_none()

        if existing_product:
            print("[OK] Test product already exists: Test Product")
            return existing_product

        # Create new product
        product = Product(
            name="Test Product",
            description="E2E test product for closeout workflow testing",
            tenant_key=tenant_key,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            config_data={
                "test_mode": True,
                "e2e_fixture": True,
            },
            product_memory={
                "github": {},
                "sequential_history": [],
                "context": {},
            },
        )

        session.add(product)
        await session.flush()  # Flush to get product.id

        print("[OK] Created test product: Test Product")
        print(f"  - Tenant: {tenant_key}")
        print("  - Status: Active")

        return product

    async def _create_test_project(self, session: AsyncSession, tenant_key: str, product_id: str) -> Project:
        """
        Create test project.

        Args:
            session: Database session
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID to associate with

        Returns:
            Project: Created project instance
        """
        # Check if project already exists
        stmt = select(Project).where(Project.tenant_key == tenant_key, Project.name == "Mock Project")
        result = await session.execute(stmt)
        existing_project = result.scalar_one_or_none()

        if existing_project:
            print("[OK] Test project already exists: Mock Project")
            return existing_project

        # Create new project
        project = Project(
            name="Mock Project",
            description="E2E test project for closeout workflow",
            mission="Complete E2E closeout workflow testing",
            tenant_key=tenant_key,
            product_id=product_id,
            status="active",
            created_at=datetime.now(timezone.utc),
            activated_at=datetime.now(timezone.utc),
            context_budget=150000,
            context_used=0,
            meta_data={"test": True, "e2e_fixture": True},
        )

        session.add(project)
        await session.flush()  # Flush to get project.id

        print("[OK] Created test project: Mock Project")
        print(f"  - Tenant: {tenant_key}")
        print(f"  - Product: {product_id}")
        print("  - Status: active")

        return project

    async def _create_test_agents(
        self, session: AsyncSession, tenant_key: str, project_id: str
    ) -> list[AgentExecution]:
        """
        Create 3 completed test agents.

        Args:
            session: Database session
            tenant_key: Tenant key for multi-tenant isolation
            project_id: Project ID to associate with

        Returns:
            list[AgentExecution]: List of created agent jobs
        """
        agents = []
        agent_configs = [
            {
                "name": "Agent 1",
                "type": "orchestrator",
                "mission": "Test orchestrator agent mission",
            },
            {
                "name": "Agent 2",
                "type": "implementer",
                "mission": "Test implementer agent mission",
            },
            {
                "name": "Agent 3",
                "type": "tester",
                "mission": "Test tester agent mission",
            },
        ]

        for config in agent_configs:
            agent = AgentExecution(
                tenant_key=tenant_key,
                project_id=project_id,
                agent_display_name=config["type"],
                agent_name=config["name"],
                mission=config["mission"],
                status="complete",  # All agents marked as completed
                progress=100,
                created_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                tool_type="claude-code",
                context_budget=150000,
                context_used=50000,
                health_status="healthy",
            )

            session.add(agent)
            agents.append(agent)

        await session.flush()  # Flush to get agent IDs

        print(f"[OK] Created {len(agents)} test agents:")
        for agent in agents:
            print(f"  - {agent.agent_name} ({agent.agent_display_name}) - Status: {agent.status}")

        return agents

    async def verify_fixtures(self, session: AsyncSession, tenant_key: str) -> bool:
        """
        Verify all fixtures were created correctly.

        Args:
            session: Database session
            tenant_key: Tenant key to verify

        Returns:
            bool: True if all fixtures valid
        """
        print("\n=== Verifying Fixtures ===")

        # Verify user
        stmt = select(User).where(User.email == self.TEST_EMAIL)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            print("[FAIL] Test user not found")
            return False
        print(f"[OK] User verified: {user.email}")

        # Verify product
        stmt = select(Product).where(Product.tenant_key == tenant_key, Product.is_active == True)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            print("[FAIL] Test product not found")
            return False
        print(f"[OK] Product verified: {product.name}")

        # Verify project
        stmt = select(Project).where(Project.tenant_key == tenant_key, Project.status == "active")
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            print("[FAIL] Test project not found")
            return False
        print(f"[OK] Project verified: {project.name}")

        # Verify agents
        stmt = select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.project_id == project.id,
            AgentExecution.status == "complete",
        )
        result = await session.execute(stmt)
        agents = result.scalars().all()

        if len(agents) != 3:
            print(f"[FAIL] Expected 3 agents, found {len(agents)}")
            return False
        print(f"[OK] Agents verified: {len(agents)} completed agents")

        print("\n=== All Fixtures Valid ===")
        return True

    async def cleanup_fixtures(self, session: AsyncSession, tenant_key: str):
        """
        Clean up test fixtures (optional).

        Args:
            session: Database session
            tenant_key: Tenant key to clean up
        """
        print(f"\n=== Cleaning up fixtures for tenant: {tenant_key} ===")

        # Delete agents
        stmt = select(AgentExecution).where(AgentExecution.tenant_key == tenant_key)
        result = await session.execute(stmt)
        agents = result.scalars().all()
        for agent in agents:
            await session.delete(agent)
        print(f"[OK] Deleted {len(agents)} agents")

        # Delete projects
        stmt = select(Project).where(Project.tenant_key == tenant_key)
        result = await session.execute(stmt)
        projects = result.scalars().all()
        for project in projects:
            await session.delete(project)
        print(f"[OK] Deleted {len(projects)} projects")

        # Delete products
        stmt = select(Product).where(Product.tenant_key == tenant_key)
        result = await session.execute(stmt)
        products = result.scalars().all()
        for product in products:
            await session.delete(product)
        print(f"[OK] Deleted {len(products)} products")

        # Delete user (optional - may be shared across tests)
        # Uncomment if you want to delete the test user
        # stmt = select(User).where(User.email == self.TEST_EMAIL)
        # result = await session.execute(stmt)
        # user = result.scalar_one_or_none()
        # if user:
        #     await session.delete(user)
        #     print(f"[OK] Deleted user: {self.TEST_EMAIL}")

        await session.commit()
        print("=== Cleanup Complete ===")


async def main():
    """
    Standalone script execution.
    Creates E2E test fixtures in the database.
    """
    from src.giljo_mcp.config_manager import get_config

    print("=== E2E Closeout Workflow Fixtures ===")
    print("Creating test data for E2E closeout workflow testing...\n")

    # Get database configuration
    config = get_config()
    db_url = config.get_database_url()

    # Create database manager
    db_manager = DatabaseManager(db_url, is_async=True)

    try:
        # Create fixtures
        fixture_creator = E2ECloseoutFixtures(db_manager)

        async with db_manager.get_session_async() as session:
            # Create all fixtures
            fixtures = await fixture_creator.create_all_fixtures(session)

            # Verify fixtures
            success = await fixture_creator.verify_fixtures(session, fixtures["tenant_key"])

            if success:
                print("\n=== Success ===")
                print("Test user credentials:")
                print(f"  Email: {E2ECloseoutFixtures.TEST_EMAIL}")
                print(f"  Password: {E2ECloseoutFixtures.TEST_PASSWORD}")
                print(f"  Tenant: {fixtures['tenant_key']}")
                print(f"\nTest project: {fixtures['project'].name}")
                print(f"Test agents: {len(fixtures['agents'])} completed agents")
                print("\nE2E test fixtures ready for use!")
            else:
                print("\n=== Verification Failed ===")
                print("Some fixtures may not have been created correctly.")
                return 1

    except Exception as e:
        print("\n=== Error ===")
        print(f"Failed to create fixtures: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        await db_manager.close_async()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
