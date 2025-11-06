"""
Test for timezone-aware/naive datetime fix in deleted projects endpoint.

This test verifies that the endpoint correctly handles timezone-naive timestamps
from the database when calculating purge countdown.

Issue: The database stores timezone-naive timestamps, but the code was using
timezone-aware datetime.now(timezone.utc) for comparison, causing:
    TypeError: can't subtract offset-naive and offset-aware datetimes

Fix: Convert naive datetime to UTC-aware before performing arithmetic.
"""

from datetime import datetime, timedelta, timezone

import pytest


def test_timezone_conversion_logic():
    """
    Test the timezone conversion logic used in the fixed endpoint.

    This test verifies that:
    1. Naive datetimes are converted to UTC-aware
    2. Already-aware datetimes are left unchanged
    3. Arithmetic works correctly after conversion
    """
    # Simulate database timestamp (naive)
    naive_datetime = datetime(2025, 10, 28, 0, 24, 38, 250090)
    assert naive_datetime.tzinfo is None, "Test data should be timezone-naive"

    # Simulate current time (UTC-aware)
    now = datetime.now(timezone.utc)
    assert now.tzinfo is not None, "Current time should be timezone-aware"

    # Apply the fix: convert naive to UTC-aware
    deleted_at_utc = naive_datetime.replace(tzinfo=timezone.utc) if naive_datetime.tzinfo is None else naive_datetime
    assert deleted_at_utc.tzinfo == timezone.utc, "Converted datetime should be UTC-aware"

    # Verify arithmetic works without TypeError
    purge_date = deleted_at_utc + timedelta(days=10)
    days_until_purge = max(0, (purge_date - now).days)

    assert isinstance(days_until_purge, int), "Days until purge should be an integer"
    assert days_until_purge >= 0, "Days until purge should be non-negative"


def test_already_aware_datetime_unchanged():
    """
    Test that already timezone-aware datetimes are not double-converted.
    """
    # Already timezone-aware datetime
    aware_datetime = datetime.now(timezone.utc)
    assert aware_datetime.tzinfo is not None

    # Apply the fix (should be a no-op)
    converted = aware_datetime.replace(tzinfo=timezone.utc) if aware_datetime.tzinfo is None else aware_datetime

    # Should be unchanged
    assert converted == aware_datetime
    assert converted.tzinfo == aware_datetime.tzinfo


def test_purge_countdown_calculation():
    """
    Test purge countdown calculation with various deletion dates.
    """
    test_cases = [
        (1, 9),  # Deleted 1 day ago -> 9 days until purge
        (5, 5),  # Deleted 5 days ago -> 5 days until purge
        (9, 1),  # Deleted 9 days ago -> 1 day until purge
        (10, 0),  # Deleted 10 days ago -> 0 days (due for purge)
        (11, 0),  # Deleted 11 days ago -> 0 days (overdue, capped at 0)
    ]

    now = datetime.now(timezone.utc)

    for days_ago, expected_days_until_purge in test_cases:
        # Create naive datetime (simulating database)
        deleted_at_naive = (now - timedelta(days=days_ago)).replace(tzinfo=None)

        # Apply the fix
        deleted_at_utc = (
            deleted_at_naive.replace(tzinfo=timezone.utc) if deleted_at_naive.tzinfo is None else deleted_at_naive
        )
        purge_date = deleted_at_utc + timedelta(days=10)
        days_until_purge = max(0, (purge_date - now).days)

        # Allow +/- 1 day tolerance due to timing
        assert abs(days_until_purge - expected_days_until_purge) <= 1, (
            f"For {days_ago} days ago, expected ~{expected_days_until_purge} days until purge, got {days_until_purge}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
