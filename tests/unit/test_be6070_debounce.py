# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6070: in-process monotonic debounce primitive (src/giljo_mcp/services/debounce.py).

The shared throttle behind the F5/F9 hot-path write reductions. These tests pin
the load-bearing contract: the FIRST call for a key always fires, a call within
the window is suppressed, distinct keys/namespaces are independent, and reset()
clears state (the test hook that keeps the gate parallel-safe).
"""

from __future__ import annotations

import pytest

from giljo_mcp.services import debounce


@pytest.fixture(autouse=True)
def _clean_debounce():
    debounce.reset()
    yield
    debounce.reset()


def test_first_call_always_fires():
    assert debounce.should_run("ns", "k", 30.0) is True


def test_second_call_within_window_is_suppressed():
    assert debounce.should_run("ns", "k", 30.0) is True
    assert debounce.should_run("ns", "k", 30.0) is False


def test_distinct_keys_are_independent():
    assert debounce.should_run("ns", "a", 30.0) is True
    assert debounce.should_run("ns", "b", 30.0) is True


def test_distinct_namespaces_are_independent():
    assert debounce.should_run("ns1", "k", 30.0) is True
    assert debounce.should_run("ns2", "k", 30.0) is True


def test_zero_interval_never_suppresses():
    # A non-positive window means "never debounce" — every call fires.
    assert debounce.should_run("ns", "k", 0.0) is True
    assert debounce.should_run("ns", "k", 0.0) is True


def test_reset_namespace_clears_only_that_bucket():
    assert debounce.should_run("ns1", "k", 30.0) is True
    assert debounce.should_run("ns2", "k", 30.0) is True
    debounce.reset("ns1")
    # ns1 fires again (cleared); ns2 still suppressed.
    assert debounce.should_run("ns1", "k", 30.0) is True
    assert debounce.should_run("ns2", "k", 30.0) is False


def test_reset_all_clears_everything():
    assert debounce.should_run("ns1", "k", 30.0) is True
    assert debounce.should_run("ns2", "k", 30.0) is True
    debounce.reset()
    assert debounce.should_run("ns1", "k", 30.0) is True
    assert debounce.should_run("ns2", "k", 30.0) is True
