# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.

"""Unit tests for startup.get_deployment_context() and _get_external_host().

Guards the branching behaviour that controls browser auto-open host and
status banner content for demo / saas-production / localhost deployments.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_STARTUP_PATH = Path(__file__).resolve().parents[2] / "startup.py"


@pytest.fixture(scope="module")
def startup_module():
    """Load startup.py as a module without running its CLI entry-point."""
    spec = importlib.util.spec_from_file_location("_giljo_startup_under_test", _STARTUP_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_yaml(tmp_path: Path, body: str) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(body, encoding="utf-8")
    return cfg


def test_returns_demo_when_deployment_context_demo(startup_module, tmp_path, monkeypatch):
    _write_yaml(tmp_path, "deployment_context: demo\n")
    monkeypatch.chdir(tmp_path)
    assert startup_module.get_deployment_context() == "demo"


def test_returns_localhost_when_key_missing(startup_module, tmp_path, monkeypatch):
    _write_yaml(tmp_path, "services:\n  external_host: ''\n")
    monkeypatch.chdir(tmp_path)
    assert startup_module.get_deployment_context() == "localhost"


def test_returns_saas_production_when_explicitly_set(startup_module, tmp_path, monkeypatch):
    _write_yaml(tmp_path, "deployment_context: saas-production\n")
    monkeypatch.chdir(tmp_path)
    assert startup_module.get_deployment_context() == "saas-production"


def test_returns_localhost_when_no_config_file(startup_module, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no config.yaml
    assert startup_module.get_deployment_context() == "localhost"


def test_external_host_read_from_services_block(startup_module, tmp_path, monkeypatch):
    _write_yaml(
        tmp_path,
        "deployment_context: demo\nservices:\n  external_host: demo.giljo.ai\n",
    )
    monkeypatch.chdir(tmp_path)
    assert startup_module._get_external_host() == "demo.giljo.ai"


def test_external_host_empty_when_absent(startup_module, tmp_path, monkeypatch):
    _write_yaml(tmp_path, "deployment_context: localhost\n")
    monkeypatch.chdir(tmp_path)
    assert startup_module._get_external_host() == ""
