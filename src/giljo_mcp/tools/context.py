"""
Context and Discovery Tools for GiljoAI MCP
Handles vision documents, context retrieval, and product settings
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from fastmcp import FastMCP
from sqlalchemy import delete, select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.discovery import DiscoveryManager, PathResolver
from giljo_mcp.models import Configuration, ContextIndex, LargeDocumentIndex, Project, Vision
from giljo_mcp.tenant import TenantManager

from .chunking import EnhancedChunker
from .context_tools.framing_helpers import (
    apply_rich_entry_framing,
    build_framed_context_response,
    build_priority_excluded_response,
    get_user_priority,
)


logger = logging.getLogger(__name__)


def register_context_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register context and discovery tools with the MCP server"""

    # Initialize discovery system
    path_resolver = PathResolver(db_manager, tenant_manager)
    discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

    @mcp.tool()
    async def get_vision(part: int = 1, max_tokens: int = 20000, force_reindex: bool = False) -> dict[str, Any]:
        """
        Get the vision document for the active product (chunked if too large)
        Creates an index on first read to help orchestrator navigate vision documents.

        Args:
            part: Which part to retrieve (1-based index)
            max_tokens: Maximum tokens per part (default 20000, max 24000)
            force_reindex: Force re-indexing of vision documents

        Returns:
            Vision document content or chunk with metadata
        """
        try:
            # Get current tenant
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            async with db_manager.get_session_async() as session:
                # Find project by tenant key
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Check if we need to force reindex
                if force_reindex:
                    # Delete existing visions and indexes
                    await session.execute(delete(Vision).where(Vision.project_id == project.id))
                    await session.execute(
                        delete(ContextIndex).where(
                            ContextIndex.project_id == project.id,
                            ContextIndex.index_type == "vision",
                        )
                    )
                    await session.commit()
                    visions = []
                else:
                    # Check for vision documents in database
                    vision_query = select(Vision).where(Vision.project_id == project.id).order_by(Vision.chunk_number)
                    vision_result = await session.execute(vision_query)
                    visions = vision_result.scalars().all()

                if visions and not force_reindex:
                    # Return from database
                    if part <= len(visions):
                        vision = visions[part - 1]
                        return {
                            "success": True,
                            "part": part,
                            "total_parts": len(visions),
                            "content": vision.content,
                            "tokens": vision.tokens,
                            "boundary_type": vision.boundary_type,
                            "keywords": vision.keywords or [],
                            "headers": vision.headers or [],
                            "has_more": part < len(visions),
                            "indexed": True,
                        }
                    return {
                        "success": False,
                        "error": f"Part {part} not found. Document has {len(visions)} parts.",
                    }

                # Try to load from filesystem
                vision_path = await path_resolver.resolve_path("vision", str(project.id))
                if not vision_path.exists():
                    return {"success": False, "error": "No vision documents found"}

                # Collect all vision documents
                vision_docs = []
                vision_files = sorted(vision_path.glob("*.md"))

                for file in vision_files:
                    try:
                        content = file.read_text(encoding="utf-8")
                        vision_docs.append({"name": file.name, "content": content})
                    except Exception as e:
                        logger.warning(f"Failed to read {file}: {e}")

                if not vision_docs:
                    return {
                        "success": False,
                        "error": "No readable vision documents found",
                    }

                # Use enhanced chunker
                chunker = EnhancedChunker(max_tokens=max_tokens)
                chunks = chunker.chunk_multiple_documents(vision_docs)

                if not chunks:
                    return {
                        "success": False,
                        "error": "Failed to chunk vision documents",
                    }

                # Store chunks in database
                for chunk_data in chunks:
                    vision = Vision(
                        tenant_key=project.tenant_key,
                        project_id=project.id,
                        document_name=chunk_data["document_name"],
                        chunk_number=chunk_data["chunk_number"],
                        total_chunks=chunk_data["total_chunks"],
                        content=chunk_data["content"],
                        tokens=chunk_data["tokens"],
                        char_start=chunk_data["char_start"],
                        char_end=chunk_data["char_end"],
                        boundary_type=chunk_data["boundary_type"],
                        keywords=chunk_data["keywords"],
                        headers=chunk_data["headers"],
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(vision)

                # Create index on first read (part=1)
                if part == 1:
                    # Create context index for navigation
                    for doc in vision_docs:
                        # Find which chunks contain this document
                        doc_chunks = []
                        for i, chunk in enumerate(chunks, 1):
                            if doc["name"] in chunk["content"]:
                                doc_chunks.append(i)

                        # Extract summary (first paragraph)
                        lines = doc["content"].split("\n")
                        summary = None
                        for line in lines:
                            if line.strip() and not line.startswith("#"):
                                summary = line.strip()[:500]
                                break

                        # Create index entry
                        index_entry = ContextIndex(
                            tenant_key=project.tenant_key,
                            project_id=project.id,
                            index_type="vision",
                            document_name=doc["name"],
                            chunk_numbers=doc_chunks,
                            summary=summary,
                            token_count=chunker.estimate_tokens(doc["content"]),
                            keywords=chunker.extract_keywords(doc["content"]),
                            full_path=f"docs/vision/{doc['name']}",
                            content_hash=chunker.calculate_content_hash(doc["content"]),
                            created_at=datetime.now(timezone.utc),
                        )
                        session.add(index_entry)

                    # Create large document index
                    total_content = "\n\n".join([d["content"] for d in vision_docs])
                    large_doc_index = LargeDocumentIndex(
                        tenant_key=project.tenant_key,
                        project_id=project.id,
                        document_path="docs/vision",
                        document_type="markdown",
                        total_size=len(total_content),
                        total_tokens=chunker.estimate_tokens(total_content),
                        chunk_count=len(chunks),
                        metadata={
                            "files": [d["name"] for d in vision_docs],
                            "created": datetime.now(timezone.utc).isoformat(),
                        },
                        indexed_at=datetime.now(timezone.utc),
                    )
                    session.add(large_doc_index)

                await session.commit()

                # Return requested part
                if part <= len(chunks):
                    chunk = chunks[part - 1]
                    return {
                        "success": True,
                        "part": part,
                        "total_parts": len(chunks),
                        "content": chunk["content"],
                        "tokens": chunk["tokens"],
                        "boundary_type": chunk["boundary_type"],
                        "keywords": chunk["keywords"],
                        "headers": chunk["headers"],
                        "has_more": part < len(chunks),
                        "indexed": True,
                        "message": "Vision documents chunked and indexed successfully",
                    }
                return {
                    "success": False,
                    "error": f"Part {part} not found. Document has {len(chunks)} parts.",
                }

        except Exception as e:
            logger.exception(f"Failed to get vision: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_vision_index() -> dict[str, Any]:
        """
        Get the vision document index (ORCHESTRATOR ONLY - helps navigate vision files)

        Returns an index showing:
        - Which vision files exist and their topics
        - Which chunks contain which files
        - Keywords and token counts for each file

        Returns:
            Vision document index from database or filesystem
        """
        try:
            # Get current tenant
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            async with db_manager.get_session_async() as session:
                # Find project
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Check for context index in database
                index_query = select(ContextIndex).where(
                    ContextIndex.project_id == project.id,
                    ContextIndex.index_type == "vision",
                )
                index_result = await session.execute(index_query)
                index_entries = index_result.scalars().all()

                if index_entries:
                    # Return from database
                    index = {
                        "files": [],
                        "total_files": len(index_entries),
                        "chunks": {},
                        "from_database": True,
                    }

                    for entry in index_entries:
                        file_info = {
                            "name": entry.document_name,
                            "summary": entry.summary,
                            "token_count": entry.token_count,
                            "keywords": entry.keywords or [],
                            "chunk_numbers": entry.chunk_numbers or [],
                            "content_hash": entry.content_hash,
                        }
                        index["files"].append(file_info)

                        # Map chunks to files
                        for chunk_num in entry.chunk_numbers or []:
                            if chunk_num not in index["chunks"]:
                                index["chunks"][chunk_num] = []
                            index["chunks"][chunk_num].append(entry.document_name)

                    # Get chunk metadata
                    vision_query = select(Vision).where(Vision.project_id == project.id).order_by(Vision.chunk_number)
                    vision_result = await session.execute(vision_query)
                    visions = vision_result.scalars().all()

                    if visions:
                        index["total_chunks"] = len(visions)
                        index["chunk_metadata"] = []
                        for vision in visions:
                            index["chunk_metadata"].append(
                                {
                                    "chunk_number": vision.chunk_number,
                                    "tokens": vision.tokens,
                                    "boundary_type": vision.boundary_type,
                                    "keywords": vision.keywords or [],
                                }
                            )

                    return {
                        "success": True,
                        "index": index,
                        "message": "Index retrieved from database",
                    }

                # Fallback to filesystem scanning
                vision_path = await path_resolver.resolve_path("vision", str(project.id) if project else None)
                if not vision_path.exists():
                    return {
                        "success": False,
                        "error": "No vision directory found and no index in database",
                    }

                vision_files = sorted(vision_path.glob("*.md"))
                if not vision_files:
                    return {"success": False, "error": "No vision files found"}

                # Build index from filesystem
                chunker = EnhancedChunker()
                index = {
                    "files": [],
                    "total_files": len(vision_files),
                    "chunks": {},
                    "from_filesystem": True,
                    "message": "Index built from filesystem (run get_vision to create database index)",
                }

                for file in vision_files:
                    try:
                        content = file.read_text(encoding="utf-8")

                        # Extract summary
                        lines = content.split("\n")
                        summary = None
                        for line in lines:
                            if line.strip() and not line.startswith("#"):
                                summary = line.strip()[:500]
                                break

                        file_info = {
                            "name": file.name,
                            "summary": summary,
                            "size": len(content),
                            "estimated_tokens": chunker.estimate_tokens(content),
                            "keywords": chunker.extract_keywords(content),
                        }
                        index["files"].append(file_info)

                    except Exception as e:
                        logger.warning(f"Failed to index {file}: {e}")

                return {"success": True, "index": index}

        except Exception as e:
            logger.exception(f"Failed to get vision index: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def discover_context(agent_role: str = "default", force_refresh: bool = False) -> dict[str, Any]:
        """
        Discover context dynamically based on agent role and priority.
        Uses the new discovery system for intelligent context loading.

        Args:
            agent_role: Role of the agent (orchestrator, analyzer, implementer, tester)
            force_refresh: Force fresh discovery ignoring cache

        Returns:
            Discovered context organized by priority
        """
        try:
            # Get current tenant and project
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            async with db_manager.get_session_async() as session:
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Use discovery manager
                context = await discovery_manager.discover_context(
                    agent_role=agent_role,
                    project_id=str(project.id),
                    force_refresh=force_refresh,
                )

                return {"success": True, "context": context, "project": project.name}

        except Exception as e:
            logger.exception(f"Failed to discover context: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_context_index(product_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get the context index for intelligent querying

        Args:
            product_id: Optional product ID (uses current if not specified)

        Returns:
            Context index with available documents and sections
        """
        try:
            # Get current tenant and project
            tenant_key = tenant_manager.get_current_tenant()
            project_id = None

            if tenant_key:
                async with db_manager.get_session_async() as session:
                    project_query = select(Project).where(Project.tenant_key == tenant_key)
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()
                    if project:
                        project_id = str(project.id)

            # Get all discovery paths
            paths = await discovery_manager.get_discovery_paths(project_id)

            # Build context source information
            context_sources = {}
            for path_key, path in paths.items():
                if path.exists():
                    if path.is_dir():
                        files = list(path.glob("*"))
                        context_sources[path_key] = {
                            "path": str(path),
                            "type": "directory",
                            "files": len(files),
                            "exists": True,
                        }
                    else:
                        context_sources[path_key] = {
                            "path": str(path),
                            "type": "file",
                            "exists": True,
                            "size": path.stat().st_size,
                        }
                else:
                    context_sources[path_key] = {"path": str(path), "exists": False}

            # Check for changes
            if project_id:
                changes = await discovery_manager.detect_changes(project_id)
            else:
                changes = {}

            return {
                "success": True,
                "sources": context_sources,
                "changes_detected": changes,
                "discovery_enabled": True,
                "priorities": discovery_manager.PRIORITY_ORDER,
                "recommendation": "Use discover_context() for role-based context loading",
            }

        except Exception as e:
            logger.exception(f"Failed to get context index: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_context_section(
        document_name: str,
        section_name: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Retrieve specific content section from the index

        Args:
            document_name: Name of the document to retrieve
            section_name: Optional section within the document
            product_id: Optional product ID

        Returns:
            Document or section content
        """
        try:
            # Get current project ID
            tenant_key = tenant_manager.get_current_tenant()
            project_id = None
            if tenant_key:
                async with db_manager.get_session_async() as session:
                    project_query = select(Project).where(Project.tenant_key == tenant_key)
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()
                    if project:
                        project_id = str(project.id)

            # Map document names to paths using PathResolver
            doc_paths = {
                "vision": await path_resolver.resolve_path("vision", project_id),
                "sessions": await path_resolver.resolve_path("sessions", project_id),
                "devlog": await path_resolver.resolve_path("devlog", project_id),
                "claude": Path("CLAUDE.md"),
            }

            doc_key = document_name.lower()
            if doc_key not in doc_paths:
                return {"success": False, "error": f"Unknown document: {document_name}"}

            doc_path = doc_paths[doc_key]

            if doc_path.is_file():
                # Single file
                try:
                    content = doc_path.read_text(encoding="utf-8")

                    if section_name:
                        # Try to find section
                        lines = content.split("\n")
                        section_content = []
                        in_section = False

                        for line in lines:
                            if section_name.lower() in line.lower() and line.startswith("#"):
                                in_section = True
                            elif in_section and line.startswith("#"):
                                break
                            elif in_section:
                                section_content.append(line)

                        if section_content:
                            content = "\n".join(section_content)
                        else:
                            return {
                                "success": False,
                                "error": f"Section '{section_name}' not found",
                            }

                    return {
                        "success": True,
                        "document": document_name,
                        "section": section_name,
                        "content": content,
                    }

                except Exception as e:
                    return {"success": False, "error": f"Failed to read document: {e}"}

            elif doc_path.is_dir():
                # Directory of documents
                files = list(doc_path.glob("*.md"))

                if not files:
                    return {
                        "success": False,
                        "error": f"No documents found in {document_name}",
                    }

                # If specific document requested
                if section_name:
                    for file in files:
                        if section_name.lower() in file.stem.lower():
                            content = file.read_text(encoding="utf-8")
                            return {
                                "success": True,
                                "document": document_name,
                                "file": file.name,
                                "content": content,
                            }

                # Return list of available documents
                file_list = [f.name for f in files]
                return {
                    "success": True,
                    "document": document_name,
                    "available_files": file_list,
                    "message": f"Specify section_name with one of: {', '.join(file_list)}",
                }
            else:
                return {
                    "success": False,
                    "error": f"Document path not found: {doc_path}",
                }

        except Exception as e:
            logger.exception(f"Failed to get context section: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_product_settings(product_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get all product settings for analysis

        Args:
            product_id: Optional product ID (uses current if not specified)

        Returns:
            Complete product configuration and settings
        """
        try:
            # Get current tenant
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            async with db_manager.get_session_async() as session:
                # Find project
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Get configurations
                config_query = select(Configuration).where(Configuration.project_id == project.id)
                config_result = await session.execute(config_query)
                configs = config_result.scalars().all()

                settings = {
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "tenant_key": project.tenant_key,
                        "status": project.status,
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                    },
                    "configurations": {},
                }

                for config in configs:
                    settings["configurations"][config.key] = {
                        "value": config.value,
                        "category": config.category,
                        "updated_at": (config.updated_at.isoformat() if config.updated_at else None),
                    }

                # Load system config
                try:
                    config_path = Path.home() / ".giljo-mcp" / "config.yaml"
                    if config_path.exists():
                        with open(config_path, encoding="utf-8") as f:
                            system_config = yaml.safe_load(f)
                            settings["system_config"] = system_config
                except Exception as e:
                    logger.warning(f"Could not load system config: {e}")

                return {"success": True, "settings": settings}

        except Exception as e:
            logger.exception(f"Failed to get product settings: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def session_info() -> dict[str, Any]:
        """
        Get current session statistics

        Returns:
            Session information and statistics
        """
        try:
            tenant_key = tenant_manager.get_current_tenant()

            if not tenant_key:
                return {
                    "success": True,
                    "session": {
                        "active_project": None,
                        "tenant_key": None,
                        "message": "No active project. Use create_project or switch_project.",
                    },
                }

            async with db_manager.get_session_async() as session:
                # Find project
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": "Active tenant key does not match any project",
                    }

                # Get session stats
                from giljo_mcp.models import MCPAgentJob, Message
                from giljo_mcp.models import Session as DBSession

                # Count agent jobs (active agents)
                agent_query = select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)
                agent_result = await session.execute(agent_query)
                agents = agent_result.scalars().all()

                # Count messages
                message_query = select(Message).where(Message.project_id == project.id)
                message_result = await session.execute(message_query)
                messages = message_result.scalars().all()

                # Get active session
                session_query = select(DBSession).where(
                    DBSession.project_id == project.id, DBSession.status == "active"
                )
                session_result = await session.execute(session_query)
                active_session = session_result.scalar_one_or_none()

                return {
                    "success": True,
                    "session": {
                        "active_project": project.name,
                        "project_id": str(project.id),
                        "tenant_key": tenant_key,
                        "agents": {
                            "total": len(agents),
                            "active": len([a for a in agents if a.status == "active"]),
                            "idle": len([a for a in agents if a.status == "idle"]),
                        },
                        "messages": {
                            "total": len(messages),
                            "pending": len([m for m in messages if m.status == "pending"]),
                            "completed": len([m for m in messages if m.status == "completed"]),
                        },
                        "context_usage": f"{project.context_used}/{project.context_budget}",
                        "session_id": (str(active_session.id) if active_session else None),
                    },
                }

        except Exception as e:
            logger.exception(f"Failed to get session info: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def recalibrate_mission(project_id: str, changes_summary: str) -> dict[str, Any]:
        """
        Notify agents about mission changes - they will re-discover context as needed

        Args:
            project_id: UUID of the project
            changes_summary: Summary of what changed in the mission

        Returns:
            Recalibration confirmation
        """
        try:
            async with db_manager.get_session_async():
                # Broadcast mission change to all agents
                from .message import broadcast

                broadcast_result = await broadcast(
                    content=f"MISSION RECALIBRATION: {changes_summary}",
                    project_id=project_id,
                    priority="high",
                )

                if broadcast_result["success"]:
                    logger.info("Mission recalibration broadcast to all agents")

                    return {
                        "success": True,
                        "project_id": project_id,
                        "agents_notified": broadcast_result["broadcast_to"],
                        "summary": changes_summary,
                    }
                return broadcast_result

        except Exception as e:
            logger.exception(f"Failed to recalibrate mission: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_large_document(
        document_path: str,
        part: int = 1,
        max_tokens: int = 20000,
        force_reindex: bool = False,
    ) -> dict[str, Any]:
        """
        Get any large document with automatic chunking.
        Supports markdown, YAML, and text files over 50K tokens.

        Args:
            document_path: Path to the document (relative to project root)
            part: Which part to retrieve (1-based index)
            max_tokens: Maximum tokens per part (default 20000, max 24000)
            force_reindex: Force re-indexing of the document

        Returns:
            Document chunk with metadata
        """
        try:
            # Get current tenant
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            async with db_manager.get_session_async() as session:
                # Find project
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Check if document is already indexed
                if not force_reindex:
                    large_doc_query = select(LargeDocumentIndex).where(
                        LargeDocumentIndex.project_id == project.id,
                        LargeDocumentIndex.document_path == document_path,
                    )
                    large_doc_result = await session.execute(large_doc_query)
                    large_doc = large_doc_result.scalar_one_or_none()

                    if large_doc:
                        # Document is indexed, retrieve chunks
                        vision_query = (
                            select(Vision)
                            .where(
                                Vision.project_id == project.id,
                                Vision.document_name == document_path,
                            )
                            .order_by(Vision.chunk_number)
                        )
                        vision_result = await session.execute(vision_query)
                        chunks = vision_result.scalars().all()

                        if chunks and part <= len(chunks):
                            chunk = chunks[part - 1]
                            return {
                                "success": True,
                                "part": part,
                                "total_parts": len(chunks),
                                "content": chunk.content,
                                "tokens": chunk.tokens,
                                "boundary_type": chunk.boundary_type,
                                "keywords": chunk.keywords or [],
                                "headers": chunk.headers or [],
                                "document_type": large_doc.document_type,
                                "has_more": part < len(chunks),
                                "indexed": True,
                            }

                # Load document from filesystem
                doc_path = Path(document_path)
                if not doc_path.exists():
                    return {
                        "success": False,
                        "error": f"Document not found: {document_path}",
                    }

                # Read document content
                try:
                    content = doc_path.read_text(encoding="utf-8")
                except Exception as e:
                    return {"success": False, "error": f"Failed to read document: {e}"}

                # Detect document type
                doc_type = "text"
                if doc_path.suffix == ".md":
                    doc_type = "markdown"
                elif doc_path.suffix in [".yml", ".yaml"]:
                    doc_type = "yaml"
                elif doc_path.suffix == ".json":
                    doc_type = "json"

                # Use enhanced chunker
                chunker = EnhancedChunker(max_tokens=max_tokens)
                chunks = chunker.chunk_content(content, document_path)

                if not chunks:
                    return {"success": False, "error": "Failed to chunk document"}

                # Store chunks in database
                for chunk_data in chunks:
                    vision = Vision(
                        tenant_key=project.tenant_key,
                        project_id=project.id,
                        document_name=document_path,
                        chunk_number=chunk_data["chunk_number"],
                        total_chunks=chunk_data["total_chunks"],
                        content=chunk_data["content"],
                        tokens=chunk_data["tokens"],
                        char_start=chunk_data["char_start"],
                        char_end=chunk_data["char_end"],
                        boundary_type=chunk_data["boundary_type"],
                        keywords=chunk_data["keywords"],
                        headers=chunk_data["headers"],
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(vision)

                # Create large document index
                large_doc_index = LargeDocumentIndex(
                    tenant_key=project.tenant_key,
                    project_id=project.id,
                    document_path=document_path,
                    document_type=doc_type,
                    total_size=len(content),
                    total_tokens=chunker.estimate_tokens(content),
                    chunk_count=len(chunks),
                    metadata={
                        "file_name": doc_path.name,
                        "file_size": doc_path.stat().st_size,
                        "created": datetime.now(timezone.utc).isoformat(),
                    },
                    indexed_at=datetime.now(timezone.utc),
                )
                session.add(large_doc_index)

                await session.commit()

                # Return requested part
                if part <= len(chunks):
                    chunk = chunks[part - 1]
                    return {
                        "success": True,
                        "part": part,
                        "total_parts": len(chunks),
                        "content": chunk["content"],
                        "tokens": chunk["tokens"],
                        "boundary_type": chunk["boundary_type"],
                        "keywords": chunk["keywords"],
                        "headers": chunk["headers"],
                        "document_type": doc_type,
                        "has_more": part < len(chunks),
                        "indexed": True,
                        "message": f"Document {document_path} chunked and indexed successfully",
                    }
                return {
                    "success": False,
                    "error": f"Part {part} not found. Document has {len(chunks)} parts.",
                }

        except Exception as e:
            logger.exception(f"Failed to get large document: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_discovery_paths() -> dict[str, Any]:
        """
        Get all dynamically resolved paths for the current project.
        Shows the path resolution hierarchy: env vars -> database -> config -> defaults

        Returns:
            All resolved paths with their sources
        """
        try:
            # Get current tenant and project
            tenant_key = tenant_manager.get_current_tenant()
            project_id = None

            if tenant_key:
                async with db_manager.get_session_async() as session:
                    project_query = select(Project).where(Project.tenant_key == tenant_key)
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()
                    if project:
                        project_id = str(project.id)

            # Get all paths
            paths = await path_resolver.get_all_paths(project_id)

            # Convert to serializable format
            path_info = {}
            for key, path in paths.items():
                path_info[key] = {
                    "resolved": str(path),
                    "exists": path.exists(),
                    "is_absolute": path.is_absolute(),
                    "default": path_resolver.DEFAULT_PATHS.get(key, key),
                }

            return {
                "success": True,
                "paths": path_info,
                "project_id": project_id,
                "resolution_order": [
                    "1. Environment variables (GILJO_MCP_PATH_*)",
                    "2. Database configuration (per-project)",
                    "3. Config.yaml (paths section)",
                    "4. Default paths",
                ],
            }

        except Exception as e:
            logger.exception(f"Failed to get discovery paths: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def help() -> dict[str, Any]:
        """
        Get documentation for all available tools

        Returns:
            Complete documentation for all 20 MCP tools grouped by category
        """
        try:
            tools_documentation = {
                "success": True,
                "tool_count": 20,
                "categories": {
                    "project": {
                        "description": "Project management tools",
                        "count": 6,
                        "tools": {
                            "create_project": {
                                "description": "Create a new project with mission and optional agent sequence",
                                "parameters": {
                                    "name": "Project name (required)",
                                    "mission": "Project mission statement (required)",
                                    "agents": "Optional list of agent names",
                                },
                                "returns": "Project ID and tenant key",
                            },
                            "list_projects": {
                                "description": "List all projects with optional status filter",
                                "parameters": {"status": "Optional status filter (active, completed, etc.)"},
                                "returns": "List of projects with details",
                            },
                            "switch_project": {
                                "description": "Switch to a different project",
                                "parameters": {"project_id": "UUID of the project (required)"},
                                "returns": "Project activation confirmation",
                            },
                            "close_project": {
                                "description": "Close a completed project with summary",
                                "parameters": {
                                    "project_id": "UUID of the project (required)",
                                    "summary": "Completion summary (required)",
                                },
                                "returns": "Closure confirmation",
                            },
                            "update_project_mission": {
                                "description": "Update the mission field after orchestrator analysis",
                                "parameters": {
                                    "project_id": "UUID of the project (required)",
                                    "mission": "Updated mission statement (required)",
                                },
                                "returns": "Update confirmation",
                            },
                            "project_status": {
                                "description": "Get comprehensive project status",
                                "parameters": {"project_id": "Optional UUID (uses current if not specified)"},
                                "returns": "Complete project status and metrics",
                            },
                        },
                    },
                    "agent": {
                        "description": "Agent lifecycle management tools",
                        "count": 6,
                        "tools": {
                            "ensure_agent": {
                                "description": "Ensure an agent exists for work on a project (idempotent)",
                                "parameters": {
                                    "project_id": "UUID of the project (required)",
                                    "agent_name": "Name of the agent (required)",
                                    "mission": "Optional agent mission",
                                },
                                "returns": "Agent details or existing agent info",
                            },
                            "activate_agent": {
                                "description": "Activate orchestrator agent - STARTS WORKING IMMEDIATELY",
                                "parameters": {
                                    "project_id": "UUID of the project (required)",
                                    "agent_name": "Name of the agent (required)",
                                    "mission": "Optional agent mission",
                                },
                                "returns": "Agent activation confirmation",
                            },
                            "assign_job": {
                                "description": "Assign a job to an agent with task descriptions",
                                "parameters": {
                                    "agent_name": "Name of the agent (required)",
                                    "job_type": "Type of job (required)",
                                    "project_id": "UUID of the project (required)",
                                    "tasks": "Optional list of task descriptions",
                                    "scope_boundary": "Optional scope boundaries",
                                    "vision_alignment": "Optional vision alignment info",
                                },
                                "returns": "Job assignment confirmation",
                            },
                            "handoff": {
                                "description": "Transfer work from one agent to another",
                                "parameters": {
                                    "from_agent": "Source agent name (required)",
                                    "to_agent": "Target agent name (required)",
                                    "project_id": "UUID of the project (required)",
                                    "context": "Handoff context object (required)",
                                },
                                "returns": "Handoff confirmation",
                            },
                            "agent_health": {
                                "description": "Check agent health and context usage",
                                "parameters": {"agent_name": "Optional agent name (all if not specified)"},
                                "returns": "Agent health metrics",
                            },
                            "decommission_agent": {
                                "description": "Gracefully end an agent's work",
                                "parameters": {
                                    "agent_name": "Name of the agent (required)",
                                    "project_id": "UUID of the project (required)",
                                    "reason": "Optional reason (default: completed)",
                                },
                                "returns": "Decommission confirmation",
                            },
                        },
                    },
                    "message": {
                        "description": "Inter-agent communication tools",
                        "count": 6,
                        "tools": {
                            "send_message": {
                                "description": "Send message to one or more agents",
                                "parameters": {
                                    "to_agents": "List of recipient agent names (required)",
                                    "content": "Message content (required)",
                                    "project_id": "UUID of the project (required)",
                                    "message_type": "Optional type (default: direct)",
                                    "priority": "Optional priority (default: normal)",
                                    "from_agent": "Optional sender (default: orchestrator)",
                                },
                                "returns": "Message ID and delivery confirmation",
                            },
                            "get_messages": {
                                "description": "Retrieve pending messages for an agent",
                                "parameters": {
                                    "agent_name": "Agent name (required)",
                                    "project_id": "Optional project ID",
                                },
                                "returns": "List of pending messages",
                            },
                            "acknowledge_message": {
                                "description": "Mark message as received by agent",
                                "parameters": {
                                    "message_id": "UUID of the message (required)",
                                    "agent_name": "Agent name (required)",
                                },
                                "returns": "Acknowledgment confirmation",
                            },
                            "complete_message": {
                                "description": "Mark message as completed with result",
                                "parameters": {
                                    "message_id": "UUID of the message (required)",
                                    "agent_name": "Agent name (required)",
                                    "result": "Completion result (required)",
                                },
                                "returns": "Completion confirmation",
                            },
                            "broadcast": {
                                "description": "Broadcast message to all agents in project",
                                "parameters": {
                                    "content": "Message content (required)",
                                    "project_id": "UUID of the project (required)",
                                    "priority": "Optional priority (default: normal)",
                                },
                                "returns": "Broadcast confirmation with recipient list",
                            },
                            "log_task": {
                                "description": "Quick task capture",
                                "parameters": {
                                    "content": "Task content (required)",
                                    "category": "Optional category",
                                    "priority": "Optional priority (default: medium)",
                                },
                                "returns": "Task logging confirmation",
                            },
                        },
                    },
                    "context": {
                        "description": "Context retrieval and discovery tools",
                        "count": 8,
                        "tools": {
                            "get_vision": {
                                "description": "Get vision document for active product (chunked if large)",
                                "parameters": {
                                    "part": "Which part to retrieve (default: 1)",
                                    "max_tokens": "Max tokens per part (default: 20000)",
                                },
                                "returns": "Vision document content or chunk",
                            },
                            "get_vision_index": {
                                "description": "Get vision document index for navigation",
                                "parameters": {},
                                "returns": "Index of vision files with metadata",
                            },
                            "get_context_index": {
                                "description": "Get context index for intelligent querying",
                                "parameters": {"product_id": "Optional product ID"},
                                "returns": "Available context sources and descriptions",
                            },
                            "get_context_section": {
                                "description": "Retrieve specific content section from index",
                                "parameters": {
                                    "document_name": "Document name (required)",
                                    "section_name": "Optional section name",
                                    "product_id": "Optional product ID",
                                },
                                "returns": "Document or section content",
                            },
                            "get_product_settings": {
                                "description": "Get all product settings for analysis",
                                "parameters": {"product_id": "Optional product ID"},
                                "returns": "Complete product configuration",
                            },
                            "session_info": {
                                "description": "Get current session statistics",
                                "parameters": {},
                                "returns": "Session information and metrics",
                            },
                            "recalibrate_mission": {
                                "description": "Notify agents about mission changes",
                                "parameters": {
                                    "project_id": "UUID of the project (required)",
                                    "changes_summary": "Summary of changes (required)",
                                },
                                "returns": "Recalibration broadcast confirmation",
                            },
                            "help": {
                                "description": "Get documentation for all available tools",
                                "parameters": {},
                                "returns": "Complete tool documentation",
                            },
                        },
                    },
                },
                "usage_tips": [
                    "Use ensure_agent() for worker agents - it's idempotent and safe",
                    "Use activate_agent() only for orchestrator - it starts discovery immediately",
                    "Always acknowledge messages when received using acknowledge_message()",
                    "Complete messages with results using complete_message()",
                    "Vision documents auto-chunk for large content (50K+ tokens)",
                    "Project isolation via tenant keys enables concurrent products",
                    "All tools return success/error status for proper error handling",
                ],
            }

            return tools_documentation

        except Exception as e:
            logger.exception(f"Failed to get help documentation: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Context and discovery tools registered")


# Expose MCP tools as importable async functions for API endpoints
async def get_context_index(product_id: Optional[str] = None) -> dict[str, Any]:
    """Wrapper for MCP tool - Get the context index for intelligent querying"""
    from sqlalchemy import select

    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.discovery import DiscoveryManager, PathResolver
    from giljo_mcp.models import Project
    from giljo_mcp.tenant import TenantManager

    db_manager = DatabaseManager(is_async=True)
    tenant_manager = TenantManager()
    path_resolver = PathResolver(db_manager, tenant_manager)
    discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

    try:
        tenant_key = tenant_manager.get_current_tenant()
        project_id = None

        if tenant_key:
            async with db_manager.get_session_async() as session:
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()
                if project:
                    project_id = str(project.id)

        # Get all discovery paths
        paths = await discovery_manager.get_discovery_paths(project_id)

        # Build context source information
        context_sources = {}
        for path_key, path in paths.items():
            if path.exists():
                if path.is_dir():
                    files = list(path.glob("*"))
                    context_sources[path_key] = {
                        "path": str(path),
                        "type": "directory",
                        "files": len(files),
                        "exists": True,
                    }
                else:
                    context_sources[path_key] = {
                        "path": str(path),
                        "type": "file",
                        "exists": True,
                        "size": path.stat().st_size,
                    }
            else:
                context_sources[path_key] = {"path": str(path), "exists": False}

        # Build index
        index = {
            "product_id": product_id or "default",
            "sources": context_sources,
            "documents": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        return {"success": True, "index": index}

    except Exception as e:
        logger.exception(f"Failed to get vision index: {e}")
        return {"success": False, "error": str(e)}


async def get_vision(part: int = 1, max_tokens: int = 20000, force_reindex: bool = False) -> dict[str, Any]:
    """Wrapper for MCP tool - Get the vision document for the active product"""
    from sqlalchemy import select

    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.discovery import PathResolver
    from giljo_mcp.models import Project, Vision
    from giljo_mcp.tenant import TenantManager

    db_manager = DatabaseManager(is_async=True)
    tenant_manager = TenantManager()
    PathResolver(db_manager, tenant_manager)

    try:
        tenant_key = tenant_manager.get_current_tenant()
        if not tenant_key:
            return {"success": False, "error": "No tenant context available"}

        async with db_manager.get_tenant_session_async(tenant_key) as session:
            project_query = select(Project).where(Project.tenant_key == tenant_key)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                return {"success": False, "error": "Project not found"}

            # Check for existing vision chunks in database
            vision_query = (
                select(Vision)
                .where(Vision.project_id == project.id, Vision.tenant_key == tenant_key)
                .order_by(Vision.chunk_number)
            )
            vision_result = await session.execute(vision_query)
            visions = vision_result.scalars().all()

            if visions:
                # Return from database
                if part <= len(visions):
                    vision = visions[part - 1]
                    return {
                        "success": True,
                        "part": part,
                        "total_parts": len(visions),
                        "content": vision.content,
                        "tokens": vision.tokens,
                        "boundary_type": vision.boundary_type,
                        "keywords": vision.keywords or [],
                        "headers": vision.headers or [],
                        "has_more": part < len(visions),
                        "indexed": True,
                    }
                return {
                    "success": False,
                    "error": f"Part {part} not found. Document has {len(visions)} parts.",
                }

            # No vision data in database, return placeholder
            return {
                "success": True,
                "part": 1,
                "total_parts": 1,
                "content": "# Vision Document\n\nNo vision documents have been indexed yet. Use the MCP tools to initialize vision documents.",
                "tokens": 20,
                "boundary_type": "paragraph",
                "keywords": ["vision", "placeholder"],
                "headers": ["Vision Document"],
                "has_more": False,
                "indexed": False,
                "message": "No vision documents found - returning placeholder",
            }

    except Exception as e:
        logger.exception(f"Failed to get vision: {e}")
        return {"success": False, "error": str(e)}


async def get_vision_index() -> dict[str, Any]:
    """Wrapper for MCP tool - Get the vision document index"""
    from sqlalchemy import select

    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.discovery import PathResolver
    from giljo_mcp.models import ContextIndex, Project
    from giljo_mcp.tenant import TenantManager

    db_manager = DatabaseManager(is_async=True)
    tenant_manager = TenantManager()
    PathResolver(db_manager, tenant_manager)

    try:
        tenant_key = tenant_manager.get_current_tenant()
        if not tenant_key:
            return {"success": False, "error": "No tenant context available"}

        async with db_manager.get_tenant_session_async(tenant_key) as session:
            project_query = select(Project).where(Project.tenant_key == tenant_key)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                return {"success": False, "error": "Project not found"}

            # Check for context index in database
            index_query = select(ContextIndex).where(
                ContextIndex.project_id == project.id,
                ContextIndex.tenant_key == tenant_key,
                ContextIndex.index_type == "vision",
            )
            index_result = await session.execute(index_query)
            index_entries = index_result.scalars().all()

            if index_entries:
                # Return from database
                index = {
                    "files": [],
                    "total_files": len(index_entries),
                    "chunks": {},
                    "from_database": True,
                }

                for entry in index_entries:
                    file_info = {
                        "name": entry.document_name,
                        "summary": entry.summary,
                        "token_count": entry.token_count,
                        "keywords": entry.keywords or [],
                        "chunk_numbers": entry.chunk_numbers or [],
                        "content_hash": entry.content_hash,
                    }
                    index["files"].append(file_info)

                return {"success": True, "index": index}

            # No index found, return placeholder
            return {
                "success": True,
                "index": {
                    "files": [],
                    "total_files": 0,
                    "chunks": {},
                    "from_database": False,
                    "message": "No vision index found - use MCP tools to initialize vision documents",
                },
            }

    except Exception as e:
        logger.exception(f"Failed to get vision index: {e}")
        return {"success": False, "error": str(e)}
