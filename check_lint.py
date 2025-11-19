#!/usr/bin/env python3
"""Test script to verify ansible-lint validation bug fix."""

import os
import sys

from tools.ansible_lint import AnsibleLintTool
from src.validation.validators import AnsibleLintValidator

# Change to the chef-examples directory where the ansible output is
os.chdir("../chef-examples/")

print("Testing AnsibleLintTool and AnsibleLintValidator")
print("=" * 80)

# Test 1: Direct tool call
print("\n1. Testing AnsibleLintTool._run() directly:")
print("-" * 80)
print("ansible/nginx_multisite:")
tool = AnsibleLintTool()
result_str = tool._run("./ansible/nginx_multisite", autofix=True)
print(result_str)


print("-" * 80)
print("FastAPI tutorial")
tool = AnsibleLintTool()
result_str = tool._run("./ansible/fastapi_tutorial", autofix=True)
print(result_str)
