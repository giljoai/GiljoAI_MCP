"""
Integration test fixtures for Handover 0316
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db_manager():
    """Mock database manager for integration tests."""
    db_manager = MagicMock()
    # Add get_product and get_project as AsyncMock methods
    db_manager.get_product = AsyncMock()
    db_manager.get_project = AsyncMock()
    # Session support
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.get = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    db_manager.get_session = MagicMock(return_value=session)
    db_manager.session = session
    return db_manager
