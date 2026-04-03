"""State manager for workflow state persistence using Azure Blob Storage."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import BlobClient

from .azure_blob_client import AzureBlobClient

logger = logging.getLogger(__name__)


class StateManager:
    """Manages workflow state persistence in Azure Blob Storage.
    
    Provides high-level operations for saving, loading, and managing workflow state.
    State is stored as JSON blobs with metadata for tracking.
    
    Example:
        >>> manager = StateManager()
        >>> state = {
        ...     "workflow_id": "wf_123",
        ...     "status": "paused",
        ...     "context": {"step": 2, "data": "..."}
        ... }
        >>> manager.save_state("wf_123", state)
        >>> loaded_state = manager.load_state("wf_123")
    """
    
    DEFAULT_CONTAINER = "workflow-states"
    
    def __init__(
        self,
        blob_client: Optional[AzureBlobClient] = None,
        container_name: Optional[str] = None,
    ):
        """Initialize the state manager.
        
        Args:
            blob_client: Azure Blob client instance. If not provided, a new one
                will be created using environment variables.
            container_name: Name of the container to use for state storage.
                Defaults to "workflow-states".
        """
        self._blob_client = blob_client or AzureBlobClient()
        self._container_name = container_name or self.DEFAULT_CONTAINER
        self._container = self._blob_client.get_or_create_container(self._container_name)
        logger.info(f"StateManager initialized with container: {self._container_name}")
    
    def _get_blob_name(self, workflow_id: str) -> str:
        """Generate blob name from workflow ID.
        
        Args:
            workflow_id: Unique workflow identifier.
            
        Returns:
            Blob name with .json extension.
        """
        # Sanitize workflow_id to ensure it's a valid blob name
        safe_id = workflow_id.replace("/", "_").replace("\\", "_")
        return f"{safe_id}.json"
    
    def save_state(self, workflow_id: str, state_data: dict[str, Any]) -> bool:
        """Save workflow state to Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            state_data: Dictionary containing the workflow state to save.
            
        Returns:
            True if save was successful, False otherwise.
            
        Raises:
            ValueError: If state_data cannot be serialized to JSON.
            AzureError: If blob upload fails.
        """
        blob_name = self._get_blob_name(workflow_id)
        
        try:
            # Ensure workflow_id is in the state data
            if "workflow_id" not in state_data:
                state_data["workflow_id"] = workflow_id
            
            # Add timestamp if not present
            if "timestamp" not in state_data:
                state_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Serialize state to JSON
            try:
                state_json = json.dumps(state_data, indent=2)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to serialize state data for workflow '{workflow_id}': {e}")
                raise ValueError(f"State data is not JSON serializable: {e}") from e
            
            # Upload to blob storage
            blob_client = self._container.get_blob_client(blob_name)
            
            # Set metadata
            metadata = {
                "workflow_id": workflow_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": state_data.get("status", "unknown"),
            }
            
            blob_client.upload_blob(
                state_json,
                overwrite=True,
                metadata=metadata
            )
            
            logger.info(f"State saved successfully for workflow '{workflow_id}'")
            return True
            
        except AzureError as e:
            logger.error(f"Failed to save state for workflow '{workflow_id}': {e}")
            raise
    
    def load_state(self, workflow_id: str) -> Optional[dict[str, Any]]:
        """Load workflow state from Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            Dictionary containing the workflow state, or None if not found.
            
        Raises:
            ValueError: If blob content is not valid JSON.
            AzureError: If blob download fails (except ResourceNotFoundError).
        """
        blob_name = self._get_blob_name(workflow_id)
        
        try:
            blob_client = self._container.get_blob_client(blob_name)
            
            # Download blob content
            download_stream = blob_client.download_blob()
            state_json = download_stream.readall().decode("utf-8")
            
            # Deserialize JSON
            try:
                state_data = json.loads(state_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to deserialize state for workflow '{workflow_id}': {e}")
                raise ValueError(f"Invalid JSON in state blob: {e}") from e
            
            logger.info(f"State loaded successfully for workflow '{workflow_id}'")
            return state_data
            
        except ResourceNotFoundError:
            logger.warning(f"No state found for workflow '{workflow_id}'")
            return None
        except AzureError as e:
            logger.error(f"Failed to load state for workflow '{workflow_id}': {e}")
            raise
    
    def delete_state(self, workflow_id: str) -> bool:
        """Delete workflow state from Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            True if state was deleted, False if it didn't exist.
            
        Raises:
            AzureError: If blob deletion fails (except ResourceNotFoundError).
        """
        blob_name = self._get_blob_name(workflow_id)
        
        try:
            blob_client = self._container.get_blob_client(blob_name)
            blob_client.delete_blob()
            logger.info(f"State deleted successfully for workflow '{workflow_id}'")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"No state found to delete for workflow '{workflow_id}'")
            return False
        except AzureError as e:
            logger.error(f"Failed to delete state for workflow '{workflow_id}': {e}")
            raise
    
    def list_states(self) -> list[str]:
        """List all stored workflow state IDs.
        
        Returns:
            List of workflow IDs that have stored states.
            
        Raises:
            AzureError: If listing blobs fails.
        """
        try:
            blobs = self._container.list_blobs()
            workflow_ids = []
            
            for blob in blobs:
                # Remove .json extension to get workflow_id
                if blob.name.endswith(".json"):
                    workflow_id = blob.name[:-5]
                    # Restore original workflow_id format (reverse sanitization)
                    workflow_ids.append(workflow_id)
            
            logger.debug(f"Found {len(workflow_ids)} stored workflow states")
            return workflow_ids
            
        except AzureError as e:
            logger.error(f"Failed to list workflow states: {e}")
            raise
    
    def state_exists(self, workflow_id: str) -> bool:
        """Check if a workflow state exists in storage.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            True if state exists, False otherwise.
        """
        blob_name = self._get_blob_name(workflow_id)
        
        try:
            blob_client = self._container.get_blob_client(blob_name)
            return blob_client.exists()
        except AzureError as e:
            logger.error(f"Failed to check state existence for workflow '{workflow_id}': {e}")
            return False
    
    def get_state_metadata(self, workflow_id: str) -> Optional[dict[str, str]]:
        """Get metadata for a workflow state without downloading the full blob.
        
        Args:
            workflow_id: Unique identifier for the workflow.
            
        Returns:
            Dictionary containing blob metadata, or None if not found.
            
        Raises:
            AzureError: If getting metadata fails (except ResourceNotFoundError).
        """
        blob_name = self._get_blob_name(workflow_id)
        
        try:
            blob_client = self._container.get_blob_client(blob_name)
            properties = blob_client.get_blob_properties()
            
            metadata = {
                "last_modified": properties.last_modified.isoformat() if properties.last_modified else None,
                "size": properties.size,
                "content_type": properties.content_type,
            }
            
            # Add custom metadata if present
            if properties.metadata:
                metadata.update(properties.metadata)
            
            logger.debug(f"Retrieved metadata for workflow '{workflow_id}'")
            return metadata
            
        except ResourceNotFoundError:
            logger.warning(f"No state found for workflow '{workflow_id}'")
            return None
        except AzureError as e:
            logger.error(f"Failed to get metadata for workflow '{workflow_id}': {e}")
            raise
    
    def close(self) -> None:
        """Close the underlying blob client connection."""
        self._blob_client.close()
        logger.debug("StateManager connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
