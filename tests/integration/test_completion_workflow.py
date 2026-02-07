import pytest
from fastapi import status

from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.tenant import TenantManager


def _completion_payload() -> dict:
    return {
        "summary": "Implemented the 360 memory closeout workflow with rich history entries.",
        "key_outcomes": [
            "Integrated MCP closeout tool with project completion",
            "Persisted sequential_history entries with metrics",
        ],
        "decisions_made": [
            "Prioritized single-field sequential history over legacy dual writes",
            "Gracefully degrade when GitHub is disabled",
        ],
        "confirm_closeout": True,
    }


@pytest.fixture(autouse=True)
def set_tenant(test_user):
    """Ensure tenant context matches the test user for endpoint calls."""
    TenantManager.set_current_tenant(test_user.tenant_key)
    return test_user.tenant_key


@pytest.mark.asyncio
async def test_complete_project_updates_memory(
    authed_client,
    db_session,
    test_product: Product,
    test_project: Project,
):
    payload = _completion_payload()

    response = await authed_client.post(
        f"/api/v1/projects/{test_project.id}/complete",
        json=payload,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["memory_updated"] is True
    assert data["sequence_number"] == 1
    assert data["git_commits_count"] == 0

    await db_session.refresh(test_project)
    refreshed_product = await db_session.get(Product, test_product.id)
    await db_session.refresh(refreshed_product)
    history = refreshed_product.product_memory.get("sequential_history", [])

    assert len(history) == 1
    entry = history[0]
    assert entry["project_id"] == test_project.id
    assert entry["summary"] == payload["summary"]
    assert entry["key_outcomes"] == payload["key_outcomes"]
    assert entry["decisions_made"] == payload["decisions_made"]
    assert entry["deliverables"] == payload["key_outcomes"]
    assert entry["metrics"]["commits"] == 0
    assert entry["git_commits"] == []
    assert entry["priority"] == 2
    assert entry["token_estimate"] > 0

    assert test_project.status == "completed"
    assert test_project.completed_at is not None
    assert test_project.closeout_executed_at is not None
    assert test_project.meta_data.get("closeout")


@pytest.mark.asyncio
async def test_complete_project_with_github_integration(
    authed_client,
    db_session,
    test_product: Product,
    test_project: Project,
    monkeypatch,
):
    # Enable git integration on the product
    product = await db_session.get(Product, test_product.id)
    product.product_memory = {
        "git_integration": {
            "enabled": True,
            "repo_name": "giljoai-mcp",
            "repo_owner": "giljoai",
            "access_token": "token",
        },
        "sequential_history": [],
    }
    await db_session.commit()

    sample_commits = [
        {"sha": "1", "message": "Add feature", "files_changed": 2, "lines_added": 15},
        {"sha": "2", "message": "Fix tests", "files_changed": 1, "lines_added": 5},
    ]

    async def fake_fetch_commits(**kwargs):
        return sample_commits

    monkeypatch.setattr(
        "giljo_mcp.tools.project_closeout._fetch_github_commits",
        fake_fetch_commits,
    )

    response = await authed_client.post(
        f"/api/v1/projects/{test_project.id}/complete",
        json=_completion_payload(),
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["memory_updated"] is True
    assert data["git_commits_count"] == len(sample_commits)

    refreshed_product = await db_session.get(Product, test_product.id)
    await db_session.refresh(refreshed_product)
    history = refreshed_product.product_memory.get("sequential_history", [])
    entry = history[-1]

    assert len(entry["git_commits"]) == len(sample_commits)
    assert entry["metrics"]["commits"] == len(sample_commits)
    assert entry["metrics"]["files_changed"] == 3
    assert entry["metrics"]["lines_added"] == 20


@pytest.mark.asyncio
async def test_complete_project_emits_websocket_event(
    authed_client,
    db_session,
    test_product: Product,
    test_project: Project,
    monkeypatch,
):
    calls = {}

    class DummyResponse:
        def __init__(self, status_code: int = 200):
            self.status_code = status_code

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, timeout):
            calls["url"] = url
            calls["json"] = json
            return DummyResponse(202)

    from giljo_mcp.services import project_service

    monkeypatch.setattr(project_service.httpx, "AsyncClient", lambda *args, **kwargs: DummyClient())

    response = await authed_client.post(
        f"/api/v1/projects/{test_project.id}/complete",
        json=_completion_payload(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert calls["json"]["event_type"] == "project:memory_updated"
    assert calls["json"]["tenant_key"] == test_product.tenant_key
    assert calls["json"]["data"]["project_id"] == test_project.id
    assert calls["json"]["data"]["sequence_number"] == 1


@pytest.mark.asyncio
async def test_complete_project_graceful_degradation_on_closeout_failure(
    authed_client,
    db_session,
    test_product: Product,
    test_project: Project,
    monkeypatch,
):
    async def failing_closeout(**kwargs):
        return {"success": False, "error": "forced failure"}

    monkeypatch.setattr(
        "giljo_mcp.tools.project_closeout.close_project_and_update_memory",
        failing_closeout,
    )

    response = await authed_client.post(
        f"/api/v1/projects/{test_project.id}/complete",
        json=_completion_payload(),
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["memory_updated"] is False

    refreshed_product = await db_session.get(Product, test_product.id)
    history = refreshed_product.product_memory.get("sequential_history", [])
    assert history == []

    await db_session.refresh(test_project)
    assert test_project.status == "completed"
