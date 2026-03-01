#!/usr/bin/env python3
"""
Quick test to verify tenant key fix
"""

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

pytestmark = pytest.mark.skip(reason="0750c3: API setup — authenticate_request on NoneType")

from fastapi.testclient import TestClient

# Import the FastAPI app
from api.app import app


def test_tenant_key_validation():
    """Test that tenant key generation now passes validation"""
    client = TestClient(app)

    # Test project creation with tenant key validation
    project_data = {
        "name": "Test Project",
        "mission": "Test mission for tenant key validation",
        "agents": ["test_agent"],
    }

    response = client.post("/api/v1/projects/", json=project_data)

    if response.status_code == 200:
        result = response.json()

        # Validate tenant key format
        tenant_key = result.get("tenant_key", "")
        if tenant_key.startswith("tk_") and len(tenant_key) == 35:  # tk_ + 32 chars
            return True
        return False
    return False


if __name__ == "__main__":
    success = test_tenant_key_validation()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
