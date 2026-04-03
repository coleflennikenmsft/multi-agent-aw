import logging
from typing import Any, Optional, List
from .manager import BlobStateManager

class CheckpointManager:
    def __init__(self, state_manager: BlobStateManager):
        self.logger = logging.getLogger(__name__)
        self.state_manager = state_manager

    def create_checkpoint(self, key: str, state: Any, metadata: Optional[dict] = None):
        checkpoint_key = f"checkpoints/{key}"
        self.state_manager.save_state(checkpoint_key, state, metadata=metadata)
        self.logger.info(f"Checkpoint created: {checkpoint_key}")

    def restore_from_checkpoint(self, key: str) -> Any:
        checkpoint_key = f"checkpoints/{key}"
        state = self.state_manager.load_state(checkpoint_key)
        self.logger.info(f"Restored from checkpoint: {checkpoint_key}")
        return state

    def list_checkpoints(self, prefix: Optional[str] = None) -> List[str]:
        prefix = prefix or "checkpoints/"
        return self.state_manager.list_versions(prefix)

    def delete_checkpoint(self, key: str):
        checkpoint_key = f"checkpoints/{key}"
        self.state_manager.delete_state(checkpoint_key)
        self.logger.info(f"Deleted checkpoint: {checkpoint_key}")
