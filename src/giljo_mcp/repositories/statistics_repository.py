# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Backward-compatibility shim — use JobStatisticsRepository or ProductStatisticsRepository directly."""

from giljo_mcp.repositories.job_statistics_repository import JobStatisticsRepository
from giljo_mcp.repositories.product_statistics_repository import ProductStatisticsRepository


__all__ = ["JobStatisticsRepository", "ProductStatisticsRepository", "StatisticsRepository"]

# Deprecated: use JobStatisticsRepository or ProductStatisticsRepository directly
StatisticsRepository = JobStatisticsRepository
