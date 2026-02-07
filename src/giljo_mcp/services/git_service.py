"""
Git Service - Handover 0269

Provides git operations for GiljoAI products without GitHub API dependency.

Responsibilities:
- Fetch git commit history from local repositories
- Validate git repositories
- Parse git log output
- Handle git command errors gracefully

This service is used by ProductService to populate git history when
GitHub integration is enabled.

Note: This is a thin wrapper around git CLI commands. GitHub API integration
has been removed (Handover 013B). All git operations are performed via
subprocess calls to local git installations.
"""

import logging
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class GitService:
    """Service for git operations on local repositories"""

    def __init__(self):
        """Initialize GitService"""
        self.logger = logger

    async def fetch_commits(
        self,
        repo_path: str,
        limit: int = 20,
        since: str | None = None,
        branch: str = "HEAD",
    ) -> list[dict[str, Any]]:
        """
        Fetch git commit history from local repository.

        Uses git log with custom format to extract:
        - sha: Commit SHA
        - author: Author name
        - email: Author email
        - timestamp: Commit timestamp (ISO 8601)
        - message: Commit message

        Args:
            repo_path: Path to git repository
            limit: Maximum number of commits to fetch (default: 20)
            since: Optional date filter (ISO 8601 format)
            branch: Branch name to fetch from (default: HEAD)

        Returns:
            List of dicts with commit information:
            [
                {
                    "sha": "abc123...",
                    "author": "John Doe",
                    "email": "john@example.com",
                    "timestamp": "2025-11-29T10:00:00Z",
                    "message": "Commit message"
                },
                ...
            ]

        Raises:
            Exception: If repository is invalid or git command fails
        """
        try:
            # Validate repository
            is_valid = await self.validate_repository(repo_path)
            if not is_valid:
                self.logger.error(f"Invalid git repository: {repo_path}")
                return []

            # Build git log command
            cmd = [
                "git",
                "-C",
                repo_path,
                "log",
                f"--max-count={limit}",
                "--format=%H|%an|%ae|%cI|%s",  # sha|author|email|iso_timestamp|subject
                branch,
            ]

            # Add date filter if provided
            if since:
                cmd.insert(4, f"--since={since}")

            # Execute git log
            result = subprocess.run(  # nosec B603 B607
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.logger.error(f"Git log failed for {repo_path}: {result.stderr}")
                return []

            # Parse git log output
            commits = self._parse_git_log(result.stdout)
            self.logger.info(f"Fetched {len(commits)} commits from {repo_path}")
            return commits

        except FileNotFoundError:
            self.logger.error(f"Git not found or path invalid: {repo_path}")
            return []
        except subprocess.TimeoutExpired:
            self.logger.error(f"Git command timeout for {repo_path}")
            return []
        except (ValueError, IndexError, KeyError) as e:
            self.logger.exception(f"Failed to fetch commits from {repo_path}: {e}")
            return []

    async def validate_repository(self, repo_path: str) -> bool:
        """
        Validate if path is a valid git repository.

        Checks if .git directory exists and git commands work.

        Args:
            repo_path: Path to validate

        Returns:
            True if valid git repository, False otherwise
        """
        try:
            # Check if .git directory exists
            git_dir = Path(repo_path) / ".git"
            if not git_dir.exists():
                self.logger.debug(f"No .git directory in {repo_path}")
                return False

            # Try to run git command to verify
            result = subprocess.run(  # nosec B603 B607
                ["git", "-C", repo_path, "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            is_valid = result.returncode == 0
            if is_valid:
                self.logger.debug(f"Valid git repository: {repo_path}")
            else:
                self.logger.debug(f"Git validation failed for {repo_path}: {result.stderr}")
            return is_valid

        except FileNotFoundError:
            self.logger.debug(f"Git not found for validation: {repo_path}")
            return False
        except subprocess.TimeoutExpired:
            self.logger.debug(f"Git validation timeout: {repo_path}")
            return False
        except (ValueError, IndexError, KeyError) as e:
            self.logger.exception(f"Validation error for {repo_path}: {e}")
            return False

    def _parse_git_log(self, log_output: str) -> list[dict[str, Any]]:
        """
        Parse git log output in format: sha|author|email|timestamp|message

        Args:
            log_output: Raw git log output

        Returns:
            List of parsed commit dictionaries
        """
        commits = []

        if not log_output.strip():
            return commits

        for line in log_output.strip().split("\n"):
            if not line.strip():
                continue

            try:
                parts = line.split("|", 4)  # Split into max 5 parts
                if len(parts) < 5:
                    self.logger.warning(f"Malformed git log line: {line}")
                    continue

                sha, author, email, timestamp, message = parts

                commit = {
                    "sha": sha.strip(),
                    "author": author.strip(),
                    "email": email.strip(),
                    "timestamp": timestamp.strip(),
                    "message": message.strip(),
                }

                commits.append(commit)

            except (ValueError, IndexError, KeyError) as e:
                self.logger.warning(f"Failed to parse git log line: {line}, error: {e}")
                continue

        return commits

    async def get_current_branch(self, repo_path: str) -> str | None:
        """
        Get the current branch name of repository.

        Args:
            repo_path: Path to git repository

        Returns:
            Current branch name or None if failed

        Example:
            >>> branch = await service.get_current_branch("/path/to/repo")
            >>> branch
            "main"
        """
        try:
            result = subprocess.run(  # nosec B603 B607
                ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return result.stdout.strip()

            self.logger.warning(f"Failed to get branch for {repo_path}: {result.stderr}")
            return None

        except (ValueError, IndexError, KeyError) as e:
            self.logger.exception(f"Error getting current branch: {e}")
            return None

    async def get_remote_url(self, repo_path: str) -> str | None:
        """
        Get the remote URL (origin) of repository.

        Args:
            repo_path: Path to git repository

        Returns:
            Remote URL or None if no remote configured

        Example:
            >>> url = await service.get_remote_url("/path/to/repo")
            >>> url
            "https://github.com/user/repo.git"
        """
        try:
            result = subprocess.run(  # nosec B603 B607
                ["git", "-C", repo_path, "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            self.logger.debug(f"No remote origin for {repo_path}")
            return None

        except (ValueError, IndexError, KeyError) as e:
            self.logger.exception(f"Error getting remote URL: {e}")
            return None

    async def get_commit_count(self, repo_path: str, branch: str = "HEAD") -> int:
        """
        Get total commit count in branch.

        Args:
            repo_path: Path to git repository
            branch: Branch name (default: HEAD)

        Returns:
            Commit count or 0 if error

        Example:
            >>> count = await service.get_commit_count("/path/to/repo", "main")
            >>> count
            42
        """
        try:
            result = subprocess.run(  # nosec B603 B607
                ["git", "-C", repo_path, "rev-list", "--count", branch],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return int(result.stdout.strip())

            self.logger.warning(f"Failed to count commits for {repo_path}: {result.stderr}")
            return 0

        except (ValueError, IndexError, KeyError) as e:
            self.logger.exception(f"Error counting commits: {e}")
            return 0
