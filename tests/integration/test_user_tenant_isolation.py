"""
TDD: Per-user tenant isolation for registered users

Behavioral tests ensure that:
- Creating first admin yields a tenant_key (existing behavior)
- Registering a new user as admin always assigns a unique tenant_key per user
- The provided tenant_key in the request is ignored (forward policy change)

We avoid testing implementation details; we assert observable API behavior.
"""

import pytest
from httpx import AsyncClient
from api.app import create_app


@pytest.mark.asyncio
async def test_register_user_assigns_unique_tenant_per_user():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1) Create first admin (fresh install path)
        admin_payload = {
            "username": "admin_user",
            "password": "AdminPassw0rd!#",
            "email": "admin@example.com",
            "full_name": "Admin",
            "role": "admin",
        }
        resp_admin = await client.post("/api/auth/create-first-admin", json=admin_payload)
        assert resp_admin.status_code in (200, 201)
        admin_data = resp_admin.json()
        assert "tenant_key" in admin_data
        admin_tenant = admin_data["tenant_key"]
        assert isinstance(admin_tenant, str) and admin_tenant.startswith("tk_")

        # 2) Register user A (request tenant_key should be ignored)
        user_a_req = {
            "username": "user_a",
            "password": "UserPassw0rd!#",
            "email": "user_a@example.com",
            "full_name": "User A",
            "role": "developer",
            "tenant_key": admin_tenant,  # should be ignored under per-user tenancy policy
        }
        resp_a = await client.post("/api/auth/register", json=user_a_req)
        assert resp_a.status_code == 201
        user_a = resp_a.json()
        assert user_a["tenant_key"].startswith("tk_")
        assert user_a["tenant_key"] != admin_tenant

        # 3) Register user B and ensure different tenant from user A
        user_b_req = {
            "username": "user_b",
            "password": "UserPassw0rd!#",
            "email": "user_b@example.com",
            "full_name": "User B",
            "role": "developer",
            "tenant_key": admin_tenant,  # ignored
        }
        resp_b = await client.post("/api/auth/register", json=user_b_req)
        assert resp_b.status_code == 201
        user_b = resp_b.json()
        assert user_b["tenant_key"].startswith("tk_")
        assert user_b["tenant_key"] != user_a["tenant_key"]

