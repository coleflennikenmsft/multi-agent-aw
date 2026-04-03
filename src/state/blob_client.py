"""Azure Blob Storage client wrapper for state management."""

import os
import logging
from typing import Optional, Dict, Any
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
from azure.identity import DefaultAzureCredential


logger = logging.getLogger(__name__)


class BlobClientWrapper:
    """Wrapper for Azure Blob Storage operations with error handling and retry logic."""
    
    def __init__(self, connection_string: Optional[str] = None, 
                 account_name: Optional[str] = None, 
                 container_name: str = "workflow-state"):
        """Initialize the blob client.
        
        Args:
            connection_string: Azure Storage connection string
            account_name: Storage account name (for managed identity)
            container_name: Name of the blob container to use
        """
        self.container_name = container_name
        self._blob_service_client = None
        self._container_client = None
        
        # Initialize connection
        if connection_string:
            self._blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        elif account_name:
            # Use managed identity authentication
            credential = DefaultAzureCredential()
            account_url = f"https://{account_name}.blob.core.windows.net"
            self._blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        else:
            raise ValueError("Either connection_string or account_name must be provided")
            
        self._container_client = self._blob_service_client.get_container_client(container_name)
        
    def ensure_container_exists(self) -> bool:
        """Ensure the container exists, create if it doesn't.
        
        Returns:
            True if container exists or was created successfully
        """
        try:
            # Try to get container properties to check if it exists
            self._container_client.get_container_properties()
            return True
        except ResourceNotFoundError:
            try:
                self._container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
                return True
            except AzureError as e:
                logger.error(f"Failed to create container {self.container_name}: {e}")
                return False
        except AzureError as e:
            logger.error(f"Error checking container {self.container_name}: {e}")
            return False
            
    def upload_blob(self, blob_name: str, data: bytes, overwrite: bool = True) -> bool:
        """Upload data to a blob.
        
        Args:
            blob_name: Name of the blob
            data: Binary data to upload
            overwrite: Whether to overwrite existing blob
            
        Returns:
            True if upload succeeded
        """
        try:
            self.ensure_container_exists()
            blob_client = self._container_client.get_blob_client(blob_name)
            blob_client.upload_blob(data, overwrite=overwrite)
            logger.info(f"Successfully uploaded blob: {blob_name}")
            return True
        except AzureError as e:
            logger.error(f"Failed to upload blob {blob_name}: {e}")
            return False
            
    def download_blob(self, blob_name: str) -> Optional[bytes]:
        """Download data from a blob.
        
        Args:
            blob_name: Name of the blob to download
            
        Returns:
            Binary data if successful, None if failed
        """
        try:
            blob_client = self._container_client.get_blob_client(blob_name)
            download_stream = blob_client.download_blob()
            data = download_stream.readall()
            logger.info(f"Successfully downloaded blob: {blob_name}")
            return data
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name}")
            return None
        except AzureError as e:
            logger.error(f"Failed to download blob {blob_name}: {e}")
            return None
            
    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob.
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            True if deletion succeeded or blob didn't exist
        """
        try:
            blob_client = self._container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            logger.info(f"Successfully deleted blob: {blob_name}")
            return True
        except ResourceNotFoundError:
            logger.info(f"Blob not found (already deleted): {blob_name}")
            return True
        except AzureError as e:
            logger.error(f"Failed to delete blob {blob_name}: {e}")
            return False
            
    def list_blobs(self, prefix: Optional[str] = None) -> list[str]:
        """List all blobs in the container.
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of blob names
        """
        try:
            blobs = []
            for blob in self._container_client.list_blobs(name_starts_with=prefix):
                blobs.append(blob.name)
            logger.info(f"Listed {len(blobs)} blobs with prefix '{prefix or 'None'}'")
            return blobs
        except AzureError as e:
            logger.error(f"Failed to list blobs: {e}")
            return []
            
    def blob_exists(self, blob_name: str) -> bool:
        """Check if a blob exists.
        
        Args:
            blob_name: Name of the blob to check
            
        Returns:
            True if blob exists
        """
        try:
            blob_client = self._container_client.get_blob_client(blob_name)
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except AzureError as e:
            logger.error(f"Error checking blob existence {blob_name}: {e}")
            return False


def create_blob_client_from_env() -> Optional[BlobClientWrapper]:
    """Create a blob client using environment variables.
    
    Expected environment variables:
    - AZURE_STORAGE_CONNECTION_STRING: Full connection string
    OR
    - AZURE_STORAGE_ACCOUNT_NAME: Storage account name (uses managed identity)
    - AZURE_STORAGE_CONTAINER_NAME: Container name (optional, defaults to 'workflow-state')
    
    Returns:
        BlobClientWrapper instance or None if configuration is missing
    """
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "workflow-state")
    
    if connection_string:
        return BlobClientWrapper(connection_string=connection_string, container_name=container_name)
    elif account_name:
        return BlobClientWrapper(account_name=account_name, container_name=container_name)
    else:
        logger.warning("No Azure Storage configuration found in environment variables")
        return None