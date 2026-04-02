import asyncio
import os
import sys
from typing_extensions import Never

# Ensure src/ is on the path when running this file directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from agents.plan import createPlanner
from agents.implement import createImplementer
from agents.reviewer import createReviewer


class PlannerExecutor(Executor):
    """Runs the planner agent to produce an implementation plan, then hands off to the implementer."""

    def __init__(self) -> None:
        super().__init__(id="planner")

    @handler
    async def handle(self, task: str, ctx: WorkflowContext[str]) -> None:
        print("[Planner] Creating implementation plan...")
        async with createPlanner() as agent:
            stream = agent.run(task, stream=True)
            print("[Planner] ", end="", flush=True)
            async for chunk in stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
            print()
            response = await stream.get_final_response()
        print("[Planner] Plan created.")
        await ctx.send_message(response.text)


class ImplementerExecutor(Executor):
    """Executes the tasks in the plan, or addresses reviewer feedback if looping."""

    def __init__(self) -> None:
        super().__init__(id="implementer")

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
        print("[Implementer] Executing tasks from plan...")
        async with createImplementer() as agent:
            stream = agent.run(message, stream=True)
            print("[Implementer] ", end="", flush=True)
            async for chunk in stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
            print()
            response = await stream.get_final_response()
        print("[Implementer] Implementation complete.")
        await ctx.send_message(response.text)


class ReviewerExecutor(Executor):
    """Reviews the implementation against the plan.

    - If the implementation is incomplete, sends the feedback back to the
      implementer (looping) via ctx.send_message.
    - If the implementation is approved, ends the workflow via ctx.yield_output.
    """

    def __init__(self) -> None:
        super().__init__(id="reviewer")

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str, str]) -> None:
        print("[Reviewer] Reviewing implementation...")
        async with createReviewer() as agent:
            stream = agent.run(message, stream=True)
            print("[Reviewer] ", end="", flush=True)
            async for chunk in stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
            print()
            response = await stream.get_final_response()
        review_text = response.text
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


def build_workflow():
    """Construct and return the plan → implement → review workflow.

    The workflow DAG is:
        planner → implementer → reviewer
                       ↑            |
                       └────────────┘  (loop when reviewer finds issues)
    """
    planner = PlannerExecutor()
    implementer = ImplementerExecutor()
    reviewer = ReviewerExecutor()

    workflow = (
        WorkflowBuilder(start_executor=planner)
        .add_edge(planner, implementer)
        .add_edge(implementer, reviewer)
        .add_edge(reviewer, implementer)   # loop back when incomplete
        .build()
    )
    return workflow


async def run_workflow(task: str) -> str:
    """Run the plan-implement-review workflow for the given task description.

    Returns the reviewer's final approval message.
    """
    workflow = build_workflow()

    print("\n=== Starting Plan-Implement-Review Workflow ===")
    print(f"Task: {task}\n")

    result = ""
    async for event in workflow.run(task, stream=True):
        if event.type == "output" and isinstance(event.data, str):
            result = event.data

    print("\n=== Workflow Complete ===")
    return result


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "Implement the feature described in the spec"
    asyncio.run(run_workflow(task))
