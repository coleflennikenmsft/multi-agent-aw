"""Azure Blob Storage client for state management."""

import logging
import os
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.core.exceptions import AzureError, ResourceNotFoundError


logger = logging.getLogger(__name__)


class AzureBlobClient:
    """Azure Blob Storage client for managing workflow state persistence."""

    def __init__(self, container_name: str = "workflow-states"):
        """Initialize the Azure Blob Storage client.
        
        Args:
            container_name: Name of the container to store state data.
        """
        self.container_name = container_name
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._container_client: Optional[ContainerClient] = None
        
    def _initialize_client(self) -> BlobServiceClient:
        """Initialize the BlobServiceClient with proper authentication.
        
        Returns:
            Initialized BlobServiceClient instance.
            
        Raises:
            ValueError: If no valid authentication method is configured.
            AzureError: If Azure SDK operations fail.
        """
        if self._blob_service_client is not None:
            return self._blob_service_client
            
        try:
            # Try connection string first (most explicit)
            connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
            if connection_string:
                logger.info("Authenticating with Azure Storage using connection string")
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    connection_string
                )
                return self._blob_service_client
            
            # Try account name + key
            account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            account_key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
            if account_name and account_key:
                logger.info(f"Authenticating with Azure Storage account: {account_name}")
                account_url = f"https://{account_name}.blob.core.windows.net"
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=account_key
                )
                return self._blob_service_client
            
            # Try DefaultAzureCredential (managed identity, etc.)
            if account_name:
                logger.info(f"Authenticating with DefaultAzureCredential for account: {account_name}")
                credential = DefaultAzureCredential()
                account_url = f"https://{account_name}.blob.core.windows.net"
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                return self._blob_service_client
                
            raise ValueError(
                "No Azure Storage authentication configured. Please set one of:\n"
                "- AZURE_STORAGE_CONNECTION_STRING\n"
                "- AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY\n"
                "- AZURE_STORAGE_ACCOUNT_NAME (for DefaultAzureCredential)"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage client: {e}")
            raise
    
    def _get_container_client(self) -> ContainerClient:
        """Get or create the container client.
        
        Returns:
            ContainerClient instance for the specified container.
            
        Raises:
            AzureError: If container operations fail.
        """
        if self._container_client is not None:
            return self._container_client
            
        try:
            blob_service_client = self._initialize_client()
            self._container_client = blob_service_client.get_container_client(
                self.container_name
            )
            
            # Create container if it doesn't exist
            try:
                self._container_client.get_container_properties()
                logger.info(f"Container '{self.container_name}' exists")
            except ResourceNotFoundError:
                logger.info(f"Creating container '{self.container_name}'")
                self._container_client.create_container()
                
            return self._container_client
            
        except Exception as e:
            logger.error(f"Failed to get container client: {e}")
            raise
    
    def upload_blob(self, blob_name: str, data: bytes, metadata: Optional[dict] = None) -> bool:
        """Upload data to a blob.
        
        Args:
            blob_name: Name of the blob to upload.
            data: Binary data to upload.
            metadata: Optional metadata to attach to the blob.
            
        Returns:
            True if upload successful, False otherwise.
        """
        try:
            container_client = self._get_container_client()
            container_client.upload_blob(
                name=blob_name,
                data=data,
                metadata=metadata or {},
                overwrite=True
            )
            logger.info(f"Successfully uploaded blob: {blob_name}")
            return True
            
        except AzureError as e:
            logger.error(f"Azure error uploading blob '{blob_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading blob '{blob_name}': {e}")
            return False
    
    def download_blob(self, blob_name: str) -> Optional[bytes]:
        """Download data from a blob.
        
        Args:
            blob_name: Name of the blob to download.
            
        Returns:
            Binary data if successful, None if blob not found or error occurred.
        """
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            download_stream = blob_client.download_blob()
            data = download_stream.readall()
            logger.info(f"Successfully downloaded blob: {blob_name}")
            return data
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name}")
            return None
        except AzureError as e:
            logger.error(f"Azure error downloading blob '{blob_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading blob '{blob_name}': {e}")
            return None
    
    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob.
        
        Args:
            blob_name: Name of the blob to delete.
            
        Returns:
            True if deletion successful, False otherwise.
        """
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            logger.info(f"Successfully deleted blob: {blob_name}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {blob_name}")
            return True  # Consider missing blob as successful deletion
        except AzureError as e:
            logger.error(f"Azure error deleting blob '{blob_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting blob '{blob_name}': {e}")
            return False
    
    def list_blobs(self, name_starts_with: Optional[str] = None) -> list[str]:
        """List blobs in the container.
        
        Args:
            name_starts_with: Optional prefix to filter blob names.
            
        Returns:
            List of blob names.
        """
        try:
            container_client = self._get_container_client()
            blobs = container_client.list_blobs(name_starts_with=name_starts_with)
            blob_names = [blob.name for blob in blobs]
            logger.info(f"Found {len(blob_names)} blobs")
            return blob_names
            
        except AzureError as e:
            logger.error(f"Azure error listing blobs: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing blobs: {e}")
            return []
    
    def get_blob_metadata(self, blob_name: str) -> Optional[dict]:
        """Get metadata for a blob.
        
        Args:
            blob_name: Name of the blob.
            
        Returns:
            Metadata dictionary if successful, None otherwise.
        """
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            properties = blob_client.get_blob_properties()
            logger.info(f"Retrieved metadata for blob: {blob_name}")
            return properties.metadata
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found for metadata: {blob_name}")
            return None
        except AzureError as e:
            logger.error(f"Azure error getting blob metadata '{blob_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting blob metadata '{blob_name}': {e}")
            return None