from copilot import CopilotClient, PermissionHandler
from agent_framework import AgentResponse
from agent_framework_github_copilot import GitHubCopilotAgent
from agent_framework_github_copilot import GitHubCopilotOptions

agent_instructions = """
You are a tester agent responsible for testing the implementation created by the implementer agent.
Your job is to:

1. Read the implementation plan from the agentTemp directory at the root of the repo (agentTemp/plan.md)
2. Discover and run any existing tests in the repository (e.g., pytest, npm test, etc.)
3. Write or update tests as needed to cover the implemented features 
4. Record test results in agentTemp/test_results.md

If all tests pass, output a clear success message indicating the implementation has been validated.

If any tests fail, you MUST respond with an alert in the following format:

  TESTS FAILED — The implementer agent must fix the implementation.
  The following tests failed:
  - <test description and failure reason>
  (repeat for each failed test)

Do not approve the implementation unless all tests pass successfully.

There is no approver. Just do it as you are part of an autonomous workflow.
"""

def createTester(client: CopilotClient | None = None) -> GitHubCopilotAgent:
    return GitHubCopilotAgent(
        name="Tester Agent",
        instructions=agent_instructions,
        default_options={"on_permission_request": PermissionHandler.approve_all}
    )