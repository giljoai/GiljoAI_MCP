"""
Priority framing utilities for MCP context tools (Handover 0248b).

Provides helper functions to:
- Fetch user priority configuration for a given context category
- Inject priority framing headers into context content
- Safely format rich sequential history entries
- Build framed responses for MCP context tools
"""

import json
import logging
from typing import Any, Callable, Dict, Optional

from sqlalchemy import select

from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import User

logger = logging.getLogger(__name__)

ALLOWED_PRIORITY_CATEGORIES = {
    "product_core",
    "vision_documents",
    "tech_stack",
    "architecture",
    "testing",
    "agent_templates",
    "project_description",
    "memory_360",
    "git_history",
}


def format_list_safely(items: Any) -> str:
    """Format list with graceful handling of empty or invalid data."""
    if not items:
        return "- (None)"

    if not isinstance(items, list):
        logger.warning("Expected list when formatting outcomes/decisions", extra={"type": str(type(items))})
        return "- (Invalid data)"

    try:
        return "\n".join(f"- {item}" for item in items if item)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Failed to format list", extra={"error": str(exc)})
        return "- (Error formatting data)"


def apply_rich_entry_framing(entry: Dict[str, Any]) -> str:
    """
    Apply priority framing to a rich product_memory_entries entry.

    Raises:
        ValueError: if required fields are missing
    """
    required_fields = ["sequence", "project_name", "summary"]
    for field in required_fields:
        if field not in entry:
            logger.error("Invalid memory entry", extra={"missing_field": field, "entry_keys": list(entry)})
            raise ValueError(f"Invalid entry: missing {field}")

    sequence = entry.get("sequence", 0)
    project_name = entry.get("project_name", "Unknown Project")
    summary = entry.get("summary", "No summary available")
    key_outcomes = entry.get("key_outcomes", [])
    decisions_made = entry.get("decisions_made", [])
    priority = entry.get("priority", 3)
    significance = entry.get("significance_score", 0.5)

    if not isinstance(key_outcomes, list):
        logger.warning("key_outcomes malformed", extra={"type": str(type(key_outcomes))})
        key_outcomes = []

    if not isinstance(decisions_made, list):
        logger.warning("decisions_made malformed", extra={"type": str(type(decisions_made))})
        decisions_made = []

    priority_label = {1: "CRITICAL", 2: "IMPORTANT", 3: "REFERENCE"}.get(priority, "REFERENCE")

    framing = (
        f"## {priority_label}: Project Memory (Sequence {sequence})\n"
        f"**Project**: {project_name}\n"
        f"**Summary**: {summary}\n\n"
        f"**Key Outcomes**:\n{format_list_safely(key_outcomes)}\n\n"
        f"**Decisions Made**:\n{format_list_safely(decisions_made)}\n\n"
        f"**Significance**: {significance:.2f}"
    )

    logger.debug("Applied rich entry framing", extra={"sequence": sequence, "priority": priority_label})
    return framing


def _extract_priorities(config: Any) -> Dict[str, int]:
    """Extract priority mapping from user config supporting legacy and nested formats."""
    if not isinstance(config, dict):
        return {}

    # Handle nested format: {"priorities": {"category": {"toggle": True, "priority": X}}}
    if isinstance(config.get("priorities"), dict):
        priorities = config["priorities"]
        # Check if values are nested dicts with "priority" key
        extracted = {}
        for key, value in priorities.items():
            if isinstance(value, dict) and "priority" in value:
                extracted[key] = value["priority"]
            elif isinstance(value, int):
                extracted[key] = value
        if extracted:
            return extracted
        # Legacy format: {"priorities": {"category": X}}
        return priorities

    # Legacy format: {"fields": {"category": X}}
    if isinstance(config.get("fields"), dict):
        return config["fields"]

    # Fallback: direct mapping at top-level
    return {k: v for k, v in config.items() if isinstance(v, int)}


def _stringify_content(content: Any) -> str:
    """Convert content to a printable string with safe fallback."""
    if isinstance(content, str):
        text = content.strip()
    else:
        try:
            text = json.dumps(content, indent=2, ensure_ascii=True)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to serialize content for framing", extra={"error": str(exc)})
            text = str(content)

    if not text:
        raise ValueError("Content must be non-empty string")

    return text


async def get_user_priority(
    category: str,
    tenant_key: str,
    user_id: Optional[str],
    db_manager: Optional[DatabaseManager],
) -> int:
    """
    Get priority for a category using user config or defaults.

    Returns default priority if user not provided, not found, or config invalid.
    """
    if category not in ALLOWED_PRIORITY_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}'. "
            f"Valid categories: {sorted(ALLOWED_PRIORITY_CATEGORIES)}"
        )

    # Handle nested format: {"category": {"toggle": True, "priority": X}}
    category_config = DEFAULT_FIELD_PRIORITY["priorities"].get(category, {})
    if isinstance(category_config, dict):
        default_priority = category_config.get("priority", 3)
    else:
        # Fallback for legacy integer format
        default_priority = category_config if isinstance(category_config, int) else 3

    if not user_id or db_manager is None:
        return default_priority

    try:
        async with db_manager.get_session_async() as session:
            result = await session.execute(
                select(User).where(User.id == user_id, User.tenant_key == tenant_key)
            )
            user = result.scalar_one_or_none()

            if not user or not user.field_priority_config:
                return default_priority

            priorities = _extract_priorities(user.field_priority_config)
            user_priority = priorities.get(category, default_priority)
            if user_priority not in {1, 2, 3, 4}:
                logger.warning(
                    "Invalid priority value in user config, falling back to default",
                    extra={"user_id": user_id, "category": category, "priority": user_priority},
                )
                return default_priority

            return int(user_priority)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning(
            "Failed to fetch user priority config, using defaults",
            extra={"error": str(exc), "user_id": user_id, "category": category},
        )
        return default_priority


def inject_priority_framing(
    content: Any,
    priority: int,
    category: str,
    user_id: Optional[str] = None,
) -> str:
    """
    Inject priority framing headers into content.

    Returns an empty string when priority=4 (EXCLUDE).
    Raises ValueError when content is empty.
    """
    if priority not in {1, 2, 3, 4}:
        logger.warning("Invalid priority supplied, defaulting to REFERENCE", extra={"priority": priority})
        priority = 3

    if priority == 4:
        logger.info("Content excluded by priority", extra={"category": category, "user_id": user_id})
        return ""

    text = _stringify_content(content)
    label = {1: "CRITICAL", 2: "IMPORTANT", 3: "REFERENCE"}.get(priority, "REFERENCE")
    field_label = category.replace("_", " ").title()

    framed_content = f"## {label}: {field_label}\n\n{text}\n\n---"

    # CRITICAL items get primacy + recency via duplication
    if priority == 1:
        framed_content = (
            framed_content
            + "\n\n"
            + f"## {label} Recap: {field_label}\n\n{text}\n\n---"
        )

    logger.info(
        "Applied priority framing",
        extra={"category": category, "priority": label, "content_length": len(text), "user_id": user_id},
    )
    return framed_content


def build_priority_excluded_response(source: str, category: str, tenant_key: str, priority: int) -> Dict[str, Any]:
    """Return a standardized response when a category is excluded (priority=4)."""
    return {
        "source": source,
        "category": category,
        "data": [],
        "metadata": {
            "tenant_key": tenant_key,
            "priority": priority,
            "excluded_by_priority": True,
        },
        "framed_content": "",
        "priority": priority,
    }


async def build_framed_context_response(
    raw_result: Dict[str, Any],
    category: str,
    tenant_key: str,
    user_id: Optional[str],
    db_manager: Optional[DatabaseManager],
    content_formatter: Optional[Callable[[Dict[str, Any]], str]] = None,
    priority_override: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Apply priority framing to a context tool response.

    Adds:
        - priority: numeric priority applied
        - framed_content: content with priority headers
        - metadata.priority, metadata.framing_applied
    """
    priority = (
        priority_override
        if priority_override is not None
        else await get_user_priority(category, tenant_key, user_id, db_manager)
    )

    metadata = dict(raw_result.get("metadata", {}) or {})
    metadata["priority"] = priority
    metadata.setdefault("tenant_key", tenant_key)

    try:
        content_payload = content_formatter(raw_result) if content_formatter else {
            "source": raw_result.get("source"),
            "depth": raw_result.get("depth"),
            "data": raw_result.get("data"),
            "metadata": raw_result.get("metadata"),
        }
        framed_content = inject_priority_framing(content_payload, priority, category, user_id)
        metadata["framing_applied"] = bool(framed_content)
        response = dict(raw_result)
        response["priority"] = priority
        response["metadata"] = metadata
        response["framed_content"] = framed_content
        response["category"] = category
        return response
    except ValueError as exc:
        metadata["framing_applied"] = False
        metadata["framing_error"] = str(exc)
        response = dict(raw_result)
        response["priority"] = priority
        response["metadata"] = metadata
        response["framed_content"] = ""
        response["category"] = category
        logger.warning(
            "Failed to apply framing; returning unframed content",
            extra={"category": category, "error": str(exc), "user_id": user_id},
        )
        return response
