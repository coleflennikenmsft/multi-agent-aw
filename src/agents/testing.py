from copilot import CopilotClient, PermissionHandler
from agent_framework import AgentResponse
from agent_framework_github_copilot import GitHubCopilotAgent
from agent_framework_github_copilot import GitHubCopilotOptions

agent_instructions = """
You are a testing agent responsible for validating the implemented code against the plan.
Read agentTemp/plan.md to understand what was required, and agentTemp/implementation_summary.md
to understand what was implemented.

Your testing process:
  1. Discover existing tests by looking for files matching test_*.py, *_test.py, or a tests/
     directory. Run them with: pytest -q (or python -m pytest -q) if pytest is available,
     otherwise python -m unittest discover.
  2. If no tests exist, write minimal smoke tests in agentTemp/smoke_tests.py that import and
     exercise the key artifacts described in the implementation summary. Run those tests.
  3. Verify that every checklist task in the plan has a corresponding testable artifact in
     the codebase (file exists, function/class is importable, etc.).
  4. Write a concise report to agentTemp/test_results.md that lists each test case with its
     pass/fail status and a one-line description.

Your final response line MUST be exactly one of:
  TESTS PASSED
  TESTS FAILED: <brief reason describing what failed>

Do not include any text after that final line. The workflow depends on this exact format.

There is no approver. Just do it as you are part of an autonomous workflow.
"""


def createTester(client: CopilotClient | None = None) -> GitHubCopilotAgent:
    return GitHubCopilotAgent(
        name="Tester Agent",
        instructions=agent_instructions,
        default_options={"on_permission_request": PermissionHandler.approve_all}
    )
