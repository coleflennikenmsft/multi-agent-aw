"""Utility functions for workflow state management."""

import logging
from typing import Dict, Any, Optional, List
from .context_manager import get_context_manager


logger = logging.getLogger(__name__)


async def create_checkpoint(workflow_id: str, phase: str, data: Dict[str, Any]) -> Optional[str]:
    """Create a checkpoint during workflow execution.
    
    Args:
        workflow_id: Unique workflow identifier
        phase: Current phase of the workflow (e.g., 'planning', 'implementation', 'review')
        data: Additional context data to store
        
    Returns:
        State key if successful, None if failed
    """
    context_manager = get_context_manager()
    if not context_manager.is_enabled():
        return None
        
    checkpoint_context = {
        "workflow_id": workflow_id,
        "phase": phase,
        **data
    }
    
    state_id = f"checkpoint_{phase}"
    return await context_manager.save_state(workflow_id, checkpoint_context, state_id)


async def get_latest_checkpoint(workflow_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent checkpoint for a workflow.
    
    Args:
        workflow_id: Workflow identifier
        
    Returns:
        Latest checkpoint context or None if not found
    """
    context_manager = get_context_manager()
    if not context_manager.is_enabled():
        return None
        
    states = await context_manager.list_states(workflow_id)
    if not states:
        return None
        
    # Sort by timestamp (newest first)
    states.sort(reverse=True)
    latest_state = states[0]
    
    return await context_manager.load_state(latest_state)


async def restore_workflow_from_checkpoint(workflow_id: str, checkpoint_phase: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Restore workflow state from a specific checkpoint.
    
    Args:
        workflow_id: Workflow identifier
        checkpoint_phase: Specific phase to restore from, or None for latest
        
    Returns:
        Restored context or None if not found
    """
    context_manager = get_context_manager()
    if not context_manager.is_enabled():
        return None
        
    if checkpoint_phase:
        # Look for specific checkpoint
        state_key = f"{workflow_id}/checkpoint_{checkpoint_phase}.state"
        context = await context_manager.load_state(state_key)
        if context:
            logger.info(f"Restored workflow from checkpoint: {checkpoint_phase}")
            return context
    
    # Fall back to latest checkpoint
    context = await get_latest_checkpoint(workflow_id)
    if context:
        logger.info(f"Restored workflow from latest checkpoint")
    
    return context


async def cleanup_workflow_checkpoints(workflow_id: str, keep_count: int = 5) -> int:
    """Clean up old checkpoints for a workflow.
    
    Args:
        workflow_id: Workflow identifier
        keep_count: Number of recent checkpoints to keep
        
    Returns:
        Number of checkpoints cleaned up
    """
    context_manager = get_context_manager()
    if not context_manager.is_enabled():
        return 0
        
    return await context_manager.cleanup_old_states(workflow_id, keep_count)


def is_state_management_available() -> bool:
    """Check if state management is configured and available.
    
    Returns:
        True if state management is available
    """
    context_manager = get_context_manager()
    return context_manager.is_enabled()


async def get_workflow_history(workflow_id: str) -> List[Dict[str, Any]]:
    """Get the full history of checkpoints for a workflow.
    
    Args:
        workflow_id: Workflow identifier
        
    Returns:
        List of checkpoint contexts, sorted by timestamp (newest first)
    """
    context_manager = get_context_manager()
    if not context_manager.is_enabled():
        return []
        
    states = await context_manager.list_states(workflow_id)
    if not states:
        return []
        
    # Sort by timestamp (newest first)
    states.sort(reverse=True)
    
    history = []
    for state_key in states:
        context = await context_manager.load_state(state_key)
        if context:
            history.append(context)
    
    return history