# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Tenant template refresh (BE-9019) — re-render the slim bootstrap, preserve user prose.

Split out of ``template_seeder`` so the seeder file stays under its size budget. The
refresh path re-renders the user-content-free ``system_instructions`` bootstrap for a
tenant's templates while PROTECTING ``user_instructions``: a default-named row whose
prose has diverged from the shipped default is treated as a user edit and left
untouched (silently clobbering it was the bug). ``force=True`` overwrites edited rows
back to the default, archiving each first so the edit stays recoverable.

Operator-triggered only (``scripts/refresh_templates.py``, stripped from the CE
export); it does NOT run on startup.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import tenant_session_context
from giljo_mcp.models import AgentTemplate
from giljo_mcp.template_seeder import (
    _get_default_templates_v103,
    _get_mcp_bootstrap_section,
    _seeded_user_instructions,
)


logger = logging.getLogger(__name__)


@dataclass
class TemplateRefreshReport:
    """Per-tenant outcome of a template refresh (BE-9019).

    - ``bootstrap_refreshed``: every row (system_instructions is user-content-free
      and is always safe to re-render).
    - ``user_instructions_rewritten``: default-named rows whose prose was (re)written
      to the shipped default — either provably-unedited rows or force-overwritten ones.
    - ``skipped_edited``: names of default-named rows LEFT UNTOUCHED because their
      prose diverged from the shipped default (user edits, preserved unless force).
    - ``archived``: rows archived (create_template_archive) before a force overwrite.
    """

    bootstrap_refreshed: int = 0
    user_instructions_rewritten: int = 0
    skipped_edited: list[str] = field(default_factory=list)
    archived: int = 0


async def refresh_tenant_template_instructions(
    session: AsyncSession,
    tenant_key: str,
    *,
    force: bool = False,
    archived_by: str = "system:template-refresh",
) -> TemplateRefreshReport:
    """
    Refresh the slim MCP bootstrap for a tenant's templates, PRESERVING user-edited prose.

    ``system_instructions`` (the ~10-line MCP bootstrap, Handover 0813) carries no user
    content and is ALWAYS re-rendered for every row. ``user_instructions`` is the
    substantial, user-editable prose and is protected: for a default-NAMED row it is
    rewritten to the shipped default ONLY when the current text is provably unedited
    (byte-identical to what the seeder would write). A default-named row whose prose has
    diverged is treated as user-edited and LEFT UNTOUCHED — its name is returned in
    ``skipped_edited``. Custom-named rows are never touched.

    BE-9019: before this fix the ``user_instructions`` overwrite was keyed on NAME alone,
    so any refresh silently clobbered hand-tuned default-named templates back to shipped
    text. The docstring claimed the opposite ("without overwriting user customizations");
    that lie is now corrected and the behavior matches the promise.

    Pass ``force=True`` to deliberately overwrite edited default-named rows back to the
    shipped default (e.g. an operator pushing a template-prose improvement everywhere);
    each such row is archived first via ``TemplateService.create_template_archive`` so the
    edit is recoverable from history. Provably-unedited rows are re-rendered regardless of
    ``force`` (a no-op for prose) and have their ``behavioral_rules`` / ``success_criteria``
    reset to ``[]`` (that content now lives in ``user_instructions`` prose).

    Note: this path is operator-triggered only (``scripts/refresh_templates.py``, stripped
    from the CE export); it does NOT run on startup (contrary to a stale claim in the
    ce_0049 migration docstring). Tool-rename healing of stale rows is owned by the
    idempotent migration ``ce_0049``, not by this refresh.

    Args:
        session: AsyncSession - Database session for operations.
        tenant_key: str - Tenant key to refresh templates for.
        force: bool - Overwrite user-edited default-named rows (archiving them first).
            Default False = preserve edits.
        archived_by: str - Author stamped on force-overwrite archives.

    Returns:
        TemplateRefreshReport - Per-row outcome (bootstrap refreshed, prose rewritten,
        edits skipped, rows archived).

    Raises:
        ValueError: If tenant_key is None or empty.
    """
    if not tenant_key:
        raise ValueError("tenant_key must be non-empty string")

    with tenant_session_context(session, tenant_key):
        return await _refresh_tenant_template_instructions(session, tenant_key, force=force, archived_by=archived_by)


async def _refresh_tenant_template_instructions(
    session: AsyncSession,
    tenant_key: str,
    *,
    force: bool,
    archived_by: str,
) -> TemplateRefreshReport:
    try:
        # Handover 0813: Use slim bootstrap for all templates
        bootstrap = _get_mcp_bootstrap_section()

        # Build lookup of default templates by name for user_instructions refresh
        default_templates_by_name = {t["name"]: t for t in _get_default_templates_v103()}

        # Query existing templates for tenant
        stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        result = await session.execute(stmt)
        templates = result.scalars().all()

        report = TemplateRefreshReport()
        if not templates:
            logger.info(f"No templates found for tenant '{tenant_key}'")
            return report

        for template in templates:
            # system_instructions is user-content-free — always safe to re-render.
            template.system_instructions = bootstrap
            report.bootstrap_refreshed += 1

            default_def = default_templates_by_name.get(template.name)
            if default_def is None:
                # Custom-named row: never touch user_instructions / rules / criteria.
                continue

            seeded_ui = _seeded_user_instructions(default_def)
            is_unedited = template.user_instructions == seeded_ui

            if not is_unedited and not force:
                # BE-9019: a default-named row whose prose diverged is a USER EDIT.
                # Preserve it (prose + rules + criteria) — silent clobber is the bug.
                report.skipped_edited.append(template.name)
                continue

            if not is_unedited and force:
                # Deliberate operator clobber — archive the edit first so it is
                # recoverable, then overwrite. Reuses the owning service's archive
                # write path (no parallel TemplateArchive construction).
                await _archive_before_force_overwrite(session, template, archived_by)
                report.archived += 1

            template.user_instructions = seeded_ui
            template.behavioral_rules = []
            template.success_criteria = []
            report.user_instructions_rewritten += 1

        await session.commit()
        logger.info(
            "Refreshed %d templates for tenant '%s' (user_instructions rewritten=%d, "
            "skipped user-edited=%d, archived=%d)",
            report.bootstrap_refreshed,
            tenant_key,
            report.user_instructions_rewritten,
            len(report.skipped_edited),
            report.archived,
        )
        if report.skipped_edited:
            logger.info(
                "Preserved user-edited default-named templates for tenant '%s': %s "
                "(pass force=True to overwrite; edits are archived first)",
                tenant_key,
                ", ".join(sorted(report.skipped_edited)),
            )
        return report

    except Exception as e:  # Broad catch: refresh boundary, logs and re-raises
        logger.error(f"Failed to refresh templates for tenant '{tenant_key}': {e}", exc_info=True)
        raise


async def _archive_before_force_overwrite(session: AsyncSession, template: AgentTemplate, archived_by: str) -> None:
    """Archive a template's current state before a force refresh overwrites its prose.

    Reuses ``TemplateService.create_template_archive`` (the owning-service archive
    write path) so recovery goes through the same history the reset/update paths use.
    The service's ``__init__`` stores its managers but ``create_template_archive`` uses
    only the repository + the passed session, so a manager-less instance is sufficient
    here (this module holds no DatabaseManager/TenantManager). Imported lazily to avoid a
    module-load import cycle (template_service imports from template_seeder).
    """
    from giljo_mcp.services.template_service import TemplateService

    service = TemplateService(db_manager=None, tenant_manager=None, session=session)  # type: ignore[arg-type]
    await service.create_template_archive(
        session,
        template,
        archive_reason="Template refresh (force overwrite)",
        archive_type="auto",
        archived_by=archived_by,
    )
