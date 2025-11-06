"""
Materialize agent templates to filesystem for operator visibility (0102a).

Writes Claude Code-compatible .md files rendered from DB to:
  exports/templates/{tenant_key}/claude_code/<name>.md

Notes:
- DB remains canonical; this is an optional artifact for visibility/backups.
- Packaging/export should render from DB to avoid stale files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgentTemplate
from .template_renderer import _slugify_filename, render_claude_agent


def _materialize_dir_for_tenant(base_dir: Optional[Path], tenant_key: str) -> Path:
    base = base_dir or (Path.cwd() / "exports" / "templates")
    target = base / tenant_key / "claude_code"
    target.mkdir(parents=True, exist_ok=True)
    return target


async def materialize_claude_templates_for_tenant(
    session: AsyncSession,
    tenant_key: str,
    include_inactive: bool = False,
    base_dir: Optional[Path] = None,
) -> List[Path]:
    """Render and write Claude-compatible templates for a tenant to disk.

    Args:
        session: Async database session
        tenant_key: Tenant identifier
        include_inactive: If True, write all templates; else only active
        base_dir: Optional base directory override

    Returns:
        List of paths written
    """
    filters = [AgentTemplate.tenant_key == tenant_key]
    if not include_inactive:
        filters.append(AgentTemplate.is_active == True)  # noqa: E712

    stmt = select(AgentTemplate).where(*filters).order_by(AgentTemplate.name)
    result = await session.execute(stmt)
    templates = result.scalars().all()

    out_dir = _materialize_dir_for_tenant(base_dir, tenant_key)

    written: List[Path] = []
    for t in templates:
        content = render_claude_agent(t)
        filename = f"{_slugify_filename(t.name)}.md"
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)

    return written


def get_materialize_on_save_flag() -> bool:
    """Return True if MATERIALIZE_TEMPLATES_ON_SAVE=1 env is set."""
    return os.getenv("MATERIALIZE_TEMPLATES_ON_SAVE", "0") in {"1", "true", "True"}

