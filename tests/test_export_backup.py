"""
Test suite for Export Backup Functionality (Handover 0075)

Tests validate:
- Zip backup creation before export
- Backup file format and structure
- Backup integration into export flow
- Backup info in export response
- Edge cases (no files to backup, backup failure)
"""

import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestCreateZipBackup:
    """Test suite for create_zip_backup() function"""

    def test_backup_directory_does_not_exist(self, tmp_path):
        """Test: Returns None when agents directory doesn't exist"""
        from api.endpoints.claude_export import create_zip_backup

        non_existent = tmp_path / "nonexistent" / "agents"
        backup_path = create_zip_backup(non_existent)

        assert backup_path is None

    def test_backup_directory_empty(self, tmp_path):
        """Test: Returns None when no .md files exist"""
        from api.endpoints.claude_export import create_zip_backup

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create non-.md file
        (agents_dir / "readme.txt").write_text("Not a markdown file")

        backup_path = create_zip_backup(agents_dir)

        assert backup_path is None

    def test_backup_creates_zip_file(self, tmp_path):
        """Test: Creates timestamped zip backup of .md files"""
        from api.endpoints.claude_export import create_zip_backup

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create test .md files
        (agents_dir / "orchestrator.md").write_text("# Orchestrator Agent")
        (agents_dir / "analyzer.md").write_text("# Analyzer Agent")
        (agents_dir / "readme.txt").write_text("Should be ignored")

        backup_path = create_zip_backup(agents_dir)

        # Verify backup created
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.suffix == ".zip"
        assert backup_path.parent == agents_dir.parent / "backups"
        assert backup_path.name.startswith("agents_backup_")

        # Verify zip contains only .md files
        with zipfile.ZipFile(backup_path, "r") as zipf:
            names = zipf.namelist()
            assert len(names) == 2
            assert "orchestrator.md" in names
            assert "analyzer.md" in names
            assert "readme.txt" not in names

    def test_backup_filename_format(self, tmp_path):
        """Test: Backup filename uses format agents_backup_YYYYMMDD_HHMMSS.zip"""
        from api.endpoints.claude_export import create_zip_backup

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test.md").write_text("Test")

        backup_path = create_zip_backup(agents_dir)

        # Verify filename format
        assert backup_path.name.startswith("agents_backup_")
        assert backup_path.name.endswith(".zip")

        # Extract timestamp from filename
        timestamp_str = backup_path.stem.replace("agents_backup_", "")
        # Verify timestamp format (YYYYMMDD_HHMMSS)
        assert len(timestamp_str) == 15  # 8 digits + _ + 6 digits
        assert timestamp_str[8] == "_"

        # Verify timestamp is valid
        datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

    def test_backup_preserves_file_content(self, tmp_path):
        """Test: Backup preserves exact file content"""
        from api.endpoints.claude_export import create_zip_backup

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        content = "# Test Agent\n\nThis is test content with special chars: äöü"
        (agents_dir / "test.md").write_text(content, encoding="utf-8")

        backup_path = create_zip_backup(agents_dir)

        # Extract and verify content
        with zipfile.ZipFile(backup_path, "r") as zipf:
            extracted = zipf.read("test.md").decode("utf-8")
            assert extracted == content

    def test_backup_creates_backups_directory(self, tmp_path):
        """Test: Automatically creates backups/ directory if needed"""
        from api.endpoints.claude_export import create_zip_backup

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test.md").write_text("Test")

        # Verify backups dir doesn't exist initially
        backups_dir = agents_dir.parent / "backups"
        assert not backups_dir.exists()

        backup_path = create_zip_backup(agents_dir)

        # Verify backups dir created
        assert backups_dir.exists()
        assert backups_dir.is_dir()
        assert backup_path.parent == backups_dir

    def test_backup_multiple_agents(self, tmp_path):
        """Test: Backs up all .md files (6-8 agents)"""
        from api.endpoints.claude_export import create_zip_backup

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create 8 agent files
        agent_names = [
            "orchestrator", "analyzer", "implementor", "tester",
            "documenter", "reviewer", "security", "optimizer"
        ]

        for name in agent_names:
            (agents_dir / f"{name}.md").write_text(f"# {name.capitalize()} Agent")

        backup_path = create_zip_backup(agents_dir)

        # Verify all 8 files backed up
        with zipfile.ZipFile(backup_path, "r") as zipf:
            names = zipf.namelist()
            assert len(names) == 8
            for name in agent_names:
                assert f"{name}.md" in names

    def test_backup_handles_write_error(self, tmp_path):
        """Test: Raises exception if backup creation fails"""
        from api.endpoints.claude_export import create_zip_backup

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test.md").write_text("Test")

        # Mock zipfile to raise exception
        with patch("zipfile.ZipFile") as mock_zip:
            mock_zip.side_effect = PermissionError("Cannot write backup")

            with pytest.raises(Exception):
                create_zip_backup(agents_dir)

    def test_backup_file_size_reasonable(self, tmp_path):
        """Test: Backup file size is reasonable (compressed)"""
        from api.endpoints.claude_export import create_zip_backup

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create agent with large content
        large_content = "# Test Agent\n\n" + ("x" * 10000)
        (agents_dir / "test.md").write_text(large_content)

        backup_path = create_zip_backup(agents_dir)

        # Verify backup is smaller than original (compression works)
        original_size = len(large_content.encode("utf-8"))
        backup_size = backup_path.stat().st_size

        assert backup_size > 0
        assert backup_size < original_size  # Compression should reduce size


class TestExportWithBackup:
    """Test suite for export flow with backup integration"""

    @pytest.mark.asyncio
    async def test_export_creates_backup_before_export(
        self, tmp_path, db_session, test_user, create_template
    ):
        """Test: Export creates backup before writing new files"""
        from api.endpoints.claude_export import export_templates_to_claude_code

        # Setup export directory with existing agents
        export_dir = tmp_path / ".claude" / "agents"
        export_dir.mkdir(parents=True)
        (export_dir / "old_agent.md").write_text("# Old Agent (will be backed up)")

        # Create active template
        await create_template(test_user.tenant_key, "new_agent", is_active=True)

        # Perform export
        result = await export_templates_to_claude_code(
            db=db_session,
            current_user=test_user,
            export_path=str(export_dir)
        )

        # Verify backup created
        assert "backup" in result
        assert result["backup"]["backup_created"] is True
        assert "backup_path" in result["backup"]
        assert "backup_size_bytes" in result["backup"]

        # Verify backup file exists
        backup_path = Path(result["backup"]["backup_path"])
        assert backup_path.exists()
        assert backup_path.suffix == ".zip"

        # Verify backup contains old agent
        with zipfile.ZipFile(backup_path, "r") as zipf:
            assert "old_agent.md" in zipf.namelist()

    @pytest.mark.asyncio
    async def test_export_no_backup_when_empty(
        self, tmp_path, db_session, test_user, create_template
    ):
        """Test: Export skips backup when no existing files"""
        from api.endpoints.claude_export import export_templates_to_claude_code

        # Setup empty export directory
        export_dir = tmp_path / ".claude" / "agents"
        export_dir.mkdir(parents=True)

        # Create active template
        await create_template(test_user.tenant_key, "agent", is_active=True)

        # Perform export
        result = await export_templates_to_claude_code(
            db=db_session,
            current_user=test_user,
            export_path=str(export_dir)
        )

        # Verify no backup created
        assert "backup" in result
        assert result["backup"]["backup_created"] is False
        assert "reason" in result["backup"]

    @pytest.mark.asyncio
    async def test_export_succeeds_even_if_backup_fails(
        self, tmp_path, db_session, test_user, create_template
    ):
        """Test: Export completes even if backup creation fails (non-blocking)"""
        from api.endpoints.claude_export import export_templates_to_claude_code

        export_dir = tmp_path / ".claude" / "agents"
        export_dir.mkdir(parents=True)
        (export_dir / "existing.md").write_text("# Existing")

        # Create active template
        await create_template(test_user.tenant_key, "agent", is_active=True)

        # Mock backup to fail
        with patch("api.endpoints.claude_export.create_zip_backup") as mock_backup:
            mock_backup.return_value = None  # Simulate backup failure

            # Export should still succeed
            result = await export_templates_to_claude_code(
                db=db_session,
                current_user=test_user,
                export_path=str(export_dir)
            )

            assert result["success"] is True
            assert result["exported_count"] == 1
            assert result["backup"]["backup_created"] is False

    @pytest.mark.asyncio
    async def test_export_backup_info_in_response(
        self, tmp_path, db_session, test_user, create_template
    ):
        """Test: Export response includes backup information"""
        from api.endpoints.claude_export import export_templates_to_claude_code

        export_dir = tmp_path / ".claude" / "agents"
        export_dir.mkdir(parents=True)
        (export_dir / "agent.md").write_text("# Agent")

        await create_template(test_user.tenant_key, "agent", is_active=True)

        result = await export_templates_to_claude_code(
            db=db_session,
            current_user=test_user,
            export_path=str(export_dir)
        )

        # Verify response structure
        assert "success" in result
        assert "exported_count" in result
        assert "files" in result
        assert "message" in result
        assert "backup" in result

        # Verify backup info structure
        backup = result["backup"]
        assert isinstance(backup, dict)
        assert "backup_created" in backup

        if backup["backup_created"]:
            assert "backup_path" in backup
            assert "backup_size_bytes" in backup
            assert isinstance(backup["backup_size_bytes"], int)
            assert backup["backup_size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_export_backup_with_8_agents(
        self, tmp_path, db_session, test_user, create_template
    ):
        """Test: Backup works correctly with maximum 8 active agents"""
        from api.endpoints.claude_export import export_templates_to_claude_code

        export_dir = tmp_path / ".claude" / "agents"
        export_dir.mkdir(parents=True)

        # Create 8 existing agent files
        for i in range(8):
            (export_dir / f"agent{i}.md").write_text(f"# Agent {i}")

        # Create 8 active templates
        for i in range(8):
            await create_template(test_user.tenant_key, f"new_agent{i}", is_active=True)

        result = await export_templates_to_claude_code(
            db=db_session,
            current_user=test_user,
            export_path=str(export_dir)
        )

        # Verify backup created with all 8 files
        assert result["backup"]["backup_created"] is True
        backup_path = Path(result["backup"]["backup_path"])

        with zipfile.ZipFile(backup_path, "r") as zipf:
            names = zipf.namelist()
            assert len(names) == 8
            for i in range(8):
                assert f"agent{i}.md" in names

        # Verify export succeeded with 8 new files
        assert result["exported_count"] == 8


class TestClaudeExportResultModel:
    """Test suite for ClaudeExportResult model with backup info"""

    def test_export_result_with_backup(self):
        """Test: ClaudeExportResult includes backup field"""
        from api.endpoints.claude_export import ClaudeExportResult

        result = ClaudeExportResult(
            success=True,
            exported_count=6,
            files=[{"name": "orchestrator", "path": "/path/orchestrator.md"}],
            message="Export successful",
            backup={
                "backup_created": True,
                "backup_path": "/path/backups/agents_backup_20251030_120000.zip",
                "backup_size_bytes": 4096
            }
        )

        assert result.success is True
        assert result.exported_count == 6
        assert result.backup is not None
        assert result.backup["backup_created"] is True

    def test_export_result_without_backup(self):
        """Test: ClaudeExportResult allows None backup"""
        from api.endpoints.claude_export import ClaudeExportResult

        result = ClaudeExportResult(
            success=True,
            exported_count=3,
            files=[],
            message="Export successful",
            backup=None
        )

        assert result.success is True
        assert result.backup is None

    def test_export_result_backup_optional(self):
        """Test: Backup field is optional in ClaudeExportResult"""
        from api.endpoints.claude_export import ClaudeExportResult

        # Should work without backup field
        result = ClaudeExportResult(
            success=True,
            exported_count=5,
            files=[],
            message="Export successful"
        )

        assert result.success is True
        assert hasattr(result, "backup")
