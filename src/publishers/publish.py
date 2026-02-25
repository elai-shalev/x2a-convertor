"""Publisher for Ansible roles — project scaffolding and AAP integration."""

from pathlib import Path

from src.publishers.tools import (
    AAPSyncResult,
    copy_role_directory,
    create_directory_structure,
    generate_ansible_cfg,
    generate_collections_requirements,
    generate_inventory_file,
    generate_playbook_yaml,
    load_collections_file,
    load_inventory_file,
    sync_to_aap,
    verify_files_exist,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


def publish_project(
    module_names: list[str] | tuple[str, ...],
    source_paths: list[str] | tuple[str, ...],
    base_path: str | None = None,
    collections_file: str | Path | None = None,
    inventory_file: str | Path | None = None,
    collections: list[dict[str, str]] | None = None,
    inventory: dict | None = None,
) -> str:
    """Create an Ansible project structure from migrated roles.

    Creates a complete Ansible project with directory structure, role copies,
    wrapper playbooks, ansible.cfg, collections requirements, and inventory.

    Args:
        module_names: Name(s) of the role(s) to include.
        source_paths: Path(s) to the migrated Ansible role directory(ies).
        base_path: Base path for constructing deployment path.
            If not provided, derived from the first source path.
        collections_file: Path to YAML/JSON file containing collections list.
        inventory_file: Path to YAML/JSON file containing inventory structure.
        collections: List of collection dicts with 'name' and optional 'version'.
        inventory: Inventory structure as dict. If None, uses sample inventory.

    Returns:
        Absolute path to the created project directory.

    Raises:
        ValueError: If input validation fails.
        FileNotFoundError: If source paths or generated files are missing.
        OSError: If file operations fail.
    """
    role_names = list(module_names)
    role_paths = list(source_paths)

    if collections is None and collections_file:
        collections = load_collections_file(collections_file)

    if inventory is None and inventory_file:
        inventory = load_inventory_file(inventory_file)

    if len(role_names) != len(role_paths):
        error_msg = (
            f"Number of role names ({len(role_names)}) must match "
            f"number of role paths ({len(role_paths)})"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    role_list = ", ".join(role_names)
    logger.info(f"Creating Ansible project for {len(role_names)} role(s): {role_list}")

    # Determine deployment path
    first_role_path_obj = Path(role_paths[0])
    if base_path:
        base_path_obj = Path(base_path)
        if len(role_names) == 1:
            deployment_path = base_path_obj / "ansible" / "deployments" / role_names[0]
        else:
            deployment_path = (
                base_path_obj / "ansible" / "deployments" / "ansible-project"
            )
    else:
        # Extract ansible path from role_path:
        # <path>/ansible/roles/{role} -> <path>/ansible
        ansible_path = first_role_path_obj.parent.parent
        if len(role_names) == 1:
            deployment_path = ansible_path / "deployments" / role_names[0]
        else:
            deployment_path = ansible_path / "deployments" / "ansible-project"

    publish_dir = str(deployment_path)

    # 1. Create directory structure
    create_directory_structure(
        base_path=publish_dir,
        structure=["collections", "inventory", "roles", "playbooks"],
    )

    # 2. Copy all role directories
    for role_name, role_path in zip(role_names, role_paths, strict=True):
        destination = f"{publish_dir}/roles/{role_name}"
        logger.info(f"Copying role {role_name} from {role_path}")
        copy_role_directory(source_role_path=role_path, destination_path=destination)

    # 3. Generate wrapper playbooks for each role
    for role_name in role_names:
        generate_playbook_yaml(
            file_path=f"{publish_dir}/playbooks/run_{role_name}.yml",
            name=f"Run {role_name}",
            role_name=role_name,
        )

    # 4. Generate ansible.cfg
    generate_ansible_cfg(f"{publish_dir}/ansible.cfg")

    # 5. Generate collections/requirements.yml
    generate_collections_requirements(
        f"{publish_dir}/collections/requirements.yml", collections=collections
    )

    # 6. Generate inventory file
    generate_inventory_file(f"{publish_dir}/inventory/hosts.yml", inventory=inventory)

    # 7. Verify all required files exist
    required_files = [
        f"{publish_dir}/ansible.cfg",
        f"{publish_dir}/collections/requirements.yml",
        f"{publish_dir}/inventory/hosts.yml",
    ]
    for role_name in role_names:
        required_files.append(f"{publish_dir}/roles/{role_name}")
        required_files.append(f"{publish_dir}/playbooks/run_{role_name}.yml")

    verify_files_exist(file_paths=required_files)

    logger.info(f"Ansible project created successfully at {publish_dir}")
    return str(deployment_path.resolve())


def publish_aap(repo_url: str, branch: str) -> AAPSyncResult:
    """Connect to AAP Controller and create/update a project pointing to the given repo.

    Args:
        repo_url: Git repository URL (e.g., https://github.com/org/repo.git).
        branch: Git branch name.

    Returns:
        AAPSyncResult with sync outcome.

    Raises:
        RuntimeError: If AAP is not configured or sync fails.
    """
    logger.info(f"Syncing to AAP: repo={repo_url} branch={branch}")

    result = sync_to_aap(repository_url=repo_url, branch=branch)

    if not result.enabled:
        raise RuntimeError(
            "AAP is not configured. Set AAP_CONTROLLER_URL and related "
            "environment variables."
        )

    if result.error:
        raise RuntimeError(f"AAP sync failed: {result.error}")

    summary_lines = result.report_summary()
    for line in summary_lines:
        logger.info(line)

    return result
