"""Consolidated tool for generating AAP configuration files (playbook, job template, inventory)."""

import yaml
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.utils.logging import get_logger
from tools.ansible_write import AnsibleWriteTool

logger = get_logger(__name__)


class GenerateAAPConfigInput(BaseModel):
    """Input schema for generating AAP configuration files."""

    config_type: str = Field(
        description="Type: 'playbook', 'job_template', or 'inventory'"
    )
    file_path: str = Field(description="Output file path")
    name: str = Field(description="Name/description")
    role_name: str = Field(
        default="", description="Role name (playbook/job_template)"
    )
    hosts: str = Field(default="all", description="Target hosts (playbook)")
    become: bool = Field(
        default=False, description="Use privilege escalation (playbook)"
    )
    vars: dict[str, Any] = Field(
        default_factory=dict, description="Variables (playbook)"
    )
    playbook_path: str = Field(
        default="", description="Playbook path (job_template)"
    )
    inventory: str = Field(
        default="", description="Inventory name/path (job_template)"
    )
    description: str = Field(
        default="", description="Description (job_template/inventory)"
    )
    extra_vars: str = Field(
        default="", description="Extra vars YAML (job_template)"
    )
    inventory_hosts: list[str] = Field(
        default_factory=list, description="Hosts (inventory)"
    )
    groups: dict[str, list[str]] = Field(
        default_factory=dict, description="Groups (inventory)"
    )


class GenerateAAPConfigTool(BaseTool):
    """Generate AAP configuration files (playbook, job template, or inventory).

    This is a consolidated tool that can generate three types of AAP
    configuration files:
    - Playbooks: Ansible playbook YAML files that use roles
    - Job Templates: AAP job template YAML configurations
    - Inventories: AAP inventory YAML configurations
    """

    name: str = "generate_aap_config"
    description: str = (
        "Generate AAP config: playbook, job_template, or inventory. "
        "Set config_type and required fields for that type."
    )
    args_schema: dict[str, Any] | type[BaseModel] | None = GenerateAAPConfigInput

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._ansible_write = AnsibleWriteTool()

    def _run(
        self,
        config_type: str,
        file_path: str,
        name: str,
        role_name: str = "",
        hosts: str = "all",
        become: bool = False,
        vars: dict[str, Any] = None,
        playbook_path: str = "",
        inventory: str = "",
        description: str = "",
        extra_vars: str = "",
        inventory_hosts: list[str] = None,
        groups: dict[str, list[str]] = None,
    ) -> str:
        """Generate AAP configuration file.

        Args:
            config_type: Type of config ('playbook', 'job_template', 'inventory')
            file_path: Path to write the file
            name: Name/description
            role_name: Role name (for playbook/job_template)
            hosts: Target hosts (for playbook)
            become: Use privilege escalation (for playbook)
            vars: Variables for role (for playbook)
            playbook_path: Path to playbook (for job_template)
            inventory: Inventory name/path (for job_template)
            description: Description (for job_template/inventory)
            extra_vars: Extra variables (for job_template)
            inventory_hosts: List of hosts (for inventory)
            groups: Dictionary of groups (for inventory)

        Returns:
            Success or error message
        """
        if vars is None:
            vars = {}
        if inventory_hosts is None:
            inventory_hosts = []
        if groups is None:
            groups = {}

        config_type = config_type.lower()

        if config_type == "playbook":
            return self._generate_playbook(
                file_path, name, role_name, hosts, become, vars
            )
        elif config_type == "job_template":
            return self._generate_job_template(
                file_path,
                name,
                playbook_path,
                inventory,
                role_name,
                description,
                extra_vars,
            )
        elif config_type == "inventory":
            return self._generate_inventory(
                file_path, name, description, inventory_hosts, groups
            )
        else:
            return (
                f"ERROR: Invalid config_type '{config_type}'. "
                f"Must be 'playbook', 'job_template', or 'inventory'."
            )

    def _generate_playbook(
        self,
        file_path: str,
        name: str,
        role_name: str,
        hosts: str,
        become: bool,
        vars: dict[str, Any],
    ) -> str:
        """Generate playbook YAML file."""
        logger.info(f"Generating playbook YAML: {name}")

        if not role_name:
            return "ERROR: role_name is required for playbook generation"

        try:
            playbook_lines = ["---"]
            playbook_lines.append(f"- name: {name}")
            playbook_lines.append(f"  hosts: {hosts}")

            if become:
                playbook_lines.append("  become: true")

            if vars:
                playbook_lines.append("  vars:")
                for key, value in vars.items():
                    if isinstance(value, str):
                        playbook_lines.append(f"    {key}: '{value}'")
                    else:
                        playbook_lines.append(f"    {key}: {value}")

            playbook_lines.append("  roles:")
            playbook_lines.append(f"    - {role_name}")

            playbook_content = "\n".join(playbook_lines)

            result = self._ansible_write._run(
                file_path=file_path, yaml_content=playbook_content
            )

            if result.startswith("Successfully"):
                logger.info(f"Successfully generated playbook YAML: {file_path}")
                return (
                    f"Successfully generated playbook YAML at {file_path}\n"
                    f"Playbook: {name}\n"
                    f"Role: {role_name}\n"
                    f"Hosts: {hosts}"
                )
            else:
                return f"ERROR: Failed to generate playbook: {result}"

        except Exception as e:
            error_msg = f"ERROR: Failed to generate playbook YAML: {e}"
            logger.error(error_msg)
            return error_msg

    def _generate_job_template(
        self,
        file_path: str,
        name: str,
        playbook_path: str,
        inventory: str,
        role_name: str,
        description: str,
        extra_vars: str,
    ) -> str:
        """Generate job template YAML file."""
        logger.info(f"Generating job template YAML: {name}")

        if not playbook_path:
            return "ERROR: playbook_path is required for job_template generation"
        if not inventory:
            return "ERROR: inventory is required for job_template generation"

        try:
            job_template = {
                "apiVersion": "tower.ansible.com/v1beta1",
                "kind": "JobTemplate",
                "metadata": {"name": name},
                "spec": {
                    "name": name,
                    "job_type": "run",
                    "playbook": playbook_path,
                    "inventory": inventory,
                },
            }

            if description:
                job_template["spec"]["description"] = description

            if role_name:
                job_template["spec"]["role_name"] = role_name

            if extra_vars:
                try:
                    parsed_vars = yaml.safe_load(extra_vars)
                    job_template["spec"]["extra_vars"] = parsed_vars
                except yaml.YAMLError:
                    job_template["spec"]["extra_vars"] = extra_vars

            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with file_path_obj.open("w") as f:
                yaml.dump(
                    job_template,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )

            logger.info(f"Successfully generated job template YAML: {file_path}")
            return (
                f"Successfully generated job template YAML at {file_path}\n"
                f"Job template: {name}\n"
                f"Playbook: {playbook_path}\n"
                f"Inventory: {inventory}"
            )

        except Exception as e:
            error_msg = f"ERROR: Failed to generate job template YAML: {e}"
            logger.error(error_msg)
            return error_msg

    def _generate_inventory(
        self,
        file_path: str,
        name: str,
        description: str,
        inventory_hosts: list[str],
        groups: dict[str, list[str]],
    ) -> str:
        """Generate inventory YAML file."""
        logger.info(f"Generating inventory YAML: {name}")

        try:
            inventory = {
                "apiVersion": "tower.ansible.com/v1beta1",
                "kind": "Inventory",
                "metadata": {"name": name},
                "spec": {
                    "name": name,
                    "organization": "Default",
                },
            }

            if description:
                inventory["spec"]["description"] = description

            inventory_hosts_dict = {}
            if inventory_hosts:
                inventory_hosts_dict["all"] = {"hosts": inventory_hosts}

            for group_name, group_hosts in groups.items():
                if group_name not in inventory_hosts_dict:
                    inventory_hosts_dict[group_name] = {"hosts": group_hosts}
                else:
                    inventory_hosts_dict[group_name]["hosts"].extend(group_hosts)

            if inventory_hosts_dict:
                inventory["spec"]["hosts"] = inventory_hosts_dict

            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with file_path_obj.open("w") as f:
                yaml.dump(
                    inventory,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )

            logger.info(f"Successfully generated inventory YAML: {file_path}")
            host_count = len(inventory_hosts) + sum(len(h) for h in groups.values())
            return (
                f"Successfully generated inventory YAML at {file_path}\n"
                f"Inventory: {name}\n"
                f"Total hosts: {host_count}\n"
                f"Groups: {len(groups) + (1 if inventory_hosts else 0)}"
            )

        except Exception as e:
            error_msg = f"ERROR: Failed to generate inventory YAML: {e}"
            logger.error(error_msg)
            return error_msg

