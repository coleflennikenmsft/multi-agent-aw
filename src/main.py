import asyncio
import os
import sys

from workflow.plan_implement_review import run_workflow


async def main() -> None:
    # When running as a GitHub Action, inputs are exposed as INPUT_<NAME> env vars.
    # Fall back to a CLI argument, then a local dev default.
    if os.environ.get("INPUT_TASK"):
        task = os.environ["INPUT_TASK"]
    elif len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])

    result = await run_workflow(task)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
