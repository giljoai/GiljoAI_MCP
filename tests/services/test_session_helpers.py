# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Behaviour tests for the shared tenant-scoped session helpers (BE-8000d item 1).

These lock the THREE distinct behaviour contracts the helpers consolidated, so a
future edit that accidentally collapses them (the drift that motivated dup-1) is
caught. Pure logic — no DB — using a fake session (dict-backed ``.info``) and a
fake manager that records the ``tenant_key`` it was called with. Parallel-safe:
no module-level mutable state; each test builds its own fakes.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace

from giljo_mcp.services._session_helpers import (
    optional_tenant_session,
    tenant_context_session,
    tenant_scoped_session,
)


TK = "tk_helper_test_0001"


def _fake_session():
    # tenant_session_context reads/writes ``session.info`` as a plain dict.
    return SimpleNamespace(info={})


class _FakeDBManager:
    """Records the tenant_key passed to get_session_async and yields a fake session."""

    def __init__(self):
        self.calls = []
        self.produced = None

    def get_session_async(self, tenant_key=None):
        self.calls.append(tenant_key)
        sess = _fake_session()
        self.produced = sess

        @asynccontextmanager
        async def _cm():
            yield sess

        return _cm()


# --- optional_tenant_session: context applied on the injected session ONLY when a key is present ---


async def test_optional_injected_with_key_applies_and_restores_context():
    dbm = _FakeDBManager()
    inj = _fake_session()
    async with optional_tenant_session(dbm, TK, inj) as s:
        assert s is inj
        assert s.info["tenant_key"] == TK
    assert "tenant_key" not in inj.info  # restored (was absent before)
    assert dbm.calls == []  # fallback path not taken


async def test_optional_injected_without_key_bare_yields():
    dbm = _FakeDBManager()
    inj = _fake_session()
    async with optional_tenant_session(dbm, None, inj) as s:
        assert s is inj
        assert "tenant_key" not in s.info  # no context applied
    assert dbm.calls == []


async def test_optional_fallback_passes_key_to_manager():
    dbm = _FakeDBManager()
    async with optional_tenant_session(dbm, TK, None) as s:
        assert s is dbm.produced
    assert dbm.calls == [TK]


# --- tenant_scoped_session: context ALWAYS applied on the injected session ---


async def test_scoped_injected_always_applies_context():
    dbm = _FakeDBManager()
    inj = _fake_session()
    async with tenant_scoped_session(dbm, TK, inj) as s:
        assert s is inj
        assert s.info["tenant_key"] == TK
    assert "tenant_key" not in inj.info
    assert dbm.calls == []


async def test_scoped_fallback_passes_key_to_manager():
    dbm = _FakeDBManager()
    async with tenant_scoped_session(dbm, TK, None) as s:
        assert s is dbm.produced
    assert dbm.calls == [TK]


# --- tenant_context_session: manager called WITHOUT a key, session still wrapped via context ---


async def test_context_injected_applies_context():
    dbm = _FakeDBManager()
    inj = _fake_session()
    async with tenant_context_session(dbm, TK, inj) as s:
        assert s is inj
        assert s.info["tenant_key"] == TK
    assert "tenant_key" not in inj.info


async def test_context_fallback_gets_session_without_key_then_wraps():
    dbm = _FakeDBManager()
    async with tenant_context_session(dbm, TK, None) as s:
        assert s is dbm.produced
        # The differentiator vs the other two helpers: the manager is called with
        # NO tenant_key, but the session is still tenant-scoped by the wrapping context.
        assert s.info["tenant_key"] == TK
    assert dbm.calls == [None]
