# Publisher Workflow Documentation

This document describes the publisher workflow for publishing Ansible roles to GitHub using GitOps approach.

## Overview

The publisher workflow (`src/publishers/publish.py`) automates the process of:

1. Finding the ansible code needed to upload
2. Generating directory structure for PR
3. Adding the ansible code to that directory in the specific tree (roles, templates etc)
4. Creating the PR via the tool

The workflow uses a LangGraph react agent that autonomously decides which tools to use based on the task description.

## Workflow Steps

### 1. Find Ansible Code

**Purpose:** Locate and validate the Ansible role/module that needs to be published.

**Actions:**

- Use file system tools (`list_directory`, `file_search`, `read_file`) to locate the ansible code
- Verify the role path exists and contains valid Ansible role structure
- Identify all files and directories that need to be included

**Tools Used:**

- `FileSearchTool`: Search for files in the role directory
- `ListDirectoryTool`: List directory contents to verify role structure
- `ReadFileTool`: Read files to validate role contents

### 2. Generate Directory Structure for PR

**Purpose:** Create the GitOps repository structure where the ansible code will be organized.

**Actions:**

- Create directories for roles, playbooks, and AAP configs
- Set up the proper tree structure (roles/, templates/, etc.)

**Tool Used:** `CreateDirectoryStructureTool`

**Parameters:**

- `base_path`: Base path where directories should be created
- `structure`: List of directory paths to create

### 3. Add Ansible Code to Directory

**Purpose:** Copy the ansible code to the repository structure in the correct tree.

**Actions:**

- Copy the role directory to the new location
- Preserve the complete role structure (tasks/, handlers/, templates/, etc.)
- Ensure all ansible code is properly organized

**Tool Used:** `CopyRoleDirectoryTool`

**Parameters:**

- `source_role_path`: Source path to the Ansible role directory
- `destination_path`: Destination path where the role should be copied

### 4. Create Pull Request

**Purpose:** Create a PR with all the changes for review.

**Actions:**

- Create a PR from the feature branch to the base branch
- Include a clear title and description

**Tool Used:** `GitHubCreatePRTool`

**Parameters:**

- `repository_url`: GitHub repository URL
- `title`: PR title
- `body`: PR description/body
- `head`: Branch name containing the changes (source branch)
- `base`: Branch name to merge into (target branch, default: "main")

**Environment Variables:**

- `GITHUB_TOKEN`: GitHub personal access token for authentication (required)

## State Structure

The `PublishState` TypedDict contains:

```python
{
    "user_message": str,
    "path": str,
    "role": AnsibleModule,
    "role_path": str,              # Path to role directory
    "github_repository_url": str,  # GitHub repo URL
    "github_branch": str,          # Branch to push to
    "job_template_name": str,     # Generated job template name
    "job_template_created": bool, # Whether template was created
    "publish_output": str,        # Final output message
    "failed": bool,               # Whether workflow failed
    "failure_reason": str,        # Error message if failed
}
```

## Tools

### File System Tools

- `FileSearchTool`: Search for files in the role directory
- `ListDirectoryTool`: List directory contents to verify role structure
- `ReadFileTool`: Read files to validate role contents

### Directory Structure Tools

- `CreateDirectoryStructureTool`: Create directory structure for GitOps
  - **File:** `tools/create_directory_structure.py`
  - Creates all specified directories, creating parent directories as needed

### Role Management Tools

- `CopyRoleDirectoryTool`: Copy an entire Ansible role directory
  - **File:** `tools/copy_role_directory.py`
  - Recursively copies all files and subdirectories preserving the complete role structure

### Configuration Generation Tools (Optional)

- `GeneratePlaybookYAMLTool`: Generate a playbook YAML that uses the role
  - **File:** `tools/generate_playbook_yaml.py`
- `GenerateJobTemplateYAMLTool`: Generate AAP job template YAML configuration
  - **File:** `tools/generate_job_template_yaml.py`
- `GenerateInventoryYAMLTool`: Generate AAP inventory YAML configuration
  - **File:** `tools/generate_inventory_yaml.py`

### GitHub Tools

- `GitHubCreatePRTool`: Create a Pull Request in GitHub
  - **File:** `tools/github_create_pr.py`
  - Creates a PR from a branch to the base branch in a GitHub repository
  - Requires `GITHUB_TOKEN` environment variable for authentication

## Usage

```python
from src.publishers.publish import publish_role

# Publish a role
result = publish_role(
    role_name="my_role",
    role_path="ansible/my_role",
    github_repository_url="https://github.com/your-org/ansible-roles.git",
    github_branch="main"
)

if result["failed"]:
    print(f"Failed: {result['failure_reason']}")
else:
    print(result["publish_output"])
```

## Environment Variables Summary

### GitHub

- `GITHUB_REPOSITORY_URL`: Repository URL (passed as parameter)
- `GITHUB_BRANCH`: Branch name (passed as parameter, defaults to "main")
- `GITHUB_TOKEN`: Authentication token (required for creating PR)

## Implementation Notes

### Repository Structure

The final repository structure should look like:

```
repository/
├── roles/
│   └── {role_name}/          # Copied role directory
│       ├── tasks/
│       ├── handlers/
│       ├── templates/
│       ├── meta/
│       └── ...
├── playbooks/               # Optional: if playbooks are generated
│   └── {role_name}_deploy.yml
└── aap-config/              # Optional: if AAP configs are generated
    ├── job-templates/
    │   └── {role_name}_deploy.yaml
    └── inventories/
        └── webservers-production.yaml
```

### Error Handling

The workflow includes comprehensive error handling:

- Each step checks for previous failures
- Errors are logged and stored in state
- Workflow stops on first failure
- Final state includes failure reason if failed

### LangGraph React Agent

The publisher uses a LangGraph react agent pattern where:

- The LLM autonomously decides which tools to use
- Tools are called based on the task description
- The agent follows the workflow defined in the system prompt
- All operations are performed via tools, ensuring traceability
