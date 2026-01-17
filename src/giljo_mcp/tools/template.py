"""
Template management tools for the MCP server.
Provides tools for managing agent templates with versioning and augmentation.
"""

import logging
import time
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, select, update
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate, TemplateArchive, TemplateAugmentation, TemplateUsageStats
from src.giljo_mcp.template_manager import extract_variables, process_template
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)



