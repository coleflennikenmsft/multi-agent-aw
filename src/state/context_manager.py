"""Context state serialization and management for workflow persistence."""

import json
import logging
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional
from .blob_client import BlobStorageClient

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages workflow context serialization, deserialization, and persistence to Azure Blob Storage."""

    def __init__(
        self,
        blob_client: Optional[BlobStorageClient] = None,
        use_json: bool = True,
        blob_prefix: str = "workflow-state",
    ):
        """Initialize the context manager.

        Args:
            blob_client: Azure Blob Storage client instance (if None, will create one)
            use_json: If True, use JSON format; if False, use pickle (default: True)
            blob_prefix: Prefix for blob names in storage
        """
        self.blob_client = blob_client or self._create_blob_client()
        self.use_json = use_json
        self.blob_prefix = blob_prefix
        self.file_extension = ".json" if use_json else ".pkl"

    def _create_blob_client(self) -> Optional[BlobStorageClient]:
        """Create blob client if Azure credentials are configured."""
        try:
            return BlobStorageClient()
        except (ValueError, Exception) as e:
            logger.warning(f"Azure Blob Storage not configured: {e}")
            return None

    def _generate_blob_name(
        self, workflow_id: str, timestamp: Optional[datetime] = None
    ) -> str:
        """Generate a blob name with timestamp.

        Args:
            workflow_id: Identifier for the workflow
            timestamp: Optional timestamp (default: current time)

        Returns:
            Blob name in format: {prefix}/{workflow_id}/{timestamp}{ext}
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        timestamp_str = timestamp.strftime("%Y%m%d-%H%M%S-%f")
        return f"{self.blob_prefix}/{workflow_id}/{timestamp_str}{self.file_extension}"

    def _serialize_context(self, context: Dict[str, Any]) -> bytes:
        """Serialize context to bytes.

        Args:
            context: Context dictionary to serialize

        Returns:
            Serialized bytes

        Raises:
            ValueError: If serialization fails
        """
        try:
            if self.use_json:
                # Add metadata
                context_with_meta = {
                    "version": "1.0",
                    "timestamp": datetime.utcnow().isoformat(),
                    "format": "json",
                    "context": context,
                }
                return json.dumps(context_with_meta, indent=2).encode("utf-8")
            else:
                # Pickle format
                return pickle.dumps(context)
        except Exception as e:
            logger.error(f"Failed to serialize context: {e}")
            raise ValueError(f"Context serialization failed: {e}")

    def _deserialize_context(self, data: bytes) -> Dict[str, Any]:
        """Deserialize context from bytes.

        Args:
            data: Serialized bytes

        Returns:
            Context dictionary

        Raises:
            ValueError: If deserialization fails
        """
        try:
            if self.use_json:
                context_with_meta = json.loads(data.decode("utf-8"))
                # Validate format
                if "context" not in context_with_meta:
                    logger.warning("Legacy format detected, returning raw data")
                    return context_with_meta
                return context_with_meta["context"]
            else:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Failed to deserialize context: {e}")
            raise ValueError(f"Context deserialization failed: {e}")

    def save_state(
        self,
        workflow_id: str,
        context: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> str:
        """Save workflow context state to Azure Blob Storage.

        Args:
            workflow_id: Unique identifier for the workflow
            context: Context dictionary to save
            timestamp: Optional timestamp (default: current time)

        Returns:
            Blob name where state was saved

        Raises:
            RuntimeError: If Azure Blob Storage is not configured
            ValueError: If serialization fails
        """
        if self.blob_client is None:
            raise RuntimeError(
                "Azure Blob Storage not configured. Please set AZURE_STORAGE_CONNECTION_STRING "
                "or AZURE_STORAGE_ACCOUNT_NAME environment variable."
            )

        blob_name = self._generate_blob_name(workflow_id, timestamp)
        logger.info(f"Saving state for workflow {workflow_id} to {blob_name}")

        try:
            data = self._serialize_context(context)
            self.blob_client.upload_blob(blob_name, data)
            logger.info(f"Successfully saved state: {blob_name}")
            return blob_name
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise

    def load_state(self, blob_name: str) -> Dict[str, Any]:
        """Load workflow context state from Azure Blob Storage.

        Args:
            blob_name: Name of the blob to load (returned from save_state)

        Returns:
            Context dictionary

        Raises:
            RuntimeError: If Azure Blob Storage is not configured
            ValueError: If deserialization fails
        """
        if self.blob_client is None:
            raise RuntimeError("Azure Blob Storage not configured")

        logger.info(f"Loading state from {blob_name}")

        try:
            data = self.blob_client.download_blob(blob_name)
            context = self._deserialize_context(data)
            logger.info(f"Successfully loaded state: {blob_name}")
            return context
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            raise

    def list_states(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available saved states.

        Args:
            workflow_id: Optional workflow ID to filter results

        Returns:
            List of dictionaries with state metadata (name, size, last_modified)

        Raises:
            RuntimeError: If Azure Blob Storage is not configured
        """
        if self.blob_client is None:
            raise RuntimeError("Azure Blob Storage not configured")

        prefix = f"{self.blob_prefix}/"
        if workflow_id:
            prefix = f"{self.blob_prefix}/{workflow_id}/"

        logger.info(f"Listing states with prefix: {prefix}")

        try:
            blob_names = self.blob_client.list_blobs(name_starts_with=prefix)
            states = []
            for blob_name in blob_names:
                try:
                    metadata = self.blob_client.get_blob_metadata(blob_name)
                    states.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to get metadata for {blob_name}: {e}")

            logger.info(f"Found {len(states)} states")
            return states
        except Exception as e:
            logger.error(f"Failed to list states: {e}")
            raise

    def delete_state(self, blob_name: str) -> None:
        """Delete a saved state from Azure Blob Storage.

        Args:
            blob_name: Name of the blob to delete

        Raises:
            RuntimeError: If Azure Blob Storage is not configured
        """
        if self.blob_client is None:
            raise RuntimeError("Azure Blob Storage not configured")

        logger.info(f"Deleting state: {blob_name}")

        try:
            self.blob_client.delete_blob(blob_name)
            logger.info(f"Successfully deleted state: {blob_name}")
        except Exception as e:
            logger.error(f"Failed to delete state: {e}")
            raise

    def get_latest_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent saved state for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Context dictionary or None if no states exist

        Raises:
            RuntimeError: If Azure Blob Storage is not configured
        """
        if self.blob_client is None:
            raise RuntimeError("Azure Blob Storage not configured")

        states = self.list_states(workflow_id)
        if not states:
            logger.info(f"No saved states found for workflow {workflow_id}")
            return None

        # Sort by last_modified descending
        latest_state = max(states, key=lambda s: s["last_modified"])
        logger.info(f"Loading latest state: {latest_state['name']}")
        return self.load_state(latest_state["name"])


# Module-level convenience functions using a default ContextManager instance
_default_manager: Optional[ContextManager] = None


def _get_default_manager() -> ContextManager:
    """Get or create the default ContextManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ContextManager()
    return _default_manager


def save_state(
    workflow_id: str, context: Dict[str, Any], timestamp: Optional[datetime] = None
) -> str:
    """Save workflow context state to Azure Blob Storage.

    Example:
        context = {"step": 2, "data": {...}}
        blob_name = save_state("workflow-123", context)

    Args:
        workflow_id: Unique identifier for the workflow
        context: Context dictionary to save
        timestamp: Optional timestamp (default: current time)

    Returns:
        Blob name where state was saved

    Raises:
        RuntimeError: If Azure Blob Storage is not configured
    """
    return _get_default_manager().save_state(workflow_id, context, timestamp)


def load_state(blob_name: str) -> Dict[str, Any]:
    """Load workflow context state from Azure Blob Storage.

    Example:
        context = load_state("workflow-state/workflow-123/20260403-143000-123456.json")

    Args:
        blob_name: Name of the blob to load (returned from save_state)

    Returns:
        Context dictionary

    Raises:
        RuntimeError: If Azure Blob Storage is not configured
    """
    return _get_default_manager().load_state(blob_name)


def list_states(workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all available saved states.

    Example:
        states = list_states("workflow-123")
        for state in states:
            print(f"{state['name']}: {state['size']} bytes, {state['last_modified']}")

    Args:
        workflow_id: Optional workflow ID to filter results

    Returns:
        List of dictionaries with state metadata

    Raises:
        RuntimeError: If Azure Blob Storage is not configured
    """
    return _get_default_manager().list_states(workflow_id)


def delete_state(blob_name: str) -> None:
    """Delete a saved state from Azure Blob Storage.

    Example:
        delete_state("workflow-state/workflow-123/20260403-143000-123456.json")

    Args:
        blob_name: Name of the blob to delete

    Raises:
        RuntimeError: If Azure Blob Storage is not configured
    """
    return _get_default_manager().delete_state(blob_name)
