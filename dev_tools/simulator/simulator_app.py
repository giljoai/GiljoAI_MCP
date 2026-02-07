from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .api_client import APIClient
from .created_registry import CreatedRegistry
from .process_manager import ProcessManager


APP_DIR = Path(__file__).parent
STATE_DIR = APP_DIR / "state"


class SimulatorState:
    def __init__(self) -> None:
        self.process = ProcessManager()
        self.client = APIClient(base_url=os.environ.get("SIM_TARGET", "http://localhost:7272"))
        self.registry = CreatedRegistry(base_dir=STATE_DIR)
        self.target = self.client.base_url


state = SimulatorState()
app = FastAPI(title="GiljoAI Dev Tools Simulator", version="0.1")


# ------------------------ Static UI ------------------------
@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    html = (APP_DIR / "static" / "index.html").read_text(encoding="utf-8")
    return html


app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


# ------------------------ Config/Auth ----------------------
@app.get("/api/config")
async def get_config() -> dict:
    return {"target_base_url": state.target, "auth_mode": "api_key"}


@app.post("/api/auth/api_key")
async def set_api_key(payload: dict) -> dict:
    api_key = payload.get("api_key")
    if not api_key:
        raise HTTPException(400, "api_key required")
    return await state.client.set_api_key(api_key)


@app.post("/api/auth/login")
async def login(payload: dict) -> dict:
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(400, "username and password required")
    return await state.client.login(username, password)


# ------------------------ Process Control ------------------
@app.post("/api/process/start_api")
async def start_api(payload: dict = {}) -> dict:
    host = payload.get("host", "0.0.0.0")
    port = int(payload.get("port", 7272))
    info = state.process.start_api(host=host, port=port)
    return {"success": True, "info": info.__dict__}


@app.post("/api/process/stop_api")
async def stop_api() -> dict:
    ok = state.process.stop_api()
    return {"success": ok}


@app.post("/api/process/start_frontend")
async def start_frontend(payload: dict = {}) -> dict:
    port = int(payload.get("port", 7274))
    info = state.process.start_frontend(port=port)
    return {"success": True, "info": info.__dict__}


@app.post("/api/process/stop_frontend")
async def stop_frontend() -> dict:
    ok = state.process.stop_frontend()
    return {"success": ok}


@app.get("/api/process/status")
async def process_status() -> dict:
    return state.process.status()


# ------------------------ Product Ops ---------------------
@app.post("/api/sim/product/create")
async def sim_create_product(payload: dict) -> dict:
    name = payload.get("name")
    description = payload.get("description", "")
    res = await state.client.create_product(name=name, description=description)
    if res.get("success"):
        pid = res["data"].get("id")
        if pid:
            state.registry.add("products", pid)
    return res


@app.post("/api/sim/product/activate")
async def sim_activate_product(payload: dict) -> dict:
    pid = payload.get("product_id")
    return await state.client.activate_product(pid)


@app.post("/api/sim/product/deactivate")
async def sim_deactivate_product(payload: dict) -> dict:
    pid = payload.get("product_id")
    return await state.client.deactivate_product(pid)


@app.post("/api/sim/product/delete")
async def sim_delete_product(payload: dict) -> dict:
    pid = payload.get("product_id")
    res = await state.client.delete_product(pid)
    if res.get("success"):
        state.registry.remove("products", pid)
    return res


@app.post("/api/sim/product/vision_upload")
async def sim_upload_vision(payload: dict) -> dict:
    pid = payload.get("product_id")
    filename = payload.get("filename", "vision.md")
    content_b64 = payload.get("content_b64")
    if not content_b64:
        raise HTTPException(400, "content_b64 required (base64-encoded file contents)")
    content = base64.b64decode(content_b64)
    return await state.client.upload_vision(pid, filename, content)


# ------------------------ Project Ops ---------------------
@app.post("/api/sim/project/create")
async def sim_create_project(payload: dict) -> dict:
    name = payload.get("name")
    mission = payload.get("mission", "")
    product_id = payload.get("product_id")
    res = await state.client.create_project(name=name, mission=mission, product_id=product_id)
    if res.get("success"):
        prj_id = res["data"].get("id")
        if prj_id:
            state.registry.add("projects", prj_id)
    return res


@app.post("/api/sim/project/cancel")
async def sim_cancel_project(payload: dict) -> dict:
    prj_id = payload.get("project_id")
    reason = payload.get("reason")
    return await state.client.cancel_project(prj_id, reason)


@app.post("/api/sim/project/restore")
async def sim_restore_project(payload: dict) -> dict:
    prj_id = payload.get("project_id")
    return await state.client.restore_project(prj_id)


# ------------------------ Task Ops ------------------------
@app.post("/api/sim/task/create")
async def sim_create_task(payload: dict) -> dict:
    title = payload.get("title")
    description = payload.get("description", "")
    product_id = payload.get("product_id")
    project_id = payload.get("project_id")
    res = await state.client.create_task(
        title=title, description=description, product_id=product_id, project_id=project_id
    )
    if res.get("success"):
        tid = res["data"].get("id")
        if tid:
            state.registry.add("tasks", tid)
    return res


@app.post("/api/sim/task/delete")
async def sim_delete_task(payload: dict) -> dict:
    tid = payload.get("task_id")
    res = await state.client.delete_task(tid)
    if res.get("success"):
        state.registry.remove("tasks", tid)
    return res


@app.post("/api/sim/task/convert")
async def sim_convert_task(payload: dict) -> dict:
    tid = payload.get("task_id")
    project_name = payload.get("project_name")
    strategy = payload.get("strategy", "single")
    include_subtasks = bool(payload.get("include_subtasks", True))
    return await state.client.convert_task(
        tid, project_name=project_name, strategy=strategy, include_subtasks=include_subtasks
    )


# ------------------------ Jobs & Orchestrator -------------
# Note: orchestrate_project endpoint removed (deprecated 2026-01-26)
# Use manual staging workflow: get_orchestrator_instructions -> spawn_agent_job


@app.get("/api/sim/jobs/workflow")
async def sim_workflow(project_id: str) -> dict:
    return await state.client.workflow_status(project_id)


# ------------------------ Messaging -----------------------
@app.post("/api/sim/messages/send")
async def sim_send_message(payload: dict) -> dict:
    to_agents = payload.get("to_agents", [])
    content = payload.get("content", "")
    project_id = payload.get("project_id")
    priority = payload.get("priority", "normal")
    res = await state.client.send_message(
        to_agents=to_agents, content=content, project_id=project_id, priority=priority
    )
    if res.get("success"):
        mid = res["data"].get("id")
        if mid:
            state.registry.add("messages", mid)
    return res


@app.get("/api/sim/messages/list")
async def sim_list_messages(
    project_id: Optional[str] = None, agent_name: Optional[str] = None, status: Optional[str] = None
) -> dict:
    return await state.client.list_messages(project_id=project_id, agent_name=agent_name, status=status)


@app.post("/api/sim/messages/ack")
async def sim_ack_message(payload: dict) -> dict:
    mid = payload.get("message_id")
    agent = payload.get("agent_name", "simulator")
    return await state.client.acknowledge_message(mid, agent)


@app.post("/api/sim/messages/complete")
async def sim_complete_message(payload: dict) -> dict:
    mid = payload.get("message_id")
    agent = payload.get("agent_name", "simulator")
    result = payload.get("result", "ok")
    return await state.client.complete_message(mid, agent, result)


# ------------------------ MCP -----------------------------
@app.post("/api/sim/mcp/initialize")
async def sim_mcp_init(payload: dict) -> dict:
    params = payload or {"client_info": {"name": "sim"}}
    return await state.client.mcp_call("initialize", params=params)


@app.post("/api/sim/mcp/tools_list")
async def sim_mcp_tools_list() -> dict:
    return await state.client.mcp_call("tools/list", params={})


@app.post("/api/sim/mcp/tools_call")
async def sim_mcp_tools_call(payload: dict) -> dict:
    name = payload.get("name")
    params = payload.get("params", {})
    return await state.client.mcp_call("tools/call", params={"name": name, "arguments": params})


# ------------------------ Dataset & Cleanup ----------------
@app.post("/api/sim/dataset/generate")
async def sim_generate_dataset(payload: dict) -> dict:
    products = int(payload.get("products", 10))
    projects_per = int(payload.get("projects_per_product", 10))
    tasks_per = int(payload.get("tasks_per_project", 10))

    results: list[dict[str, Any]] = []

    # Create products
    for p in range(products):
        pr_name = f"SIM_PRODUCT_{p:02d}"
        r = await state.client.create_product(pr_name, description="Simulator generated")
        results.append({"op": "create_product", "name": pr_name, **r})
        if not r.get("success"):
            continue
        prod_id = r["data"].get("id")
        if prod_id:
            state.registry.add("products", prod_id)

        # Create projects for product
        for j in range(projects_per):
            pj_name = f"SIM_{p:02d}_PROJECT_{j:02d}"
            r2 = await state.client.create_project(pj_name, mission="Sim test mission", product_id=prod_id)
            results.append({"op": "create_project", "name": pj_name, **r2})
            if not r2.get("success"):
                continue
            project_id = r2["data"].get("id")
            if project_id:
                state.registry.add("projects", project_id)

            # Create tasks for project
            for t in range(tasks_per):
                tk_title = f"SIM_{p:02d}_{j:02d}_TASK_{t:02d}"
                r3 = await state.client.create_task(title=tk_title, description="Sim task", project_id=project_id)
                results.append({"op": "create_task", "title": tk_title, **r3})
                if r3.get("success"):
                    tid = r3["data"].get("id")
                    if tid:
                        state.registry.add("tasks", tid)

    return {"success": True, "results": results}


@app.post("/api/sim/cleanup/created")
async def sim_cleanup_created() -> dict:
    """Delete items created by the simulator using recorded IDs.

    Products are soft-deleted via API. Tasks are deleted. Projects are cancelled
    (no explicit delete in current endpoints). Messages/jobs may not have delete endpoints;
    we best-effort mark/ignore.
    """
    report: list[dict[str, Any]] = []

    # Tasks
    for tid in list(state.registry.items.get("tasks", [])):
        r = await state.client.delete_task(tid)
        report.append({"kind": "task", "id": tid, **r})
        if r.get("success"):
            state.registry.remove("tasks", tid)

    # Projects → cancel
    for pid in list(state.registry.items.get("projects", [])):
        r = await state.client.cancel_project(pid, reason="sim cleanup")
        report.append({"kind": "project", "id": pid, **r})
        # keep id to potentially restore later; do not remove from registry automatically

    # Products → delete (soft)
    for prd in list(state.registry.items.get("products", [])):
        r = await state.client.delete_product(prd)
        report.append({"kind": "product", "id": prd, **r})
        if r.get("success"):
            state.registry.remove("products", prd)

    # Messages/Jobs: no delete endpoints; clear local registry to avoid retries
    state.registry.clear_kind("messages")
    state.registry.clear_kind("agent_jobs")

    return {"success": True, "report": report}


@app.post("/api/sim/cleanup/purge_sim")
async def sim_purge_sim_entities() -> dict:
    """Best-effort purge of entities named with SIM_* prefix.

    - Products: delete (soft)
    - Projects: cancel
    - Tasks: delete
    - Messages/Jobs: not supported via API (skipped)
    """
    report: list[dict[str, Any]] = []

    # Products
    prod_list = await state.client.list_products()
    if prod_list.get("success"):
        for p in prod_list["data"]:
            try:
                if (
                    str(p.get("name", "")).startswith("SIM_")
                    or str(p.get("name", "")).startswith("SIM-")
                    or str(p.get("name", "")).startswith("SIM PRODUCT")
                ):
                    r = await state.client.delete_product(p.get("id"))
                    report.append({"kind": "product", "id": p.get("id"), **r})
            except Exception as e:
                report.append({"kind": "product", "id": p.get("id"), "success": False, "error": str(e)})

    # Projects
    prj_list = await state.client.list_projects()
    if prj_list.get("success"):
        for pr in prj_list["data"]:
            try:
                if str(pr.get("name", "")).startswith("SIM_"):
                    r = await state.client.cancel_project(pr.get("id"), reason="purge sim")
                    report.append({"kind": "project", "id": pr.get("id"), **r})
            except Exception as e:
                report.append({"kind": "project", "id": pr.get("id"), "success": False, "error": str(e)})

    # Tasks (created_by current user)
    task_list = await state.client.list_tasks(created_by_me=True)
    if task_list.get("success"):
        for t in task_list["data"]:
            try:
                if str(t.get("title", "")).startswith("SIM_"):
                    r = await state.client.delete_task(t.get("id"))
                    report.append({"kind": "task", "id": t.get("id"), **r})
            except Exception as e:
                report.append({"kind": "task", "id": t.get("id"), "success": False, "error": str(e)})

    return {"success": True, "report": report}


# ------------------------ Run helper ----------------------
# For local running: uvicorn dev_tools.simulator.simulator_app:app --port 7390
