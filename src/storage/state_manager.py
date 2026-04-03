"""State management for workflow persistence using Azure Blob Storage."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from .azure_blob_client import AzureBlobClient


logger = logging.getLogger(__name__)


class StateManager:
    """Manages workflow state persistence using Azure Blob Storage."""

    def __init__(self, container_name: str = "workflow-states"):
        """Initialize the state manager.
        
        Args:
            container_name: Name of the Azure blob container for state storage.
        """
        self.blob_client = AzureBlobClient(container_name)
    
    def _generate_blob_name(self, workflow_id: str) -> str:
        """Generate blob name for a workflow state.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            Blob name for storing the workflow state.
        """
        # Sanitize workflow_id for blob naming
        safe_id = "".join(c for c in workflow_id if c.isalnum() or c in "-_.")
        return f"{safe_id}.json"
    
    def save_state(self, workflow_id: str, state_data: dict) -> bool:
        """Save workflow state to Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            state_data: Dictionary containing the workflow state data.
            
        Returns:
            True if state saved successfully, False otherwise.
        """
        try:
            # Add timestamp and workflow_id to state data
            enriched_state = {
                "workflow_id": workflow_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "saved_at": datetime.now(timezone.utc).isoformat(),
                **state_data
            }
            
            # Serialize to JSON
            json_data = json.dumps(enriched_state, indent=2)
            blob_data = json_data.encode('utf-8')
            
            # Create metadata
            metadata = {
                "workflow_id": workflow_id,
                "timestamp": enriched_state["timestamp"],
                "content_type": "application/json"
            }
            
            # Upload to blob storage
            blob_name = self._generate_blob_name(workflow_id)
            success = self.blob_client.upload_blob(
                blob_name=blob_name,
                data=blob_data,
                metadata=metadata
            )
            
            if success:
                logger.info(f"State saved for workflow: {workflow_id}")
            else:
                logger.error(f"Failed to save state for workflow: {workflow_id}")
                
            return success
            
        except json.JSONEncodeError as e:
            logger.error(f"JSON serialization error for workflow '{workflow_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving state for workflow '{workflow_id}': {e}")
            return False
    
    def load_state(self, workflow_id: str) -> Optional[dict]:
        """Load workflow state from Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            Dictionary containing the workflow state data, or None if not found/error.
        """
        try:
            blob_name = self._generate_blob_name(workflow_id)
            blob_data = self.blob_client.download_blob(blob_name)
            
            if blob_data is None:
                logger.info(f"No state found for workflow: {workflow_id}")
                return None
            
            # Deserialize from JSON
            json_data = blob_data.decode('utf-8')
            state_data = json.loads(json_data)
            
            logger.info(f"State loaded for workflow: {workflow_id}")
            return state_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON deserialization error for workflow '{workflow_id}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading state for workflow '{workflow_id}': {e}")
            return None
    
    def delete_state(self, workflow_id: str) -> bool:
        """Delete workflow state from Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            True if state deleted successfully, False otherwise.
        """
        try:
            blob_name = self._generate_blob_name(workflow_id)
            success = self.blob_client.delete_blob(blob_name)
            
            if success:
                logger.info(f"State deleted for workflow: {workflow_id}")
            else:
                logger.error(f"Failed to delete state for workflow: {workflow_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Unexpected error deleting state for workflow '{workflow_id}': {e}")
            return False
    
    def list_states(self) -> list[str]:
        """List all stored workflow states.
        
        Returns:
            List of workflow IDs that have stored states.
        """
        try:
            blob_names = self.blob_client.list_blobs(name_starts_with="")
            
            # Extract workflow IDs from blob names (remove .json extension)
            workflow_ids = []
            for blob_name in blob_names:
                if blob_name.endswith('.json'):
                    workflow_id = blob_name[:-5]  # Remove .json extension
                    workflow_ids.append(workflow_id)
            
            logger.info(f"Found {len(workflow_ids)} stored workflow states")
            return workflow_ids
            
        except Exception as e:
            logger.error(f"Unexpected error listing workflow states: {e}")
            return []
    
    def get_state_metadata(self, workflow_id: str) -> Optional[dict]:
        """Get metadata for a workflow state.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            Dictionary containing state metadata, or None if not found/error.
        """
        try:
            blob_name = self._generate_blob_name(workflow_id)
            metadata = self.blob_client.get_blob_metadata(blob_name)
            
            if metadata:
                logger.info(f"Metadata retrieved for workflow: {workflow_id}")
            else:
                logger.info(f"No metadata found for workflow: {workflow_id}")
                
            return metadata
            
        except Exception as e:
            logger.error(f"Unexpected error getting metadata for workflow '{workflow_id}': {e}")
            return None
    
    def save_checkpoint(self, workflow_id: str, executor_id: str, context: dict, status: str = "paused") -> bool:
        """Save a workflow checkpoint with executor context.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            executor_id: ID of the current executor.
            context: Current workflow context (task, plan, messages, etc.).
            status: Current workflow status (paused, completed, failed).
            
        Returns:
            True if checkpoint saved successfully, False otherwise.
        """
        try:
            # Get GitHub context if available
            github_context = {
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "repository": os.environ.get("GITHUB_REPOSITORY"),
                "actor": os.environ.get("GITHUB_ACTOR"),
                "workflow": os.environ.get("GITHUB_WORKFLOW")
            }
            
            checkpoint_data = {
                "executor_id": executor_id,
                "status": status,
                "context": context,
                "metadata": {
                    "github": github_context,
                    "checkpoint_version": "1.0"
                }
            }
            
            return self.save_state(workflow_id, checkpoint_data)
            
        except Exception as e:
            logger.error(f"Unexpected error saving checkpoint for workflow '{workflow_id}': {e}")
            return False
    
    def load_checkpoint(self, workflow_id: str) -> Optional[dict]:
        """Load a workflow checkpoint.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            Dictionary containing checkpoint data, or None if not found/error.
        """
        return self.load_state(workflow_id)