from copilot import CopilotClient, PermissionHandler
from agent_framework import AgentResponse
from agent_framework_github_copilot import GitHubCopilotAgent
from agent_framework_github_copilot import GitHubCopilotOptions

agent_instructions = """
You are a tester agent responsible for validating that the implementation works as intended.

Instructions:
- Read the implementation plan from agentTemp/plan.md.
- Discover and run any existing tests in the repo (e.g., pytest, npm test, etc.).
- If no tests exist for the implemented features, write or update tests as needed to cover them.
- Record all test results in agentTemp/test_results.md.
- If all tests pass, output a clear success message.
- If any tests fail, output a failure message prefixed with TESTS FAILED and list the failures so the workflow can loop back to the implementer.
- Do not approve unless all relevant tests pass.
"""

def createTester(client: CopilotClient | None = None) -> GitHubCopilotAgent:
    return GitHubCopilotAgent(
        name="Tester Agent",
        instructions=agent_instructions,
        default_options={"on_permission_request": PermissionHandler.approve_all}
    )
