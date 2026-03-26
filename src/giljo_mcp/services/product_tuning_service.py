"""
ProductTuningService - On-demand product context drift detection (Handover 0831)

Assembles comparison prompts from current product context vs 360 memory history,
stores agent-submitted tuning proposals, and manages the review lifecycle.

Design: User-initiated, not automatic. GiljoAI assembles context and generates
the comparison prompt. The user's AI coding agent does the reasoning.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.config.defaults import (
    DEFAULT_FIELD_PRIORITY,
    TUNING_SECTION_TOGGLE_MAP,
)
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.models import Product
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository
from src.giljo_mcp.schemas.jsonb_validators import validate_tuning_state


logger = logging.getLogger(__name__)

# Maps section keys to product fields for applying proposals
# Handover 0840c: Rewritten for normalized tables
SECTION_FIELD_MAP: dict[str, dict[str, str]] = {
    "description": {"type": "direct", "field": "description"},
    "tech_stack": {
        "type": "relation",
        "relation": "tech_stack",
        "fields": {
            "programming_languages": "programming_languages",
            "frontend_frameworks": "frontend_frameworks",
            "backend_frameworks": "backend_frameworks",
            "databases_storage": "databases_storage",
            "infrastructure": "infrastructure",
            "dev_tools": "dev_tools",
        },
    },
    "architecture": {
        "type": "relation",
        "relation": "architecture",
        "fields": {
            "primary_pattern": "primary_pattern",
            "design_patterns": "design_patterns",
            "api_style": "api_style",
            "architecture_notes": "architecture_notes",
        },
    },
    "core_features": {"type": "direct", "field": "core_features"},
    "quality_standards": {"type": "relation_field", "relation": "test_config", "field": "quality_standards"},
    "target_platforms": {"type": "direct", "field": "target_platforms"},
}

# Evidence sources per section for the comparison prompt
SECTION_EVIDENCE_SOURCES: dict[str, list[str]] = {
    "description": ["summary", "key_outcomes"],
    "tech_stack": ["deliverables", "decisions_made", "git_commits"],
    "architecture": ["decisions_made"],
    "core_features": ["key_outcomes", "deliverables"],
    "codebase_structure": ["deliverables"],
    "database_type": ["decisions_made"],
    "backend_framework": ["deliverables", "decisions_made"],
    "frontend_framework": ["deliverables", "decisions_made"],
    "quality_standards": ["metrics", "decisions_made"],
    "target_platforms": ["decisions_made", "deliverables"],
    "vision_documents": ["summary"],
}


TUNING_PROMPT_TEMPLATE = """You are reviewing a product's context for accuracy after recent development work.

## Your Task
Compare the CURRENT PRODUCT CONTEXT against RECENT PROJECT HISTORY below.
For each section, determine if the current description is still accurate.

## Current Product Context
{current_context}

## Recent Project History (360 Memory — last {lookback_count} projects)
{memory_entries}

{git_section}

## Instructions
1. For each section, compare what the product context claims against
   what actually happened in recent projects.
2. Flag sections where the context is stale, incomplete, or contradicted
   by project outcomes.
3. Distinguish between intentional product evolution (update the context)
   and temporary project-specific details (don't update).
4. When proposing changes, write the COMPLETE replacement value for
   the section, not a diff or partial edit.

## Required Action
When your analysis is complete, call the submit_tuning_review MCP tool with
your findings. Use this exact structure:

- product_id: "{product_id}"
- proposals: array with one entry per section analyzed
  - section: the section key ({section_keys})
  - drift_detected: true/false
  - current_summary: brief note on what the current context says
  - evidence: what the project history/git shows that differs
  - proposed_value: the full replacement text (or current text if no drift)
  - confidence: "high" / "medium" / "low"
  - reasoning: one-sentence explanation
- overall_summary: one-paragraph summary of the product's context health

Do NOT output the analysis as text. Call the MCP tool with structured results."""


class ProductTuningService:
    """Service for product context tuning: prompt assembly, proposal storage, and review lifecycle."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        websocket_manager=None,
        test_session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._websocket_manager = websocket_manager
        self._test_session = test_session
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._memory_repo = ProductMemoryRepository()

    def _get_session(self):
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        return self.db_manager.get_session_async()

    async def _get_product(self, session: AsyncSession, product_id: str) -> Product:
        stmt = select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_key == self.tenant_key,
                Product.deleted_at.is_(None),
            )
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            raise ResourceNotFoundError(
                message="Product not found",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            )
        return product

    async def _get_user_configs(self, session: AsyncSession, user_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get user's toggle and depth configurations from normalized tables/columns."""
        from src.giljo_mcp.config.defaults import DEFAULT_CATEGORY_TOGGLES
        from src.giljo_mcp.models.auth import UserFieldPriority

        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Build toggle_config from user_field_priorities table
        prio_result = await session.execute(
            select(UserFieldPriority).where(
                and_(UserFieldPriority.user_id == user_id, UserFieldPriority.tenant_key == self.tenant_key)
            )
        )
        rows = prio_result.scalars().all()

        if rows:
            toggles = dict(DEFAULT_CATEGORY_TOGGLES)
            for row in rows:
                toggles[row.category] = row.enabled
            priorities = {"product_core": {"toggle": True}, "project_description": {"toggle": True}}
            for cat, enabled in toggles.items():
                priorities[cat] = {"toggle": enabled}
            toggle_config = {"version": "4.0", "priorities": priorities}
        else:
            toggle_config = DEFAULT_FIELD_PRIORITY

        # Build depth_config from columns
        depth_config = {
            "vision_documents": user.depth_vision_documents,
            "memory_last_n_projects": user.depth_memory_last_n,
            "git_commits": user.depth_git_commits,
            "agent_templates": user.depth_agent_templates,
            "tech_stack_sections": user.depth_tech_stack_sections,
            "architecture_depth": user.depth_architecture,
        }

        return toggle_config, depth_config

    def _get_eligible_sections(self, toggle_config: dict[str, Any]) -> list[str]:
        """Return section keys whose parent toggle is ON."""
        priorities = toggle_config.get("priorities", {})
        eligible = []
        for section_key, parent_toggle in TUNING_SECTION_TOGGLE_MAP.items():
            cat_config = priorities.get(parent_toggle, {})
            if isinstance(cat_config, dict) and cat_config.get("toggle", True):
                eligible.append(section_key)
        return eligible

    def _serialize_current_context(self, product: Product, sections: list[str]) -> str:
        """Serialize current product context for selected sections."""
        parts = []
        for section in sections:
            mapping = SECTION_FIELD_MAP.get(section)
            if not mapping:
                continue

            label = section.replace("_", " ").title()

            if mapping["type"] == "direct":
                value = getattr(product, mapping["field"], None)
            elif mapping["type"] == "relation":
                rel_obj = getattr(product, mapping["relation"], None)
                if rel_obj:
                    items = []
                    for field_name in mapping["fields"]:
                        v = getattr(rel_obj, field_name, None)
                        if v:
                            items.append(f"- {field_name}: {v}")
                    value = "\n".join(items) if items else None
                else:
                    value = None
            elif mapping["type"] == "relation_field":
                rel_obj = getattr(product, mapping["relation"], None)
                value = getattr(rel_obj, mapping["field"], None) if rel_obj else None
            else:
                continue

            if value is None:
                parts.append(f"### {label}\n(not set)")
            elif isinstance(value, list):
                parts.append(f"### {label}\n{', '.join(str(v) for v in value)}")
            else:
                parts.append(f"### {label}\n{value}")

        return "\n\n".join(parts) if parts else "(no context sections selected)"

    def _serialize_memory_entries(self, entries: list[dict[str, Any]], sections: list[str]) -> str:
        """Serialize 360 memory entries, focusing on evidence relevant to selected sections."""
        if not entries:
            return "(no project history available yet)"

        parts = []
        for entry in entries:
            project_name = entry.get("project_name", "Unknown project")
            entry_parts = [f"### Project: {project_name}"]

            relevant_fields = set()
            for section in sections:
                relevant_fields.update(SECTION_EVIDENCE_SOURCES.get(section, []))

            for field in sorted(relevant_fields):
                value = entry.get(field)
                if not value:
                    continue
                label = field.replace("_", " ").title()
                if isinstance(value, list):
                    if value and isinstance(value[0], dict):
                        items = "\n".join(f"- {item.get('message', str(item))}" for item in value[:10])
                    else:
                        items = "\n".join(f"- {v}" for v in value)
                    entry_parts.append(f"**{label}:**\n{items}")
                elif isinstance(value, dict):
                    items = "\n".join(f"- {k}: {v}" for k, v in value.items())
                    entry_parts.append(f"**{label}:**\n{items}")
                else:
                    entry_parts.append(f"**{label}:** {value}")

            parts.append("\n".join(entry_parts))

        return "\n\n---\n\n".join(parts)

    def _serialize_git_section(self, entries: list[dict[str, Any]]) -> str:
        """Extract git commits from 360 memory entries."""
        all_commits = []
        for entry in entries:
            commits = entry.get("git_commits", [])
            if commits:
                all_commits.extend(commits)

        if not all_commits:
            return ""

        commit_lines = []
        for commit in all_commits[:25]:
            sha = commit.get("sha", "")[:8]
            message = commit.get("message", "")
            commit_lines.append(f"- {sha}: {message}")

        return "## Git Activity\n" + "\n".join(commit_lines)

    async def assemble_tuning_prompt(
        self,
        product_id: str,
        user_id: str,
        sections: list[str],
    ) -> dict[str, Any]:
        """
        Assemble a comparison prompt for the user to paste into their AI coding agent.

        Args:
            product_id: Target product ID
            user_id: User ID for toggle/depth config
            sections: List of section keys to include

        Returns:
            Dict with prompt, sections_included, lookback_depth, git_enabled

        Raises:
            ResourceNotFoundError: If product or user not found
            ValidationError: If no valid sections provided
        """
        async with self._get_session() as session:
            product = await self._get_product(session, product_id)
            toggle_config, depth_config = await self._get_user_configs(session, user_id)

            eligible = self._get_eligible_sections(toggle_config)
            valid_sections = [s for s in sections if s in eligible]

            if not valid_sections:
                raise ValidationError(
                    message="No valid sections selected for tuning",
                    context={"requested": sections, "eligible": eligible},
                )

            # Get depth settings
            depths = depth_config if isinstance(depth_config, dict) else depth_config.get("depths", {})
            lookback = depths.get("memory_last_n_projects", 3)

            # Fetch 360 memory entries
            memory_entries = await self._memory_repo.get_entries_for_context(
                session=session,
                product_id=product_id,
                tenant_key=self.tenant_key,
                limit=lookback,
            )

            # Check git integration
            git_config = product.product_memory.get("git_integration", {}) if product.product_memory else {}
            git_enabled = git_config.get("enabled", False)

            # Serialize sections
            current_context = self._serialize_current_context(product, valid_sections)
            memory_text = self._serialize_memory_entries(memory_entries, valid_sections)
            git_section = self._serialize_git_section(memory_entries) if git_enabled else ""

            prompt = TUNING_PROMPT_TEMPLATE.format(
                current_context=current_context,
                lookback_count=lookback,
                memory_entries=memory_text,
                git_section=git_section,
                product_id=product_id,
                section_keys=", ".join(valid_sections),
            )

            return {
                "prompt": prompt,
                "sections_included": valid_sections,
                "lookback_depth": lookback,
                "git_enabled": git_enabled,
            }

    async def get_eligible_sections(self, product_id: str, user_id: str) -> list[str]:
        """Get sections eligible for tuning based on user's toggle settings."""
        async with self._get_session() as session:
            await self._get_product(session, product_id)
            toggle_config, _ = await self._get_user_configs(session, user_id)
            return self._get_eligible_sections(toggle_config)

    async def store_proposals(
        self,
        product_id: str,
        proposals: list[dict[str, Any]],
        overall_summary: str | None = None,
    ) -> dict[str, Any]:
        """
        Store tuning proposals submitted by an agent via submit_tuning_review.

        Args:
            product_id: Target product ID
            proposals: List of per-section proposal dicts
            overall_summary: Optional high-level drift assessment

        Returns:
            Dict with success, review_id, message
        """
        review_id = str(uuid4())

        async with self._get_session() as session:
            product = await self._get_product(session, product_id)

            tuning_state = product.tuning_state or {}
            tuning_state["pending_proposals"] = {
                "review_id": review_id,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "overall_summary": overall_summary,
                "proposals": proposals,
            }
            product.tuning_state = validate_tuning_state(tuning_state)
            product.updated_at = datetime.now(timezone.utc)

            await session.commit()

        # Emit WebSocket event after commit
        await self._emit_websocket_event(
            event_type="product:tuning:proposals_ready",
            data={
                "product_id": product_id,
                "review_id": review_id,
                "proposal_count": len(proposals),
            },
        )

        self._logger.info(f"Stored {len(proposals)} tuning proposals for product {product_id} (review {review_id})")

        return {
            "success": True,
            "review_id": review_id,
            "message": f"Stored {len(proposals)} tuning proposals for review",
        }

    async def get_proposals(self, product_id: str) -> dict[str, Any] | None:
        """Get current pending proposals for a product."""
        async with self._get_session() as session:
            product = await self._get_product(session, product_id)
            if not product.tuning_state:
                return None
            return product.tuning_state.get("pending_proposals")

    async def apply_proposal(
        self,
        product_id: str,
        section: str,
        action: str,
        value: str | None = None,
    ) -> dict[str, Any]:
        """
        Apply, edit, or dismiss a single tuning proposal.

        Args:
            product_id: Target product ID
            section: Section key (e.g., "tech_stack")
            action: "accept", "edit", or "dismiss"
            value: Override value for "edit" action

        Returns:
            Dict with success and updated section info
        """
        if action not in ("accept", "edit", "dismiss"):
            raise ValidationError(
                message="Invalid action", context={"action": action, "valid": ["accept", "edit", "dismiss"]}
            )

        async with self._get_session() as session:
            product = await self._get_product(session, product_id)

            tuning_state = product.tuning_state or {}
            pending = tuning_state.get("pending_proposals")
            if not pending:
                raise ValidationError(message="No pending proposals", context={"product_id": product_id})

            proposals = pending.get("proposals", [])
            proposal = next((p for p in proposals if p.get("section") == section), None)
            if not proposal:
                raise ValidationError(
                    message="Proposal not found for section",
                    context={"section": section, "product_id": product_id},
                )

            if action == "dismiss":
                proposals = [p for p in proposals if p.get("section") != section]
            else:
                apply_value = value if action == "edit" else proposal.get("proposed_value")
                self._apply_value_to_product(product, section, apply_value)
                proposals = [p for p in proposals if p.get("section") != section]

            # Update pending proposals
            if proposals:
                pending["proposals"] = proposals
                tuning_state["pending_proposals"] = pending
            else:
                tuning_state["pending_proposals"] = None
                tuning_state["last_tuned_at"] = datetime.now(timezone.utc).isoformat()

            product.tuning_state = validate_tuning_state(tuning_state)
            product.updated_at = datetime.now(timezone.utc)
            await session.commit()

        return {"success": True, "section": section, "action": action, "remaining_proposals": len(proposals)}

    def _apply_value_to_product(self, product: Product, section: str, value: Any) -> None:
        """Apply a tuning value to the correct product field."""
        from src.giljo_mcp.models.products import ProductArchitecture, ProductTechStack

        mapping = SECTION_FIELD_MAP.get(section)
        if not mapping:
            raise ValidationError(message=f"Unknown section: {section}", context={"section": section})

        if mapping["type"] == "direct":
            setattr(product, mapping["field"], value)
        elif mapping["type"] == "relation":
            rel_obj = getattr(product, mapping["relation"], None)
            if rel_obj is None:
                # Create the related object if it doesn't exist
                if mapping["relation"] == "tech_stack":
                    rel_obj = ProductTechStack(product_id=product.id, tenant_key=product.tenant_key)
                    product.tech_stack = rel_obj
                elif mapping["relation"] == "architecture":
                    rel_obj = ProductArchitecture(product_id=product.id, tenant_key=product.tenant_key)
                    product.architecture = rel_obj
            # Value could be a dict of fields or a string
            if isinstance(value, dict):
                for field_name, field_value in value.items():
                    if hasattr(rel_obj, field_name):
                        setattr(rel_obj, field_name, field_value)
            elif isinstance(value, str):
                # For string values, set all text fields to the value
                for field_name in mapping["fields"]:
                    setattr(rel_obj, field_name, value)
        elif mapping["type"] == "relation_field":
            from src.giljo_mcp.models.products import ProductTestConfig

            rel_obj = getattr(product, mapping["relation"], None)
            if rel_obj is None:
                rel_obj = ProductTestConfig(product_id=product.id, tenant_key=product.tenant_key)
                product.test_config = rel_obj
            setattr(rel_obj, mapping["field"], value)

    async def clear_review(self, product_id: str) -> dict[str, Any]:
        """Clear all pending proposals and update last_tuned_at."""
        async with self._get_session() as session:
            product = await self._get_product(session, product_id)

            # Get current max sequence from 360 memory
            current_sequence = await self._memory_repo.get_next_sequence(session, product_id) - 1

            tuning_state = product.tuning_state or {}
            tuning_state["pending_proposals"] = None
            tuning_state["last_tuned_at"] = datetime.now(timezone.utc).isoformat()
            tuning_state["last_tuned_at_sequence"] = max(current_sequence, 0)

            product.tuning_state = validate_tuning_state(tuning_state)
            product.updated_at = datetime.now(timezone.utc)
            await session.commit()

        self._logger.info(f"Cleared tuning review for product {product_id}")
        return {"success": True, "last_tuned_at_sequence": max(current_sequence, 0)}

    async def check_tuning_staleness(self, product_id: str, user_id: str) -> dict[str, Any]:
        """
        Check if product context needs tuning based on completed projects since last tune.

        Args:
            product_id: Product to check
            user_id: User for notification preference lookup

        Returns:
            Dict with is_stale, projects_since_tune, threshold
        """
        async with self._get_session() as session:
            product = await self._get_product(session, product_id)

            # Get user's notification preferences
            stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            prefs = (user.notification_preferences if user else None) or {}
            if not prefs.get("context_tuning_reminder", True):
                return {"is_stale": False, "projects_since_tune": 0, "threshold": 0, "enabled": False}

            threshold = max(prefs.get("tuning_reminder_threshold", 10), 3)

            # Get current sequence
            current_sequence = await self._memory_repo.get_next_sequence(session, product_id) - 1

            # Get last tuned sequence
            tuning_state = product.tuning_state or {}
            last_tuned_seq = tuning_state.get("last_tuned_at_sequence", 0)

            projects_since = max(current_sequence - last_tuned_seq, 0)

            return {
                "is_stale": projects_since >= threshold,
                "projects_since_tune": projects_since,
                "threshold": threshold,
                "enabled": True,
            }

    async def _emit_websocket_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit WebSocket event with graceful degradation."""
        if not self._websocket_manager:
            self._logger.debug(f"No WebSocket manager available for event: {event_type}")
            return

        try:
            event_data = {
                **data,
                "tenant_key": self.tenant_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=self.tenant_key, event_type=event_type, data=event_data
            )
            self._logger.debug(f"WebSocket event emitted: {event_type}")
        except (RuntimeError, ValueError) as e:
            self._logger.warning(f"Failed to emit WebSocket event {event_type}: {e}", exc_info=True)
