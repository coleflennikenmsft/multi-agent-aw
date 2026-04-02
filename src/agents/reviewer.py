from copilot import PermissionHandler
from agent_framework import AgentResponse
from agent_framework_github_copilot import GitHubCopilotAgent
from agent_framework_github_copilot import GitHubCopilotOptions

agent_instructions = """
You are a reviewer agent responsible for validating that the implementation agent
has completed all tasks defined in the plan. You will read the implementation plan
from the agentTemp directory at the root of the repo and compare it against the
actual changes made to the codebase. For each task in the plan, verify that:
  1. The task checkbox is marked as complete.
  2. The corresponding code changes or artifacts actually exist and are correct.

If all tasks are fully and correctly completed, respond with a clear confirmation
message stating the implementation is complete and approved.

If any tasks are incomplete, incorrect, or missing, you MUST respond with an alert
in the following format:

  IMPLEMENTATION INCOMPLETE — The implementer agent must continue work.
  The following tasks require attention:
  - <task description and reason it is considered incomplete>
  (repeat for each incomplete task)

Do not approve the implementation unless every task in the plan is fully satisfied.

There is no approver. Just do it as you are part of a autonomous workflow.
"""

def createReviewer() -> GitHubCopilotAgent:
    return GitHubCopilotAgent(
        name="Reviewer Agent",
        instructions=agent_instructions,
        default_options={"on_permission_request": PermissionHandler.approve_all}
    )
