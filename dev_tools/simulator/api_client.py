from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx


class APIClient:
    """Stateful HTTP client to the main API.

    Supports two auth modes:
    - API key (X-API-Key)
    - JWT cookie (via /api/auth/login)
    """

    def __init__(self, base_url: str = "http://localhost:7272") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0, follow_redirects=True)
        self._auth_mode: str = "api_key"  # or "cookie"
        self._api_key: Optional[str] = None

    async def aclose(self) -> None:
        await self._client.aclose()

    # ----------------- Auth -----------------
    async def set_api_key(self, api_key: str) -> dict:
        self._auth_mode = "api_key"
        self._api_key = api_key
        # set header on client
        self._client.headers.update({"X-API-Key": api_key})
        return {"success": True, "mode": self._auth_mode}

    async def login(self, username: str, password: str) -> dict:
        self._auth_mode = "cookie"
        # remove API key header (if present)
        self._client.headers.pop("X-API-Key", None)
        resp = await self._client.post("/api/auth/login", json={"username": username, "password": password})
        if resp.status_code != 200:
            return {"success": False, "status": resp.status_code, "error": resp.text}
        return {"success": True, "mode": self._auth_mode, "data": resp.json()}

    # ------------- Generic request -----------
    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = path if path.startswith("http") else path
        return await self._client.request(method.upper(), url, **kwargs)

    # ------------- Convenience wrappers ------
    async def create_product(self, name: str, description: str = "", project_path: Optional[str] = None) -> dict:
        payload = {"name": name, "description": description, "project_path": project_path}
        r = await self._client.post("/api/v1/products/", json=payload)
        return self._result(r)

    async def list_products(self) -> dict:
        r = await self._client.get("/api/v1/products/")
        return self._result(r)

    async def activate_product(self, product_id: str) -> dict:
        r = await self._client.post(f"/api/v1/products/{product_id}/activate")
        return self._result(r)

    async def deactivate_product(self, product_id: str) -> dict:
        r = await self._client.post(f"/api/v1/products/{product_id}/deactivate")
        return self._result(r)

    async def delete_product(self, product_id: str) -> dict:
        r = await self._client.delete(f"/api/v1/products/{product_id}")
        return self._result(r)

    async def restore_product(self, product_id: str) -> dict:
        r = await self._client.post(f"/api/v1/products/{product_id}/restore")
        return self._result(r)

    async def upload_vision(self, product_id: str, filename: str, content: bytes) -> dict:
        files = {"file": (filename, content, "text/markdown")}
        r = await self._client.post(f"/api/v1/products/{product_id}/upload-vision", files=files)
        return self._result(r)

    async def create_project(self, name: str, mission: str, product_id: Optional[str] = None, description: str = "") -> dict:
        payload = {"name": name, "mission": mission, "product_id": product_id, "description": description}
        r = await self._client.post("/api/v1/projects/", json=payload)
        return self._result(r)

    async def list_projects(self) -> dict:
        r = await self._client.get("/api/v1/projects/")
        return self._result(r)

    async def cancel_project(self, project_id: str, reason: Optional[str] = None) -> dict:
        params = {"reason": reason} if reason else None
        r = await self._client.post(f"/api/v1/projects/{project_id}/cancel", params=params)
        return self._result(r)

    async def restore_project(self, project_id: str) -> dict:
        r = await self._client.post(f"/api/v1/projects/{project_id}/restore")
        return self._result(r)

    async def workflow_status(self, project_id: str) -> dict:
        r = await self._client.get(f"/api/agent-jobs/workflow/{project_id}")
        return self._result(r)

    async def list_tasks(self, **filters: Any) -> dict:
        r = await self._client.get("/api/v1/tasks/", params=filters)
        return self._result(r)

    async def create_task(self, title: str, description: str = "", product_id: Optional[str] = None, project_id: Optional[str] = None) -> dict:
        payload = {"title": title, "description": description, "product_id": product_id, "project_id": project_id}
        r = await self._client.post("/api/v1/tasks/", json=payload)
        return self._result(r)

    async def delete_task(self, task_id: str) -> dict:
        r = await self._client.delete(f"/api/v1/tasks/{task_id}")
        return self._result(r)

    async def convert_task(self, task_id: str, project_name: Optional[str] = None, strategy: str = "single", include_subtasks: bool = True) -> dict:
        payload = {"project_name": project_name, "strategy": strategy, "include_subtasks": include_subtasks}
        r = await self._client.post(f"/api/v1/tasks/{task_id}/convert", json=payload)
        return self._result(r)

    async def send_message(self, to_agents: list[str], content: str, project_id: str, priority: str = "normal") -> dict:
        payload = {"to_agents": to_agents, "content": content, "project_id": project_id, "priority": priority}
        r = await self._client.post("/api/v1/messages/", json=payload)
        return self._result(r)

    async def list_messages(self, **filters: Any) -> dict:
        r = await self._client.get("/api/v1/messages/", params=filters)
        return self._result(r)

    async def complete_message(self, message_id: str, agent_name: str = "simulator", result: str = "ok") -> dict:
        r = await self._client.post(
            f"/api/v1/messages/{message_id}/complete", params={"agent_name": agent_name, "result": result}
        )
        return self._result(r)

    async def mcp_call(self, method: str, params: Optional[dict] = None, id: Optional[str] = "1") -> dict:
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": id}
        r = await self._client.post("/mcp", json=payload)
        if r.status_code == 200:
            return {"success": True, "result": r.json()}
        return {"success": False, "status": r.status_code, "error": r.text}

    # ------------- utils ---------------------
    @staticmethod
    def _result(resp: httpx.Response) -> dict:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        ok = 200 <= resp.status_code < 300
        return {"success": ok, "status": resp.status_code, "data": data}
