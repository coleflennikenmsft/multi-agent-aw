"""Azure Blob Storage client wrapper for state management."""

import logging
import os
from typing import Optional
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class BlobStorageClient:
    """Wrapper for Azure Blob Storage operations with retry logic and error handling."""

    def __init__(
        self,
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        container_name: Optional[str] = "workflow-context-state",
    ):
        """Initialize the blob storage client.

        Args:
            connection_string: Azure Storage connection string (preferred method)
            account_name: Azure Storage account name (for managed identity auth)
            container_name: Name of the container to use for state storage

        Environment variables:
            AZURE_STORAGE_CONNECTION_STRING: Connection string
            AZURE_STORAGE_ACCOUNT_NAME: Account name for managed identity
            AZURE_STORAGE_CONTAINER_NAME: Container name (default: workflow-context-state)
        """
        self.container_name = container_name or os.getenv(
            "AZURE_STORAGE_CONTAINER_NAME", "workflow-context-state"
        )

        # Try connection string first (from parameter or environment)
        conn_str = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        if conn_str:
            logger.info("Initializing BlobServiceClient with connection string")
            self.blob_service_client = BlobServiceClient.from_connection_string(
                conn_str
            )
        else:
            # Fall back to managed identity with account name
            acct_name = account_name or os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            if not acct_name:
                raise ValueError(
                    "Either AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_NAME "
                    "must be provided"
                )

            logger.info(
                f"Initializing BlobServiceClient with managed identity for account: {acct_name}"
            )
            account_url = f"https://{acct_name}.blob.core.windows.net"
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(
                account_url=account_url, credential=credential
            )

        self._container_client: Optional[ContainerClient] = None
        self._ensure_container()

    def _ensure_container(self) -> None:
        """Ensure the container exists, creating it if necessary."""
        try:
            self._container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            # Check if container exists
            if not self._container_client.exists():
                logger.info(f"Creating container: {self.container_name}")
                self._container_client.create_container()
            else:
                logger.debug(f"Container exists: {self.container_name}")
        except AzureError as e:
            logger.error(f"Failed to access/create container: {e}")
            raise

    @property
    def container_client(self) -> ContainerClient:
        """Get the container client, ensuring it's initialized."""
        if self._container_client is None:
            self._ensure_container()
        return self._container_client

    def upload_blob(self, blob_name: str, data: bytes, overwrite: bool = True) -> None:
        """Upload data to a blob.

        Args:
            blob_name: Name of the blob
            data: Binary data to upload
            overwrite: Whether to overwrite existing blob (default: True)

        Raises:
            AzureError: If upload fails
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            logger.info(f"Uploading blob: {blob_name} ({len(data)} bytes)")
            blob_client.upload_blob(data, overwrite=overwrite)
            logger.debug(f"Successfully uploaded blob: {blob_name}")
        except AzureError as e:
            logger.error(f"Failed to upload blob {blob_name}: {e}")
            raise

    def download_blob(self, blob_name: str) -> bytes:
        """Download blob data.

        Args:
            blob_name: Name of the blob to download

        Returns:
            Binary data from the blob

        Raises:
            ResourceNotFoundError: If blob doesn't exist
            AzureError: If download fails
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            logger.info(f"Downloading blob: {blob_name}")
            data = blob_client.download_blob().readall()
            logger.debug(f"Successfully downloaded blob: {blob_name} ({len(data)} bytes)")
            return data
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name}")
            raise
        except AzureError as e:
            logger.error(f"Failed to download blob {blob_name}: {e}")
            raise

    def list_blobs(self, name_starts_with: Optional[str] = None) -> list[str]:
        """List all blobs in the container.

        Args:
            name_starts_with: Optional prefix to filter blobs

        Returns:
            List of blob names

        Raises:
            AzureError: If listing fails
        """
        try:
            logger.info(f"Listing blobs (prefix: {name_starts_with or 'none'})")
            blobs = self.container_client.list_blobs(
                name_starts_with=name_starts_with
            )
            blob_names = [blob.name for blob in blobs]
            logger.debug(f"Found {len(blob_names)} blobs")
            return blob_names
        except AzureError as e:
            logger.error(f"Failed to list blobs: {e}")
            raise

    def delete_blob(self, blob_name: str) -> None:
        """Delete a blob.

        Args:
            blob_name: Name of the blob to delete

        Raises:
            ResourceNotFoundError: If blob doesn't exist
            AzureError: If deletion fails
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            logger.info(f"Deleting blob: {blob_name}")
            blob_client.delete_blob()
            logger.debug(f"Successfully deleted blob: {blob_name}")
        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {blob_name}")
            raise
        except AzureError as e:
            logger.error(f"Failed to delete blob {blob_name}: {e}")
            raise

    def blob_exists(self, blob_name: str) -> bool:
        """Check if a blob exists.

        Args:
            blob_name: Name of the blob to check

        Returns:
            True if blob exists, False otherwise
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            return blob_client.exists()
        except AzureError as e:
            logger.error(f"Failed to check blob existence {blob_name}: {e}")
            return False

    def get_blob_metadata(self, blob_name: str) -> dict:
        """Get blob metadata.

        Args:
            blob_name: Name of the blob

        Returns:
            Dictionary of blob metadata

        Raises:
            ResourceNotFoundError: If blob doesn't exist
            AzureError: If operation fails
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            properties = blob_client.get_blob_properties()
            return {
                "name": blob_name,
                "size": properties.size,
                "last_modified": properties.last_modified,
                "content_type": properties.content_settings.content_type,
                "metadata": properties.metadata or {},
            }
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name}")
            raise
        except AzureError as e:
            logger.error(f"Failed to get blob metadata {blob_name}: {e}")
            raise
