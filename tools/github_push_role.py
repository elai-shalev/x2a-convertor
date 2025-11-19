"""Tool for pushing an Ansible role to a GitHub repository."""

import os
import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.utils.logging import get_logger

logger = get_logger(__name__)


class GitHubPushRoleInput(BaseModel):
    """Input schema for pushing a role to GitHub."""

    role_path: str = Field(description="The local filesystem path to the role directory")
    repository_url: str = Field(
        description="GitHub repository URL (e.g., 'https://github.com/user/repo.git')"
    )
    branch: str = Field(
        default="main",
        description="Branch to push to (default: 'main')",
    )
    commit_message: str = Field(
        default="",
        description="Commit message (default: auto-generated)",
    )


class GitHubPushRoleTool(BaseTool):
    """Push an Ansible role to a GitHub repository.

    This tool commits the role directory and pushes it to the specified
    GitHub repository. It handles git initialization if needed.
    """

    name: str = "github_push_role"
    description: str = (
        "Push an Ansible role to a GitHub repository. "
        "Commits the role directory and pushes to the specified branch. "
        "Requires GITHUB_TOKEN environment variable for authentication."
    )
    args_schema: dict[str, Any] | type[BaseModel] | None = GitHubPushRoleInput

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.github_token = os.getenv("GITHUB_TOKEN", "")

    def _run(
        self,
        role_path: str,
        repository_url: str,
        branch: str = "main",
        commit_message: str = "",
    ) -> str:
        """Push role to GitHub repository.

        Args:
            role_path: The local filesystem path to the role directory
            repository_url: GitHub repository URL
            branch: Branch to push to
            commit_message: Commit message

        Returns:
            Success or error message
        """
        logger.info(
            f"Pushing role from {role_path} to {repository_url} on branch {branch}"
        )

        role_path_obj = Path(role_path)
        if not role_path_obj.exists():
            return f"ERROR: Role path does not exist: {role_path}"

        if not role_path_obj.is_dir():
            return f"ERROR: Role path is not a directory: {role_path}"

        if not self.github_token:
            return (
                "ERROR: GITHUB_TOKEN environment variable not set. "
                "Cannot authenticate with GitHub."
            )

        try:
            # TODO: Implement actual git operations
            # Steps would be:
            # 1. Initialize git repo in role_path if not already initialized
            # 2. Add remote if not exists
            # 3. Stage all files
            # 4. Commit with message
            # 5. Push to branch
            # Use subprocess to run git commands or use GitPython library

            logger.warning(
                "GitHub push not yet implemented. This is a placeholder tool."
            )

            return (
                f"GitHub push for role at {role_path} to {repository_url} - "
                "API implementation pending. "
                "Tool structure ready for implementation."
            )

        except Exception as e:
            logger.error(f"Error pushing to GitHub: {e}")
            return f"ERROR: Failed to push to GitHub: {e}"

