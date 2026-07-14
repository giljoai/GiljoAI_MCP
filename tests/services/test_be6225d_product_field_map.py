# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6225d: the shared product-field translator.

The vision-extraction writer (tools/vision_analysis.py) and the context-tuning writer
(services/product_tuning_service.py) used to maintain two parallel block-grouping
mappers to the SAME ProductService.update_product fields. They now both route through
ONE translator (services/product_field_map.py). These tests prove:

1. The translator groups a flat {column: value} mapping into update_product kwargs
   correctly (direct columns top-level, relation columns into their block dict).
2. Both INPUT SHAPES -- vision extraction field names and tuning section keys -- land
   on the same update_product kwargs through that one translator.
"""

import pytest

from giljo_mcp.services.product_field_map import (
    RELATION_BLOCK_FIELDS,
    assemble_update_kwargs,
    block_for_column,
)


# ============================================================================
# The shared translator itself
# ============================================================================


class TestBlockForColumn:
    def test_direct_columns_route_to_products(self):
        for col in ("name", "description", "core_features", "brand_guidelines", "target_platforms"):
            assert block_for_column(col) == "products"

    def test_relation_columns_route_to_their_block(self):
        assert block_for_column("backend_frameworks") == "tech_stack"
        assert block_for_column("primary_pattern") == "architecture"
        assert block_for_column("quality_standards") == "test_config"

    def test_unknown_column_returns_none(self):
        assert block_for_column("not_a_real_column") is None

    def test_every_column_resolves_to_a_block(self):
        for block, columns in RELATION_BLOCK_FIELDS.items():
            for col in columns:
                assert block_for_column(col) == block


class TestAssembleUpdateKwargs:
    def test_direct_columns_stay_top_level(self):
        kwargs = assemble_update_kwargs({"name": "X", "description": "Y"})
        assert kwargs == {"name": "X", "description": "Y"}

    def test_relation_columns_group_into_block(self):
        kwargs = assemble_update_kwargs({"backend_frameworks": "FastAPI"})
        assert kwargs == {"tech_stack": {"backend_frameworks": "FastAPI"}}

    def test_multiple_columns_same_block_accumulate(self):
        kwargs = assemble_update_kwargs({"backend_frameworks": "FastAPI", "databases_storage": "PostgreSQL"})
        assert kwargs == {"tech_stack": {"backend_frameworks": "FastAPI", "databases_storage": "PostgreSQL"}}

    def test_mixed_direct_and_relations(self):
        kwargs = assemble_update_kwargs(
            {
                "description": "An app",
                "api_style": "REST",
                "quality_standards": "90% coverage",
            }
        )
        assert kwargs == {
            "description": "An app",
            "architecture": {"api_style": "REST"},
            "test_config": {"quality_standards": "90% coverage"},
        }

    def test_unknown_columns_dropped(self):
        kwargs = assemble_update_kwargs({"bogus": "x", "name": "keep"})
        assert kwargs == {"name": "keep"}


# ============================================================================
# Both input shapes land on the same update_product kwargs
# ============================================================================


class TestBothInputShapesConverge:
    """The whole point of the de-dup: vision extraction names and tuning section keys,
    routed through their own input-vocabulary maps, produce identical update_product
    kwargs because they share the one block-grouping translator."""

    def test_vision_extraction_shape(self):
        """Vision input vocabulary (extraction field names) -> update_product kwargs."""
        from giljo_mcp.tools.vision_analysis import _build_update_kwargs

        fields = {
            "product_description": "An AI app",
            "backend_frameworks": "FastAPI",
            "databases": "PostgreSQL",  # extraction name -> column databases_storage
            "api_style": "REST",
            "testing_strategy": "TDD",  # extraction name -> column test_strategy
        }
        fields_written: list[str] = []
        kwargs = _build_update_kwargs(fields, fields_written)

        assert kwargs == {
            "description": "An AI app",
            "tech_stack": {"backend_frameworks": "FastAPI", "databases_storage": "PostgreSQL"},
            "architecture": {"api_style": "REST"},
            "test_config": {"test_strategy": "TDD"},
        }
        # All five extraction fields are tracked as written.
        assert set(fields_written) == {
            "product_description",
            "backend_frameworks",
            "databases",
            "api_style",
            "testing_strategy",
        }

    def test_tuning_section_shape(self):
        """Tuning input vocabulary (section keys) -> update_product kwargs, via the
        SAME translator -- the relation columns land in identical block dicts."""
        from giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        proposals = [
            {"section": "description", "drift_detected": True, "proposed_value": "An AI app"},
            {"section": "tech_stack.backend_frameworks", "drift_detected": True, "proposed_value": "FastAPI"},
            {"section": "tech_stack.databases_storage", "drift_detected": True, "proposed_value": "PostgreSQL"},
            {"section": "architecture.api_style", "drift_detected": True, "proposed_value": "REST"},
        ]
        kwargs, sections = service._build_update_kwargs(proposals)

        assert kwargs == {
            "description": "An AI app",
            "tech_stack": {"backend_frameworks": "FastAPI", "databases_storage": "PostgreSQL"},
            "architecture": {"api_style": "REST"},
        }
        assert set(sections) == {
            "description",
            "tech_stack.backend_frameworks",
            "tech_stack.databases_storage",
            "architecture.api_style",
        }

    def test_relation_block_dicts_are_structurally_identical(self):
        """The tech_stack block produced from the vision shape and the tuning shape is
        the same dict shape -- proof there is one grouping path, not two."""
        from giljo_mcp.services.product_tuning_service import ProductTuningService
        from giljo_mcp.tools.vision_analysis import _build_update_kwargs

        vision_kwargs = _build_update_kwargs({"backend_frameworks": "FastAPI", "databases": "PostgreSQL"}, [])

        service = ProductTuningService.__new__(ProductTuningService)
        tuning_kwargs, _ = service._build_update_kwargs(
            [
                {"section": "tech_stack.backend_frameworks", "drift_detected": True, "proposed_value": "FastAPI"},
                {"section": "tech_stack.databases_storage", "drift_detected": True, "proposed_value": "PostgreSQL"},
            ]
        )

        assert vision_kwargs["tech_stack"] == tuning_kwargs["tech_stack"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
