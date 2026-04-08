import asyncio
import os
import sys
from typing_extensions import Never

# Ensure src/ is on the path when running this file directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot import CopilotClient
from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from agents.plan import createPlanner
from agents.implement import createImplementer
from agents.testing import createTester
from agents.reviewer import createReviewer


def _make_client() -> CopilotClient:
    return CopilotClient()

# When running inside GitHub Actions, os.environ["GITHUB_ACTIONS"] == "true".
_IN_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


def _group(title: str) -> None:
    if _IN_ACTIONS:
        print(f"::group::{title}", flush=True)
    else:
        print(f"\n=== {title} ===", flush=True)


def _endgroup() -> None:
    if _IN_ACTIONS:
        print("::endgroup::", flush=True)


async def _stream_agent(agent, message: str, label: str) -> str:
    """Run *agent* with *message*, printing thoughts and text to the log.

    Returns the final response text.
    """
    _group(f"{label} — thoughts & output")
    buffer: list[str] = []
    stream = agent.run(message, stream=True)
    async for chunk in stream:
        # Thoughts / reasoning (available when the model exposes them)
        thoughts = getattr(chunk, "thoughts", None)
        if thoughts:
            for line in thoughts.splitlines():
                print(f"[{label}][thought] {line}", flush=True)

        # Tool calls / results the agent is making (via chunk.contents)
        for content in chunk.contents:
            if content.type == "function_call":
                print(f"[{label}][tool] {content.name}", flush=True)
            elif content.type == "function_result":
                print(f"[{label}][tool_result] call_id={content.call_id}", flush=True)

        # Streamed text output — collect and emit line-by-line so Actions
        # renders each line as a separate log entry instead of one giant blob.
        if chunk.text:
            buffer.append(chunk.text)
            # Flush complete lines immediately
            combined = "".join(buffer)
            lines = combined.split("\n")
            for line in lines[:-1]:
                print(f"[{label}] {line}", flush=True)
            buffer = [lines[-1]]  # keep the incomplete trailing fragment

    # Flush any remaining text
    if buffer:
        remainder = "".join(buffer).strip()
        if remainder:
            print(f"[{label}] {remainder}", flush=True)

    _endgroup()
    response = await stream.get_final_response()
    return response.text


class PlannerExecutor(Executor):
    """Runs the planner agent to produce an implementation plan, then hands off to the implementer."""

    def __init__(self, client: CopilotClient) -> None:
        super().__init__(id="planner")
        self._client = client

    @handler
    async def handle(self, task: str, ctx: WorkflowContext[str]) -> None:
        print("[Planner] Creating implementation plan...")
        async with createPlanner(self._client) as agent:
            result = await _stream_agent(agent, task, "Planner")
        print("[Planner] Plan created.")
        await ctx.send_message(result)


class ImplementerExecutor(Executor):
    """Executes the tasks in the plan, or addresses reviewer feedback if looping."""

    def __init__(self, client: CopilotClient) -> None:
        super().__init__(id="implementer")
        self._client = client

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
        print("[Implementer] Executing tasks from plan...")
        async with createImplementer(self._client) as agent:
            result = await _stream_agent(agent, message, "Implementer")
        print("[Implementer] Implementation complete.")
        await ctx.send_message(result)


class TesterExecutor(Executor):
    """Runs the test suite against the implementation.

    - If tests fail, sends failure details back to the implementer (looping).
    - If tests pass, forwards the result to the reviewer.
    """

    def __init__(self, client: CopilotClient) -> None:
        super().__init__(id="tester")
        self._client = client

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
        print("[Tester] Running tests against implementation...")
        async with createTester(self._client) as agent:
            test_text = await _stream_agent(agent, message, "Tester")
        print("[Tester] Testing complete.")

        if "TESTS FAILED" in test_text:
            print("[Tester] Test failures found — sending back to implementer.")
            await ctx.send_message(
                "The tester agent found failures. Please address the following "
                "and fix the implementation:\n\n" + test_text
            )
        else:
            print("[Tester] All tests passed — forwarding to reviewer.")
            await ctx.send_message(test_text)


class ReviewerExecutor(Executor):
    """Reviews the implementation against the plan.

    - If the implementation is incomplete, sends the feedback back to the
      implementer (looping) via ctx.send_message.
    - If the implementation is approved, ends the workflow via ctx.yield_output.
    """

    def __init__(self, client: CopilotClient) -> None:
        super().__init__(id="reviewer")
        self._client = client

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str, str]) -> None:
        print("[Reviewer] Reviewing implementation...")
        async with createReviewer(self._client) as agent:
            review_text = await _stream_agent(agent, message, "Reviewer")
        print("[Reviewer] Review complete.")

        if "IMPLEMENTATION INCOMPLETE" in review_text:
            print("[Reviewer] Issues found — sending back to implementer.")
            await ctx.send_message(
                "The reviewer found incomplete tasks. Please address the following "
                "and continue implementing:\n\n" + review_text
            )
        else:
            print("[Reviewer] Implementation approved.")
            await ctx.yield_output(review_text)


def build_workflow(client: CopilotClient):
    """Construct and return the plan → implement → test → review workflow.

    The workflow DAG is:
        planner → implementer → tester → reviewer
                      ↑            |         |
                      └────────────┘         |  (loop when tests fail)
                      ↑                      |
                      └──────────────────────┘  (loop when reviewer finds issues)
    """
    planner = PlannerExecutor(client)
    implementer = ImplementerExecutor(client)
    tester = TesterExecutor(client)
    reviewer = ReviewerExecutor(client)

    workflow = (
        WorkflowBuilder(start_executor=planner)
        .add_edge(planner, implementer)
        .add_edge(implementer, tester)
        .add_edge(tester, implementer)    # loop back when tests fail
        .add_edge(tester, reviewer)       # forward when tests pass
        .add_edge(reviewer, implementer)  # loop back when review finds issues
        .build()
    )
    return workflow


async def run_workflow(task: str) -> str:
    """Run the plan-implement-review workflow for the given task description.

    Returns the reviewer's final approval message.
    """
    client = _make_client()
    try:
        workflow = build_workflow(client)

        print("\n=== Starting Plan-Implement-Review Workflow ===")
        print(f"Task: {task}\n")

        result = ""
        async for event in workflow.run(task, stream=True):
            if event.type == "output" and isinstance(event.data, str):
                result = event.data

        print("\n=== Workflow Complete ===")
        return result
    finally:
        await client.stop()


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "Implement the feature described in the spec"
    asyncio.run(run_workflow(task))
