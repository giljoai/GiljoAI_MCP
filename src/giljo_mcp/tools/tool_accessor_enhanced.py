"""
Enhanced Tool Accessor for API Integration
Provides direct access to MCP tool functions with improved error handling,
retry logic, performance timing, and transaction management
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from giljo_mcp.database import DatabaseManager

# Import from centralized exceptions
from giljo_mcp.exceptions import DatabaseError, RetryExhaustedError, ValidationError
from giljo_mcp.models import Agent, Message, Project, Task
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

T = TypeVar("T")


def validate_uuid(uuid_string: str, param_name: str = "id") -> UUID:
    """Validate and convert UUID string"""
    try:
        return UUID(uuid_string)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid UUID for {param_name}: {uuid_string}")


def measure_performance(operation_name: str):
    """Decorator to measure and log operation performance"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(self, *args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log performance
                logger.info(f"{operation_name} completed in {duration_ms:.2f}ms")

                # Add timing to result if it's a dict
                if isinstance(result, dict):
                    result["_performance_ms"] = duration_ms

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.exception(f"{operation_name} failed after {duration_ms:.2f}ms: {e}")
                raise

        return wrapper

    return decorator


def with_retry(max_attempts: int = 3, backoff_factor: float = 2.0):
    """Decorator to add retry logic with exponential backoff"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(self, *args, **kwargs)

                except OperationalError as e:
                    # Database connection errors - retry
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = (backoff_factor**attempt) * 0.1
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s: {e}")
                        await asyncio.sleep(wait_time)
                    continue

                except IntegrityError as e:
                    # Constraint violations - don't retry
                    logger.exception(f"Integrity error, not retrying: {e}")
                    raise DatabaseError(f"Database constraint violation: {e}")

                except Exception as e:
                    # Other errors - don't retry
                    logger.exception(f"Unexpected error, not retrying: {e}")
                    raise

            # All retries exhausted
            raise RetryExhaustedError(f"Failed after {max_attempts} attempts: {last_exception}")

        return wrapper

    return decorator


class EnhancedToolAccessor:
    """Enhanced Tool Accessor with improved error handling and performance"""

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._performance_metrics = {}

    @asynccontextmanager
    async def _get_transactional_session(self):
        """Get a database session with proper transaction management"""
        async with self.db_manager.get_session_async() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.exception(f"Transaction rolled back: {e}")
                raise

    # Project Tools with Enhanced Error Handling

    @measure_performance("create_project")
    @with_retry(max_attempts=3)
    async def create_project(
        self, name: str, mission: str, agents: Optional[list[str]] = None, product_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a new project with transaction rollback on failure"""
        try:
            async with self._get_transactional_session() as session:
                # Generate unique tenant key
                tenant_key = f"tk_{uuid4().hex}"

                # Create project
                project = Project(
                    name=name,
                    mission=mission,
                    tenant_key=tenant_key,
                    product_id=product_id,
                    status="active",
                    context_budget=150000,
                    context_used=0,
                )

                session.add(project)
                await session.flush()  # Get the project ID

                project_id = str(project.id)

                # Initialize agents if provided
                if agents:
                    for agent_name in agents:
                        agent = Agent(
                            name=agent_name,
                            project_id=project.id,
                            tenant_key=tenant_key,
                            status="active",
                            role=agent_name,  # Use agent name as default role
                        )
                        session.add(agent)

                # Commit handled by context manager

                logger.info(f"Created project {project_id} with tenant key {tenant_key}")

                return {
                    "success": True,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "product_id": product_id,
                    "name": name,
                    "status": "active",
                }

        except SQLAlchemyError as e:
            logger.exception(f"Database error creating project: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error creating project: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("list_projects")
    @with_retry(max_attempts=2)
    async def list_projects(self, status: Optional[str] = None) -> dict[str, Any]:
        """List all projects with optional status filter"""
        try:
            async with self.db_manager.get_session_async() as session:
                query = select(Project)
                if status:
                    query = query.where(Project.status == status)

                result = await session.execute(query)
                projects = result.scalars().all()

                project_list = []
                for project in projects:
                    project_list.append(
                        {
                            "id": str(project.id),
                            "name": project.name,
                            "mission": project.mission,
                            "status": project.status,
                            "tenant_key": project.tenant_key,
                            "created_at": project.created_at.isoformat(),
                            "updated_at": (project.updated_at.isoformat() if project.updated_at else None),
                            "context_budget": project.context_budget,
                            "context_used": project.context_used,
                        }
                    )

                return {
                    "success": True,
                    "projects": project_list,
                    "count": len(project_list),
                }

        except SQLAlchemyError as e:
            logger.exception(f"Database error listing projects: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error listing projects: {e}")
            return {"success": False, "error": str(e)}

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Get a specific project by ID"""
        try:
            async with self.db_manager.get_session_async() as session:
                query = select(Project).where(Project.id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "status": project.status,
                        "product_id": project.product_id,
                        "tenant_key": project.tenant_key,
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                        "created_at": project.created_at.isoformat() if project.created_at else None,
                        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                    },
                }

        except SQLAlchemyError as e:
            logger.exception(f"Database error getting project: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Failed to get project: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("project_status")
    @with_retry(max_attempts=2)
    async def project_status(self, project_id: Optional[str] = None) -> dict[str, Any]:
        """Get comprehensive project status with validation"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Validate UUID if provided
                if project_id:
                    project_uuid = validate_uuid(project_id, "project_id")
                    query = select(Project).where(Project.id == project_uuid)
                else:
                    query = select(Project).where(Project.status == "active").limit(1)

                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Get agents
                agent_result = await session.execute(select(Agent).where(Agent.project_id == project.id))
                agents = agent_result.scalars().all()

                # Get pending messages
                message_result = await session.execute(
                    select(Message).where(Message.project_id == project.id, Message.status == "pending")
                )
                pending_messages = len(message_result.scalars().all())

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "status": project.status,
                        "tenant_key": project.tenant_key,
                        "created_at": project.created_at.isoformat(),
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                    },
                    "agents": [
                        {
                            "name": agent.name,
                            "status": agent.status,
                            "role": agent.role,
                            "context_used": agent.context_used,
                        }
                        for agent in agents
                    ],
                    "pending_messages": pending_messages,
                    "agent_count": len(agents),
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error getting project status: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error getting project status: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("close_project")
    @with_retry(max_attempts=3)
    async def close_project(self, project_id: str, summary: str) -> dict[str, Any]:
        """Close a completed project with summary"""
        try:
            project_uuid = validate_uuid(project_id, "project_id")

            async with self._get_transactional_session() as session:
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_uuid)
                    .values(
                        status="completed",
                        updated_at=datetime.utcnow(),
                        meta_data={"summary": summary},
                    )
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                logger.info(f"Closed project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} closed successfully",
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error closing project: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error closing project: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("update_project_mission")
    @with_retry(max_attempts=3)
    async def update_project_mission(self, project_id: str, mission: str) -> dict[str, Any]:
        """Update the mission field after orchestrator analysis"""
        try:
            project_uuid = validate_uuid(project_id, "project_id")

            async with self._get_transactional_session() as session:
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_uuid)
                    .values(mission=mission, updated_at=datetime.utcnow())
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                return {"success": True, "message": "Mission updated successfully"}

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error updating mission: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error updating mission: {e}")
            return {"success": False, "error": str(e)}

    # Agent Tools with Enhanced Error Handling

    @measure_performance("ensure_agent")
    @with_retry(max_attempts=3)
    async def ensure_agent(self, project_id: str, agent_name: str, mission: Optional[str] = None) -> dict[str, Any]:
        """Ensure an agent exists for work on a project (idempotent)"""
        try:
            project_uuid = validate_uuid(project_id, "project_id")

            async with self._get_transactional_session() as session:
                # Get project
                result = await session.execute(select(Project).where(Project.id == project_uuid))
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Check if agent exists
                agent_result = await session.execute(
                    select(Agent).where(Agent.name == agent_name, Agent.project_id == project_uuid)
                )
                agent = agent_result.scalar_one_or_none()

                if agent:
                    return {
                        "success": True,
                        "agent": agent_name,
                        "agent_id": str(agent.id),
                        "message": "Agent already exists",
                        "is_existing": True,
                    }

                # Create agent
                agent = Agent(
                    name=agent_name,
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    status="active",
                    role=mission,
                )

                session.add(agent)
                # Commit handled by context manager

                return {
                    "success": True,
                    "agent": agent_name,
                    "agent_id": str(agent.id),
                    "message": "Agent created successfully",
                    "is_existing": False,
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error ensuring agent: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error ensuring agent: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("agent_health")
    @with_retry(max_attempts=2)
    async def agent_health(self, agent_name: Optional[str] = None) -> dict[str, Any]:
        """Check agent health and context usage with null safety"""
        try:
            async with self.db_manager.get_session_async() as session:
                if agent_name:
                    result = await session.execute(select(Agent).where(Agent.name == agent_name))
                    agents = [result.scalar_one_or_none()]
                    if not agents[0]:
                        return {
                            "success": False,
                            "error": f"Agent '{agent_name}' not found",
                        }
                else:
                    result = await session.execute(select(Agent))
                    agents = result.scalars().all()

                if not agents:
                    return {"success": False, "error": "No agents found"}

                health_data = []
                for agent in agents:
                    if agent:
                        health_data.append(
                            {
                                "name": agent.name,
                                "status": agent.status,
                                "context_used": agent.context_used or 0,
                                "message_count": 0,  # Skip relationship access in async context
                                "created_at": (agent.created_at.isoformat() if agent.created_at else None),
                            }
                        )

                return {
                    "success": True,
                    "health": health_data[0] if agent_name else health_data,
                    "count": 1 if agent_name else len(health_data),
                }

        except SQLAlchemyError as e:
            logger.exception(f"Database error checking agent health: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error checking agent health: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("decommission_agent")
    @with_retry(max_attempts=3)
    async def decommission_agent(self, agent_name: str, project_id: str, reason: str = "completed") -> dict[str, Any]:
        """Gracefully end an agent's work"""
        try:
            project_uuid = validate_uuid(project_id, "project_id")

            async with self._get_transactional_session() as session:
                result = await session.execute(
                    update(Agent)
                    .where(Agent.name == agent_name, Agent.project_id == project_uuid)
                    .values(
                        status="decommissioned",
                        meta_data={
                            "reason": reason,
                            "decommissioned_at": datetime.utcnow().isoformat(),
                        },
                    )
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Agent not found"}

                return {
                    "success": True,
                    "message": f"Agent {agent_name} decommissioned",
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error decommissioning agent: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error decommissioning agent: {e}")
            return {"success": False, "error": str(e)}

    # Message Tools with Enhanced Error Handling

    @measure_performance("send_message")
    @with_retry(max_attempts=3)
    async def send_message(
        self,
        to_agents: list[str],
        content: str,
        project_id: str,
        message_type: str = "direct",
        priority: str = "normal",
        from_agent: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send message to one or more agents with validation"""
        try:
            project_uuid = validate_uuid(project_id, "project_id")

            if not to_agents:
                raise ValidationError("to_agents list cannot be empty")

            async with self._get_transactional_session() as session:
                # Get project
                result = await session.execute(select(Project).where(Project.id == project_uuid))
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Create message
                message = Message(
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    from_agent_id=from_agent or "orchestrator",
                    to_agents=to_agents,
                    content=content,
                    message_type=message_type,
                    priority=priority,
                    status="pending",
                    acknowledged_by=[],  # Initialize as empty list
                    completed_by=[],  # Initialize as empty list
                )

                session.add(message)
                # Commit handled by context manager

                return {
                    "success": True,
                    "message_id": str(message.id),
                    "to_agents": to_agents,
                    "type": message_type,
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error sending message: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error sending message: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("get_messages")
    @with_retry(max_attempts=2)
    async def get_messages(self, agent_name: str, project_id: Optional[str] = None) -> dict[str, Any]:
        """Retrieve pending messages for an agent with auto-acknowledgment"""
        try:
            project_uuid = None
            if project_id:
                project_uuid = validate_uuid(project_id, "project_id")

            async with self._get_transactional_session() as session:
                query = select(Message).where(Message.status == "pending")

                if project_uuid:
                    query = query.where(Message.project_id == project_uuid)

                result = await session.execute(query)
                messages = result.scalars().all()

                # Filter messages for this agent and auto-acknowledge
                agent_messages = []
                for msg in messages:
                    if agent_name in (msg.to_agents or []) or not msg.to_agents:
                        # Auto-acknowledge if not already acknowledged
                        if msg.acknowledged_by is None:
                            msg.acknowledged_by = []

                        if agent_name not in msg.acknowledged_by:
                            msg.acknowledged_by.append(agent_name)
                            # Mark for update in session
                            session.add(msg)

                        agent_messages.append(
                            {
                                "id": str(msg.id),
                                "from": msg.from_agent_id,
                                "content": msg.content,
                                "type": msg.message_type,
                                "priority": msg.priority,
                                "created": msg.created_at.isoformat(),
                            }
                        )

                # Commit acknowledgments
                # Handled by context manager

                return {
                    "success": True,
                    "agent": agent_name,
                    "count": len(agent_messages),
                    "messages": agent_messages,
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error getting messages: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error getting messages: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("acknowledge_message")
    @with_retry(max_attempts=3)
    async def acknowledge_message(self, message_id: str, agent_name: str) -> dict[str, Any]:
        """Mark message as received by agent with null safety"""
        try:
            message_uuid = validate_uuid(message_id, "message_id")

            async with self._get_transactional_session() as session:
                result = await session.execute(select(Message).where(Message.id == message_uuid))
                message = result.scalar_one_or_none()

                if not message:
                    return {"success": False, "error": "Message not found"}

                # Initialize if null
                if message.acknowledged_by is None:
                    message.acknowledged_by = []

                # Add to acknowledged_by array if not already present
                if agent_name not in message.acknowledged_by:
                    message.acknowledged_by.append(agent_name)
                    session.add(message)
                    # Commit handled by context manager

                return {
                    "success": True,
                    "message_id": message_id,
                    "acknowledged_by": agent_name,
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error acknowledging message: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error acknowledging message: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("complete_message")
    @with_retry(max_attempts=3)
    async def complete_message(self, message_id: str, agent_name: str, result: str) -> dict[str, Any]:
        """Mark message as completed with result"""
        try:
            message_uuid = validate_uuid(message_id, "message_id")

            async with self._get_transactional_session() as session:
                msg_result = await session.execute(select(Message).where(Message.id == message_uuid))
                message = msg_result.scalar_one_or_none()

                if not message:
                    return {"success": False, "error": "Message not found"}

                # Update message
                message.status = "completed"
                message.result = result

                # Initialize if null
                if message.completed_by is None:
                    message.completed_by = []

                # Add completion info
                completion_info = {
                    "agent": agent_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "notes": result,
                }
                message.completed_by.append(completion_info)
                message.completed_at = datetime.utcnow()

                session.add(message)
                # Commit handled by context manager

                return {
                    "success": True,
                    "message_id": message_id,
                    "completed_by": agent_name,
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error completing message: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error completing message: {e}")
            return {"success": False, "error": str(e)}

    @measure_performance("broadcast")
    async def broadcast(self, content: str, project_id: str, priority: str = "normal") -> dict[str, Any]:
        """Broadcast message to all agents in project (optimized)"""
        try:
            project_uuid = validate_uuid(project_id, "project_id")

            async with self.db_manager.get_session_async() as session:
                # Get all agents in project
                result = await session.execute(select(Agent).where(Agent.project_id == project_uuid))
                agents = result.scalars().all()

                if not agents:
                    return {"success": False, "error": "No agents found in project"}

                agent_names = [agent.name for agent in agents]

                # Send message to all agents (no recursive call)
                return await self.send_message(
                    to_agents=agent_names,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority=priority,
                    from_agent="orchestrator",
                )

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error broadcasting message: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error broadcasting message: {e}")
            return {"success": False, "error": str(e)}

    # Task Tools

    @measure_performance("log_task")
    @with_retry(max_attempts=3)
    async def log_task(self, content: str, category: Optional[str] = None, priority: str = "medium") -> dict[str, Any]:
        """Quick task capture with validation"""
        try:
            if not content:
                raise ValidationError("Task content cannot be empty")

            async with self._get_transactional_session() as session:
                # Get the first active project as context
                from sqlalchemy import select

                stmt = select(Project).where(Project.status == "active").limit(1)
                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if not project:
                    # Create a default project for task logging
                    project = Project(
                        name="Default Tasks",
                        mission="Default project for task logging",
                        tenant_key=f"tk_{uuid4().hex[:12]}",
                        status="active",
                    )
                    session.add(project)
                    await session.flush()

                task = Task(
                    tenant_key=project.tenant_key,
                    project_id=str(project.id),
                    title=content,  # Use content as title
                    description=content,  # Also store as description
                    category=category,
                    priority=priority,
                    status="pending",
                )

                session.add(task)
                # Commit handled by context manager

                return {
                    "success": True,
                    "task_id": str(task.id),
                    "message": "Task logged successfully",
                }

        except ValidationError as e:
            logger.exception(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        except SQLAlchemyError as e:
            logger.exception(f"Database error logging task: {e}")
            return {"success": False, "error": f"Database error: {e!s}"}
        except Exception as e:
            logger.exception(f"Unexpected error logging task: {e}")
            return {"success": False, "error": str(e)}

    # Context Tools (stubs remain the same)

    async def get_context_index(self, product_id: Optional[str] = None) -> dict[str, Any]:
        """Get the context index for intelligent querying"""
        return {"success": True, "index": {"documents": [], "sections": []}}

    async def get_vision(self, part: int = 1, max_tokens: int = 20000) -> dict[str, Any]:
        """Get the vision document"""
        return {
            "success": True,
            "part": part,
            "total_parts": 1,
            "content": "Vision document placeholder",
            "tokens": 100,
        }

    async def get_vision_index(self) -> dict[str, Any]:
        """Get the vision document index"""
        return {"success": True, "index": {"files": [], "chunks": []}}

    async def get_product_settings(self, product_id: Optional[str] = None) -> dict[str, Any]:
        """Get all product settings for analysis"""
        return {
            "success": True,
            "settings": {"product_id": product_id or "default", "config": {}},
        }

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get accumulated performance metrics"""
        return self._performance_metrics
