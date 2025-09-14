"""
Pytest configuration for test suite
Provides test fixtures and database setup
"""

import pytest
import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import Base
from src.giljo_mcp.tenant_manager import TenantManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db():
    """Create a test database for each test"""
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    
    # Create database manager with test database
    connection_string = f"sqlite+aiosqlite:///{temp_db.name}"
    db_manager = DatabaseManager(connection_string, is_async=True)
    
    # Initialize database
    await db_manager.create_tables_async()
    
    yield db_manager
    
    # Cleanup
    await db_manager.close_async()
    try:
        os.unlink(temp_db.name)
    except:
        pass


@pytest.fixture(scope="function")
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for testing"""
    async with test_db.get_session_async() as session:
        yield session


@pytest.fixture(scope="function")
async def tenant_manager(test_db) -> TenantManager:
    """Create tenant manager for testing"""
    return TenantManager(test_db)


@pytest.fixture(scope="function")
def test_config():
    """Get test configuration"""
    config = get_config()
    # Override with test settings
    config.database.database_url = "sqlite+aiosqlite:///:memory:"
    config.api.port = 7000  # Use different port for tests
    config.websocket.port = 7001
    return config


@pytest.fixture(scope="function")
async def test_project_id(db_session):
    """Create a test project and return its ID"""
    from src.giljo_mcp.models import Project
    import uuid
    
    project = Project(
        id=str(uuid.uuid4()),
        name="Test Project",
        mission="Test mission for integration testing",
        status="active",
        tenant_key=str(uuid.uuid4())
    )
    
    db_session.add(project)
    await db_session.commit()
    
    return project.id


@pytest.fixture(scope="function")
async def test_agent(db_session, test_project_id):
    """Create a test agent"""
    from src.giljo_mcp.models import Agent
    import uuid
    from datetime import datetime
    
    agent = Agent(
        id=str(uuid.uuid4()),
        name="test_agent",
        type="worker",
        status="active",
        project_id=test_project_id,
        created_at=datetime.utcnow()
    )
    
    db_session.add(agent)
    await db_session.commit()
    
    return agent


# Performance benchmarking fixtures
@pytest.fixture(scope="function")
def benchmark_timer():
    """Simple timer for performance benchmarking"""
    import time
    
    class Timer:
        def __init__(self):
            self.times = []
            
        def start(self):
            self.start_time = time.perf_counter()
            
        def stop(self):
            elapsed = (time.perf_counter() - self.start_time) * 1000  # Convert to ms
            self.times.append(elapsed)
            return elapsed
            
        def average(self):
            return sum(self.times) / len(self.times) if self.times else 0
            
        def max(self):
            return max(self.times) if self.times else 0
            
        def min(self):
            return min(self.times) if self.times else 0
    
    return Timer()