"""Tool for creating a GitHub Pull Request."""

import os
import requests
import json
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.utils.logging import get_logger

logger = get_logger(__name__)


class GitHubCreatePRInput(BaseModel):
    """Input schema for creating a GitHub PR."""

    repository_url: str = Field(
        description=(
            "GitHub repository URL "
            "(e.g., 'https://github.com/user/repo')"
        )
    )
    title: str = Field(description="PR title")
    body: str = Field(description="PR description/body")
    head: str = Field(
        description="Branch name containing the changes (source branch)"
    )
    base: str = Field(
        default="main",
        description=(
            "Branch name to merge into "
            "(target branch, default: 'main')"
        ),
    )


class GitHubCreatePRTool(BaseTool):
    """Create a GitHub Pull Request.

    Creates a PR from a branch to the base branch in a GitHub repository.
    This tool can be used after pushing changes to create a PR for review.
    """

    name: str = "github_create_pr"
    description: str = (
        "Create a Pull Request (PR) in a GitHub repository. "
        "Creates a PR from the head branch to the base branch. "
        "Requires GITHUB_TOKEN environment variable for authentication."
    )
    args_schema: dict[str, Any] | type[BaseModel] | None = GitHubCreatePRInput

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def _run(
        self,
        repository_url: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> str:
        """Create GitHub Pull Request.

        Args:
            repository_url: GitHub repository URL
            title: PR title
            body: PR description
            head: Source branch name
            base: Target branch name

        Returns:
            Success message with PR URL or error message
        """
        logger.info(
            f"Creating PR from {head} to {base} in {repository_url}"
        )

        # Get token from environment in _run method to avoid Pydantic issues
        github_token = os.environ.get("GITHUB_TOKEN", "")

        if not github_token:
            return (
                "ERROR: GITHUB_TOKEN environment variable not set. "
                "Cannot create PR."
            )

        # Extract owner and repo from URL
        try:
            url_parts = repository_url.replace(".git", "").split("/")
            if "github.com" not in url_parts:
                return (
                    f"ERROR: Invalid GitHub repository URL: {repository_url}"
                )

            github_index = url_parts.index("github.com")
            if len(url_parts) < github_index + 3:
                return (
                    f"ERROR: Could not extract owner/repo from URL: "
                    f"{repository_url}"
                )

            owner = url_parts[github_index + 1]
            repo = url_parts[github_index + 2]

        except (ValueError, IndexError) as e:
            return (
                f"ERROR: Failed to parse repository URL {repository_url}: {e}"
            )

        # GITHUB API CALL TO CREATE PR

        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }

        logger.info(f"Sending POST request to {api_url}")

        try:
            response = requests.post(
                api_url, headers=headers, data=json.dumps(payload)
            )
            response.raise_for_status()

            pr_data = response.json()
            pr_url = pr_data.get("html_url")
            pr_number = pr_data.get("number")

            success_message = (
                f"✅ Pull Request #{pr_number} created successfully! "
                f"URL: {pr_url}"
            )
            logger.info(success_message)
            return success_message

        except requests.exceptions.HTTPError as e:
            error_message = (
                f"GitHub API Error ({response.status_code}) "
                f"when creating PR: {e}"
            )
            logger.error(error_message)

            # Try to extract detailed error message from GitHub
            try:
                error_details = response.json()
                if 'message' in error_details:
                    error_message += (
                        f"\nAPI Message: {error_details['message']}"
                    )
                if 'errors' in error_details:
                    error_message += (
                        f"\nValidation Errors: {error_details['errors']}"
                    )
            except json.JSONDecodeError:
                error_message += "\nCould not decode JSON error response."

            return error_message

        except requests.exceptions.RequestException as e:
            error_message = (
                f"❌ An error occurred during the request to GitHub API: {e}"
            )
            logger.error(error_message)
            return error_message
