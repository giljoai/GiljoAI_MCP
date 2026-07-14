# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

from __future__ import annotations

import pytest

from giljo_mcp.models.settings import Settings
from giljo_mcp.models.system_setting import SystemSetting
from giljo_mcp.repositories.agent_operations_repository import AgentOperationsRepository
from giljo_mcp.services.silence_detector import DEFAULT_SILENCE_THRESHOLD_MINUTES, _get_silence_threshold


SILENCE_THRESHOLD_KEY = "agent_silence_threshold_minutes"


@pytest.mark.asyncio
async def test_silence_threshold_reads_global_system_setting(db_session):
    db_session.add(SystemSetting(key=SILENCE_THRESHOLD_KEY, value="17"))
    await db_session.flush()

    result = await AgentOperationsRepository().get_silence_threshold_setting(db_session)

    assert result == 17


@pytest.mark.asyncio
async def test_silence_threshold_falls_back_when_system_setting_missing(db_session):
    result = await _get_silence_threshold(db_session)

    assert result == DEFAULT_SILENCE_THRESHOLD_MINUTES


@pytest.mark.asyncio
async def test_silence_threshold_ignores_tenant_general_settings_rows(db_session):
    db_session.add_all(
        [
            Settings(
                tenant_key="tk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                category="general",
                settings_data={SILENCE_THRESHOLD_KEY: 2},
            ),
            Settings(
                tenant_key="tk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                category="general",
                settings_data={SILENCE_THRESHOLD_KEY: 99},
            ),
            SystemSetting(key=SILENCE_THRESHOLD_KEY, value="14"),
        ]
    )
    await db_session.flush()

    result = await AgentOperationsRepository().get_silence_threshold_setting(db_session)

    assert result == 14


@pytest.mark.asyncio
async def test_silence_threshold_clamps_global_system_setting_to_minimum(db_session):
    db_session.add(SystemSetting(key=SILENCE_THRESHOLD_KEY, value="0"))
    await db_session.flush()

    result = await AgentOperationsRepository().get_silence_threshold_setting(db_session)

    assert result == 1
