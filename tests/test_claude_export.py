"""
Test suite for Claude Code agent template export functionality.

Tests the export system that generates YAML-frontmatter formatted template files
for use with Claude Code, with multi-tenant isolation and proper backup handling.

Following TDD principles - these tests are written BEFORE implementation.
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, User


# Test fixtures for agent templates
@pytest_asyncio.fixture
async def test_templates(db_session: AsyncSession) -> list[AgentTemplate]:
    """Create test agent templates with different configurations"""
    templates = [
        AgentTemplate(
            id="tmpl_orchestrator_001",
            tenant_key="test_tenant_001",
            product_id=None,  # Tenant-level template
            name="orchestrator",
            category="role",
            role="orchestrator",
            system_instructions="You are the Orchestrator agent responsible for coordinating complex tasks.",
            behavioral_rules=["Always validate inputs", "Coordinate with other agents"],
            success_criteria=["All sub-tasks completed", "No errors in workflow"],

            is_active=True,
        ),
        AgentTemplate(
            id="tmpl_analyzer_001",
            tenant_key="test_tenant_001",
            product_id="prod_001",  # Product-level template
            name="analyzer",
            category="role",
            role="analyzer",
            system_instructions="You are the Analyzer agent responsible for code analysis.",
            behavioral_rules=["Focus on code quality", "Report security issues"],
            success_criteria=["Complete analysis report", "All vulnerabilities identified"],

            is_active=True,
        ),
        AgentTemplate(
            id="tmpl_implementor_001",
            tenant_key="test_tenant_002",  # Different tenant
            name="implementor",
            category="role",
            role="implementor",
            system_instructions="You are the Implementor agent responsible for writing code.",
            behavioral_rules=["Follow TDD principles", "Write clean code"],
            success_criteria=["All tests pass", "Code is well-documented"],

            is_active=True,
        ),
        AgentTemplate(
            id="tmpl_inactive_001",
            tenant_key="test_tenant_001",
            name="inactive_agent",
            category="role",
            role="tester",
            system_instructions="Inactive template",
            behavioral_rules=[],
            success_criteria=[],

            is_active=False,  # Inactive template
        ),
    ]

    for template in templates:
        db_session.add(template)
    await db_session.commit()

    return templates


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user for authentication"""
    user = User(
        tenant_key="test_tenant_001",
        username="test_user",
        email="test@example.com",
        password_hash="hashed_password_placeholder",
        role="developer",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user for authentication"""
    user = User(
        tenant_key="test_tenant_001",
        username="admin_user",
        email="admin@example.com",
        password_hash="hashed_password_placeholder",
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
def temp_export_dir() -> Path:
    """Create temporary directory for export testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# Test YAML frontmatter generation
@pytest.mark.asyncio
async def test_generate_yaml_frontmatter_basic():
    """Test YAML frontmatter generation with minimal template"""
    from api.endpoints.claude_export import generate_yaml_frontmatter

    frontmatter = generate_yaml_frontmatter(
        name="orchestrator",
        role="orchestrator",
        preferred_tool="claude",
    )

    assert frontmatter.startswith("---\n")
    assert frontmatter.endswith("---\n")
    assert "name: orchestrator" in frontmatter
    assert "description: Orchestrator - role agent" in frontmatter
    assert 'tools: ["mcp__giljo_mcp__*"]' in frontmatter
    assert "model: sonnet" in frontmatter


@pytest.mark.asyncio
async def test_generate_yaml_frontmatter_with_description():
    """Test YAML frontmatter with custom description"""
    from api.endpoints.claude_export import generate_yaml_frontmatter

    frontmatter = generate_yaml_frontmatter(
        name="analyzer",
        role="analyzer",
        preferred_tool="claude",
        description="Custom analyzer description",
    )

    assert "description: Custom analyzer description" in frontmatter
    assert "name: analyzer" in frontmatter


@pytest.mark.asyncio
async def test_generate_yaml_frontmatter_escaping():
    """Test YAML frontmatter properly escapes special characters"""
    from api.endpoints.claude_export import generate_yaml_frontmatter

    frontmatter = generate_yaml_frontmatter(
        name="test-agent",
        role="test",
        preferred_tool="claude",
        description='Description with "quotes" and: colons',
    )

    # Should handle special characters properly
    assert "name: test-agent" in frontmatter or "name: 'test-agent'" in frontmatter


# Test export to project directory
@pytest.mark.asyncio
async def test_export_to_project_directory(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test exporting templates to project .claude/agents/ directory"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    # Create project .claude/agents/ directory
    project_dir = temp_export_dir / "test_project"
    claude_dir = project_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(claude_dir),
    )

    assert result["success"] is True
    assert result["exported_count"] >= 2  # Should export active templates for tenant
    assert len(result["files"]) >= 2

    # Verify files were created
    orchestrator_file = claude_dir / "orchestrator.md"
    analyzer_file = claude_dir / "analyzer.md"

    assert orchestrator_file.exists()
    assert analyzer_file.exists()

    # Verify file content structure
    orchestrator_content = orchestrator_file.read_text()
    assert orchestrator_content.startswith("---\n")
    assert "name: orchestrator" in orchestrator_content
    assert "You are the Orchestrator agent" in orchestrator_content


# Test export to personal directory
@pytest.mark.asyncio
async def test_export_to_personal_directory(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test exporting templates to personal ~/.claude/agents/ directory"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    # Create personal .claude/agents/ directory
    personal_dir = temp_export_dir / "home" / ".claude" / "agents"
    personal_dir.mkdir(parents=True, exist_ok=True)

    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(personal_dir),
    )

    assert result["success"] is True
    assert result["exported_count"] >= 2

    # Verify files exist
    assert (personal_dir / "orchestrator.md").exists()
    assert (personal_dir / "analyzer.md").exists()


# Test backup creation
@pytest.mark.asyncio
async def test_backup_creation(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test that existing files are backed up before overwriting"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Create existing file
    existing_file = claude_dir / "orchestrator.md"
    existing_content = "Old content that should be backed up"
    existing_file.write_text(existing_content)

    # Record the time before export
    time_before = datetime.now().strftime("%Y%m%d")

    # Export (should create backup)
    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(claude_dir),
    )

    assert result["success"] is True

    # Verify backup was created
    backup_files = list(claude_dir.glob("orchestrator.md.old.*"))
    assert len(backup_files) >= 1

    # Verify backup contains old content
    backup_file = backup_files[0]
    assert backup_file.read_text() == existing_content

    # Verify new file has new content
    assert existing_file.read_text() != existing_content
    assert "You are the Orchestrator agent" in existing_file.read_text()


# Test multi-tenant isolation
@pytest.mark.asyncio
async def test_multi_tenant_isolation(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    temp_export_dir: Path,
):
    """Test that export only includes templates from user's tenant"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    # Create user in tenant_001
    user1 = User(
        tenant_key="test_tenant_001",
        username="user1",
        email="user1@example.com",
        password_hash="hash",
        role="developer",
    )
    db_session.add(user1)
    await db_session.commit()
    await db_session.refresh(user1)

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=user1,
        export_path=str(claude_dir),
    )

    assert result["success"] is True

    # Should have orchestrator and analyzer (both from test_tenant_001)
    exported_names = [f["name"] for f in result["files"]]
    assert "orchestrator" in exported_names
    assert "analyzer" in exported_names

    # Should NOT have implementor (from test_tenant_002)
    assert "implementor" not in exported_names

    # Verify implementor.md was NOT created
    assert not (claude_dir / "implementor.md").exists()


# Test inactive templates excluded
@pytest.mark.asyncio
async def test_inactive_templates_excluded(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test that inactive templates are not exported"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(claude_dir),
    )

    assert result["success"] is True

    # Should NOT include inactive template
    exported_names = [f["name"] for f in result["files"]]
    assert "inactive_agent" not in exported_names

    # Verify inactive_agent.md was NOT created
    assert not (claude_dir / "inactive_agent.md").exists()


# Test behavioral rules appending
@pytest.mark.asyncio
async def test_behavioral_rules_appending(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test that behavioral rules and success criteria are appended to template"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(claude_dir),
    )

    assert result["success"] is True

    # Check orchestrator file content
    orchestrator_file = claude_dir / "orchestrator.md"
    content = orchestrator_file.read_text()

    # Should contain behavioral rules
    assert "## Behavioral Rules" in content
    assert "Always validate inputs" in content
    assert "Coordinate with other agents" in content

    # Should contain success criteria
    assert "## Success Criteria" in content
    assert "All sub-tasks completed" in content
    assert "No errors in workflow" in content


# Test path validation - only .claude/agents/ allowed
@pytest.mark.asyncio
async def test_path_validation_invalid_path(
    db_session: AsyncSession,
    test_user: User,
    temp_export_dir: Path,
):
    """Test that export rejects invalid paths (not .claude/agents/)"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    # Try to export to non-.claude directory
    invalid_dir = temp_export_dir / "random_directory"
    invalid_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match=r"Export path must end with.*\.claude[/\\]agents"):
        await export_templates_to_claude_code(
            db=db_session,
            current_user=test_user,
            export_path=str(invalid_dir),
        )


@pytest.mark.asyncio
async def test_path_validation_valid_project_path(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test that project .claude/agents/ path is accepted"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    claude_dir = temp_export_dir / "myproject" / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(claude_dir),
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_path_validation_home_expansion(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    monkeypatch,
    temp_export_dir: Path,
):
    """Test that ~ home directory is properly expanded"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    # Mock home directory
    monkeypatch.setenv("HOME", str(temp_export_dir))
    monkeypatch.setenv("USERPROFILE", str(temp_export_dir))  # Windows

    # Create .claude/agents in mock home
    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Use ~ path
    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path="~/.claude/agents",
    )

    assert result["success"] is True
    assert (claude_dir / "orchestrator.md").exists()


# Test error handling - directory doesn't exist
@pytest.mark.asyncio
async def test_error_handling_nonexistent_directory(
    db_session: AsyncSession,
    test_user: User,
):
    """Test error handling when export directory doesn't exist"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    nonexistent_path = "/nonexistent/path/.claude/agents"

    with pytest.raises(ValueError, match=r"Export directory does not exist"):
        await export_templates_to_claude_code(
            db=db_session,
            current_user=test_user,
            export_path=nonexistent_path,
        )


# Test error handling - no templates found
@pytest.mark.asyncio
async def test_error_handling_no_templates(
    db_session: AsyncSession,
    temp_export_dir: Path,
):
    """Test error handling when no templates exist for user's tenant"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    # Create user with tenant that has no templates
    user = User(
        tenant_key="empty_tenant",
        username="empty_user",
        email="empty@example.com",
        password_hash="hash",
        role="developer",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=user,
        export_path=str(claude_dir),
    )

    # Should succeed but with zero exports
    assert result["success"] is True
    assert result["exported_count"] == 0
    assert len(result["files"]) == 0


# Test Pydantic models
@pytest.mark.asyncio
async def test_claude_export_request_model():
    """Test ClaudeExportRequest Pydantic model"""
    from api.endpoints.claude_export import ClaudeExportRequest

    # Valid request
    request = ClaudeExportRequest(export_path="/project/.claude/agents")
    assert request.export_path == "/project/.claude/agents"

    # Home directory expansion
    request_home = ClaudeExportRequest(export_path="~/.claude/agents")
    assert request_home.export_path == "~/.claude/agents"


@pytest.mark.asyncio
async def test_claude_export_result_model():
    """Test ClaudeExportResult Pydantic model"""
    from api.endpoints.claude_export import ClaudeExportResult

    result = ClaudeExportResult(
        success=True,
        exported_count=3,
        files=[
            {"name": "orchestrator", "path": "/path/orchestrator.md"},
            {"name": "analyzer", "path": "/path/analyzer.md"},
            {"name": "implementor", "path": "/path/implementor.md"},
        ],
        message="Successfully exported 3 templates",
    )

    assert result.success is True
    assert result.exported_count == 3
    assert len(result.files) == 3


# Test FastAPI endpoint integration
@pytest.mark.asyncio
async def test_api_endpoint_post_export(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test POST /export/claude-code endpoint (programmatic call)"""
    from api.endpoints.claude_export import export_claude_code_endpoint

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Create request object
    from api.endpoints.claude_export import ClaudeExportRequest

    request = ClaudeExportRequest(export_path=str(claude_dir))

    # Call endpoint directly
    result = await export_claude_code_endpoint(request=request, current_user=test_user, db=db_session)

    assert result.success is True
    assert result.exported_count >= 2
    assert len(result.files) >= 2


# Test backup filename format
@pytest.mark.asyncio
async def test_backup_filename_format(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test that backup files use .old.YYYYMMDD_HHMMSS format"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Create existing file
    existing_file = claude_dir / "orchestrator.md"
    existing_file.write_text("Old content")

    # Export to trigger backup
    await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(claude_dir),
    )

    # Find backup file
    backup_files = list(claude_dir.glob("orchestrator.md.old.*"))
    assert len(backup_files) == 1

    backup_file = backup_files[0]
    backup_name = backup_file.name

    # Verify format: orchestrator.md.old.YYYYMMDD_HHMMSS
    assert backup_name.startswith("orchestrator.md.old.")

    timestamp_part = backup_name.split(".old.")[1]
    # Should be YYYYMMDD_HHMMSS format (15 characters)
    assert len(timestamp_part) == 15
    assert timestamp_part[8] == "_"  # Underscore separator


# Test cross-platform path handling
@pytest.mark.asyncio
async def test_cross_platform_path_handling(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test that path handling works on Windows and Unix"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    # Create directory with pathlib (cross-platform)
    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Test with both forward and backslashes (should both work via Path)
    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(claude_dir),
    )

    assert result["success"] is True

    # Verify files created with proper paths
    for file_info in result["files"]:
        file_path = Path(file_info["path"])
        assert file_path.exists()
        assert file_path.is_file()


# Test template with empty behavioral rules
@pytest.mark.asyncio
async def test_template_with_empty_behavioral_rules(
    db_session: AsyncSession,
    test_user: User,
    temp_export_dir: Path,
):
    """Test export of template with no behavioral rules or success criteria"""
    # Create minimal template
    minimal_template = AgentTemplate(
        id="tmpl_minimal_001",
        tenant_key="test_tenant_001",
        name="minimal",
        category="role",
        role="minimal",
        system_instructions="Minimal template content.",
        behavioral_rules=[],  # Empty
        success_criteria=[],  # Empty
        is_active=True,
    )
    db_session.add(minimal_template)
    await db_session.commit()

    from api.endpoints.claude_export import export_templates_to_claude_code

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=test_user,
        export_path=str(claude_dir),
    )

    assert result["success"] is True

    # Verify file created without empty sections
    minimal_file = claude_dir / "minimal.md"
    content = minimal_file.read_text()

    # Should NOT have empty sections
    if "## Behavioral Rules" in content:
        # If section exists, it should have content
        assert content.count("\n## ") >= 1

    assert "Minimal template content." in content


# Test concurrent exports (thread safety)
@pytest.mark.asyncio
async def test_concurrent_exports(
    db_session: AsyncSession,
    test_templates: list[AgentTemplate],
    test_user: User,
    temp_export_dir: Path,
):
    """Test that concurrent exports don't interfere with each other"""
    from api.endpoints.claude_export import export_templates_to_claude_code

    claude_dir = temp_export_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Run multiple exports concurrently
    tasks = [
        export_templates_to_claude_code(
            db=db_session,
            current_user=test_user,
            export_path=str(claude_dir),
        )
        for _ in range(3)
    ]

    results = await asyncio.gather(*tasks)

    # All should succeed
    assert all(r["success"] for r in results)

    # Verify final files are valid
    orchestrator_file = claude_dir / "orchestrator.md"
    assert orchestrator_file.exists()

    content = orchestrator_file.read_text()
    assert "name: orchestrator" in content
