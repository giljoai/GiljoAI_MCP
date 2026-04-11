# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Backward-compatibility shim — use JobStatisticsRepository or ProductStatisticsRepository directly."""

from src.giljo_mcp.repositories.job_statistics_repository import JobStatisticsRepository
from src.giljo_mcp.repositories.product_statistics_repository import ProductStatisticsRepository


__all__ = ["JobStatisticsRepository", "ProductStatisticsRepository", "StatisticsRepository"]

# Deprecated: use JobStatisticsRepository or ProductStatisticsRepository directly
StatisticsRepository = JobStatisticsRepository
