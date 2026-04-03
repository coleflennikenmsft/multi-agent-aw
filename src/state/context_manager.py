"""Context manager for workflow state serialization and persistence."""

import json
import pickle
import gzip
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Union
from .blob_client import BlobClientWrapper, create_blob_client_from_env


logger = logging.getLogger(__name__)


class ContextManager:
    """Manages serialization, persistence, and retrieval of workflow context state."""
    
    def __init__(self, blob_client: Optional[BlobClientWrapper] = None):
        """Initialize the context manager.
        
        Args:
            blob_client: Optional blob client instance. If None, will try to create from environment.
        """
        self.blob_client = blob_client or create_blob_client_from_env()
        self._enabled = self.blob_client is not None
        
        if not self._enabled:
            logger.warning("Context manager disabled - no Azure Storage configuration found")
    
    def is_enabled(self) -> bool:
        """Check if context management is enabled (blob client available)."""
        return self._enabled
    
    def _generate_state_key(self, workflow_id: str, timestamp: Optional[datetime] = None) -> str:
        """Generate a unique key for storing state.
        
        Args:
            workflow_id: Unique identifier for the workflow
            timestamp: Optional timestamp, defaults to current time
            
        Returns:
            Unique state key
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Format: workflow_id/YYYY-MM-DD/HH-MM-SS-ffffff.state
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H-%M-%S-%f")
        return f"{workflow_id}/{date_str}/{time_str}.state"
    
    def _serialize_context(self, context: Dict[str, Any], use_json: bool = True) -> bytes:
        """Serialize context to bytes.
        
        Args:
            context: Context dictionary to serialize
            use_json: If True, use JSON serialization; otherwise use pickle
            
        Returns:
            Serialized context as compressed bytes
        """
        try:
            if use_json:
                # Add metadata
                serialized_data = {
                    "version": "1.0",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "serialization": "json",
                    "context": context
                }
                json_bytes = json.dumps(serialized_data, default=str, ensure_ascii=False).encode('utf-8')
                # Compress with gzip
                return gzip.compress(json_bytes)
            else:
                # Use pickle for complex objects
                serialized_data = {
                    "version": "1.0",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "serialization": "pickle",
                    "context": context
                }
                pickle_bytes = pickle.dumps(serialized_data)
                return gzip.compress(pickle_bytes)
                
        except Exception as e:
            logger.error(f"Failed to serialize context: {e}")
            raise
    
    def _deserialize_context(self, data: bytes) -> Dict[str, Any]:
        """Deserialize context from bytes.
        
        Args:
            data: Serialized and compressed context data
            
        Returns:
            Deserialized context dictionary
        """
        try:
            # Decompress
            decompressed_data = gzip.decompress(data)
            
            # Try JSON first
            try:
                json_data = json.loads(decompressed_data.decode('utf-8'))
                if json_data.get("serialization") == "json":
                    return json_data["context"]
                else:
                    # Fall back to pickle if metadata indicates it
                    pickle_data = pickle.loads(decompressed_data)
                    return pickle_data["context"]
            except json.JSONDecodeError:
                # Try pickle
                pickle_data = pickle.loads(decompressed_data)
                return pickle_data["context"]
                
        except Exception as e:
            logger.error(f"Failed to deserialize context: {e}")
            raise
    
    async def save_state(self, workflow_id: str, context: Dict[str, Any], 
                        state_id: Optional[str] = None, use_json: bool = True) -> Optional[str]:
        """Save workflow context state to Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow
            context: Context dictionary to save
            state_id: Optional custom state identifier
            use_json: If True, use JSON serialization; otherwise use pickle
            
        Returns:
            State key if successful, None if failed or disabled
        """
        if not self._enabled:
            logger.warning("Cannot save state - context manager disabled")
            return None
            
        try:
            # Generate state key
            if state_id:
                state_key = f"{workflow_id}/{state_id}.state"
            else:
                state_key = self._generate_state_key(workflow_id)
            
            # Serialize context
            serialized_data = self._serialize_context(context, use_json)
            
            # Upload to blob storage
            success = self.blob_client.upload_blob(state_key, serialized_data)
            
            if success:
                logger.info(f"Saved workflow state: {state_key}")
                return state_key
            else:
                logger.error(f"Failed to save workflow state: {state_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving state for workflow {workflow_id}: {e}")
            return None
    
    async def load_state(self, state_key: str) -> Optional[Dict[str, Any]]:
        """Load workflow context state from Azure Blob Storage.
        
        Args:
            state_key: State key returned from save_state
            
        Returns:
            Context dictionary if successful, None if failed or not found
        """
        if not self._enabled:
            logger.warning("Cannot load state - context manager disabled")
            return None
            
        try:
            # Download from blob storage
            data = self.blob_client.download_blob(state_key)
            
            if data is None:
                logger.warning(f"State not found: {state_key}")
                return None
            
            # Deserialize context
            context = self._deserialize_context(data)
            logger.info(f"Loaded workflow state: {state_key}")
            return context
            
        except Exception as e:
            logger.error(f"Error loading state {state_key}: {e}")
            return None
    
    async def list_states(self, workflow_id: Optional[str] = None) -> List[str]:
        """List available saved states.
        
        Args:
            workflow_id: Optional workflow ID to filter by
            
        Returns:
            List of state keys
        """
        if not self._enabled:
            logger.warning("Cannot list states - context manager disabled")
            return []
            
        try:
            prefix = f"{workflow_id}/" if workflow_id else None
            blob_names = self.blob_client.list_blobs(prefix=prefix)
            
            # Filter to only .state files
            state_keys = [name for name in blob_names if name.endswith('.state')]
            logger.info(f"Found {len(state_keys)} saved states")
            return state_keys
            
        except Exception as e:
            logger.error(f"Error listing states: {e}")
            return []
    
    async def delete_state(self, state_key: str) -> bool:
        """Delete a saved state.
        
        Args:
            state_key: State key to delete
            
        Returns:
            True if deletion successful or state didn't exist
        """
        if not self._enabled:
            logger.warning("Cannot delete state - context manager disabled")
            return False
            
        try:
            success = self.blob_client.delete_blob(state_key)
            if success:
                logger.info(f"Deleted workflow state: {state_key}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting state {state_key}: {e}")
            return False
    
    async def cleanup_old_states(self, workflow_id: str, keep_count: int = 10) -> int:
        """Clean up old states, keeping only the most recent ones.
        
        Args:
            workflow_id: Workflow ID to clean up
            keep_count: Number of most recent states to keep
            
        Returns:
            Number of states deleted
        """
        if not self._enabled:
            logger.warning("Cannot cleanup states - context manager disabled")
            return 0
            
        try:
            states = await self.list_states(workflow_id)
            
            if len(states) <= keep_count:
                logger.info(f"No cleanup needed - {len(states)} states (keeping {keep_count})")
                return 0
            
            # Sort by timestamp (newest first)
            states.sort(reverse=True)
            
            # Delete older states
            deleted_count = 0
            for state_key in states[keep_count:]:
                if await self.delete_state(state_key):
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old states for workflow {workflow_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up states for workflow {workflow_id}: {e}")
            return 0


# Global context manager instance
_context_manager = None


def get_context_manager() -> ContextManager:
    """Get the global context manager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


async def save_workflow_state(workflow_id: str, context: Dict[str, Any], 
                             state_id: Optional[str] = None) -> Optional[str]:
    """Convenience function to save workflow state.
    
    Args:
        workflow_id: Unique identifier for the workflow
        context: Context dictionary to save
        state_id: Optional custom state identifier
        
    Returns:
        State key if successful, None if failed
    """
    manager = get_context_manager()
    return await manager.save_state(workflow_id, context, state_id)


async def load_workflow_state(state_key: str) -> Optional[Dict[str, Any]]:
    """Convenience function to load workflow state.
    
    Args:
        state_key: State key returned from save_workflow_state
        
    Returns:
        Context dictionary if successful, None if failed
    """
    manager = get_context_manager()
    return await manager.load_state(state_key)


async def list_workflow_states(workflow_id: Optional[str] = None) -> List[str]:
    """Convenience function to list workflow states.
    
    Args:
        workflow_id: Optional workflow ID to filter by
        
    Returns:
        List of state keys
    """
    manager = get_context_manager()
    return await manager.list_states(workflow_id)