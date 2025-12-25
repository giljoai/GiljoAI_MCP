"""
Slash command handlers for template installation and updates (/gil_fetch, /gil_update_agents)
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..downloads.token_manager import TokenManager
from ..file_staging import FileStaging


async def _stage_agent_templates(db_session: AsyncSession, tenant_key: str) -> dict[str, Any]:
    token_mgr = TokenManager(db_session=db_session)
    token = await token_mgr.generate_token(
        tenant_key=tenant_key,
        download_type="agent_templates",
        metadata={"filename": "agent_templates.zip"},
    )

    staging = FileStaging(db_session=db_session)
    # token directory created by caller of FileStaging in downloads flow; here we stage directly in temp/tenant/token
    # Use convenience method to create staging dir and stage files
    # Create staging dir
    from pathlib import Path
    temp_root = Path.cwd() / "temp"
    staging_dir = temp_root / tenant_key / token
    staging_dir.mkdir(parents=True, exist_ok=True)

    zip_path, message = await staging.stage_agent_templates(staging_dir, tenant_key, db_session=db_session)
    if not zip_path:
        await token_mgr.mark_failed(token, message)
        return {"success": False, "error": message}

    await token_mgr.mark_ready(token)

    # Build public download URL (served by downloads endpoint)
    from api.app import state
    cfg = state.config
    host = cfg.get("services", {}).get("api", {}).get("host", "localhost")
    port = cfg.get("services", {}).get("api", {}).get("port", 7272)
    download_url = f"http://{host}:{port}/api/download/temp/{token}/agent_templates.zip"

    return {
        "success": True,
        "download_url": download_url,
        "message": "Agent templates staged. Download and install to your CLI."
    }


async def handle_gil_fetch(db_session: AsyncSession, tenant_key: str, **_: Any) -> dict[str, Any]:
    return await _stage_agent_templates(db_session, tenant_key)


async def handle_gil_update_agents(db_session: AsyncSession, tenant_key: str, **_: Any) -> dict[str, Any]:
    return await _stage_agent_templates(db_session, tenant_key)
