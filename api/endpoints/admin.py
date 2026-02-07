"""
Admin endpoints for system maintenance tasks.
"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/admin", tags=["admin"])


class UpdateGraphResponse(BaseModel):
    """Response for dependency graph update."""

    success: bool
    message: str
    stats: dict | None = None


@router.post("/update-dependency-graph", response_model=UpdateGraphResponse)
async def update_dependency_graph():
    """
    Regenerate dependency graph from current codebase.

    This endpoint runs the dependency graph builder script which:
    - Scans all Python, JavaScript, Vue files
    - Parses imports and builds dependency map
    - Classifies files by layer and risk
    - Updates both JSON and HTML files

    No LLM required - pure static analysis.
    """
    script_path = Path(__file__).parent.parent.parent / "scripts" / "update_dependency_graph_full.py"

    if not script_path.exists():
        raise HTTPException(status_code=500, detail=f"Update script not found at {script_path}")

    try:
        # Run the update script
        result = await asyncio.create_subprocess_exec(
            "python", str(script_path), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Script failed: {stderr.decode()}")

        # Parse output for stats (simplified)
        output = stdout.decode()

        return UpdateGraphResponse(
            success=True, message="Dependency graph updated successfully", stats={"output": output}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update graph: {e!s}") from e
