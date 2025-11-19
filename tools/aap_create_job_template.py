"""Tool for creating a job template in Ansible Automation Platform."""

import os
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.utils.logging import get_logger

logger = get_logger(__name__)


class AAPCreateJobTemplateInput(BaseModel):
    """Input schema for creating a job template in AAP."""

    name: str = Field(description="Name of the job template")
    playbook_path: str = Field(
        description="Path to the playbook file (relative to project root or full path)"
    )
    inventory: str = Field(
        description="Inventory name or ID to use for the job template"
    )
    role_name: str = Field(
        default="",
        description="Name of the role to include in the playbook (optional)",
    )
    credential: str = Field(
        default="",
        description="Credential name or ID (optional)",
    )
    description: str = Field(
        default="",
        description="Description for the job template",
    )
    extra_vars: str = Field(
        default="",
        description="Extra variables in YAML format (optional)",
    )


class AAPCreateJobTemplateTool(BaseTool):
    """Create a job template in Ansible Automation Platform.

    This tool creates a new job template in AAP that can be used to run
    Ansible playbooks. The job template references a playbook and inventory.
    """

    name: str = "aap_create_job_template"
    description: str = (
        "Create a new job template in Ansible Automation Platform (AAP). "
        "A job template defines how to run an Ansible playbook, including "
        "which playbook, inventory, and credentials to use. "
        "Returns success message if created, error if creation fails. "
        "Requires AAP_API_URL, AAP_USERNAME, and AAP_PASSWORD environment variables."
    )
    args_schema: dict[str, Any] | type[BaseModel] | None = (
        AAPCreateJobTemplateInput
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_url = os.getenv("AAP_API_URL", "")
        self.username = os.getenv("AAP_USERNAME", "")
        self.password = os.getenv("AAP_PASSWORD", "")

    def _run(
        self,
        name: str,
        playbook_path: str,
        inventory: str,
        role_name: str = "",
        credential: str = "",
        description: str = "",
        extra_vars: str = "",
    ) -> str:
        """Create job template in AAP.

        Args:
            name: Name of the job template
            playbook_path: Path to the playbook file
            inventory: Inventory name or ID
            role_name: Name of the role to include (optional)
            credential: Credential name or ID (optional)
            description: Description for the job template
            extra_vars: Extra variables in YAML format (optional)

        Returns:
            Success or error message
        """
        logger.info(f"Creating job template '{name}' in AAP")

        if not self.api_url:
            return (
                "ERROR: AAP_API_URL environment variable not set. "
                "Cannot create job template."
            )

        if not self.username or not self.password:
            return (
                "ERROR: AAP_USERNAME and AAP_PASSWORD environment variables "
                "not set. Cannot authenticate with AAP API."
            )

        # TODO: Implement actual AAP API call
        # This is a placeholder for the actual implementation
        # Example API call structure:
        # POST {AAP_API_URL}/api/v2/job_templates/
        # Headers: Authorization: Basic {base64(username:password)}
        # Body: {
        #   "name": name,
        #   "playbook": playbook_path,
        #   "inventory": inventory_id,
        #   "credential": credential_id (if provided),
        #   "description": description,
        #   "extra_vars": extra_vars (if provided)
        # }

        logger.warning(
            "AAP API call not yet implemented. This is a placeholder tool."
        )

        return (
            f"Job template creation for '{name}' - "
            "API implementation pending. "
            "Tool structure ready for implementation."
        )

