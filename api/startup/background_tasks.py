# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Background tasks initialization module

Handles background tasks: download token cleanup, API metrics sync, and one-time purge.
Extracted from api/app.py lifespan function (lines ~335-577).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from api.app import APIState
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import ApiMetrics, Product, Project
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


async def cleanup_expired_download_tokens(state: APIState):
    """Background task to cleanup expired download tokens every 15 minutes"""
    from src.giljo_mcp.download_tokens import TokenManager

    while True:
        try:
            await asyncio.sleep(900)  # 15 minutes

            if state.db_manager:
                async with state.db_manager.get_session_async() as session:
                    token_manager = TokenManager(session)
                    result = await token_manager.cleanup_expired_tokens()
                    # Backward-compatible handling: support int or dict
                    deleted_total = result.get("total", 0) if isinstance(result, dict) else int(result or 0)
                    if deleted_total > 0:
                        logger.info(f"Download token cleanup: {deleted_total} tokens removed")
                    else:
                        logger.debug("Download token cleanup: no tokens removed")
        except (SQLAlchemyError, TypeError, ValueError, AttributeError) as e:  # noqa: PERF203
            logger.error(f"Error during download token cleanup: {e}", exc_info=True)


async def sync_api_metrics_to_db(state: APIState):
    """Background task to sync API metrics to the database every 5 minutes."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        if state.db_manager:
            async with state.db_manager.get_session_async() as session:
                try:
                    # Get a copy of the current counters and reset them
                    api_counts = state.api_call_count.copy()
                    mcp_counts = state.mcp_call_count.copy()
                    state.api_call_count.clear()
                    state.mcp_call_count.clear()

                    for tenant_key, api_count in api_counts.items():
                        mcp_count = mcp_counts.get(tenant_key, 0)

                        stmt = (
                            insert(ApiMetrics)
                            .values(
                                tenant_key=tenant_key,
                                date=datetime.now(timezone.utc),
                                total_api_calls=api_count,
                                total_mcp_calls=mcp_count,
                            )
                            .on_conflict_do_update(
                                index_elements=["tenant_key"],
                                set_={
                                    "total_api_calls": ApiMetrics.total_api_calls + api_count,
                                    "total_mcp_calls": ApiMetrics.total_mcp_calls + mcp_count,
                                    "date": datetime.now(timezone.utc),
                                },
                            )
                        )
                        await session.execute(stmt)
                    await session.commit()
                    logger.info(f"Synced API metrics for {len(api_counts)} tenants.")
                except SQLAlchemyError as e:
                    logger.error(f"Error during API metrics sync: {e}", exc_info=True)
                    # If sync fails, restore the counters
                    state.api_call_count.update(api_counts)
                    state.mcp_call_count.update(mcp_counts)


async def purge_expired_deleted_items(db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Run one-time purge of expired deleted projects and products (Handover 0070)"""
    try:
        logger.info("Running startup purge of expired deleted items...")

        # Get all tenants that have deleted items
        async with db_manager.get_session_async() as session:
            # Find all unique tenant keys with deleted items
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=10)

            # Get unique tenants with expired deleted projects
            project_stmt = (
                select(Project.tenant_key)
                .distinct()
                .where(Project.deleted_at.isnot(None), Project.deleted_at < cutoff_date)
            )
            project_result = await session.execute(project_stmt)
            project_tenants = {row[0] for row in project_result.fetchall()}

            # Get unique tenants with expired deleted products
            product_stmt = (
                select(Product.tenant_key)
                .distinct()
                .where(Product.deleted_at.isnot(None), Product.deleted_at < cutoff_date)
            )
            product_result = await session.execute(product_stmt)
            product_tenants = {row[0] for row in product_result.fetchall()}

            all_tenants = project_tenants | product_tenants

            if not all_tenants:
                logger.debug("[Handover 0070] No expired deleted items to purge")
            else:
                total_projects_purged = 0
                total_products_purged = 0

                # Purge for each tenant
                for tenant_key in all_tenants:
                    # Purge expired deleted projects
                    project_service = ProjectService(db_manager=db_manager, tenant_manager=tenant_manager)
                    # Set tenant context for this purge
                    tenant_manager.set_current_tenant(tenant_key)

                    project_purge_result = await project_service.purge_expired_deleted_projects(days_before_purge=10)
                    total_projects_purged += project_purge_result.purged_count

                    # Purge expired deleted products
                    product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)

                    product_purge_result = await product_service.purge_expired_deleted_products(days_before_purge=10)
                    total_products_purged += product_purge_result.purged_count

                # Clear tenant context
                tenant_manager.clear_current_tenant()

                if total_projects_purged > 0 or total_products_purged > 0:
                    logger.info(
                        f"[Handover 0070] Purged {total_projects_purged} expired deleted project(s) "
                        f"and {total_products_purged} expired deleted product(s)"
                    )
                else:
                    logger.debug("[Handover 0070] No expired deleted items to purge")

        logger.info("Startup purge complete")
    except Exception as e:  # Broad catch: background task startup, non-fatal
        logger.error(f"Failed to purge expired deleted items: {e}", exc_info=True)
        logger.warning("Continuing startup despite purge failure")


async def init_background_tasks(state: APIState) -> None:
    """Initialize background tasks: cleanup, metrics sync, and one-time purge

    Args:
        state: APIState instance to populate with task references

    Raises:
        Exception: Logged but not raised - background task failures are non-fatal
    """
    # Start download token cleanup task (Handover 0100)
    try:
        logger.info("Starting download token cleanup task...")
        cleanup_task = asyncio.create_task(cleanup_expired_download_tokens(state))
        state.cleanup_task = cleanup_task  # Store reference to prevent garbage collection
        logger.info("Download token cleanup task started (runs every 15 minutes)")
    except Exception as e:  # Broad catch: background task startup, non-fatal
        logger.error(f"Failed to start download token cleanup task: {e}", exc_info=True)

    # Start API metrics sync task
    try:
        logger.info("Starting API metrics sync task...")
        metrics_sync_task = asyncio.create_task(sync_api_metrics_to_db(state))
        state.metrics_sync_task = metrics_sync_task
        logger.info("API metrics sync task started (runs every 5 minutes)")
    except Exception as e:  # Broad catch: background task startup, non-fatal
        logger.error(f"Failed to start API metrics sync task: {e}", exc_info=True)

    # Run one-time purge of expired deleted items
    if state.db_manager:
        await purge_expired_deleted_items(state.db_manager, state.tenant_manager)
