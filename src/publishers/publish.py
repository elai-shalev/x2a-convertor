import os
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from src.model import get_model, get_runnable_config
from src.utils.logging import get_logger
from tools.aap_create_job_template import AAPCreateJobTemplateTool
from tools.aap_register_role import AAPRegisterRoleTool
from tools.github_push_role import GitHubPushRoleTool

logger = get_logger(__name__)


class SourceMetadata(BaseModel):
    """Structured output for source metadata"""

    path: str


class PublishState(TypedDict):
    user_message: str
    path: str
    role: str
    role_path: str
    github_repository_url: str
    github_branch: str
    role_registered: bool
    job_template_name: str
    job_template_created: bool
    publish_output: str
    failed: bool
    failure_reason: str


class PublishAgent:
    def __init__(self, model=None) -> None:
        self.model = model or get_model()
        self._graph = self._build_graph()
        workflow_mermaid = self._graph.get_graph().draw_mermaid()
        logger.debug("Publish workflow: " + workflow_mermaid)

        # Initialize tools
        self.github_push_tool = GitHubPushRoleTool()
        self.register_role_tool = AAPRegisterRoleTool()
        self.create_job_template_tool = AAPCreateJobTemplateTool()

    def _build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(PublishState)

        workflow.add_node(
            "push_to_github", lambda state: self._push_to_github(state)
        )
        workflow.add_node(
            "register_role", lambda state: self._register_role(state)
        )
        workflow.add_node(
            "create_job_template",
            lambda state: self._create_job_template(state),
        )

        workflow.set_entry_point("push_to_github")
        workflow.add_edge("push_to_github", "register_role")
        workflow.add_edge("register_role", "create_job_template")
        workflow.add_edge("create_job_template", END)

        return workflow.compile()

    def _push_to_github(self, state: PublishState) -> PublishState:
        """Push the role to GitHub repository."""
        if state.get("failed"):
            return state

        logger.info("PublishAgent is pushing role to GitHub")

        role = state["role"]
        role_path = state["role_path"]
        repository_url = state["github_repository_url"]
        branch = state["github_branch"]

        # Verify role path exists
        role_path_obj = Path(role_path)
        if not role_path_obj.exists():
            state["failed"] = True
            state["failure_reason"] = f"Role path does not exist: {role_path}"
            return state

        try:
            commit_message = (
                f"Add migrated Ansible role: {role}\n\n"
                "Migrated from Chef/Puppet/Salt using x2a-convertor"
            )

            result = self.github_push_tool.invoke(
                {
                    "role_path": role_path,
                    "repository_url": repository_url,
                    "branch": branch,
                    "commit_message": commit_message,
                }
            )

            # TODO: Parse the actual result when API is implemented
            if "ERROR" in result:
                state["failed"] = True
                state["failure_reason"] = f"Failed to push to GitHub: {result}"
            else:
                logger.info(
                    f"Role {role} pushed to GitHub successfully: "
                    f"{repository_url}"
                )

        except Exception as e:
            logger.error(f"Error pushing to GitHub: {e}")
            state["failed"] = True
            state["failure_reason"] = f"Failed to push to GitHub: {e}"

        return state

    def _register_role(self, state: PublishState) -> PublishState:
        """Register the role in AAP from GitHub repository."""
        if state.get("failed"):
            return state

        logger.info("PublishAgent is registering role in AAP")

        role_name = state["role"]
        repository_url = state["github_repository_url"]
        branch = state["github_branch"]
        role_path = state["role_path"]

        try:
            # Extract role path within repository
            # If role is at ansible/{role_name}, the path in repo
            # would be {role_name}
            role_path_in_repo = Path(role_path).name

            result = self.register_role_tool.invoke(
                {
                    "role_name": role_name,
                    "github_repository_url": repository_url,
                    "github_branch": branch,
                    "role_path": role_path_in_repo,
                }
            )

            # TODO: Parse the actual result when API is implemented
            if "ERROR" in result:
                state["failed"] = True
                state["failure_reason"] = (
                    f"Failed to register role in AAP: {result}"
                )
            else:
                logger.info(
                    f"Role {role_name} registered in AAP successfully from "
                    f"{repository_url}"
                )
                state["role_registered"] = True

        except Exception as e:
            logger.error(f"Error registering role in AAP: {e}")
            state["failed"] = True
            state["failure_reason"] = f"Failed to register role in AAP: {e}"

        return state

    def _create_job_template(self, state: PublishState) -> PublishState:
        """Create a job template in AAP that uses the role."""
        if state.get("failed"):
            return state

        logger.info("PublishAgent is creating job template")

        role_name = state["role"]
        job_template_name = state["job_template_name"]
        github_repo = state["github_repository_url"]

        # Determine playbook path - typically a playbook that uses the role
        # The playbook should be in the GitHub repository
        # Format: playbooks/{role_name}_deploy.yml
        playbook_path = f"playbooks/{role_name}_deploy.yml"

        # Get inventory from environment or use default
        inventory = os.getenv("AAP_INVENTORY", "Default")

        try:
            result = self.create_job_template_tool.invoke(
                {
                    "name": job_template_name,
                    "playbook_path": playbook_path,
                    "inventory": inventory,
                    "role_name": role_name,
                    "description": (
                        f"Job template for deploying {role_name} role. "
                        f"Role available in GitHub: {github_repo}. "
                        "Created by x2a-convertor."
                    ),
                }
            )

            # TODO: Parse the actual result when API is implemented
            if "ERROR" in result:
                state["failed"] = True
                state["failure_reason"] = (
                    f"Failed to create job template: {result}"
                )
            else:
                logger.info(
                    f"Job template '{job_template_name}' created successfully"
                )
                state["job_template_created"] = True
                state["publish_output"] = (
                    f"Role {role_name} published successfully:\n"
                    f"- Pushed to GitHub: {state['github_repository_url']}\n"
                    f"- Registered in AAP from GitHub\n"
                    f"- Job template created: {job_template_name}"
                )

        except Exception as e:
            logger.error(f"Error creating job template: {e}")
            state["failed"] = True
            state["failure_reason"] = f"Failed to create job template: {e}"

        return state

    def invoke(self, initial_state: PublishState) -> PublishState:
        """Invoke the publish agent"""
        result = self._graph.invoke(
            input=initial_state, config=get_runnable_config()
        )
        logger.debug(f"Publish agent result: {result}")
        return PublishState(**result)


def publish_role(
    role_name: str,
    role_path: str,
    github_repository_url: str,
    github_branch: str,
) -> PublishState:
    """Publish the role to Ansible Automation Platform"""
    logger.info(f"Publishing: {role_name}")

    # Run the publish agent
    publish_agent = PublishAgent()
    initial_state = PublishState(
        user_message="",
        path="/",
        role=role_name,
        role_path=role_path,
        github_repository_url=github_repository_url,
        github_branch=github_branch,
        role_registered=False,
        job_template_name=f"{role_name}_deploy",
        job_template_created=False,
        publish_output="",
        failed=False,
        failure_reason="",
    )
    result = publish_agent.invoke(initial_state)

    if result["failed"]:
        failure_reason = result.get("failure_reason", "Unknown error")
        logger.error(f"Publish failed for role {role_name}: {failure_reason}")
    else:
        logger.info(f"Publish completed successfully for role {role_name}!")

    return PublishState(**result)
