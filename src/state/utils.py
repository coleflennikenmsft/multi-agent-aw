"""Utility functions for state management integration."""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def is_state_management_available() -> bool:
    """Check if Azure Blob Storage is configured and available.

    Returns:
        True if state management can be used, False otherwise
    """
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    
    return bool(connection_string or account_name)


def create_state_checkpoint(
    workflow_id: str,
    step_name: str,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """Create a state checkpoint for a workflow step.

    This is a helper function that gracefully handles the case where
    Azure Blob Storage is not configured.

    Args:
        workflow_id: Workflow identifier
        step_name: Name of the current step
        data: Data to checkpoint
        metadata: Optional metadata to include

    Returns:
        Blob name if checkpoint was saved, None if state management is unavailable

    Example:
        checkpoint = create_state_checkpoint(
            workflow_id="workflow-123",
            step_name="planner",
            data={"plan": plan_text},
            metadata={"agent": "planner"}
        )
    """
    if not is_state_management_available():
        logger.debug("State management not available, skipping checkpoint")
        return None

    try:
        from state.context_manager import save_state
        
        context = {
            "step_name": step_name,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "metadata": metadata or {},
        }
        
        blob_name = save_state(workflow_id, context)
        logger.info(f"Created checkpoint: {blob_name}")
        return blob_name
    except Exception as e:
        logger.error(f"Failed to create checkpoint: {e}")
        return None


def restore_latest_checkpoint(workflow_id: str) -> Optional[Dict[str, Any]]:
    """Restore the latest checkpoint for a workflow.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Context dictionary or None if not available

    Example:
        context = restore_latest_checkpoint("workflow-123")
        if context:
            step_name = context["step_name"]
            data = context["data"]
    """
    if not is_state_management_available():
        logger.debug("State management not available")
        return None

    try:
        from state.context_manager import ContextManager
        
        manager = ContextManager()
        context = manager.get_latest_state(workflow_id)
        
        if context:
            logger.info(f"Restored checkpoint for workflow {workflow_id}")
        else:
            logger.info(f"No checkpoints found for workflow {workflow_id}")
            
        return context
    except Exception as e:
        logger.error(f"Failed to restore checkpoint: {e}")
        return None


def cleanup_old_checkpoints(
    workflow_id: str,
    keep_latest: int = 5
) -> int:
    """Clean up old checkpoints, keeping only the most recent ones.

    Args:
        workflow_id: Workflow identifier
        keep_latest: Number of most recent checkpoints to keep

    Returns:
        Number of checkpoints deleted

    Example:
        deleted = cleanup_old_checkpoints("workflow-123", keep_latest=3)
        print(f"Deleted {deleted} old checkpoints")
    """
    if not is_state_management_available():
        logger.debug("State management not available")
        return 0

    try:
        from state.context_manager import ContextManager, delete_state
        
        manager = ContextManager()
        states = manager.list_states(workflow_id)
        
        if len(states) <= keep_latest:
            logger.info(f"No cleanup needed, only {len(states)} checkpoints exist")
            return 0
        
        # Sort by last_modified descending and keep the most recent
        states_sorted = sorted(states, key=lambda s: s["last_modified"], reverse=True)
        to_delete = states_sorted[keep_latest:]
        
        deleted_count = 0
        for state in to_delete:
            try:
                delete_state(state["name"])
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {state['name']}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old checkpoints")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup checkpoints: {e}")
        return 0
