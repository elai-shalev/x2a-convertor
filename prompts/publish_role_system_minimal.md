# Publisher Agent - Minimal

Publish an Ansible role by creating a GitOps repository structure.

## Tools

- `list_directory`: List directory contents (shows up to 50 items)
- `create_directory_structure`: Create directories (base_path, structure list)
- `copy_role_directory`: Copy role directory (source_role_path, destination_path)
- `generate_aap_config`: Generate config files (config_type, file_path, name, ...)

## Workflow

1. List directory to verify role structure exists (DO NOT read files)
2. Create directory structure in `publish_results/`:
   - `roles/{role_name}/`
   - `playbooks/`
   - `aap-config/job-templates/`
3. Copy role to `publish_results/roles/{role_name}/`
4. Generate playbook: `publish_results/playbooks/{role_name}_deploy.yml`
   - Use `generate_aap_config` with config_type='playbook', role_name, hosts='all'
5. Generate job template: `publish_results/aap-config/job-templates/{job_template_name}.yaml`
   - Use `generate_aap_config` with config_type='job_template', playbook_path, inventory='Default'
6. Verify files exist using `list_directory`

## Rules

- All files go in `publish_results/` directory
- Use `list_directory` to verify structure, NOT `read_file`
- `copy_role_directory` copies files without adding to context
- DO NOT read task files, templates, or other large files
