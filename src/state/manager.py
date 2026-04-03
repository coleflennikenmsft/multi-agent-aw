import logging
from typing import Any, Optional, Dict
from .blob_client import BlobStorageClient
from .serialization import StateSerializer

class BlobStateManager:
    def __init__(self, blob_client: BlobStorageClient, serializer: Optional[StateSerializer] = None):
        self.logger = logging.getLogger(__name__)
        self.blob_client = blob_client
        self.serializer = serializer or StateSerializer()

    def save_state(self, key: str, state: Any, fmt: str = "json", compress: bool = False, metadata: Optional[Dict[str, str]] = None):
        data = self.serializer.serialize(state, fmt=fmt, compress=compress)
        self.blob_client.upload_blob(key, data, overwrite=True, metadata=metadata)
        self.logger.info(f"State saved under key: {key}")

    def load_state(self, key: str, fmt: Optional[str] = None, compressed: Optional[bool] = None) -> Any:
        data = self.blob_client.download_blob(key)
        if fmt is None:
            fmt = self.serializer.detect_format(data)
        if compressed is None:
            compressed = data[:2] == b'\x1f\x8b'  # gzip magic number
        state = self.serializer.deserialize(data, fmt=fmt, compressed=compressed)
        self.logger.info(f"State loaded from key: {key}")
        return state

    def delete_state(self, key: str):
        self.blob_client.delete_blob(key)
        self.logger.info(f"State deleted for key: {key}")

    def list_versions(self, prefix: str) -> list:
        return self.blob_client.list_blobs(prefix=prefix)
