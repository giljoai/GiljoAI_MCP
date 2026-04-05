"""Backward-compatibility shim — use JobStatisticsRepository or ProductStatisticsRepository directly."""

from src.giljo_mcp.repositories.job_statistics_repository import JobStatisticsRepository
from src.giljo_mcp.repositories.product_statistics_repository import ProductStatisticsRepository


__all__ = ["JobStatisticsRepository", "ProductStatisticsRepository", "StatisticsRepository"]

# Deprecated: use JobStatisticsRepository or ProductStatisticsRepository directly
StatisticsRepository = JobStatisticsRepository
