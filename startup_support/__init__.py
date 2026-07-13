# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Helper package for the CE startup entry point (BE-9060 mechanical split).

Modules here are imported by startup.py only AFTER its venv-relaunch guard has
re-executed inside the project virtualenv, so they may import third-party
packages (colorama) at module top. Keep this __init__ import-free so importing
the package has no side effects.

Monkeypatch seam gotcha: ``startup.py`` and each ``startup_support`` module do
``from startup_support.console import print_success`` (etc.), so each holds its
OWN module-level binding of the symbol. ``patch("startup.print_success")`` only
rebinds the name in the ``startup`` namespace — it does NOT intercept calls made
from within ``startup_support.checks``/``services`` (those resolve through their
own module globals). To stub console output for those, patch the per-module
binding, e.g. ``patch("startup_support.checks.print_success")``.
"""
