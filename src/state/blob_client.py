"""
Azure Blob Storage client wrapper for state management.

Usage:
    from state.blob_client import AzureBlobClient
    client = AzureBlobClient()
    client.upload_blob('blobname', b'data')
    data = client.download_blob('blobname')
    blobs = client.list_blobs()
    client.delete_blob('blobname')

Handles connection via connection string or managed identity.
"""
import os
from typing import Optional
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.core.exceptions import AzureError

class AzureBlobClient:
    def __init__(self, connection_string: Optional[str] = None, account_name: Optional[str] = None, container_name: Optional[str] = None):
        """
        Initialize Azure Blob client.
        Args:
            connection_string: Azure connection string (optional)
            account_name: Storage account name (optional)
            container_name: Blob container name (optional)
        """
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.account_name = account_name or os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.container_name = container_name or os.getenv("AZURE_STORAGE_CONTAINER_NAME")
        self._client = None
        self._container_client = None
        self._init_client()

    def _init_client(self):
        try:
            if self.connection_string:
                self._client = BlobServiceClient.from_connection_string(self.connection_string)
            elif self.account_name:
                url = f"https://{self.account_name}.blob.core.windows.net"
                self._client = BlobServiceClient(account_url=url)
            else:
                raise ValueError("Azure Blob credentials not configured.")
            self._container_client = self._client.get_container_client(self.container_name)
        except AzureError as e:
            raise RuntimeError(f"Failed to initialize Azure Blob client: {e}")

    def get_container_client(self) -> ContainerClient:
        """Return the container client."""
        return self._container_client

    def upload_blob(self, blob_name: str, data: bytes, overwrite: bool = True):
        """Upload data to a blob."""
        try:
            self._container_client.upload_blob(blob_name, data, overwrite=overwrite)
        except AzureError as e:
            raise RuntimeError(f"Failed to upload blob: {e}")

    def download_blob(self, blob_name: str) -> bytes:
        """Download blob data as bytes."""
        try:
            blob_client = self._container_client.get_blob_client(blob_name)
            return blob_client.download_blob().readall()
        except AzureError as e:
            raise RuntimeError(f"Failed to download blob: {e}")

    def list_blobs(self, prefix: Optional[str] = None):
        """List blobs in the container, optionally filtered by prefix."""
        try:
            return list(self._container_client.list_blobs(name_starts_with=prefix))
        except AzureError as e:
            raise RuntimeError(f"Failed to list blobs: {e}")

    def delete_blob(self, blob_name: str):
        """Delete a blob from the container."""
        try:
            self._container_client.delete_blob(blob_name)
        except AzureError as e:
            raise RuntimeError(f"Failed to delete blob: {e}")
