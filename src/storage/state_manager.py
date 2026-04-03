import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from .azure_blob_client import AzureBlobClient
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger("StateManager")

class StateManager:
    def __init__(self, container_name: str = "workflow-states"):
        self.client = AzureBlobClient(container_name)
        self.container = self.client.get_container_client()

    def save_state(self, workflow_id: str, state_data: dict) -> bool:
        blob_name = f"{workflow_id}.json"
        try:
            state_data["timestamp"] = datetime.utcnow().isoformat()
            self.container.upload_blob(
                name=blob_name,
                data=json.dumps(state_data),
                overwrite=True,
                metadata={"timestamp": state_data["timestamp"]}
            )
            logger.info(f"Saved state for workflow_id={workflow_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save state for {workflow_id}: {e}")
            return False

    def load_state(self, workflow_id: str) -> Optional[dict]:
        blob_name = f"{workflow_id}.json"
        try:
            blob = self.container.get_blob_client(blob_name)
            data = blob.download_blob().readall()
            logger.info(f"Loaded state for workflow_id={workflow_id}")
            return json.loads(data)
        except ResourceNotFoundError:
            logger.warning(f"State not found for workflow_id={workflow_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to load state for {workflow_id}: {e}")
            return None

    def delete_state(self, workflow_id: str) -> bool:
        blob_name = f"{workflow_id}.json"
        try:
            self.container.delete_blob(blob_name)
            logger.info(f"Deleted state for workflow_id={workflow_id}")
            return True
        except ResourceNotFoundError:
            logger.warning(f"State not found for deletion: workflow_id={workflow_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete state for {workflow_id}: {e}")
            return False

    def list_states(self) -> List[str]:
        try:
            blobs = self.container.list_blobs()
            state_blobs = [b.name for b in blobs if b.name.endswith('.json')]
            logger.info(f"Listed {len(state_blobs)} state blobs.")
            return state_blobs
        except Exception as e:
            logger.error(f"Failed to list states: {e}")
            return []
