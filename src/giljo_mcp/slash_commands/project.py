"""
Slash command handlers for project actions (/gil_activate, /gil_launch)
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AgentExecution, AgentJob, Product, Project


async def handle_gil_activate(
    db_session: AsyncSession, tenant_key: str, project_id: Optional[str] = None, **_: Any
) -> dict[str, Any]:
    if not project_id:
        return {"success": False, "error": "project_id is required"}

    # Fetch project
    result = await db_session.execute(select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key))
    project = result.scalar_one_or_none()
    if not project:
        return {"success": False, "error": "Project not found"}

    if project.status != "inactive":
        return {"success": False, "error": f"Project cannot be activated from status '{project.status}'"}

    # Validate product active
    if project.product_id:
        prod_res = await db_session.execute(select(Product).where(Product.id == project.product_id))
        product = prod_res.scalar_one_or_none()
        if not product or not getattr(product, "is_active", False):
            return {"success": False, "error": "Parent product inactive or missing"}

    # Activate
    project.status = "active"
    project.updated_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Ensure orchestrator job exists
    orch_res = await db_session.execute(
        select(AgentJob).where(
            AgentJob.project_id == project_id,
            AgentJob.tenant_key == tenant_key,
            AgentJob.job_type == "orchestrator",
        )
    )
    agent_job = orch_res.scalar_one_or_none()
    if not agent_job:
        # Create both AgentJob and AgentExecution
        job_id = str(uuid4())
        agent_id = str(uuid4())

        # Step 1: Create AgentJob (work order)
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project_id,
            mission=(
                "I am ready to create the project mission based on product context and project description. "
                "I will write the mission in the mission window and select the proper agents below."
            ),
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        # Step 2: Create AgentExecution (executor instance)
        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="Orchestrator #1",
            agent_name="orchestrator",
            instance_number=1,
            status="waiting",
            progress=0,
            tool_type="universal",
            messages=[],
        )
        db_session.add(agent_execution)
        await db_session.commit()

    return {"success": True, "message": f"Project {project.name} activated", "project_id": project_id}


async def handle_gil_launch(
    db_session: AsyncSession, tenant_key: str, project_id: Optional[str] = None, **_: Any
) -> dict[str, Any]:
    if not project_id:
        return {"success": False, "error": "project_id is required"}

    # Validate project
    proj_res = await db_session.execute(
        select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
    )
    project = proj_res.scalar_one_or_none()
    if not project:
        return {"success": False, "error": "Project not found"}

    if not project.mission or not project.mission.strip():
        return {"success": False, "error": "Project mission has not been created. Please complete staging first."}

    # Ensure agents spawned exist (check via AgentJob)
    agents_res = await db_session.execute(
        select(AgentJob).where(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key)
    )
    agents = agents_res.scalars().all()
    if not agents:
        return {
            "success": False,
            "error": "No agents have been spawned for this project. Please complete staging first.",
        }

    # staging_status tracking (if present on Project)
    try:
        if hasattr(project, "staging_status"):
            project.staging_status = "launching"
            project.updated_at = datetime.now(timezone.utc)
            await db_session.commit()
    except Exception:
        await db_session.rollback()

    return {
        "success": True,
        "message": f"Project {project.name} launching with {len(agents)} agents",
        "project_id": project_id,
        "agent_count": len(agents),
    }
