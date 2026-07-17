# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""FE-9200 onboarding tutorial — backend contract locks for the Prompt-D flow.

The tutorial's "I have an existing codebase" path pre-creates an EMPTY-named
product, interpolates its UUID into Prompt-D, and then polls the product row
for ``vision_analysis_complete`` as the "agent is done" signal. That flow rests
on two backend behaviors this module locks as regression tests (they were
verified by reading the code; these tests keep them true):

1. ``update_product_fields`` with ``consolidated_vision={light, medium}`` and
   ZERO uploaded vision documents does NOT flip ``vision_analysis_complete``
   (``evaluate_vision_analysis_complete`` requires at least one active doc:
   ``bool(active_docs) and ...``). This is WHY the tutorial's Prompt-D poll
   watches populated card state (name + description) instead of the flag —
   if this test ever starts failing because zero-docs flips TRUE, the FE poll
   can be simplified back to the flag.

2. ``product_name`` is user-owned but only SKIPPED when the existing name is
   non-empty — an empty-string name (the tutorial's silent pre-create) is
   agent-writable, so the agent can name the product from the repository.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models import Product
from giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def fe9200_tenant() -> str:
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def fe9200_empty_product(db_session: AsyncSession, fe9200_tenant: str) -> Product:
    """The tutorial's silent pre-create: a product with an EMPTY name and no docs."""
    product = Product(
        id=str(uuid.uuid4()),
        name="",
        description="",
        tenant_key=fe9200_tenant,
        is_active=False,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest.mark.asyncio
async def test_consolidated_vision_does_not_flip_complete_with_zero_docs(
    db_session: AsyncSession,
    fe9200_tenant: str,
    fe9200_empty_product: Product,
) -> None:
    """With ZERO uploaded docs, consolidated_vision alone must NOT flip
    vision_analysis_complete (evaluator requires >=1 active doc). The tutorial's
    Prompt-D poll therefore watches name+description, not this flag. The card
    fields from the same call must still land (that IS the poll signal)."""
    from giljo_mcp.tools.vision_analysis import update_product_fields

    result = await update_product_fields(
        product_id=fe9200_empty_product.id,
        tenant_key=fe9200_tenant,
        _test_session=db_session,
        product_name="agent-audited-product",
        product_description="A repo-audited product.",
        consolidated_vision={
            "light": "Light consolidated summary from the agent's repo audit.",
            "medium": "Medium consolidated summary with more detail from the audit.",
        },
    )
    assert result["success"] is True
    assert "consolidated_vision" in result["fields"]

    await db_session.refresh(fe9200_empty_product)
    # The evaluator's zero-docs semantics — the load-bearing fact for the FE poll.
    assert fe9200_empty_product.vision_analysis_complete is False
    # The populated-card signal the FE poll actually watches.
    assert fe9200_empty_product.name == "agent-audited-product"
    assert fe9200_empty_product.description == "A repo-audited product."


@pytest.mark.asyncio
async def test_empty_name_is_agent_writable(
    db_session: AsyncSession,
    fe9200_tenant: str,
    fe9200_empty_product: Product,
) -> None:
    """product_name is user-owned, but an EMPTY existing name writes normally —
    the agent can name the tutorial's silently pre-created product."""
    from giljo_mcp.tools.vision_analysis import update_product_fields

    result = await update_product_fields(
        product_id=fe9200_empty_product.id,
        tenant_key=fe9200_tenant,
        _test_session=db_session,
        product_name="agent-named-product",
    )
    assert result["success"] is True
    assert "product_name" in result["fields"]
    assert not result.get("fields_skipped")

    await db_session.refresh(fe9200_empty_product)
    assert fe9200_empty_product.name == "agent-named-product"


@pytest.mark.asyncio
async def test_nonempty_name_stays_user_owned(
    db_session: AsyncSession,
    fe9200_tenant: str,
    fe9200_empty_product: Product,
) -> None:
    """Guard the other half of the contract: a non-empty name is skipped."""
    from giljo_mcp.tools.vision_analysis import update_product_fields

    fe9200_empty_product.name = "User Chosen Name"
    await db_session.flush()

    result = await update_product_fields(
        product_id=fe9200_empty_product.id,
        tenant_key=fe9200_tenant,
        _test_session=db_session,
        product_name="agent-attempted-rename",
        product_description="Description still lands.",
    )
    assert result["success"] is True
    assert "product_name" not in result["fields"]
    skipped_fields = {entry["field"] for entry in result.get("fields_skipped", [])}
    assert "product_name" in skipped_fields

    await db_session.refresh(fe9200_empty_product)
    assert fe9200_empty_product.name == "User Chosen Name"
