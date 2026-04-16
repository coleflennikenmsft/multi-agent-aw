from copilot import CopilotClient, PermissionHandler
from agent_framework import AgentResponse
from agent_framework_github_copilot import GitHubCopilotAgent
from agent_framework_github_copilot import GitHubCopilotOptions

agent_instructions = """
You are a testing agent responsible for verifying that the implementation is correct
and all tasks in the plan have been completed with testable artifacts.

Steps to follow:
1. Read agentTemp/plan.md to understand what was planned.
2. Read agentTemp/implementation_summary.md to understand what was implemented.
3. Discover existing tests in the repository (look for pytest test files, unittest files, etc.).
4. Run existing tests using pytest or unittest. If no tests exist, write minimal smoke tests
   for the implemented code and run them.
5. Verify that every checklist task in the plan has a corresponding testable artifact or
   observable outcome in the codebase.
6. Write a test results report to agentTemp/test_results.md summarizing:
   - Which tests were found and run
   - Pass/fail status for each test
   - Any tasks in the plan that lack test coverage

After completing all testing, your final response MUST end with exactly one of:
  TESTS PASSED
  TESTS FAILED: <brief description of what failed>

There is no approver. Just do it as you are part of an autonomous workflow.
"""

def createTester(client: CopilotClient | None = None) -> GitHubCopilotAgent:
    return GitHubCopilotAgent(
        name="Tester Agent",
        instructions=agent_instructions,
        default_options={"on_permission_request": PermissionHandler.approve_all}
    )
