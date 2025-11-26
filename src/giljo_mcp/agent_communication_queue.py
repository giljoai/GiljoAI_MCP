"""
Lightweight in-memory AgentCommunicationQueue to satisfy integration tests.

The original persistence layer is out of scope; tests only assert that messages
can be sent, retrieved, and tenant-scoped. This implementation stores messages
in memory per-instance and filters by tenant_key/job_id/message_type.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4


class AgentCommunicationQueue:
    """Simple in-memory message queue with tenant isolation."""

    def __init__(self, db_manager: Any):
        # db_manager is accepted for signature compatibility but unused here.
        self.db_manager = db_manager
        self._messages: List[Dict[str, Any]] = []

    def send_message(
        self,
        session: Any,
        job_id: str,
        tenant_key: str,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: str,
        priority: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        message = {
            "message_id": str(uuid4()),
            "job_id": job_id,
            "tenant_key": tenant_key,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "content": content,
            "priority": priority,
            "metadata": metadata or {},
        }
        self._messages.append(message)
        return {"status": "success", "message_id": message["message_id"]}

    def get_messages(
        self,
        session: Any,
        job_id: str,
        tenant_key: str,
        message_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        msgs = [
            m
            for m in self._messages
            if m.get("job_id") == job_id
            and m.get("tenant_key") == tenant_key
            and (message_type is None or m.get("message_type") == message_type)
        ]
        return {"status": "success", "messages": msgs}
