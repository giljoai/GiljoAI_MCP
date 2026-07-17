# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9211: active-template slot limit raised 8 -> 16 (owner ruling "users decide").

The active-slot cap is USER_MANAGED_AGENT_LIMIT (15) distinct user-managed roles
plus 1 reserved orchestrator = 16 total active slots. This is the SECOND, separate
server-enforced cap from BE-9208's export/packaging cap (MAX_PACKAGED_TEMPLATES).

Boundary test at the enforcing layer (TemplateService.validate_active_agent_limit):
the 16th total slot (15th user role) is accepted, the 17th (16th user role) is
rejected. Plus a value-lock so the cap cannot silently regress to 8 and the REST
layer keeps importing the single owning constant instead of redefining it.

Parallel-safe: rows created under the fixture's unique test_tenant_key on a
TransactionalTestContext session (rolled back at teardown); no module-level state.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from giljo_mcp.models.templates import AgentTemplate
from giljo_mcp.services.template_service import USER_MANAGED_AGENT_LIMIT


def _active_template(tenant_key: str, product_id: str, role: str) -> AgentTemplate:
    return AgentTemplate(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product_id,
        name=f"slot-tmpl-{role}",
        role=role,
        category="custom",
        system_instructions="boundary seed",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_active_slot_limit_16th_accepted_17th_rejected(
    db_session, template_service, test_tenant_key, test_product
):
    """15 user roles + orchestrator = 16 total is the cap; a 17th total is rejected."""
    # Fill to the cap: 15 distinct active user-managed roles.
    for i in range(USER_MANAGED_AGENT_LIMIT):
        db_session.add(_active_template(test_tenant_key, test_product.id, f"custom-role-{i}"))
    await db_session.flush()

    new_role = "custom-role-new"
    candidate_id = str(uuid4())

    # A 16th distinct user role (the 17th total slot) is REJECTED at the cap.
    ok, msg = await template_service.validate_active_agent_limit(
        session=db_session,
        tenant_key=test_tenant_key,
        template_id=candidate_id,
        new_is_active=True,
        role=new_role,
    )
    assert ok is False
    assert str(USER_MANAGED_AGENT_LIMIT) in msg  # message reports the 15-role user cap

    # Drop one active role -> 14 active -> the 15th user role (16th total slot) is ACCEPTED.
    row = (
        await db_session.execute(
            select(AgentTemplate).where(
                AgentTemplate.tenant_key == test_tenant_key,
                AgentTemplate.role == "custom-role-0",
            )
        )
    ).scalar_one()
    row.is_active = False
    await db_session.flush()

    ok2, msg2 = await template_service.validate_active_agent_limit(
        session=db_session,
        tenant_key=test_tenant_key,
        template_id=candidate_id,
        new_is_active=True,
        role=new_role,
    )
    assert ok2 is True
    assert msg2 == ""


def test_active_slot_cap_is_16_total_and_single_source():
    """Value-lock: the cap is 16 total (15 user + 1 orchestrator) and the REST layer
    imports the one owning constant instead of redefining its own (BE-9211
    consolidation of the former service/endpoint duplicate). Guards against a silent
    regression back to 8 and against the duplicate drifting apart again."""
    from api.endpoints.templates import crud

    assert USER_MANAGED_AGENT_LIMIT == 15
    assert USER_MANAGED_AGENT_LIMIT + 1 == 16
    # crud must expose the imported service constant, not a private redefinition.
    assert crud.USER_MANAGED_AGENT_LIMIT == USER_MANAGED_AGENT_LIMIT
