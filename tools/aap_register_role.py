"""Tool for registering an Ansible role in AAP from a GitHub repository."""

import os
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.utils.logging import get_logger

logger = get_logger(__name__)


class AAPRegisterRoleInput(BaseModel):
    """Input schema for registering a role in AAP from GitHub."""

    role_name: str = Field(description="Name of the role to register")
    github_repository_url: str = Field(
        description="GitHub repository URL where the role is located"
    )
    github_branch: str = Field(
        default="main",
        description="Branch in the GitHub repository (default: 'main')",
    )
    role_path: str = Field(
        default="",
        description=(
            "Path to the role within the repository "
            "(e.g., 'roles/my_role' or empty if role is at repo root)"
        ),
    )


class AAPRegisterRoleTool(BaseTool):
    """Register an Ansible role in AAP from a GitHub repository.

    This tool configures AAP to fetch and register a role from a GitHub
    repository. AAP will sync the repository and make the role available
    for use in job templates.
    """

    name: str = "aap_register_role"
    description: str = (
        "Register an Ansible role in Ansible Automation Platform (AAP) "
        "from a GitHub repository. AAP will fetch the role from GitHub "
        "and make it available for use in job templates. "
        "Requires AAP_API_URL, AAP_USERNAME, and AAP_PASSWORD environment variables."
    )
    args_schema: dict[str, Any] | type[BaseModel] | None = AAPRegisterRoleInput

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_url = os.getenv("AAP_API_URL", "")
        self.username = os.getenv("AAP_USERNAME", "")
        self.password = os.getenv("AAP_PASSWORD", "")

    def _run(
        self,
        role_name: str,
        github_repository_url: str,
        github_branch: str = "main",
        role_path: str = "",
    ) -> str:
        """Register role in AAP from GitHub repository.

        Args:
            role_name: Name of the role to register
            github_repository_url: GitHub repository URL
            github_branch: Branch in the repository
            role_path: Path to role within repository (if not at root)

        Returns:
            Success or error message
        """
        logger.info(
            f"Registering role '{role_name}' from GitHub repository "
            f"{github_repository_url} (branch: {github_branch})"
        )

        if not self.api_url:
            return (
                "ERROR: AAP_API_URL environment variable not set. "
                "Cannot register role."
            )

        if not self.username or not self.password:
            return (
                "ERROR: AAP_USERNAME and AAP_PASSWORD environment variables "
                "not set. Cannot authenticate with AAP API."
            )

        # TODO: Implement actual AAP API calls
        # This is a placeholder for the actual implementation
        # Steps would be:
        # 1. Create or update a Project in AAP that points to the GitHub repo
        #    POST {AAP_API_URL}/api/v2/projects/
        #    Body: {
        #      "name": project_name,
        #      "scm_type": "git",
        #      "scm_url": github_repository_url,
        #      "scm_branch": github_branch,
        #      ...
        #    }
        # 2. Sync the project to fetch the latest code
        #    POST {AAP_API_URL}/api/v2/projects/{project_id}/update/
        # 3. The role should now be available in AAP
        #    The role path would be: {project_path}/{role_path}/{role_name}

        logger.warning(
            "AAP API call not yet implemented. This is a placeholder tool."
        )

        return (
            f"Role registration for '{role_name}' from {github_repository_url} - "
            "API implementation pending. "
            "Tool structure ready for implementation."
        )

