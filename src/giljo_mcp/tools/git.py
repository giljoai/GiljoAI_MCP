"""
Git Integration Tools for GiljoAI MCP
Handles git operations: init, commit, push, history, configuration
"""

import base64
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet
from fastmcp import FastMCP
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager

# Import from centralized exceptions
from giljo_mcp.exceptions import GitAuthenticationError, GitOperationError
from giljo_mcp.models import GitCommit, GitConfig, Project
from giljo_mcp.tenant import TenantManager, current_tenant


logger = logging.getLogger(__name__)


def _get_encryption_key() -> bytes:
    """Get or generate encryption key for secure credential storage"""
    # In production, this should come from a secure key management system
    # For now, we'll use a simple approach
    key_file = Path.home() / ".giljo-mcp" / "git.key"
    key_file.parent.mkdir(exist_ok=True)

    if key_file.exists():
        return key_file.read_bytes()
    key = Fernet.generate_key()
    key_file.write_bytes(key)
    key_file.chmod(0o600)  # Secure permissions
    return key


def _encrypt_credential(credential: str) -> str:
    """Encrypt a credential for secure storage"""
    if not credential:
        return ""

    key = _get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(credential.encode())
    return base64.b64encode(encrypted).decode()


def _decrypt_credential(encrypted_credential: str) -> str:
    """Decrypt a stored credential"""
    if not encrypted_credential:
        return ""

    try:
        key = _get_encryption_key()
        fernet = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_credential.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        logger.exception(f"Failed to decrypt credential: {e}")
        raise GitAuthenticationError("Failed to decrypt stored credentials")


async def _get_git_config(session: AsyncSession, product_id: str, tenant_key: str) -> Optional[GitConfig]:
    """Get git configuration for a product"""
    result = await session.execute(
        select(GitConfig).where(
            GitConfig.product_id == product_id,
            GitConfig.tenant_key == tenant_key,
            GitConfig.is_active,
        )
    )
    return result.scalar_one_or_none()


async def _run_git_command(
    command: list[str],
    cwd: str,
    use_system_auth: bool = True,
    env: Optional[dict[str, str]] = None,
    capture_output: bool = True,
) -> tuple[str, str, int]:
    """Run a git command and return stdout, stderr, returncode"""
    try:
        # Ensure git is available
        git_check = subprocess.run(["git", "--version"], check=False, capture_output=True, text=True)
        if git_check.returncode != 0:
            raise GitOperationError("Git is not installed or not available in PATH")

        # Prepare environment - use system environment by default
        full_env = os.environ.copy()

        # Only override environment if explicitly requested and not using system auth
        if not use_system_auth and env:
            full_env.update(env)

        # Run the command
        process = subprocess.run(
            command,
            check=False,
            cwd=cwd,
            env=full_env,
            capture_output=capture_output,
            text=True,
            timeout=30,  # 30 second timeout
        )

        return process.stdout, process.stderr, process.returncode

    except subprocess.TimeoutExpired:
        raise GitOperationError("Git command timed out after 30 seconds")
    except Exception as e:
        raise GitOperationError(f"Failed to execute git command: {e}")


def _generate_commit_message(project_name: str, project_mission: str, changes_summary: str = "") -> str:
    """Generate a semantic commit message from project context"""
    # Extract commit type from mission or changes
    commit_type = "feat"  # Default to feature

    mission_lower = project_mission.lower()
    if "fix" in mission_lower or "bug" in mission_lower:
        commit_type = "fix"
    elif "refactor" in mission_lower:
        commit_type = "refactor"
    elif "test" in mission_lower:
        commit_type = "test"
    elif "doc" in mission_lower:
        commit_type = "docs"
    elif "style" in mission_lower or "ui" in mission_lower:
        commit_type = "style"

    # Create concise commit message
    if changes_summary:
        message = f"{commit_type}: {changes_summary}"
    else:
        # Extract key action from mission
        mission_words = project_mission.split()[:10]  # First 10 words
        summary = " ".join(mission_words)
        if len(project_mission) > len(summary):
            summary += "..."
        message = f"{commit_type}: {summary}"

    # Add project context
    message += "\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n"
    message += f"Project: {project_name}\n"
    message += "Co-Authored-By: Claude <noreply@anthropic.com>"

    return message


def register_git_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register git management tools with the MCP server"""

    @mcp.tool()
    async def configure_git(
        product_id: str,
        repo_url: str,
        auth_method: str,
        branch: str = "main",
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        auto_commit: bool = True,
        auto_push: bool = False,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Configure git settings for a product

        Args:
            product_id: Product identifier
            repo_url: Git repository URL
            auth_method: Authentication method ('https', 'ssh', 'token')
            branch: Default branch name
            username: Username for HTTPS authentication
            password: Password/token for authentication
            ssh_key_path: Path to SSH private key
            auto_commit: Enable automatic commits on project completion
            auto_push: Enable automatic push after commits
            webhook_url: Webhook URL for CI/CD triggers
            webhook_secret: Secret for webhook verification

        Returns:
            Configuration status and details
        """
        try:
            tenant_key = current_tenant.get()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            async with db_manager.get_session_async() as session:
                # Check if configuration already exists
                existing = await _get_git_config(session, product_id, tenant_key)

                if existing:
                    # Update existing configuration
                    existing.repo_url = repo_url
                    existing.branch = branch
                    existing.auth_method = auth_method
                    existing.auto_commit = auto_commit
                    existing.auto_push = auto_push
                    existing.webhook_url = webhook_url
                    existing.webhook_secret = webhook_secret
                    existing.updated_at = datetime.utcnow()

                    if username:
                        existing.username = username
                    if password:
                        existing.password_encrypted = _encrypt_credential(password)
                    if ssh_key_path:
                        existing.ssh_key_path = ssh_key_path

                    git_config = existing
                else:
                    # Create new configuration
                    git_config = GitConfig(
                        tenant_key=tenant_key,
                        product_id=product_id,
                        repo_url=repo_url,
                        branch=branch,
                        auth_method=auth_method,
                        username=username,
                        password_encrypted=(_encrypt_credential(password) if password else None),
                        ssh_key_path=ssh_key_path,
                        auto_commit=auto_commit,
                        auto_push=auto_push,
                        webhook_url=webhook_url,
                        webhook_secret=webhook_secret,
                    )
                    session.add(git_config)

                await session.commit()

                return {
                    "success": True,
                    "config_id": git_config.id,
                    "is_configured": git_config.is_configured,
                    "webhook_configured": git_config.webhook_configured,
                    "message": "Git configuration saved successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to configure git: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def init_repo(product_id: str, repo_path: str, initial_commit: bool = True) -> dict[str, Any]:
        """
        Initialize a git repository for a product

        Args:
            product_id: Product identifier
            repo_path: Local path to initialize repository
            initial_commit: Create initial commit

        Returns:
            Initialization status and details
        """
        try:
            tenant_key = current_tenant.get()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            async with db_manager.get_session_async() as session:
                git_config = await _get_git_config(session, product_id, tenant_key)
                if not git_config:
                    return {
                        "success": False,
                        "error": "Git configuration not found. Configure git first.",
                    }

                # Ensure path exists
                repo_path_obj = Path(repo_path)
                repo_path_obj.mkdir(parents=True, exist_ok=True)

                # Initialize git repository
                stdout, stderr, code = await _run_git_command(["git", "init"], str(repo_path_obj))

                if code != 0:
                    raise GitOperationError(f"Git init failed: {stderr}")

                # Set default branch
                if git_config.branch != "master":
                    await _run_git_command(["git", "checkout", "-b", git_config.branch], str(repo_path_obj))

                # Add remote if configured
                if git_config.repo_url:
                    remote_name = git_config.remote_name or "origin"
                    await _run_git_command(
                        ["git", "remote", "add", remote_name, git_config.repo_url],
                        str(repo_path_obj),
                    )

                # Create initial commit if requested
                initial_commit_hash = None
                if initial_commit:
                    # Create basic .gitignore
                    gitignore_path = repo_path_obj / ".gitignore"
                    default_ignore = [
                        "# GiljoAI MCP",
                        ".giljo-mcp/",
                        "*.log",
                        "__pycache__/",
                        "*.pyc",
                        ".env",
                        ".venv/",
                    ]
                    gitignore_path.write_text("\n".join(default_ignore + git_config.ignore_patterns))

                    # Add and commit
                    await _run_git_command(["git", "add", ".gitignore"], str(repo_path_obj))

                    commit_msg = "feat: initialize repository with GiljoAI MCP\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\nCo-Authored-By: Claude <noreply@anthropic.com>"
                    _stdout, stderr, code = await _run_git_command(
                        ["git", "commit", "-m", commit_msg], str(repo_path_obj)
                    )

                    if code == 0:
                        # Get commit hash
                        hash_out, _, _ = await _run_git_command(["git", "rev-parse", "HEAD"], str(repo_path_obj))
                        initial_commit_hash = hash_out.strip()

                # Update git config with last known state
                git_config.last_commit_hash = initial_commit_hash
                git_config.verified_at = datetime.utcnow()
                await session.commit()

                return {
                    "success": True,
                    "repo_path": str(repo_path_obj),
                    "branch": git_config.branch,
                    "remote_added": bool(git_config.repo_url),
                    "initial_commit": initial_commit_hash,
                    "message": "Repository initialized successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to initialize repository: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def commit_changes(
        product_id: str,
        repo_path: str,
        message: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        commit_type: str = "auto",
    ) -> dict[str, Any]:
        """
        Commit changes to the repository

        Args:
            product_id: Product identifier
            repo_path: Local repository path
            message: Custom commit message (auto-generated if not provided)
            project_id: Associated project ID
            agent_id: Agent making the commit
            commit_type: Type of commit ('auto', 'manual', 'project_completion')

        Returns:
            Commit status and details
        """
        try:
            tenant_key = current_tenant.get()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            async with db_manager.get_session_async() as session:
                git_config = await _get_git_config(session, product_id, tenant_key)
                if not git_config:
                    return {"success": False, "error": "Git configuration not found"}

                repo_path_obj = Path(repo_path)
                if not repo_path_obj.exists():
                    return {"success": False, "error": "Repository path does not exist"}

                # Check for changes
                status_out, _, _status_code = await _run_git_command(
                    ["git", "status", "--porcelain"], str(repo_path_obj)
                )

                if not status_out.strip():
                    return {
                        "success": True,
                        "message": "No changes to commit",
                        "commit_hash": None,
                    }

                # Add all changes
                await _run_git_command(["git", "add", "."], str(repo_path_obj))

                # Generate commit message if not provided
                if not message:
                    project_name = "Unknown Project"
                    project_mission = "Development work"

                    if project_id:
                        project_result = await session.execute(select(Project).where(Project.id == project_id))
                        project = project_result.scalar_one_or_none()
                        if project:
                            project_name = project.name
                            project_mission = project.mission

                    # Get file changes for summary
                    diff_out, _, _ = await _run_git_command(["git", "diff", "--cached", "--stat"], str(repo_path_obj))

                    message = _generate_commit_message(project_name, project_mission, diff_out)

                # Commit changes
                _stdout, stderr, code = await _run_git_command(["git", "commit", "-m", message], str(repo_path_obj))

                if code != 0:
                    raise GitOperationError(f"Git commit failed: {stderr}")

                # Get commit details
                hash_out, _, _ = await _run_git_command(["git", "rev-parse", "HEAD"], str(repo_path_obj))
                commit_hash = hash_out.strip()

                # Get commit info
                info_out, _, _ = await _run_git_command(
                    ["git", "show", "--stat", "--format=%an|%ae|%s", commit_hash],
                    str(repo_path_obj),
                )

                lines = info_out.strip().split("\n")
                author_info = lines[0].split("|")
                author_name = author_info[0] if len(author_info) > 0 else "Unknown"
                author_email = author_info[1] if len(author_info) > 1 else "unknown@example.com"
                commit_subject = author_info[2] if len(author_info) > 2 else message.split("\n")[0]

                # Parse file changes
                files_changed = []
                insertions = 0
                deletions = 0

                for line in lines[1:]:
                    if " | " in line and (" +" in line or " -" in line):
                        parts = line.split(" | ")
                        if len(parts) >= 2:
                            files_changed.append(parts[0].strip())
                            # Parse insertions/deletions
                            changes = parts[1]
                            if "+" in changes:
                                insertions += changes.count("+")
                            if "-" in changes:
                                deletions += changes.count("-")

                # Record commit in database
                git_commit = GitCommit(
                    tenant_key=tenant_key,
                    product_id=product_id,
                    project_id=project_id,
                    commit_hash=commit_hash,
                    commit_message=message,
                    author_name=author_name,
                    author_email=author_email,
                    branch_name=git_config.branch,
                    files_changed=files_changed,
                    insertions=insertions,
                    deletions=deletions,
                    triggered_by=commit_type,
                    agent_id=agent_id,
                    committed_at=datetime.utcnow(),
                )
                session.add(git_commit)

                # Update git config
                git_config.last_commit_hash = commit_hash
                git_config.last_error = None

                await session.commit()

                result = {
                    "success": True,
                    "commit_hash": commit_hash,
                    "message": commit_subject,
                    "files_changed": len(files_changed),
                    "insertions": insertions,
                    "deletions": deletions,
                    "auto_push_enabled": git_config.auto_push,
                }

                # Auto-push if enabled
                if git_config.auto_push:
                    push_result = await push_to_remote(product_id, repo_path)
                    result["push_result"] = push_result

                return result

        except Exception as e:
            logger.exception(f"Failed to commit changes: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def push_to_remote(
        product_id: str,
        repo_path: str,
        remote_name: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Push commits to remote repository

        Args:
            product_id: Product identifier
            repo_path: Local repository path
            remote_name: Remote name (defaults to configured remote)
            branch: Branch to push (defaults to configured branch)

        Returns:
            Push status and details
        """
        try:
            tenant_key = current_tenant.get()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            async with db_manager.get_session_async() as session:
                git_config = await _get_git_config(session, product_id, tenant_key)
                if not git_config:
                    return {"success": False, "error": "Git configuration not found"}

                if not git_config.is_configured:
                    return {
                        "success": False,
                        "error": "Git configuration is incomplete",
                    }

                repo_path_obj = Path(repo_path)
                if not repo_path_obj.exists():
                    return {"success": False, "error": "Repository path does not exist"}

                # Use configured values if not specified
                remote = remote_name or git_config.remote_name or "origin"
                branch_name = branch or git_config.branch or "main"

                # Check if we should use system authentication (recommended)
                use_system_auth = git_config.auth_method == "system" or not git_config.auth_method

                if use_system_auth:
                    # Use existing git configuration and credential helpers
                    stdout, stderr, code = await _run_git_command(
                        ["git", "push", remote, branch_name],
                        str(repo_path_obj),
                        use_system_auth=True,
                    )
                else:
                    # Legacy mode: use configured credentials
                    env = {}

                    if git_config.auth_method == "https":
                        if git_config.username and git_config.password_encrypted:
                            username = git_config.username
                            password = _decrypt_credential(git_config.password_encrypted)

                            # Use credential helper for HTTPS
                            env["GIT_ASKPASS"] = "echo"
                            env["GIT_USERNAME"] = username
                            env["GIT_PASSWORD"] = password

                    elif git_config.auth_method == "ssh":
                        if git_config.ssh_key_path:
                            env["GIT_SSH_COMMAND"] = f"ssh -i {git_config.ssh_key_path} -o StrictHostKeyChecking=no"

                    elif git_config.auth_method == "token" and git_config.password_encrypted:
                        token = _decrypt_credential(git_config.password_encrypted)
                        env["GIT_ASKPASS"] = "echo"
                        env["GIT_USERNAME"] = "token"
                        env["GIT_PASSWORD"] = token

                    # Push to remote with custom authentication
                    _stdout, stderr, code = await _run_git_command(
                        ["git", "push", remote, branch_name],
                        str(repo_path_obj),
                        use_system_auth=False,
                        env=env,
                    )

                # Update commit records
                if code == 0:
                    # Mark recent commits as pushed
                    await session.execute(
                        update(GitCommit)
                        .where(
                            GitCommit.product_id == product_id,
                            GitCommit.tenant_key == tenant_key,
                            GitCommit.push_status == "pending",
                        )
                        .values(push_status="pushed", pushed_at=datetime.utcnow())
                    )

                    git_config.last_push_at = datetime.utcnow()
                    git_config.last_error = None

                    await session.commit()

                    return {
                        "success": True,
                        "remote": remote,
                        "branch": branch_name,
                        "message": "Changes pushed successfully",
                    }
                # Mark commits as failed
                await session.execute(
                    update(GitCommit)
                    .where(
                        GitCommit.product_id == product_id,
                        GitCommit.tenant_key == tenant_key,
                        GitCommit.push_status == "pending",
                    )
                    .values(push_status="failed", push_error=stderr)
                )

                git_config.last_error = stderr
                await session.commit()

                raise GitOperationError(f"Git push failed: {stderr}")

        except Exception as e:
            logger.exception(f"Failed to push to remote: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_commit_history(
        product_id: str, repo_path: str, limit: int = 10, branch: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get commit history from repository

        Args:
            product_id: Product identifier
            repo_path: Local repository path
            limit: Maximum number of commits to return
            branch: Branch to get history from (defaults to configured branch)

        Returns:
            List of commits with details
        """
        try:
            tenant_key = current_tenant.get()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            async with db_manager.get_session_async() as session:
                git_config = await _get_git_config(session, product_id, tenant_key)
                if not git_config:
                    return {"success": False, "error": "Git configuration not found"}

                repo_path_obj = Path(repo_path)
                if not repo_path_obj.exists():
                    return {"success": False, "error": "Repository path does not exist"}

                branch_name = branch or git_config.branch or "HEAD"

                # Get commit history
                stdout, stderr, code = await _run_git_command(
                    [
                        "git",
                        "log",
                        f"-{limit}",
                        "--format=%H|%an|%ae|%at|%s",
                        branch_name,
                    ],
                    str(repo_path_obj),
                )

                if code != 0:
                    raise GitOperationError(f"Failed to get commit history: {stderr}")

                commits = []
                for line in stdout.strip().split("\n"):
                    if line:
                        parts = line.split("|", 4)
                        if len(parts) >= 5:
                            commits.append(
                                {
                                    "hash": parts[0],
                                    "author_name": parts[1],
                                    "author_email": parts[2],
                                    "timestamp": int(parts[3]),
                                    "message": parts[4],
                                    "date": datetime.fromtimestamp(int(parts[3])).isoformat(),
                                }
                            )

                # Get database records for additional context
                db_commits = await session.execute(
                    select(GitCommit)
                    .where(
                        GitCommit.product_id == product_id,
                        GitCommit.tenant_key == tenant_key,
                    )
                    .order_by(GitCommit.committed_at.desc())
                    .limit(limit)
                )

                db_commit_map = {c.commit_hash: c for c in db_commits.scalars()}

                # Enhance with database info
                for commit in commits:
                    if commit["hash"] in db_commit_map:
                        db_commit = db_commit_map[commit["hash"]]
                        commit.update(
                            {
                                "triggered_by": db_commit.triggered_by,
                                "files_changed": db_commit.files_changed,
                                "insertions": db_commit.insertions,
                                "deletions": db_commit.deletions,
                                "push_status": db_commit.push_status,
                                "project_id": db_commit.project_id,
                            }
                        )

                return {
                    "success": True,
                    "commits": commits,
                    "branch": branch_name,
                    "total_shown": len(commits),
                }

        except Exception as e:
            logger.exception(f"Failed to get commit history: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_git_status(product_id: str, repo_path: str) -> dict[str, Any]:
        """
        Get current git status for a repository

        Args:
            product_id: Product identifier
            repo_path: Local repository path

        Returns:
            Repository status and configuration info
        """
        try:
            tenant_key = current_tenant.get()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            async with db_manager.get_session_async() as session:
                git_config = await _get_git_config(session, product_id, tenant_key)

                repo_path_obj = Path(repo_path)
                status_info = {
                    "success": True,
                    "configured": bool(git_config),
                    "repo_exists": repo_path_obj.exists() and (repo_path_obj / ".git").exists(),
                    "config": None,
                    "status": None,
                }

                if git_config:
                    status_info["config"] = {
                        "repo_url": git_config.repo_url,
                        "branch": git_config.branch,
                        "auth_method": git_config.auth_method,
                        "auto_commit": git_config.auto_commit,
                        "auto_push": git_config.auto_push,
                        "is_configured": git_config.is_configured,
                        "webhook_configured": git_config.webhook_configured,
                        "last_commit_hash": git_config.last_commit_hash,
                        "last_push_at": (git_config.last_push_at.isoformat() if git_config.last_push_at else None),
                        "last_error": git_config.last_error,
                    }

                if status_info["repo_exists"]:
                    # Get git status
                    status_out, _, _status_code = await _run_git_command(
                        ["git", "status", "--porcelain"], str(repo_path_obj)
                    )

                    # Get current branch
                    branch_out, _, _ = await _run_git_command(["git", "branch", "--show-current"], str(repo_path_obj))

                    # Get remote info
                    remote_out, _, _ = await _run_git_command(["git", "remote", "-v"], str(repo_path_obj))

                    status_info["status"] = {
                        "current_branch": branch_out.strip(),
                        "has_changes": bool(status_out.strip()),
                        "changed_files": (len(status_out.strip().split("\n")) if status_out.strip() else 0),
                        "remotes": [line.strip() for line in remote_out.split("\n") if line.strip()],
                    }

                return status_info

        except Exception as e:
            logger.exception(f"Failed to get git status: {e}")
            return {"success": False, "error": str(e)}
