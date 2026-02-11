"""
Tests for service-layer Pydantic response models.

Follows TDD: these tests are written BEFORE the implementation models.
Each model is tested for:
1. Creation with valid data
2. Required field validation (missing fields raise ValidationError)
3. Default values
4. model_dump() serialization
5. from_attributes compatibility (ConfigDict)

Created: Handover 0731
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.giljo_mcp.schemas.service_responses import (
    AuthResult,
    BroadcastResult,
    CascadeImpact,
    ConsolidationResult,
    ConversionResult,
    DeleteResult,
    GitIntegrationSettings,
    InstructionsResponse,
    MessageListResult,
    MissionResponse,
    MissionUpdateResult,
    OperationResult,
    PaginatedResult,
    PathValidationResult,
    ProductStatistics,
    PurgeResult,
    SendMessageResult,
    SetupState,
    SpawnResult,
    SuccessionResult,
    SuccessionStatus,
    TaskListResponse,
    TaskSummary,
    TaskUpdateResult,
    TemplateListResult,
    TransferResult,
    VisionUploadResult,
)


# ---------------------------------------------------------------------------
# Shared Result Types
# ---------------------------------------------------------------------------


class TestDeleteResult:
    """Tests for DeleteResult model."""

    def test_creation_defaults(self):
        """DeleteResult should default deleted=True and deleted_at=None."""
        result = DeleteResult()
        assert result.deleted is True
        assert result.deleted_at is None

    def test_creation_with_timestamp(self):
        """DeleteResult accepts an explicit deleted_at timestamp."""
        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = DeleteResult(deleted=True, deleted_at=ts)
        assert result.deleted is True
        assert result.deleted_at == ts

    def test_model_dump(self):
        """model_dump should produce a plain dict."""
        result = DeleteResult()
        dumped = result.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["deleted"] is True
        assert dumped["deleted_at"] is None

    def test_from_attributes_config(self):
        """Model should have from_attributes=True in config."""
        assert DeleteResult.model_config.get("from_attributes") is True


class TestOperationResult:
    """Tests for OperationResult model."""

    def test_creation_with_message(self):
        """OperationResult requires a message string."""
        result = OperationResult(message="Product activated successfully")
        assert result.message == "Product activated successfully"

    def test_missing_message_raises(self):
        """OperationResult without message should raise ValidationError."""
        with pytest.raises(ValidationError):
            OperationResult()

    def test_model_dump(self):
        """model_dump should serialize correctly."""
        result = OperationResult(message="Done")
        dumped = result.model_dump()
        assert dumped == {"message": "Done"}

    def test_from_attributes_config(self):
        assert OperationResult.model_config.get("from_attributes") is True


class TestTransferResult:
    """Tests for TransferResult model."""

    def test_creation_with_required_fields(self):
        """TransferResult requires from_user_id and to_user_id."""
        result = TransferResult(from_user_id="user-1", to_user_id="user-2")
        assert result.transferred is True
        assert result.from_user_id == "user-1"
        assert result.to_user_id == "user-2"

    def test_missing_from_user_id_raises(self):
        with pytest.raises(ValidationError):
            TransferResult(to_user_id="user-2")

    def test_missing_to_user_id_raises(self):
        with pytest.raises(ValidationError):
            TransferResult(from_user_id="user-1")

    def test_model_dump(self):
        result = TransferResult(from_user_id="a", to_user_id="b")
        dumped = result.model_dump()
        assert dumped["transferred"] is True
        assert dumped["from_user_id"] == "a"
        assert dumped["to_user_id"] == "b"

    def test_from_attributes_config(self):
        assert TransferResult.model_config.get("from_attributes") is True


class TestPaginatedResult:
    """Tests for PaginatedResult generic model."""

    def test_creation_with_string_items(self):
        """PaginatedResult[str] should hold a list of strings."""
        result = PaginatedResult[str](items=["a", "b", "c"], total=3)
        assert result.items == ["a", "b", "c"]
        assert result.total == 3
        assert result.page == 1
        assert result.page_size == 50

    def test_creation_with_int_items(self):
        """PaginatedResult[int] should hold a list of ints."""
        result = PaginatedResult[int](items=[1, 2], total=100, page=2, page_size=25)
        assert result.items == [1, 2]
        assert result.total == 100
        assert result.page == 2
        assert result.page_size == 25

    def test_creation_with_dict_items(self):
        """PaginatedResult[dict] should hold a list of dicts."""
        items = [{"id": "1", "name": "Product A"}, {"id": "2", "name": "Product B"}]
        result = PaginatedResult[dict](items=items, total=2)
        assert len(result.items) == 2
        assert result.items[0]["name"] == "Product A"

    def test_empty_items(self):
        """PaginatedResult with empty items list and total=0."""
        result = PaginatedResult[str](items=[], total=0)
        assert result.items == []
        assert result.total == 0

    def test_missing_total_raises(self):
        """total is required."""
        with pytest.raises(ValidationError):
            PaginatedResult[str](items=["a"])

    def test_missing_items_raises(self):
        """items is required."""
        with pytest.raises(ValidationError):
            PaginatedResult[str](total=5)

    def test_model_dump(self):
        result = PaginatedResult[str](items=["x"], total=1, page=3, page_size=10)
        dumped = result.model_dump()
        assert dumped["items"] == ["x"]
        assert dumped["total"] == 1
        assert dumped["page"] == 3
        assert dumped["page_size"] == 10

    def test_from_attributes_config(self):
        assert PaginatedResult.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Product Service Models
# ---------------------------------------------------------------------------


class TestProductStatistics:
    """Tests for ProductStatistics model."""

    def test_creation_defaults(self):
        """All fields should default to 0."""
        stats = ProductStatistics()
        assert stats.total_projects == 0
        assert stats.active_projects == 0
        assert stats.completed_projects == 0
        assert stats.total_jobs == 0
        assert stats.active_jobs == 0
        assert stats.total_tasks == 0
        assert stats.total_vision_documents == 0

    def test_creation_with_values(self):
        stats = ProductStatistics(
            total_projects=10,
            active_projects=3,
            completed_projects=5,
            total_jobs=50,
            active_jobs=8,
            total_tasks=200,
            total_vision_documents=15,
        )
        assert stats.total_projects == 10
        assert stats.active_projects == 3
        assert stats.completed_projects == 5
        assert stats.total_jobs == 50
        assert stats.active_jobs == 8
        assert stats.total_tasks == 200
        assert stats.total_vision_documents == 15

    def test_model_dump(self):
        stats = ProductStatistics(total_projects=5)
        dumped = stats.model_dump()
        assert dumped["total_projects"] == 5
        assert dumped["active_projects"] == 0

    def test_from_attributes_config(self):
        assert ProductStatistics.model_config.get("from_attributes") is True


class TestCascadeImpact:
    """Tests for CascadeImpact model."""

    def test_creation_with_product_id(self):
        """product_id is required."""
        impact = CascadeImpact(product_id="prod-123")
        assert impact.product_id == "prod-123"
        assert impact.projects_affected == 0
        assert impact.jobs_affected == 0
        assert impact.tasks_affected == 0
        assert impact.vision_documents_affected == 0
        assert impact.memory_entries_affected == 0

    def test_missing_product_id_raises(self):
        with pytest.raises(ValidationError):
            CascadeImpact()

    def test_creation_with_counts(self):
        impact = CascadeImpact(
            product_id="prod-456",
            projects_affected=3,
            jobs_affected=12,
            tasks_affected=45,
            vision_documents_affected=7,
            memory_entries_affected=20,
        )
        assert impact.projects_affected == 3
        assert impact.jobs_affected == 12
        assert impact.tasks_affected == 45
        assert impact.vision_documents_affected == 7
        assert impact.memory_entries_affected == 20

    def test_model_dump(self):
        impact = CascadeImpact(product_id="p1", projects_affected=2)
        dumped = impact.model_dump()
        assert dumped["product_id"] == "p1"
        assert dumped["projects_affected"] == 2

    def test_from_attributes_config(self):
        assert CascadeImpact.model_config.get("from_attributes") is True


class TestVisionUploadResult:
    """Tests for VisionUploadResult model."""

    def test_creation_with_required_fields(self):
        result = VisionUploadResult(document_id="doc-1", filename="design.pdf")
        assert result.document_id == "doc-1"
        assert result.filename == "design.pdf"
        assert result.chunks_created == 0
        assert result.total_tokens == 0
        assert result.summary_level is None

    def test_missing_document_id_raises(self):
        with pytest.raises(ValidationError):
            VisionUploadResult(filename="test.pdf")

    def test_missing_filename_raises(self):
        with pytest.raises(ValidationError):
            VisionUploadResult(document_id="doc-1")

    def test_creation_with_all_fields(self):
        result = VisionUploadResult(
            document_id="doc-2",
            filename="architecture.md",
            chunks_created=5,
            total_tokens=12000,
            summary_level="medium",
        )
        assert result.chunks_created == 5
        assert result.total_tokens == 12000
        assert result.summary_level == "medium"

    def test_model_dump(self):
        result = VisionUploadResult(document_id="d", filename="f.txt")
        dumped = result.model_dump()
        assert dumped["document_id"] == "d"
        assert dumped["filename"] == "f.txt"
        assert dumped["chunks_created"] == 0

    def test_from_attributes_config(self):
        assert VisionUploadResult.model_config.get("from_attributes") is True


class TestPurgeResult:
    """Tests for PurgeResult model."""

    def test_creation_defaults(self):
        result = PurgeResult()
        assert result.purged_count == 0
        assert result.purged_ids == []

    def test_creation_with_values(self):
        result = PurgeResult(purged_count=3, purged_ids=["p1", "p2", "p3"])
        assert result.purged_count == 3
        assert len(result.purged_ids) == 3
        assert "p2" in result.purged_ids

    def test_purged_ids_default_factory_isolation(self):
        """Each instance should get its own list (no shared mutable default)."""
        r1 = PurgeResult()
        r2 = PurgeResult()
        r1.purged_ids.append("x")
        assert "x" not in r2.purged_ids

    def test_model_dump(self):
        result = PurgeResult(purged_count=1, purged_ids=["abc"])
        dumped = result.model_dump()
        assert dumped["purged_count"] == 1
        assert dumped["purged_ids"] == ["abc"]

    def test_from_attributes_config(self):
        assert PurgeResult.model_config.get("from_attributes") is True


class TestPathValidationResult:
    """Tests for PathValidationResult model."""

    def test_creation_with_required_fields(self):
        result = PathValidationResult(valid=True, path="/home/user/project")
        assert result.valid is True
        assert result.path == "/home/user/project"
        assert result.message == ""

    def test_invalid_path(self):
        result = PathValidationResult(
            valid=False,
            path="/nonexistent",
            message="Directory does not exist",
        )
        assert result.valid is False
        assert result.message == "Directory does not exist"

    def test_missing_valid_raises(self):
        with pytest.raises(ValidationError):
            PathValidationResult(path="/some/path")

    def test_missing_path_raises(self):
        with pytest.raises(ValidationError):
            PathValidationResult(valid=True)

    def test_model_dump(self):
        result = PathValidationResult(valid=True, path="/p", message="OK")
        dumped = result.model_dump()
        assert dumped == {"valid": True, "path": "/p", "message": "OK"}

    def test_from_attributes_config(self):
        assert PathValidationResult.model_config.get("from_attributes") is True


class TestGitIntegrationSettings:
    """Tests for GitIntegrationSettings model."""

    def test_creation_defaults(self):
        settings = GitIntegrationSettings()
        assert settings.enabled is False
        assert settings.repo_url is None
        assert settings.branch is None
        assert settings.auto_commit is False

    def test_creation_with_values(self):
        settings = GitIntegrationSettings(
            enabled=True,
            repo_url="https://github.com/org/repo.git",
            branch="main",
            auto_commit=True,
        )
        assert settings.enabled is True
        assert settings.repo_url == "https://github.com/org/repo.git"
        assert settings.branch == "main"
        assert settings.auto_commit is True

    def test_model_dump(self):
        settings = GitIntegrationSettings(enabled=True, branch="develop")
        dumped = settings.model_dump()
        assert dumped["enabled"] is True
        assert dumped["branch"] == "develop"
        assert dumped["repo_url"] is None

    def test_from_attributes_config(self):
        assert GitIntegrationSettings.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Task Service Models
# ---------------------------------------------------------------------------


class TestTaskListResponse:
    """Tests for TaskListResponse model."""

    def test_creation_defaults(self):
        result = TaskListResponse()
        assert result.tasks == []
        assert result.count == 0

    def test_creation_with_tasks(self):
        tasks = [
            {"id": "t1", "title": "Task 1", "status": "pending"},
            {"id": "t2", "title": "Task 2", "status": "completed"},
        ]
        result = TaskListResponse(tasks=tasks, count=2)
        assert len(result.tasks) == 2
        assert result.count == 2
        assert result.tasks[0]["title"] == "Task 1"

    def test_tasks_default_factory_isolation(self):
        """Each instance should get its own list."""
        r1 = TaskListResponse()
        r2 = TaskListResponse()
        r1.tasks.append({"id": "t1"})
        assert len(r2.tasks) == 0

    def test_model_dump(self):
        result = TaskListResponse(tasks=[{"id": "t1"}], count=1)
        dumped = result.model_dump()
        assert dumped["count"] == 1
        assert len(dumped["tasks"]) == 1

    def test_from_attributes_config(self):
        assert TaskListResponse.model_config.get("from_attributes") is True


class TestTaskUpdateResult:
    """Tests for TaskUpdateResult model."""

    def test_creation_with_required_fields(self):
        result = TaskUpdateResult(task_id="task-123")
        assert result.task_id == "task-123"
        assert result.updated_fields == []

    def test_creation_with_updated_fields(self):
        result = TaskUpdateResult(
            task_id="task-456",
            updated_fields=["status", "priority", "description"],
        )
        assert len(result.updated_fields) == 3
        assert "status" in result.updated_fields

    def test_missing_task_id_raises(self):
        with pytest.raises(ValidationError):
            TaskUpdateResult()

    def test_updated_fields_default_factory_isolation(self):
        r1 = TaskUpdateResult(task_id="t1")
        r2 = TaskUpdateResult(task_id="t2")
        r1.updated_fields.append("title")
        assert "title" not in r2.updated_fields

    def test_model_dump(self):
        result = TaskUpdateResult(task_id="t1", updated_fields=["status"])
        dumped = result.model_dump()
        assert dumped["task_id"] == "t1"
        assert dumped["updated_fields"] == ["status"]

    def test_from_attributes_config(self):
        assert TaskUpdateResult.model_config.get("from_attributes") is True


class TestTaskSummary:
    """Tests for TaskSummary model."""

    def test_creation_defaults(self):
        summary = TaskSummary()
        assert summary.total == 0
        assert summary.by_status == {}
        assert summary.by_priority == {}
        assert summary.by_category == {}

    def test_creation_with_values(self):
        summary = TaskSummary(
            total=25,
            by_status={"pending": 10, "in_progress": 8, "completed": 7},
            by_priority={"high": 5, "medium": 15, "low": 5},
            by_category={"backend": 12, "frontend": 13},
        )
        assert summary.total == 25
        assert summary.by_status["pending"] == 10
        assert summary.by_priority["high"] == 5
        assert summary.by_category["backend"] == 12

    def test_dict_default_factory_isolation(self):
        """Each dict field should have its own instance."""
        s1 = TaskSummary()
        s2 = TaskSummary()
        s1.by_status["pending"] = 5
        assert "pending" not in s2.by_status

    def test_model_dump(self):
        summary = TaskSummary(total=3, by_status={"done": 3})
        dumped = summary.model_dump()
        assert dumped["total"] == 3
        assert dumped["by_status"] == {"done": 3}
        assert dumped["by_priority"] == {}

    def test_from_attributes_config(self):
        assert TaskSummary.model_config.get("from_attributes") is True


class TestConversionResult:
    """Tests for ConversionResult model."""

    def test_creation_with_required_fields(self):
        result = ConversionResult(
            task_id="task-1",
            project_id="proj-1",
            project_name="New Feature",
        )
        assert result.task_id == "task-1"
        assert result.project_id == "proj-1"
        assert result.project_name == "New Feature"

    def test_missing_task_id_raises(self):
        with pytest.raises(ValidationError):
            ConversionResult(project_id="p1", project_name="P")

    def test_missing_project_id_raises(self):
        with pytest.raises(ValidationError):
            ConversionResult(task_id="t1", project_name="P")

    def test_missing_project_name_raises(self):
        with pytest.raises(ValidationError):
            ConversionResult(task_id="t1", project_id="p1")

    def test_model_dump(self):
        result = ConversionResult(task_id="t", project_id="p", project_name="N")
        dumped = result.model_dump()
        assert dumped == {
            "task_id": "t",
            "project_id": "p",
            "project_name": "N",
        }

    def test_from_attributes_config(self):
        assert ConversionResult.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Message Service Models
# ---------------------------------------------------------------------------


class TestSendMessageResult:
    """Tests for SendMessageResult model."""

    def test_creation_with_required_fields(self):
        result = SendMessageResult(message_id="msg-1")
        assert result.message_id == "msg-1"
        assert result.delivered_to == []

    def test_creation_with_recipients(self):
        result = SendMessageResult(
            message_id="msg-2",
            delivered_to=["agent-1", "agent-2"],
        )
        assert len(result.delivered_to) == 2

    def test_missing_message_id_raises(self):
        with pytest.raises(ValidationError):
            SendMessageResult()

    def test_delivered_to_default_factory_isolation(self):
        r1 = SendMessageResult(message_id="m1")
        r2 = SendMessageResult(message_id="m2")
        r1.delivered_to.append("agent-x")
        assert "agent-x" not in r2.delivered_to

    def test_model_dump(self):
        result = SendMessageResult(message_id="m1", delivered_to=["a"])
        dumped = result.model_dump()
        assert dumped["message_id"] == "m1"
        assert dumped["delivered_to"] == ["a"]

    def test_from_attributes_config(self):
        assert SendMessageResult.model_config.get("from_attributes") is True


class TestBroadcastResult:
    """Tests for BroadcastResult model."""

    def test_creation_with_required_fields(self):
        result = BroadcastResult(broadcast_id="bc-1")
        assert result.broadcast_id == "bc-1"
        assert result.recipients_count == 0
        assert result.message_ids == []

    def test_creation_with_all_fields(self):
        result = BroadcastResult(
            broadcast_id="bc-2",
            recipients_count=5,
            message_ids=["m1", "m2", "m3", "m4", "m5"],
        )
        assert result.recipients_count == 5
        assert len(result.message_ids) == 5

    def test_missing_broadcast_id_raises(self):
        with pytest.raises(ValidationError):
            BroadcastResult()

    def test_message_ids_default_factory_isolation(self):
        r1 = BroadcastResult(broadcast_id="b1")
        r2 = BroadcastResult(broadcast_id="b2")
        r1.message_ids.append("x")
        assert "x" not in r2.message_ids

    def test_model_dump(self):
        result = BroadcastResult(broadcast_id="b1", recipients_count=2, message_ids=["a", "b"])
        dumped = result.model_dump()
        assert dumped["broadcast_id"] == "b1"
        assert dumped["recipients_count"] == 2

    def test_from_attributes_config(self):
        assert BroadcastResult.model_config.get("from_attributes") is True


class TestMessageListResult:
    """Tests for MessageListResult model."""

    def test_creation_defaults(self):
        result = MessageListResult()
        assert result.messages == []
        assert result.count == 0

    def test_creation_with_messages(self):
        msgs = [
            {"id": "m1", "content": "Hello"},
            {"id": "m2", "content": "World"},
        ]
        result = MessageListResult(messages=msgs, count=2)
        assert len(result.messages) == 2
        assert result.count == 2

    def test_messages_default_factory_isolation(self):
        r1 = MessageListResult()
        r2 = MessageListResult()
        r1.messages.append({"id": "m1"})
        assert len(r2.messages) == 0

    def test_model_dump(self):
        result = MessageListResult(messages=[{"id": "m1"}], count=1)
        dumped = result.model_dump()
        assert dumped["count"] == 1

    def test_from_attributes_config(self):
        assert MessageListResult.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Orchestration Service Models
# ---------------------------------------------------------------------------


class TestSpawnResult:
    """Tests for SpawnResult model."""

    def test_creation_with_required_fields(self):
        result = SpawnResult(
            job_id="job-1",
            agent_role="tdd-implementor",
            project_id="proj-1",
        )
        assert result.job_id == "job-1"
        assert result.agent_role == "tdd-implementor"
        assert result.project_id == "proj-1"
        assert result.status == "pending"

    def test_creation_with_custom_status(self):
        result = SpawnResult(
            job_id="job-2",
            agent_role="backend-integration-tester",
            project_id="proj-2",
            status="active",
        )
        assert result.status == "active"

    def test_missing_job_id_raises(self):
        with pytest.raises(ValidationError):
            SpawnResult(agent_role="tester", project_id="p1")

    def test_missing_agent_role_raises(self):
        with pytest.raises(ValidationError):
            SpawnResult(job_id="j1", project_id="p1")

    def test_missing_project_id_raises(self):
        with pytest.raises(ValidationError):
            SpawnResult(job_id="j1", agent_role="tester")

    def test_model_dump(self):
        result = SpawnResult(job_id="j", agent_role="r", project_id="p")
        dumped = result.model_dump()
        assert dumped["job_id"] == "j"
        assert dumped["status"] == "pending"

    def test_from_attributes_config(self):
        assert SpawnResult.model_config.get("from_attributes") is True


class TestMissionResponse:
    """Tests for MissionResponse model."""

    def test_creation_with_required_fields(self):
        result = MissionResponse(job_id="job-1", mission="Implement auth module")
        assert result.job_id == "job-1"
        assert result.mission == "Implement auth module"
        assert result.full_protocol is None
        assert result.agent_role is None

    def test_creation_with_all_fields(self):
        result = MissionResponse(
            job_id="job-2",
            mission="Build feature X",
            full_protocol="Phase 1: ...\nPhase 2: ...",
            agent_role="tdd-implementor",
        )
        assert result.full_protocol is not None
        assert result.agent_role == "tdd-implementor"

    def test_missing_job_id_raises(self):
        with pytest.raises(ValidationError):
            MissionResponse(mission="Do something")

    def test_missing_mission_raises(self):
        with pytest.raises(ValidationError):
            MissionResponse(job_id="j1")

    def test_model_dump(self):
        result = MissionResponse(job_id="j", mission="m")
        dumped = result.model_dump()
        assert dumped["job_id"] == "j"
        assert dumped["mission"] == "m"
        assert dumped["full_protocol"] is None
        assert dumped["agent_role"] is None

    def test_from_attributes_config(self):
        assert MissionResponse.model_config.get("from_attributes") is True


class TestMissionUpdateResult:
    """Tests for MissionUpdateResult model."""

    def test_creation_with_required_fields(self):
        result = MissionUpdateResult(job_id="job-1")
        assert result.job_id == "job-1"
        assert result.mission_updated is True

    def test_creation_with_explicit_false(self):
        result = MissionUpdateResult(job_id="job-2", mission_updated=False)
        assert result.mission_updated is False

    def test_missing_job_id_raises(self):
        with pytest.raises(ValidationError):
            MissionUpdateResult()

    def test_model_dump(self):
        result = MissionUpdateResult(job_id="j")
        dumped = result.model_dump()
        assert dumped == {"job_id": "j", "mission_updated": True}

    def test_from_attributes_config(self):
        assert MissionUpdateResult.model_config.get("from_attributes") is True


class TestInstructionsResponse:
    """Tests for InstructionsResponse model."""

    def test_creation_with_required_fields(self):
        result = InstructionsResponse(
            orchestrator_id="orch-1",
            instructions="Step 1: Discover agents...",
        )
        assert result.orchestrator_id == "orch-1"
        assert result.instructions == "Step 1: Discover agents..."
        assert result.priority_categories == []

    def test_creation_with_priority_categories(self):
        result = InstructionsResponse(
            orchestrator_id="orch-2",
            instructions="Full protocol here",
            priority_categories=["product_core", "tech_stack", "vision_documents"],
        )
        assert len(result.priority_categories) == 3
        assert "product_core" in result.priority_categories

    def test_missing_orchestrator_id_raises(self):
        with pytest.raises(ValidationError):
            InstructionsResponse(instructions="test")

    def test_missing_instructions_raises(self):
        with pytest.raises(ValidationError):
            InstructionsResponse(orchestrator_id="o1")

    def test_priority_categories_default_factory_isolation(self):
        r1 = InstructionsResponse(orchestrator_id="o1", instructions="i1")
        r2 = InstructionsResponse(orchestrator_id="o2", instructions="i2")
        r1.priority_categories.append("memory_360")
        assert "memory_360" not in r2.priority_categories

    def test_model_dump(self):
        result = InstructionsResponse(orchestrator_id="o", instructions="i", priority_categories=["a"])
        dumped = result.model_dump()
        assert dumped["orchestrator_id"] == "o"
        assert dumped["priority_categories"] == ["a"]

    def test_from_attributes_config(self):
        assert InstructionsResponse.model_config.get("from_attributes") is True


class TestSuccessionResult:
    """Tests for SuccessionResult model."""

    def test_creation_with_required_fields(self):
        result = SuccessionResult(
            predecessor_id="orch-1",
            successor_id="orch-2",
        )
        assert result.predecessor_id == "orch-1"
        assert result.successor_id == "orch-2"
        assert result.handover_summary is None

    def test_creation_with_handover_summary(self):
        result = SuccessionResult(
            predecessor_id="o1",
            successor_id="o2",
            handover_summary="Context transferred: 3 active agents, 2 pending tasks.",
        )
        assert result.handover_summary is not None
        assert "3 active agents" in result.handover_summary

    def test_missing_predecessor_id_raises(self):
        with pytest.raises(ValidationError):
            SuccessionResult(successor_id="o2")

    def test_missing_successor_id_raises(self):
        with pytest.raises(ValidationError):
            SuccessionResult(predecessor_id="o1")

    def test_model_dump(self):
        result = SuccessionResult(predecessor_id="p", successor_id="s")
        dumped = result.model_dump()
        assert dumped["predecessor_id"] == "p"
        assert dumped["successor_id"] == "s"
        assert dumped["handover_summary"] is None

    def test_from_attributes_config(self):
        assert SuccessionResult.model_config.get("from_attributes") is True


class TestSuccessionStatus:
    """Tests for SuccessionStatus model."""

    def test_creation_with_required_fields(self):
        result = SuccessionStatus(orchestrator_id="orch-1")
        assert result.orchestrator_id == "orch-1"
        assert result.context_used == 0
        assert result.context_budget == 0
        assert result.succession_recommended is False
        assert result.active_agents == 0

    def test_creation_with_all_fields(self):
        result = SuccessionStatus(
            orchestrator_id="orch-2",
            context_used=85000,
            context_budget=100000,
            succession_recommended=True,
            active_agents=4,
        )
        assert result.context_used == 85000
        assert result.context_budget == 100000
        assert result.succession_recommended is True
        assert result.active_agents == 4

    def test_missing_orchestrator_id_raises(self):
        with pytest.raises(ValidationError):
            SuccessionStatus()

    def test_model_dump(self):
        result = SuccessionStatus(orchestrator_id="o1", context_used=5000)
        dumped = result.model_dump()
        assert dumped["orchestrator_id"] == "o1"
        assert dumped["context_used"] == 5000
        assert dumped["succession_recommended"] is False

    def test_from_attributes_config(self):
        assert SuccessionStatus.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Template Service Models
# ---------------------------------------------------------------------------


class TestTemplateListResult:
    """Tests for TemplateListResult model."""

    def test_creation_defaults(self):
        result = TemplateListResult()
        assert result.templates == []
        assert result.count == 0

    def test_creation_with_templates(self):
        templates = [
            {"id": "t1", "name": "Backend Tester", "role": "tester"},
            {"id": "t2", "name": "Frontend Dev", "role": "developer"},
        ]
        result = TemplateListResult(templates=templates, count=2)
        assert len(result.templates) == 2
        assert result.count == 2

    def test_templates_default_factory_isolation(self):
        r1 = TemplateListResult()
        r2 = TemplateListResult()
        r1.templates.append({"id": "t1"})
        assert len(r2.templates) == 0

    def test_model_dump(self):
        result = TemplateListResult(templates=[{"id": "t1"}], count=1)
        dumped = result.model_dump()
        assert dumped["count"] == 1

    def test_from_attributes_config(self):
        assert TemplateListResult.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Consolidation Service Models
# ---------------------------------------------------------------------------


class TestConsolidationResult:
    """Tests for ConsolidationResult model."""

    def test_creation_with_required_fields(self):
        result = ConsolidationResult(product_id="prod-1")
        assert result.product_id == "prod-1"
        assert result.documents_consolidated == 0
        assert result.aggregate == {}

    def test_creation_with_all_fields(self):
        result = ConsolidationResult(
            product_id="prod-2",
            documents_consolidated=5,
            aggregate={"total_tokens": 50000, "avg_tokens": 10000},
        )
        assert result.documents_consolidated == 5
        assert result.aggregate["total_tokens"] == 50000

    def test_missing_product_id_raises(self):
        with pytest.raises(ValidationError):
            ConsolidationResult()

    def test_aggregate_default_factory_isolation(self):
        r1 = ConsolidationResult(product_id="p1")
        r2 = ConsolidationResult(product_id="p2")
        r1.aggregate["key"] = "value"
        assert "key" not in r2.aggregate

    def test_model_dump(self):
        result = ConsolidationResult(product_id="p", documents_consolidated=3)
        dumped = result.model_dump()
        assert dumped["product_id"] == "p"
        assert dumped["documents_consolidated"] == 3
        assert dumped["aggregate"] == {}

    def test_from_attributes_config(self):
        assert ConsolidationResult.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Auth Service Models
# ---------------------------------------------------------------------------


class TestAuthResult:
    """Tests for AuthResult model (Handover 0731c: enhanced with profile fields)."""

    def test_creation_with_required_fields(self):
        result = AuthResult(
            user_id="user-1",
            username="admin",
            token="jwt-token-here",
            tenant_key="tenant-abc",
        )
        assert result.user_id == "user-1"
        assert result.username == "admin"
        assert result.token == "jwt-token-here"
        assert result.tenant_key == "tenant-abc"
        assert result.role == "user"
        # Optional fields default to None/True
        assert result.email is None
        assert result.full_name is None
        assert result.is_active is True
        assert result.created_at is None
        assert result.last_login is None

    def test_creation_with_admin_role(self):
        result = AuthResult(
            user_id="u1",
            username="superadmin",
            token="t",
            tenant_key="tk",
            role="admin",
        )
        assert result.role == "admin"

    def test_creation_with_profile_fields(self):
        result = AuthResult(
            user_id="u1",
            username="admin",
            token="t",
            tenant_key="tk",
            email="admin@example.com",
            full_name="Admin User",
            is_active=True,
            created_at="2026-01-01T00:00:00+00:00",
            last_login="2026-02-11T12:00:00+00:00",
        )
        assert result.email == "admin@example.com"
        assert result.full_name == "Admin User"
        assert result.is_active is True
        assert result.created_at == "2026-01-01T00:00:00+00:00"
        assert result.last_login == "2026-02-11T12:00:00+00:00"

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError):
            AuthResult(username="u", token="t", tenant_key="tk")

    def test_missing_username_raises(self):
        with pytest.raises(ValidationError):
            AuthResult(user_id="u1", token="t", tenant_key="tk")

    def test_missing_token_raises(self):
        with pytest.raises(ValidationError):
            AuthResult(user_id="u1", username="u", tenant_key="tk")

    def test_missing_tenant_key_raises(self):
        with pytest.raises(ValidationError):
            AuthResult(user_id="u1", username="u", token="t")

    def test_model_dump(self):
        result = AuthResult(user_id="u", username="n", token="t", tenant_key="k")
        dumped = result.model_dump()
        assert dumped["user_id"] == "u"
        assert dumped["username"] == "n"
        assert dumped["token"] == "t"
        assert dumped["tenant_key"] == "k"
        assert dumped["role"] == "user"
        assert dumped["email"] is None
        assert dumped["full_name"] is None
        assert dumped["is_active"] is True

    def test_from_attributes_config(self):
        assert AuthResult.model_config.get("from_attributes") is True


class TestSetupState:
    """Tests for SetupState/SetupStateInfo model (Handover 0731c: renamed with new fields)."""

    def test_creation_with_tenant_key(self):
        state = SetupState(tenant_key="test_tenant")
        assert state.first_admin_created is False
        assert state.database_initialized is False
        assert state.tenant_key == "test_tenant"

    def test_creation_fully_configured(self):
        state = SetupState(
            first_admin_created=True,
            database_initialized=True,
            tenant_key="test_tenant",
        )
        assert state.first_admin_created is True
        assert state.database_initialized is True
        assert state.tenant_key == "test_tenant"

    def test_partial_configuration(self):
        state = SetupState(database_initialized=True, tenant_key="tk")
        assert state.first_admin_created is False
        assert state.database_initialized is True
        assert state.tenant_key == "tk"

    def test_model_dump(self):
        state = SetupState(first_admin_created=True, tenant_key="tk")
        dumped = state.model_dump()
        assert dumped["first_admin_created"] is True
        assert dumped["database_initialized"] is False
        assert dumped["tenant_key"] == "tk"

    def test_from_attributes_config(self):
        assert SetupState.model_config.get("from_attributes") is True

    def test_missing_tenant_key_raises(self):
        with pytest.raises(ValidationError):
            SetupState()


# ---------------------------------------------------------------------------
# Cross-Cutting Concerns
# ---------------------------------------------------------------------------


class TestModelJsonSerialization:
    """Test JSON serialization round-trip for models with complex types."""

    def test_delete_result_with_datetime_json(self):
        """Datetime fields should serialize to JSON correctly."""
        ts = datetime(2026, 2, 1, 10, 30, 0, tzinfo=timezone.utc)
        result = DeleteResult(deleted_at=ts)
        json_str = result.model_dump_json()
        assert "2026" in json_str

    def test_paginated_result_json(self):
        """PaginatedResult should serialize to JSON correctly."""
        result = PaginatedResult[str](items=["a", "b"], total=2)
        json_str = result.model_dump_json()
        assert '"items"' in json_str
        assert '"total"' in json_str

    def test_task_summary_nested_dicts_json(self):
        """Nested dict fields should serialize to JSON correctly."""
        summary = TaskSummary(
            total=10,
            by_status={"pending": 5, "completed": 5},
        )
        json_str = summary.model_dump_json()
        assert '"pending"' in json_str


class TestModelFromDict:
    """Test model construction from dictionaries (common API pattern)."""

    def test_spawn_result_from_dict(self):
        data = {"job_id": "j1", "agent_role": "tester", "project_id": "p1"}
        result = SpawnResult(**data)
        assert result.job_id == "j1"

    def test_auth_result_from_dict(self):
        data = {
            "user_id": "u1",
            "username": "admin",
            "token": "jwt",
            "tenant_key": "tk",
            "role": "admin",
        }
        result = AuthResult(**data)
        assert result.role == "admin"

    def test_product_statistics_from_partial_dict(self):
        """Models with all-default fields should accept partial dicts."""
        data = {"total_projects": 5, "active_jobs": 2}
        stats = ProductStatistics(**data)
        assert stats.total_projects == 5
        assert stats.active_jobs == 2
        assert stats.total_tasks == 0
