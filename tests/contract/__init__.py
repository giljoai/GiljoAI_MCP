# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Cross-layer contract tests.

Tests in this directory assert that two or more independently-maintained
layers (e.g. backend Python and frontend Vue) agree on a shared contract.
A failure here means a code change drifted one side without updating the
other -- the message will name which side has extras and how to sync them.
"""
