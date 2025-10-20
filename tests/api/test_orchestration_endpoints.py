"""
Tests for orchestration REST API endpoints (Handover 0020 Phase 3A).

Tests follow TDD principles:
1. Write comprehensive tests first
2. Run tests (expect failures)
3. Implement endpoints
4. Run tests (expect pass)
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing"""
    from unittest.mock import AsyncMock, MagicMock

    db_manager = Mock()

    # Create a proper async context manager for session
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=Mock())
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)

    db_manager.get_session_async = Mock(return_value=mock_session_cm)
    return db_manager


@pytest.fixture
def mock_orchestrator():
    """Mock ProjectOrchestrator for testing"""
    orchestrator = Mock()

    # Mock process_product_vision
    orchestrator.process_product_vision = AsyncMock(return_value={
        'project_id': 'test-project-123',
        'mission_plan': {
            'analyzer': {
                'role': 'analyzer',
                'description': 'Analyze requirements',
                'token_count': 1000
            },
            'implementer': {
                'role': 'implementer',
                'description': 'Implement features',
                'token_count': 1500
            }
        },
        'selected_agents': ['analyzer', 'implementer'],
        'spawned_jobs': ['job-1', 'job-2'],
        'workflow_result': Mock(
            status='completed',
            completed=['analyzer', 'implementer'],
            failed=[]
        ),
        'token_reduction': {
            'original_tokens': 10000,
            'optimized_tokens': 2500,
            'reduction_percent': 75.0
        }
    })

    return orchestrator


@pytest.fixture
def client(mock_db_manager, mock_orchestrator):
    """Create test client with mocked dependencies"""
    from api.app import app, state

    # Mock state
    state.db_manager = mock_db_manager

    # Mock auth manager for middleware
    mock_auth = Mock()
    mock_auth.authenticate_request = AsyncMock(return_value={
        'authenticated': True,
        'user_id': 'test-user',
        'user': 'test-user',
        'user_obj': {'id': 'test-user', 'tenant_key': 'test-tenant'},
        'tenant_key': 'test-tenant',
        'is_auto_login': False
    })
    state.auth = mock_auth

    # Patch ProjectOrchestrator
    with patch('api.endpoints.orchestration.ProjectOrchestrator', return_value=mock_orchestrator):
        yield TestClient(app)


class TestProcessVisionEndpoint:
    """Tests for POST /api/orchestrator/process-vision"""

    def test_process_vision_success(self, client, mock_db_manager, mock_orchestrator):
        """Test successful vision processing workflow"""
        # Setup mocks
        mock_product = Mock()
        mock_product.id = 'product-123'
        mock_product.tenant_key = 'test-tenant'
        mock_product.name = 'Test Product'
        mock_product.vision_path = '/path/to/vision.md'

        async def mock_get_product(product_type, product_id):
            if product_id == 'product-123':
                return mock_product
            return None

        # Mock session with proper async context manager
        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_product)

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        # Make request
        response = client.post(
            '/api/orchestrator/process-vision',
            json={
                'tenant_key': 'test-tenant',
                'product_id': 'product-123',
                'project_requirements': 'Build REST API for user management',
                'workflow_type': 'waterfall'
            },
            headers={'Authorization': 'Bearer test-token'}
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert 'project_id' in data
        assert data['project_id'] == 'test-project-123'

        assert 'mission_plan' in data
        assert 'analyzer' in data['mission_plan']
        assert 'implementer' in data['mission_plan']

        assert 'selected_agents' in data
        assert 'analyzer' in data['selected_agents']
        assert 'implementer' in data['selected_agents']

        assert 'spawned_jobs' in data
        assert len(data['spawned_jobs']) == 2

        assert 'workflow_status' in data
        assert data['workflow_status'] == 'completed'

        assert 'token_reduction' in data
        assert data['token_reduction']['reduction_percent'] == 75.0

        # Verify orchestrator was called
        mock_orchestrator.process_product_vision.assert_called_once()

    def test_process_vision_invalid_product(self, client, mock_db_manager):
        """Test 404 error for non-existent product"""
        # Mock session returning None
        mock_session = Mock()
        mock_session.get = AsyncMock(return_value=None)

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        response = client.post(
            '/api/orchestrator/process-vision',
            json={
                'tenant_key': 'test-tenant',
                'product_id': 'non-existent-product',
                'project_requirements': 'Build something',
                'workflow_type': 'waterfall'
            },
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        detail = data.get('detail') or data.get('error', '')
        assert 'not found' in detail.lower()

    def test_process_vision_tenant_mismatch(self, client, mock_db_manager):
        """Test 404 error for tenant mismatch (multi-tenant isolation)"""
        # Mock product with different tenant
        mock_product = Mock()
        mock_product.id = 'product-123'
        mock_product.tenant_key = 'other-tenant'

        async def mock_get_product(product_type, product_id):
            return mock_product

        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_product)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        response = client.post(
            '/api/orchestrator/process-vision',
            json={
                'tenant_key': 'test-tenant',
                'product_id': 'product-123',
                'project_requirements': 'Build something',
                'workflow_type': 'waterfall'
            },
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        detail = data.get('detail') or data.get('error', '')
        assert 'not found' in detail.lower()

    def test_process_vision_no_vision_document(self, client, mock_db_manager, mock_orchestrator):
        """Test 400 error when product has no vision document"""
        # Mock product without vision
        mock_product = Mock()
        mock_product.id = 'product-123'
        mock_product.tenant_key = 'test-tenant'
        mock_product.vision_path = None
        mock_product.vision_document = None
        mock_product.vision_type = None

        async def mock_get_product(product_type, product_id):
            return mock_product

        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_product)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        # Mock orchestrator to raise ValueError
        mock_orchestrator.process_product_vision = AsyncMock(
            side_effect=ValueError('Product product-123 has no vision document')
        )

        response = client.post(
            '/api/orchestrator/process-vision',
            json={
                'tenant_key': 'test-tenant',
                'product_id': 'product-123',
                'project_requirements': 'Build something',
                'workflow_type': 'waterfall'
            },
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        detail = data.get('detail') or data.get('error', '')
        assert 'vision' in detail.lower()


class TestWorkflowStatusEndpoint:
    """Tests for GET /api/orchestrator/workflow-status/{project_id}"""

    def test_workflow_status_success(self, client, mock_db_manager):
        """Test successful workflow status retrieval"""
        from src.giljo_mcp.models import Project, Agent

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = 'project-123'
        mock_project.tenant_key = 'test-tenant'
        mock_project.status = 'active'
        mock_project.context_used = 5000
        mock_project.context_budget = 150000

        # Mock agents
        mock_agents = [
            Mock(spec=Agent, status='completed', role='analyzer'),
            Mock(spec=Agent, status='active', role='implementer'),
            Mock(spec=Agent, status='pending', role='tester'),
        ]
        mock_project.agents = mock_agents

        async def mock_get_project(project_type, project_id):
            if project_id == 'project-123':
                return mock_project
            return None

        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_project)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        response = client.get(
            '/api/orchestrator/workflow-status/project-123',
            params={'tenant_key': 'test-tenant'},
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['project_id'] == 'project-123'
        assert data['active_agents'] == 1
        assert data['completed_agents'] == 1
        assert data['failed_agents'] == 0
        assert data['current_stage'] == 'active'
        assert 'progress_percent' in data

    def test_workflow_status_invalid_project(self, client, mock_db_manager):
        """Test 404 for invalid project ID"""
        mock_session = Mock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        response = client.get(
            '/api/orchestrator/workflow-status/invalid-project',
            params={'tenant_key': 'test-tenant'},
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_workflow_status_tenant_mismatch(self, client, mock_db_manager):
        """Test 404 for tenant mismatch"""
        from src.giljo_mcp.models import Project

        mock_project = Mock(spec=Project)
        mock_project.id = 'project-123'
        mock_project.tenant_key = 'other-tenant'

        async def mock_get_project(project_type, project_id):
            return mock_project

        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_project)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        response = client.get(
            '/api/orchestrator/workflow-status/project-123',
            params={'tenant_key': 'test-tenant'},
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMetricsEndpoint:
    """Tests for GET /api/orchestrator/metrics/{project_id}"""

    def test_metrics_success(self, client, mock_db_manager):
        """Test successful metrics retrieval"""
        from src.giljo_mcp.models import Project

        # Mock project with token metrics
        mock_project = Mock(spec=Project)
        mock_project.id = 'project-123'
        mock_project.tenant_key = 'test-tenant'
        mock_project.token_metrics = {
            'total_tokens': 50000,
            'tokens_used': 15000,
            'tokens_saved': 35000,
            'reduction_percent': 70.0,
            'estimated_cost_savings': 12.50
        }

        async def mock_get_project(project_type, project_id):
            if project_id == 'project-123':
                return mock_project
            return None

        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_project)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        response = client.get(
            '/api/orchestrator/metrics/project-123',
            params={'tenant_key': 'test-tenant'},
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['project_id'] == 'project-123'
        assert data['token_metrics']['total_tokens'] == 50000
        assert data['token_metrics']['reduction_percent'] == 70.0

    def test_metrics_no_metrics(self, client, mock_db_manager):
        """Test metrics endpoint handles missing metrics gracefully"""
        from src.giljo_mcp.models import Project

        mock_project = Mock(spec=Project)
        mock_project.id = 'project-123'
        mock_project.tenant_key = 'test-tenant'
        mock_project.token_metrics = None

        async def mock_get_project(project_type, project_id):
            return mock_project

        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_project)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        response = client.get(
            '/api/orchestrator/metrics/project-123',
            params={'tenant_key': 'test-tenant'},
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['project_id'] == 'project-123'
        assert data['token_metrics'] == {}

    def test_metrics_invalid_project(self, client, mock_db_manager):
        """Test 404 for invalid project"""
        mock_session = Mock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        response = client.get(
            '/api/orchestrator/metrics/invalid-project',
            params={'tenant_key': 'test-tenant'},
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateMissionsEndpoint:
    """Tests for POST /api/orchestrator/create-missions"""

    def test_create_missions_success(self, client, mock_db_manager, mock_orchestrator):
        """Test successful mission creation"""
        from src.giljo_mcp.models import Product

        mock_product = Mock(spec=Product)
        mock_product.id = 'product-123'
        mock_product.tenant_key = 'test-tenant'

        async def mock_get_product(product_type, product_id):
            return mock_product

        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_product)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        # Mock generate_mission_plan
        mock_orchestrator.generate_mission_plan = AsyncMock(return_value={
            'analyzer': {'role': 'analyzer', 'description': 'Analyze requirements'},
            'implementer': {'role': 'implementer', 'description': 'Implement features'}
        })

        response = client.post(
            '/api/orchestrator/create-missions',
            json={
                'tenant_key': 'test-tenant',
                'product_id': 'product-123',
                'project_description': 'Build REST API'
            },
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert 'missions' in data
        assert 'analyzer' in data['missions']
        assert 'implementer' in data['missions']


class TestSpawnTeamEndpoint:
    """Tests for POST /api/orchestrator/spawn-team"""

    def test_spawn_team_success(self, client, mock_db_manager, mock_orchestrator):
        """Test successful team spawning"""
        from src.giljo_mcp.models import Project

        mock_project = Mock(spec=Project)
        mock_project.id = 'project-123'
        mock_project.tenant_key = 'test-tenant'

        async def mock_get_project(project_type, project_id):
            return mock_project

        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=mock_get_project)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_db_manager.get_session_async.return_value = mock_session_cm

        # Mock workflow coordination
        mock_orchestrator.coordinate_agent_workflow = AsyncMock(return_value=Mock(
            status='completed',
            completed=['analyzer', 'implementer'],
            failed=[]
        ))

        response = client.post(
            '/api/orchestrator/spawn-team',
            json={
                'tenant_key': 'test-tenant',
                'project_id': 'project-123',
                'agent_roles': ['analyzer', 'implementer'],
                'workflow_type': 'waterfall'
            },
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['workflow_status'] == 'completed'
        assert len(data['spawned_agents']) == 2


class TestCoordinateEndpoint:
    """Tests for POST /api/orchestrator/coordinate"""

    def test_coordinate_success(self, client, mock_orchestrator):
        """Test successful coordination request"""
        mock_orchestrator.coordinate_agent_workflow = AsyncMock(return_value=Mock(
            status='in_progress',
            completed=[],
            failed=[]
        ))

        response = client.post(
            '/api/orchestrator/coordinate',
            json={
                'project_id': 'project-123',
                'coordination_action': 'start'
            },
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['status'] == 'in_progress'


class TestHandleFailureEndpoint:
    """Tests for POST /api/orchestrator/handle-failure"""

    def test_handle_failure_success(self, client):
        """Test successful failure handling"""
        response = client.post(
            '/api/orchestrator/handle-failure',
            json={
                'project_id': 'project-123',
                'agent_id': 'agent-456',
                'failure_reason': 'Agent context limit exceeded',
                'recovery_action': 'handoff'
            },
            headers={'Authorization': 'Bearer test-token'}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert 'recovery_status' in data
        assert data['recovery_status'] in ['success', 'pending', 'failed']
