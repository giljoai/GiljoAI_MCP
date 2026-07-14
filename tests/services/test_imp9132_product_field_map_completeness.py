# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""IMP-9132 test 1 — product field-map completeness.

``PRODUCT_DIRECT_FIELDS`` (the ``products``-row columns the vision-extraction and
context-tuning writers both target) must each ALSO be in
``ProductService``'s ``_ALLOWED_PRODUCT_FIELDS`` write allowlist — otherwise
``update_product()``'s ``if field in _ALLOWED_PRODUCT_FIELDS`` gate silently drops
the field at write time and the value never persists. The rule is stated only as a
comment at ``product_field_map.py:31-32`` ("each must also be in
ProductService._ALLOWED_PRODUCT_FIELDS to actually persist"); existing tests pin the
allowlist CONTENTS but not this subset relation. This makes the comment a test.
"""

from __future__ import annotations

from giljo_mcp.services.product_field_map import PRODUCT_DIRECT_FIELDS
from giljo_mcp.services.product_service import _ALLOWED_PRODUCT_FIELDS


def test_product_direct_fields_are_all_in_the_write_allowlist():
    missing = set(PRODUCT_DIRECT_FIELDS) - set(_ALLOWED_PRODUCT_FIELDS)
    assert not missing, (
        "PRODUCT_DIRECT_FIELDS not present in ProductService._ALLOWED_PRODUCT_FIELDS "
        "are SILENTLY DROPPED at write time (update_product()'s "
        "`if field in _ALLOWED_PRODUCT_FIELDS` gate): "
        f"{sorted(missing)}. Add them to _ALLOWED_PRODUCT_FIELDS in "
        "product_service.py, or remove them from PRODUCT_DIRECT_FIELDS. "
        "Contract: product_field_map.py:31-32."
    )
