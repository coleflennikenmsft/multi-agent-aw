import logging
from typing import List, Optional, Dict, Any
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError, AzureError
from azure.core.retry import RetryPolicy

class BlobStorageClient:
    def __init__(self, connection_string: str, container_name: str):
        self.logger = logging.getLogger(__name__)
        self.connection_string = connection_string
        self.container_name = container_name
        self._client = BlobServiceClient.from_connection_string(self.connection_string)
        self._container = self._get_or_create_container()

    def _get_or_create_container(self) -> ContainerClient:
        try:
            container = self._client.get_container_client(self.container_name)
            container.get_container_properties()
            return container
        except ResourceNotFoundError:
            self.logger.info(f"Container '{self.container_name}' not found. Creating it.")
            return self._client.create_container(self.container_name)
        except AzureError as e:
            self.logger.error(f"Failed to get or create container: {e}")
            raise

    def upload_blob(self, blob_name: str, data: bytes, overwrite: bool = True, metadata: Optional[Dict[str, str]] = None):
        try:
            blob_client = self._container.get_blob_client(blob_name)
            blob_client.upload_blob(data, overwrite=overwrite, metadata=metadata)
            self.logger.info(f"Uploaded blob: {blob_name}")
        except AzureError as e:
            self.logger.error(f"Failed to upload blob '{blob_name}': {e}")
            raise

    def download_blob(self, blob_name: str) -> bytes:
        try:
            blob_client = self._container.get_blob_client(blob_name)
            stream = blob_client.download_blob()
            data = stream.readall()
            self.logger.info(f"Downloaded blob: {blob_name}")
            return data
        except ResourceNotFoundError:
            self.logger.warning(f"Blob '{blob_name}' not found.")
            raise
        except AzureError as e:
            self.logger.error(f"Failed to download blob '{blob_name}': {e}")
            raise

    def delete_blob(self, blob_name: str):
        try:
            blob_client = self._container.get_blob_client(blob_name)
            blob_client.delete_blob()
            self.logger.info(f"Deleted blob: {blob_name}")
        except ResourceNotFoundError:
            self.logger.warning(f"Blob '{blob_name}' not found for deletion.")
        except AzureError as e:
            self.logger.error(f"Failed to delete blob '{blob_name}': {e}")
            raise

    def list_blobs(self, prefix: Optional[str] = None) -> List[str]:
        try:
            blobs = self._container.list_blobs(name_starts_with=prefix)
            blob_names = [blob.name for blob in blobs]
            self.logger.info(f"Listed blobs with prefix '{prefix}': {blob_names}")
            return blob_names
        except AzureError as e:
            self.logger.error(f"Failed to list blobs: {e}")
            raise
