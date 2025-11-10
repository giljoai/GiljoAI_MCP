"""
Dependencies for Product Endpoints - Handover 0126

Provides dependency injection for database access.

NOTE: ProductService does not exist yet. This module uses direct DB access
temporarily until ProductService is extracted in a future handover.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User


# No ProductService yet - endpoints will use direct DB access temporarily
# TODO: Create ProductService and add get_product_service dependency
