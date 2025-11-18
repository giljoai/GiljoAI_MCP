"""
Integration tests for field priority mapping (UI -> Backend).

CRITICAL BUG FIX: UI sends 1/2/3 but backend expects 10/7/4 for correct detail levels.
Before fix: All priorities map to "minimal" (80% context prioritization)
After fix: Priorities map to "full"/"moderate"/"abbreviated" as intended

Handover: 0301
"""

import pytest
from src.giljo_mcp.mission_planner import MissionPlanner


class TestFieldPriorityMapping:
    """
    Test suite for field priority to detail level mapping.

    These tests verify that the correct priority values map to the intended detail levels.
    The BUG is that the UI sends 1/2/3 but the backend expects 10/7/4.
    """

    def setup_method(self):
        """Create planner instance for testing _get_detail_level method."""
        # Create planner without database (just testing the mapping logic)
        self.planner = MissionPlanner.__new__(MissionPlanner)

    def test_priority_10_maps_to_full_detail(self):
        """
        Priority 10 should map to "full" detail level (0% context prioritization).
        This is what UI SHOULD send for Priority 1 (Always Included).
        """
        detail_level = self.planner._get_detail_level(10)
        assert detail_level == "full", f"Priority 10 should map to 'full', got '{detail_level}'"

    def test_priority_7_maps_to_moderate_detail(self):
        """
        Priority 7 should map to "moderate" detail level (25% context prioritization).
        This is what UI SHOULD send for Priority 2 (High Priority).
        """
        detail_level = self.planner._get_detail_level(7)
        assert detail_level == "moderate", f"Priority 7 should map to 'moderate', got '{detail_level}'"

    def test_priority_4_maps_to_abbreviated_detail(self):
        """
        Priority 4 should map to "abbreviated" detail level (50% context prioritization).
        This is what UI SHOULD send for Priority 3 (Medium Priority).
        """
        detail_level = self.planner._get_detail_level(4)
        assert detail_level == "abbreviated", f"Priority 4 should map to 'abbreviated', got '{detail_level}'"

    def test_priority_0_maps_to_exclude(self):
        """
        Priority 0 should map to "exclude" (100% context prioritization - omitted).
        This is for unassigned fields.
        """
        detail_level = self.planner._get_detail_level(0)
        assert detail_level == "exclude", f"Priority 0 should map to 'exclude', got '{detail_level}'"

    def test_priority_1_maps_to_minimal_THIS_IS_THE_BUG(self):
        """
        Priority 1 currently maps to "minimal" detail level (80% context prioritization).

        This is the BUG - UI sends 1 for Priority 1, which maps to "minimal" instead of "full".
        This test documents the CURRENT BROKEN behavior.

        After fix: UI will send 10 instead of 1, making this test case irrelevant.
        """
        detail_level = self.planner._get_detail_level(1)
        # This is the BUG - priority 1 maps to "minimal" (not "full")
        assert detail_level == "minimal", (
            f"Priority 1 maps to 'minimal' (this is the BUG - should be 'full' but UI sends wrong value)"
        )

    def test_priority_2_maps_to_minimal_THIS_IS_THE_BUG(self):
        """
        Priority 2 currently maps to "minimal" detail level (80% context prioritization).

        This is the BUG - UI sends 2 for Priority 2, which maps to "minimal" instead of "moderate".
        This test documents the CURRENT BROKEN behavior.

        After fix: UI will send 7 instead of 2, making this test case irrelevant.
        """
        detail_level = self.planner._get_detail_level(2)
        # This is the BUG - priority 2 maps to "minimal" (not "moderate")
        assert detail_level == "minimal", (
            f"Priority 2 maps to 'minimal' (this is the BUG - should be 'moderate' but UI sends wrong value)"
        )

    def test_priority_3_maps_to_minimal_THIS_IS_THE_BUG(self):
        """
        Priority 3 currently maps to "minimal" detail level (80% context prioritization).

        This is the BUG - UI sends 3 for Priority 3, which maps to "minimal" instead of "abbreviated".
        This test documents the CURRENT BROKEN behavior.

        After fix: UI will send 4 instead of 3, making this test case irrelevant.
        """
        detail_level = self.planner._get_detail_level(3)
        # This is the BUG - priority 3 maps to "minimal" (not "abbreviated")
        assert detail_level == "minimal", (
            f"Priority 3 maps to 'minimal' (this is the BUG - should be 'abbreviated' but UI sends wrong value)"
        )
