import asyncio
import os
import sys
import logging
import uuid

from workflow.plan_implement_review import run_workflow
from state.context_manager import get_context_manager, save_workflow_state, load_workflow_state

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main() -> None:
    # When running as a GitHub Action, inputs are exposed as INPUT_<NAME> env vars.
    # Fall back to a CLI argument, then a local dev default.
    if os.environ.get("INPUT_TASK"):
        task = os.environ["INPUT_TASK"]
    elif len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])

    # Generate workflow ID for state management
    workflow_id = os.environ.get("GITHUB_RUN_ID", str(uuid.uuid4()))
    
    # Initialize context manager and check if state management is available
    context_manager = get_context_manager()
    if context_manager.is_enabled():
        logging.info(f"State management enabled for workflow: {workflow_id}")
        
        # Create initial checkpoint with task information
        initial_context = {
            "workflow_id": workflow_id,
            "task": task,
            "phase": "started",
            "timestamp": None  # Will be set by context manager
        }
        
        checkpoint_key = await save_workflow_state(workflow_id, initial_context, "initial")
        if checkpoint_key:
            logging.info(f"Created initial checkpoint: {checkpoint_key}")
    else:
        logging.info("State management disabled - no Azure Storage configuration")

    result = await run_workflow(task)
    
    # Save final state if state management is enabled
    if context_manager.is_enabled():
        final_context = {
            "workflow_id": workflow_id,
            "task": task,
            "phase": "completed",
            "result": result
        }
        
        final_key = await save_workflow_state(workflow_id, final_context, "final")
        if final_key:
            logging.info(f"Created final checkpoint: {final_key}")
    
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
