"""
Context state serialization and Azure Blob Storage integration.

Usage:
    from state.context_manager import ContextManager
    manager = ContextManager(blob_client, workflow_id)
    blob_name = manager.save_state({'foo': 'bar'})
    context = manager.load_state(blob_name)
    blobs = manager.list_states()
    manager.delete_state(blob_name)

State is versioned and stored as JSON.
"""
import json
import time
from typing import Any, Dict, Optional
from .blob_client import AzureBlobClient

STATE_VERSION = 1

class ContextManager:
    def __init__(self, blob_client: AzureBlobClient, workflow_id: str):
        """
        Args:
            blob_client: AzureBlobClient instance
            workflow_id: Unique workflow identifier
        """
        self.blob_client = blob_client
        self.workflow_id = workflow_id

    def _blob_name(self, timestamp: Optional[int] = None) -> str:
        ts = timestamp or int(time.time())
        return f"context/{self.workflow_id}/state_{ts}_v{STATE_VERSION}.json"

    def save_state(self, context: Dict[str, Any]) -> str:
        """
        Save context state to Azure Blob as JSON.
        Returns blob name.
        """
        data = {
            "version": STATE_VERSION,
            "timestamp": int(time.time()),
            "context": context
        }
        blob_name = self._blob_name(data["timestamp"])
        serialized = json.dumps(data).encode("utf-8")
        self.blob_client.upload_blob(blob_name, serialized)
        return blob_name

    def load_state(self, blob_name: str) -> Dict[str, Any]:
        """
        Load context state from Azure Blob.
        Returns context dict.
        """
        raw = self.blob_client.download_blob(blob_name)
        data = json.loads(raw.decode("utf-8"))
        if data.get("version") != STATE_VERSION:
            raise ValueError(f"Unsupported state version: {data.get('version')}")
        return data["context"]

    def list_states(self):
        """
        List all saved state blobs for this workflow.
        Returns list of BlobProperties.
        """
        prefix = f"context/{self.workflow_id}/"
        return self.blob_client.list_blobs(prefix=prefix)

    def delete_state(self, blob_name: str):
        """
        Delete a state blob by name.
        """
        self.blob_client.delete_blob(blob_name)
