#!/usr/bin/env python3
"""
Quick test to verify tenant key fix
"""
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

# Import the FastAPI app
from src.giljo_mcp.api.app import app


def test_tenant_key_validation():
    """Test that tenant key generation now passes validation"""
    client = TestClient(app)

    # Test project creation with tenant key validation
    project_data = {
        "name": "Test Project",
        "mission": "Test mission for tenant key validation",
        "agents": ["test_agent"]
    }

    print("Testing project creation with tenant key validation...")
    response = client.post("/api/v1/projects/", json=project_data)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Project ID: {result.get('project_id')}")
        print(f"Tenant Key: {result.get('tenant_key')}")

        # Validate tenant key format
        tenant_key = result.get("tenant_key", "")
        if tenant_key.startswith("tk_") and len(tenant_key) == 35:  # tk_ + 32 chars
            print("PASS: Tenant key format is correct")
            return True
        print(f"FAIL: Tenant key format incorrect. Length: {len(tenant_key)}")
        return False
    print(f"FAIL: Request failed with status {response.status_code}")
    print(f"Response: {response.text}")
    return False

if __name__ == "__main__":
    print("Quick Tenant Key Validation Test")
    print("=" * 40)

    success = test_tenant_key_validation()

    print("=" * 40)
    if success:
        print("RESULT: TENANT KEY FIX VERIFIED")
        sys.exit(0)
    else:
        print("RESULT: TENANT KEY ISSUE PERSISTS")
        sys.exit(1)
