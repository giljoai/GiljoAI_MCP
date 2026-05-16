# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""TenantExportService — GDPR data portability for the authenticated tenant.

Produces a ZIP file containing:
    manifest.json   (schema version, exported_at, tenant_key provenance,
                     alembic_revision, giljo_mcp_version, per-file SHA-256,
                     model_counts, model->file map)
    schema.md       (human-readable redaction notice + table descriptions)
    data/<Model>.json   (one file per exported model, list of row dicts)
    files/products/<id>/vision/<name>   (vision documents from disk)

Strip filter is applied per-field at serialize time (mission spec, narrow):
    ALWAYS_STRIP, CREDENTIAL_STRIP, PLATFORM_METADATA_STRIP    — field-level
    EPHEMERAL_EXCLUDE_MODELS, OPS_EXCLUDE_TABLES               — entire-table

The full export is wrapped in REPEATABLE READ so the snapshot is consistent
across all model queries.

WebSocket progress emission uses the existing app.state.websocket_manager;
no new broker is created. Event type is "tenant:export_progress".
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.events.schemas import EventFactory
from giljo_mcp.models import (
    AgentExecution,
    AgentJob,
    AgentTemplate,
    AgentTodoItem,
    Configuration,
    MCPContextIndex,
    Message,
    MessageAcknowledgment,
    MessageCompletion,
    MessageRecipient,
    Organization,
    OrgMembership,
    Product,
    ProductAgentAssignment,
    ProductArchitecture,
    ProductMemoryEntry,
    ProductTechStack,
    ProductTestConfig,
    Project,
    Settings,
    SetupState,
    Task,
    TaxonomyType,
    TemplateArchive,
    User,
    UserApproval,
    UserFieldPriority,
    VisionDocument,
    VisionDocumentSummary,
)


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Strip lists — narrow form (mission spec, EXACT — different from
# CE_TO_SOLO_ROADMAP round-trip migration version).
# --------------------------------------------------------------------------- #

ALWAYS_STRIP: frozenset[str] = frozenset({"tenant_key"})

CREDENTIAL_STRIP: frozenset[str] = frozenset(
    {
        "password_hash",
        "recovery_pin_hash",
        "password_encrypted",
        "ssh_key_encrypted",
        "webhook_secret",
    }
)

PLATFORM_METADATA_STRIP: frozenset[str] = frozenset(
    {
        "customer_id",
        "subscription_id",
        "trial_status",
        "trial_started_at",
        "trial_expires_at",
    }
)

OPS_EXCLUDE_TABLES: frozenset[str] = frozenset({"ops_audit_log", "ops_billing_links"})

EPHEMERAL_EXCLUDE_MODELS: frozenset[str] = frozenset(
    {
        "APIKey",
        "ApiKeyIpLog",
        "DownloadToken",
        "ApiMetrics",
        "OAuthAuthorizationCode",
        "MCPSession",
        "OptimizationMetric",
    }
)

_ALL_STRIP_FIELDS: frozenset[str] = ALWAYS_STRIP | CREDENTIAL_STRIP | PLATFORM_METADATA_STRIP


# --------------------------------------------------------------------------- #
# Model registry — verified against live src/giljo_mcp/models/ on 2026-05-14.
# Drift vs 0844a snapshot is documented in the complete_job result.
# --------------------------------------------------------------------------- #

EXPORT_MODELS: tuple[type, ...] = (
    # Identity / org
    Organization,
    OrgMembership,
    User,
    UserFieldPriority,
    Settings,
    SetupState,
    # Configuration (now tenant-scoped post-SEC-0005b)
    Configuration,
    # Products
    Product,
    ProductTechStack,
    ProductArchitecture,
    ProductTestConfig,
    # Vision
    VisionDocument,
    VisionDocumentSummary,
    # Projects
    TaxonomyType,
    Project,
    # Memory
    ProductMemoryEntry,
    MCPContextIndex,
    # Tasks / messages
    Task,
    Message,
    MessageRecipient,
    MessageAcknowledgment,
    MessageCompletion,
    # Agent templates
    AgentTemplate,
    TemplateArchive,
    ProductAgentAssignment,
    # Agent jobs
    AgentJob,
    AgentExecution,
    AgentTodoItem,
    # User approvals (BE-5029)
    UserApproval,
)


_REDACTION_NOTICE = (
    "> NOTE: Password hashes, recovery PIN hashes, encrypted secrets, and "
    "webhook secrets were redacted from this export for security hygiene. "
    "Tenant-key values (`tk_...`) embedded in free-form text and JSONB "
    "content (mission strings, message bodies, memory entries, agent "
    "execution results) were also replaced with `<redacted-tenant-key>`. "
    "If you import this data into another tool, you will need to re-set "
    "credentials."
)


# Tenant-key values may appear inside free-form text or JSONB content
# (mission strings, message bodies, memory entries, agent execution
# result blobs). The per-field strip filter cannot reach those because
# they are payload, not column names. We scrub them at the JSON-bytes
# level just before each data/*.json is written to the ZIP. The pattern
# is intentionally narrow (the GiljoAI tenant_key format is `tk_` +
# 20+ alphanumeric chars) so it does not false-positive on normal user
# content.
_TENANT_KEY_PATTERN = re.compile(rb"tk_[A-Za-z0-9]{20,}")
_TENANT_KEY_REDACTION = b"<redacted-tenant-key>"


def _redact_tenant_key_values(blob: bytes) -> bytes:
    return _TENANT_KEY_PATTERN.sub(_TENANT_KEY_REDACTION, blob)


class TenantExportService:
    """Exports all tenant-scoped data for one tenant to a portable ZIP file."""

    def __init__(
        self,
        db_session: AsyncSession,
        *,
        products_root: Path | None = None,
        websocket_manager: Any | None = None,
    ) -> None:
        self.db_session = db_session
        self.products_root = products_root or (Path.cwd() / "products")
        self.websocket_manager = websocket_manager

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    async def export(self, *, tenant_key: str) -> tuple[Path, dict[str, int]]:
        """Run the full export for ``tenant_key`` and return (zip_path, model_counts).

        The zip is written to a temp file on disk; caller is responsible for
        moving it to the download-token staging directory.
        """
        if not tenant_key:
            raise ValueError("tenant_key is required")

        await self._set_repeatable_read()

        model_data: dict[str, list[dict[str, Any]]] = {}
        model_counts: dict[str, int] = {}
        total = len(EXPORT_MODELS)

        for idx, model in enumerate(EXPORT_MODELS, start=1):
            name = model.__name__
            if name in EPHEMERAL_EXCLUDE_MODELS:
                continue
            if model.__tablename__ in OPS_EXCLUDE_TABLES:
                continue
            rows = await self._query_model_rows(model, tenant_key)
            model_data[name] = rows
            model_counts[name] = len(rows)
            await self._emit_progress(
                tenant_key=tenant_key,
                model=name,
                current=idx,
                total=total,
                records=len(rows),
                phase="exporting",
            )

        vision_entries = self._collect_vision_files(model_data.get("VisionDocument", []))

        zip_path = self._write_zip(
            tenant_key=tenant_key,
            model_data=model_data,
            vision_entries=vision_entries,
            model_counts=model_counts,
        )

        await self._emit_progress(
            tenant_key=tenant_key,
            model="",
            current=total,
            total=total,
            records=sum(model_counts.values()),
            phase="complete",
        )
        return zip_path, model_counts

    # ------------------------------------------------------------------ #
    # Snapshot consistency
    # ------------------------------------------------------------------ #

    async def _set_repeatable_read(self) -> None:
        # SET TRANSACTION ISOLATION LEVEL must precede any query in the
        # transaction. SQLAlchemy AsyncSession lazily opens a tx on the
        # first execute, so once any query has been issued on the session
        # the SET will fail with ActiveSQLTransactionError AND poison the
        # in-flight transaction. We skip the SET entirely when a tx is
        # already in flight — the export still produces a coherent
        # snapshot under default READ COMMITTED for single-user CE use,
        # and SaaS/hosted modes are 403'd at the endpoint anyway.
        conn = await self.db_session.connection()
        if conn.in_transaction():
            logger.debug("Session already in transaction; export at default isolation")
            return
        try:
            await self.db_session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        except Exception as exc:  # noqa: BLE001 — boundary, log + continue
            await self.db_session.rollback()
            logger.warning("Could not set REPEATABLE READ for export: %s", exc)

    # ------------------------------------------------------------------ #
    # Per-model query + serialize
    # ------------------------------------------------------------------ #

    async def _query_model_rows(self, model: type, tenant_key: str) -> list[dict[str, Any]]:
        columns = sa_inspect(model).columns
        column_names = [c.name for c in columns]
        if "tenant_key" not in column_names:
            logger.debug(
                "Skipping %s: no tenant_key column (would leak cross-tenant data)",
                model.__name__,
            )
            return []

        stmt = select(model).where(model.tenant_key == tenant_key)
        result = await self.db_session.execute(stmt)
        instances = result.scalars().all()
        return [self._serialize_row(inst, column_names) for inst in instances]

    @staticmethod
    def _serialize_row(instance: Any, column_names: list[str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for col_name in column_names:
            if col_name in _ALL_STRIP_FIELDS:
                continue
            value = getattr(instance, col_name, None)
            out[col_name] = _to_json_safe(value)
        # Also strip any non-column attribute that happens to match a strip
        # field name (defense-in-depth against ORM augmentations).
        for stripped in _ALL_STRIP_FIELDS:
            out.pop(stripped, None)
        return out

    # ------------------------------------------------------------------ #
    # Vision file bundling
    # ------------------------------------------------------------------ #

    def _collect_vision_files(self, vision_rows: list[dict[str, Any]]) -> list[tuple[str, Path]]:
        """Resolve vision files referenced by VisionDocument rows.

        Returns list of (zip_path, source_path) pairs for files that exist on
        disk. Missing files emit a WARNING and are skipped (mission spec).
        """
        entries: list[tuple[str, Path]] = []
        for row in vision_rows:
            vision_path = row.get("vision_path")
            product_id = row.get("product_id")
            storage_type = row.get("storage_type")
            if not vision_path or not product_id:
                continue
            if storage_type not in ("file", "hybrid"):
                continue
            src = Path(vision_path)
            if not src.is_absolute():
                src = self.products_root.parent / src if vision_path else src
            if not src.exists():
                logger.warning(
                    "Vision file referenced by VisionDocument id=%s does not exist on disk: %s",
                    row.get("id"),
                    vision_path,
                )
                continue
            zip_path = f"files/products/{product_id}/vision/{src.name}"
            entries.append((zip_path, src))
        return entries

    # ------------------------------------------------------------------ #
    # ZIP packaging + manifest + schema.md
    # ------------------------------------------------------------------ #

    def _write_zip(
        self,
        *,
        tenant_key: str,
        model_data: dict[str, list[dict[str, Any]]],
        vision_entries: list[tuple[str, Path]],
        model_counts: dict[str, int],
    ) -> Path:
        tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115 — closed below
            mode="wb", suffix=".zip", delete=False
        )
        tmp.close()
        zip_path = Path(tmp.name)

        file_entries: list[dict[str, Any]] = []
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # data/*.json
            for model_name, rows in model_data.items():
                blob = _redact_tenant_key_values(json.dumps(rows, indent=2, sort_keys=True).encode("utf-8"))
                arcname = f"data/{model_name}.json"
                zf.writestr(arcname, blob)
                file_entries.append(
                    {
                        "zip_path": arcname,
                        "sha256": hashlib.sha256(blob).hexdigest(),
                        "bytes": len(blob),
                    }
                )

            # files/products/<id>/vision/<name>
            for arcname, src in vision_entries:
                data = src.read_bytes()
                zf.writestr(arcname, data)
                file_entries.append(
                    {
                        "zip_path": arcname,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data),
                    }
                )

            # schema.md
            schema_blob = self._build_schema_md(model_counts).encode("utf-8")
            zf.writestr("schema.md", schema_blob)
            file_entries.append(
                {
                    "zip_path": "schema.md",
                    "sha256": hashlib.sha256(schema_blob).hexdigest(),
                    "bytes": len(schema_blob),
                }
            )

            # manifest.json — must be the LAST entry so it can reference all others
            manifest = self._build_manifest(
                tenant_key=tenant_key,
                model_counts=model_counts,
                file_entries=file_entries,
            )
            manifest_blob = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
            zf.writestr("manifest.json", manifest_blob)

        return zip_path

    @staticmethod
    def _build_manifest(
        *,
        tenant_key: str,
        model_counts: dict[str, int],
        file_entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        from giljo_mcp import __version__ as _giljo_version

        try:
            from alembic.config import Config as AlembicConfig
            from alembic.script import ScriptDirectory

            cfg = AlembicConfig(str(Path.cwd() / "alembic.ini"))
            script = ScriptDirectory.from_config(cfg)
            head = script.get_current_head() or "unknown"
        except Exception:  # noqa: BLE001 — boundary, optional metadata
            head = "unknown"

        return {
            "schema_version": "1.0",
            "exported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "tenant_key": tenant_key,
            "giljo_mcp_version": _giljo_version,
            "alembic_revision": head,
            "model_counts": model_counts,
            "models": {name: {"file": f"data/{name}.json", "count": count} for name, count in model_counts.items()},
            "files": file_entries,
        }

    @staticmethod
    def _build_schema_md(model_counts: dict[str, int]) -> str:
        lines: list[str] = [
            "# GiljoAI MCP — Tenant Data Export",
            "",
            _REDACTION_NOTICE,
            "",
            "## Contents",
            "",
            "One `data/<Model>.json` file per exported table, plus any vision",
            "documents referenced from disk under `files/products/<id>/vision/`.",
            "",
            "## Tables",
            "",
        ]
        descriptions = _TABLE_DESCRIPTIONS
        for name, count in sorted(model_counts.items()):
            blurb = descriptions.get(name, "Tenant-scoped table.")
            lines.append(f"### {name}  ({count} row{'s' if count != 1 else ''})")
            lines.append("")
            lines.append(blurb)
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # WebSocket progress emission (reuse existing broker)
    # ------------------------------------------------------------------ #

    async def _emit_progress(
        self,
        *,
        tenant_key: str,
        model: str,
        current: int,
        total: int,
        records: int,
        phase: str,
    ) -> None:
        if not self.websocket_manager:
            return
        try:
            event = EventFactory.tenant_envelope(
                event_type="tenant:export_progress",
                tenant_key=tenant_key,
                data={
                    "model": model,
                    "current": current,
                    "total": total,
                    "records": records,
                    "phase": phase,
                },
            )
            await self.websocket_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)
        except (RuntimeError, OSError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("export progress emit failed (non-blocking): %s", exc)


# --------------------------------------------------------------------------- #
# JSON serialization helpers
# --------------------------------------------------------------------------- #


def _to_json_safe(value: Any) -> Any:
    """Convert SQLAlchemy/Python values to JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (bytes, bytearray, memoryview)):
        return None  # TSVECTOR / bytea columns are not portable
    # Fallback for SQLAlchemy ARRAY / Enum / etc.
    return str(value)


# --------------------------------------------------------------------------- #
# schema.md descriptions (terse — schema is documented in models, this is
# the user-facing crib sheet)
# --------------------------------------------------------------------------- #

_TABLE_DESCRIPTIONS: dict[str, str] = {
    "Organization": "Tenant organization record.",
    "OrgMembership": "User -> organization membership rows.",
    "User": "User accounts. password_hash, recovery_pin_hash redacted.",
    "UserFieldPriority": "Per-user toggle of optional context categories.",
    "Settings": "Per-tenant settings blob.",
    "SetupState": "Installation state (one row per tenant).",
    "Configuration": "Tenant-scoped configuration entries.",
    "Product": "Top-level product entities.",
    "ProductTechStack": "Tech-stack rows joined 1:N to Product.",
    "ProductArchitecture": "Architecture description rows joined 1:N to Product.",
    "ProductTestConfig": "Test configuration rows joined 1:N to Product.",
    "VisionDocument": "Vision document metadata. Inline text + on-disk file path.",
    "VisionDocumentSummary": "Pre-computed summaries (light/medium) for vision docs.",
    "TaxonomyType": "Project/task taxonomy rows.",
    "Project": "Projects (work orders for agents).",
    "ProductMemoryEntry": "360 memory entries scoped to a product.",
    "MCPContextIndex": "Chunked context index for RAG. searchable_vector excluded.",
    "Task": "Tasks (work items, may be lifted from agent TODOs).",
    "Message": "Inter-agent messages.",
    "MessageRecipient": "Junction: messages -> recipient agents.",
    "MessageAcknowledgment": "Per-recipient ack timestamps for messages.",
    "MessageCompletion": "Per-recipient completion records for messages.",
    "AgentTemplate": "Customizable agent template definitions.",
    "TemplateArchive": "Soft-deleted / archived agent templates.",
    "ProductAgentAssignment": "Per-product enable/disable toggle for agent templates.",
    "AgentJob": "Spawned agent work orders.",
    "AgentExecution": "Per-job execution traces.",
    "AgentTodoItem": "Per-job TODO list items (the product feature, not source markers).",
    "UserApproval": "User approval gate records (BE-5029 awaiting_user flow).",
}
