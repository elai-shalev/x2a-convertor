#!/usr/bin/env python
from tools.ansible_lint import AnsibleLintTool
from tools.ansible_role_check import AnsibleRoleCheckTool

# result = AnsibleLintTool()._run("../chef-examples/ansible/nginx_multisite")
# print(result)


result = AnsibleRoleCheckTool()._run("../chef-examples/ansible/nginx_multisite")
print(result)
