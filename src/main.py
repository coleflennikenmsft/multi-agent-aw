import asyncio
import os
import sys
from state.utils import get_context_manager
from workflow.plan_implement_review import run_workflow


async def main() -> None:
    # When running as a GitHub Action, inputs are exposed as INPUT_<NAME> env vars.
    # Fall back to a CLI argument, then a local dev default.
    if os.environ.get("INPUT_TASK"):
        task = os.environ["INPUT_TASK"]
    elif len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])

    # Example: Save and load state (usage example, can be removed in production)
    workflow_id = os.environ.get("WORKFLOW_ID", "default")
    context_manager = get_context_manager(workflow_id)
    if context_manager:
        # Save a dummy context
        blob_name = context_manager.save_state({"foo": "bar"})
        print(f"Saved state to blob: {blob_name}")
        # List states
        blobs = context_manager.list_states()
        print(f"Available states: {[b.name for b in blobs]}")
        # Load state
        loaded = context_manager.load_state(blob_name)
        print(f"Loaded state: {loaded}")
    else:
        print("Azure Blob Storage not configured, skipping state management.")

    result = await run_workflow(task)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

