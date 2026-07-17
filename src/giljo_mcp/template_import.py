# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Default-template import (FE-9203) — additive re-import of the seeded defaults.

Sibling of ``template_seeder`` / ``template_refresh`` for the same size-budget
reason (BE-9019 precedent): the owning ``TemplateService`` sits at its
shrink-only budget, so this per-tenant import lives next to the seed content it
consumes. It reuses the seeder's content trio (``_get_default_templates_v103``
+ ``_seeded_user_instructions`` + ``_get_mcp_bootstrap_section``) and routes
every write through ``TemplateService.add_and_commit_template`` — no parallel
write path.

Semantics (additive ONLY — an existing template is never modified):

- default name free              → create the default exactly as the seeder would
- pristine copy already present  → skip (``skipped_identical``)
- default name taken by an
  edited row                     → add the PRISTINE default under the existing
                                   suffix machinery (``slugify_name(role,
                                   "duplicate")`` + the -2..-20 collision loop),
                                   ``is_default=False`` so the user's default
                                   flag is never stolen

The pristine check is the BE-9019 provably-unedited byte-compare against ANY
live template in the tenant, which is also the repeat-click anti-spam guard:
once a pristine copy of a default exists (under its own name OR a -duplicate
name), further imports of that default skip instead of multiplying copies.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import AlreadyExistsError, ValidationError
from giljo_mcp.models import AgentTemplate
from giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES
from giljo_mcp.template_seeder import (
    _get_default_templates_v103,
    _get_mcp_bootstrap_section,
    _seeded_user_instructions,
)
from giljo_mcp.template_validation import slugify_name


logger = logging.getLogger(__name__)

# House spelling of the owner-specified "_duplicate" marker: the name grammar
# bans underscores and slugify_name maps "_" -> "-", so the collision copy of
# e.g. "implementer" lands as "implementer-duplicate".
DUPLICATE_SUFFIX = "duplicate"


@dataclass
class TemplateImportReport:
    """Per-default outcome of an import run (names as persisted).

    - ``added``: defaults created under their own name (name was free).
    - ``added_as_duplicate``: pristine copies created under a suffixed name
      because the default name is taken by a user-edited row.
    - ``skipped_identical``: defaults whose pristine prose already lives on a
      live template (under any name) — nothing to add.
    """

    added: list[str] = field(default_factory=list)
    added_as_duplicate: list[str] = field(default_factory=list)
    skipped_identical: list[str] = field(default_factory=list)


async def import_default_templates(session: AsyncSession, tenant_key: str) -> TemplateImportReport:
    """Additively import the seeded default agent templates for a tenant.

    Unlike ``seed_tenant_templates`` (all-or-nothing: skips entirely when the
    tenant has ANY templates), this imports per-default into a populated tenant
    and never touches an existing row. System-managed roles (orchestrator) stay
    out of the template table, exactly as at seed time.

    Args:
        session: Caller-owned DB session (transaction boundary shared with the
            owning-service commit helper).
        tenant_key: Tenant key to import for (must be non-empty).

    Returns:
        TemplateImportReport — names added / added-as-duplicate / skipped.

    Raises:
        ValueError: If tenant_key is empty.
        ValidationError: Suffix exhaustion on the collision loop (>20 copies).
    """
    if not tenant_key:
        raise ValueError("tenant_key must be non-empty string")

    with tenant_session_context(session, tenant_key):
        return await _import_default_templates(session, tenant_key)


async def _import_default_templates(session: AsyncSession, tenant_key: str) -> TemplateImportReport:
    # Owning-service write path via a manager-less instance — the exact
    # template_refresh.py precedent (add_and_commit_template uses only the
    # repository + the passed session). Imported lazily to avoid a module-load
    # import cycle (template_service imports from template_seeder).
    from giljo_mcp.services.template_service import TemplateService

    service = TemplateService(db_manager=None, tenant_manager=None, session=session)  # type: ignore[arg-type]

    # One read of the tenant's live templates: name / prose / default-flag basis
    # for every per-default decision below.
    stmt = select(AgentTemplate).where(
        AgentTemplate.tenant_key == tenant_key,
        AgentTemplate.deleted_at.is_(None),
    )
    existing = list((await session.execute(stmt)).scalars().all())
    live_names = {t.name for t in existing}

    bootstrap = _get_mcp_bootstrap_section()
    report = TemplateImportReport()
    now = datetime.now(UTC)

    for template_def in _get_default_templates_v103():
        if template_def["role"] in SYSTEM_MANAGED_ROLES:
            continue  # orchestrator: identity is server-injected, never a table row

        default_name = template_def["name"]
        pristine_ui = _seeded_user_instructions(template_def)

        # Anti-spam core: a live template already carrying the pristine prose
        # (under ANY name) means this default is present — skip, never multiply.
        if any(t.user_instructions == pristine_ui for t in existing):
            report.skipped_identical.append(default_name)
            continue

        if default_name in live_names:
            # Default name taken by an edited row → collide-add the pristine
            # copy via the EXISTING suffix machinery; never steal is_default.
            new_name = slugify_name(template_def["role"], DUPLICATE_SUFFIX)
            base_name = new_name
            counter = 2
            while await service.check_template_name_exists(session, tenant_key, new_name):
                new_name = f"{base_name}-{counter}"
                counter += 1
                if counter > 20:
                    raise ValidationError(message=f"Too many agents named '{base_name}' — clean up copies first")
            is_default = False
            report.added_as_duplicate.append(new_name)
        else:
            new_name = default_name
            # Keep the seeder's is_default=True ONLY when no existing live
            # template of this role already holds the default flag.
            is_default = not any(t.role == template_def["role"] and t.is_default for t in existing)
            report.added.append(new_name)

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=None,
            name=new_name,
            category="role",
            role=template_def["role"],
            cli_tool=template_def["cli_tool"],
            background_color=template_def["background_color"],
            description=template_def["description"],
            system_instructions=bootstrap,
            user_instructions=pristine_ui,
            model=template_def.get("model", "sonnet"),
            tools=template_def.get("tools"),
            variables=[],
            behavioral_rules=template_def.get("behavioral_rules", []),
            success_criteria=template_def.get("success_criteria", []),
            tool=template_def["cli_tool"],
            version=template_def.get("version", "1.0.0"),
            is_active=template_def.get("is_active", True),
            is_default=is_default,
            tags=["default", "tenant"],
            created_at=now,
        )
        try:
            await service.add_and_commit_template(session, template)
        except IntegrityError as e:
            # TSK-9205: two concurrent import sessions both pass the name pre-check
            # and race to add the same new name+version; the loser hits the
            # uq_template_tenant_name_version partial unique index on commit. Roll
            # back the failed insert and map the race to the already-exists domain
            # rejection (409) instead of a generic 500. Idempotent on retry: the
            # winner's row is now present, so the re-run skips it.
            await session.rollback()
            raise AlreadyExistsError(
                message=(f"An agent template named '{new_name}' already exists (concurrent import). Please retry."),
                context={"tenant_key": tenant_key, "name": new_name},
            ) from e
        existing.append(template)
        live_names.add(new_name)

    logger.info(
        "Imported default templates for tenant '%s': %d added, %d added as duplicate, %d skipped identical",
        tenant_key,
        len(report.added),
        len(report.added_as_duplicate),
        len(report.skipped_identical),
    )
    return report
