# Publisher Workflow Documentation

This document describes the publisher workflow for pushing Ansible roles to GitHub and creating AAP job templates.

## Overview

The publisher workflow (`src/publishers/publish.py`) automates the process of:
1. Identifying the migrated Ansible role
2. Pushing the role to a GitHub repository
3. Creating a job template in Ansible Automation Platform (AAP) that uses the role

## Workflow Steps

### 1. Identify Role (`identify_role`)

**Purpose:** Identifies the Ansible role/module that was created and determines configuration.

**Actions:**
- Determines the role path: `ansible/{role_name}/`
- Gets GitHub repository URL from environment or uses default
- Gets GitHub branch from environment (defaults to "main")
- Generates job template name: `{role_name}_deploy`

**Configuration:**
- `GITHUB_REPOSITORY_URL`: GitHub repository URL (default: "https://github.com/your-org/ansible-roles.git")
- `GITHUB_BRANCH`: Branch to push to (default: "main")

### 2. Push to GitHub (`push_to_github`)

**Purpose:** Commits and pushes the role to the GitHub repository.

**Actions:**
- Verifies role path exists
- Commits role files with descriptive message
- Pushes to specified branch

**Tool Used:** `GitHubPushRoleTool`

**Environment Variables:**
- `GITHUB_TOKEN`: GitHub personal access token for authentication

**Implementation Status:** Placeholder - Git operations pending implementation

### 3. Create Job Template (`create_job_template`)

**Purpose:** Creates a job template in AAP that references the role in GitHub.

**Actions:**
- Determines playbook path: `playbooks/{role_name}_deploy.yml`
- Gets inventory from environment (default: "Default")
- Creates job template with appropriate description

**Tool Used:** `AAPCreateJobTemplateTool`

**Environment Variables:**
- `AAP_API_URL`: Base URL for AAP API
- `AAP_USERNAME`: Username for AAP authentication
- `AAP_PASSWORD`: Password for AAP authentication
- `AAP_INVENTORY`: Inventory name or ID (default: "Default")

**Implementation Status:** Placeholder - AAP API calls pending implementation

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

### GitHubPushRoleTool

**File:** `tools/github_push_role.py`

**Purpose:** Push Ansible role to GitHub repository.

**Parameters:**
- `role_path`: Local filesystem path to role directory
- `repository_url`: GitHub repository URL
- `branch`: Branch to push to (default: "main")
- `commit_message`: Commit message

**TODO:**
- Implement git initialization if needed
- Add remote if not exists
- Stage all files
- Commit with message
- Push to branch
- Handle authentication with GITHUB_TOKEN

### AAPCreateJobTemplateTool

**File:** `tools/aap_create_job_template.py`

**Purpose:** Create a job template in AAP.

**Parameters:**
- `name`: Job template name
- `playbook_path`: Path to playbook file
- `inventory`: Inventory name or ID
- `credential`: Credential name or ID (optional)
- `description`: Description for job template
- `extra_vars`: Extra variables in YAML format (optional)

**TODO:**
- Implement AAP API call to create job template
- Handle authentication
- Parse and validate API responses
- Handle errors appropriately

## Usage

```python
from src.publishers.publish import publish_role
from src.types import AnsibleModule

# Publish a role
role = AnsibleModule("my_role")
result = publish_role(role)

if result["failed"]:
    print(f"Failed: {result['failure_reason']}")
else:
    print(result["publish_output"])
```

## Environment Variables Summary

### GitHub
- `GITHUB_REPOSITORY_URL`: Repository URL (optional, has default)
- `GITHUB_BRANCH`: Branch name (optional, defaults to "main")
- `GITHUB_TOKEN`: Authentication token (required for push)

### AAP
- `AAP_API_URL`: AAP API base URL (required)
- `AAP_USERNAME`: AAP username (required)
- `AAP_PASSWORD`: AAP password (required)
- `AAP_INVENTORY`: Inventory name/ID (optional, defaults to "Default")

## Implementation Notes

### Playbook Path

The job template references a playbook at `playbooks/{role_name}_deploy.yml`. This playbook should:
- Be present in the GitHub repository
- Use the role that was pushed
- Be structured appropriately for deployment

Example playbook structure:
```yaml
---
- name: Deploy {role_name}
  hosts: all
  roles:
    - {role_name}
```

### Error Handling

The workflow includes comprehensive error handling:
- Each step checks for previous failures
- Errors are logged and stored in state
- Workflow stops on first failure
- Final state includes failure reason if failed

## Next Steps

1. **Implement GitHub Push:**
   - Use GitPython or subprocess for git operations
   - Handle authentication with GITHUB_TOKEN
   - Implement proper error handling

2. **Implement AAP Job Template Creation:**
   - Research AAP API endpoints
   - Implement HTTP client for API calls
   - Handle authentication and response parsing

3. **Generate Playbook:**
   - Optionally generate the playbook file that uses the role
   - Include it in the GitHub push

4. **Testing:**
   - Unit tests for each tool
   - Integration tests for full workflow
   - Error scenario testing

