"""Azure Blob Storage client for workflow state management."""

import logging
import os
from typing import Optional

from azure.core.exceptions import (
    AzureError,
    ResourceExistsError,
    ResourceNotFoundError,
)
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContainerClient

logger = logging.getLogger(__name__)


class AzureBlobClient:
    """Encapsulates Azure Blob Storage operations for state management.
    
    Supports multiple authentication methods:
    1. Managed Identity (DefaultAzureCredential) - recommended for Azure-hosted runners
    2. Connection String (AZURE_STORAGE_CONNECTION_STRING)
    3. Account Key (AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY)
    
    Example:
        >>> client = AzureBlobClient()
        >>> container = client.get_or_create_container("workflow-states")
        >>> blob_client = container.get_blob_client("workflow_123.json")
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
    ):
        """Initialize the Azure Blob Storage client.
        
        Args:
            connection_string: Azure Storage connection string. If not provided,
                will try to read from AZURE_STORAGE_CONNECTION_STRING env var.
            account_name: Storage account name. If not provided, will try to read
                from AZURE_STORAGE_ACCOUNT_NAME env var.
            account_key: Storage account key. If not provided, will try to read
                from AZURE_STORAGE_ACCOUNT_KEY env var.
                
        Raises:
            ValueError: If no valid authentication method is configured.
            AzureError: If connection to Azure fails.
        """
        self._service_client: Optional[BlobServiceClient] = None
        self._initialize_client(connection_string, account_name, account_key)
    
    def _initialize_client(
        self,
        connection_string: Optional[str],
        account_name: Optional[str],
        account_key: Optional[str],
    ) -> None:
        """Initialize the BlobServiceClient with the appropriate authentication method."""
        # Try connection string first
        conn_str = connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if conn_str:
            try:
                self._service_client = BlobServiceClient.from_connection_string(conn_str)
                logger.info("Azure Blob Storage client initialized with connection string")
                return
            except Exception as e:
                logger.error(f"Failed to initialize with connection string: {e}")
                raise ValueError(f"Invalid connection string: {e}") from e
        
        # Try account name + key
        acc_name = account_name or os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
        acc_key = account_key or os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
        
        if acc_name and acc_key:
            try:
                account_url = f"https://{acc_name}.blob.core.windows.net"
                self._service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=acc_key
                )
                logger.info(f"Azure Blob Storage client initialized for account: {acc_name}")
                return
            except Exception as e:
                logger.error(f"Failed to initialize with account key: {e}")
                raise ValueError(f"Invalid account credentials: {e}") from e
        
        # Try DefaultAzureCredential (Managed Identity)
        if acc_name:
            try:
                account_url = f"https://{acc_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self._service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                logger.info(f"Azure Blob Storage client initialized with DefaultAzureCredential for account: {acc_name}")
                return
            except Exception as e:
                logger.error(f"Failed to initialize with DefaultAzureCredential: {e}")
                raise ValueError(f"Failed to authenticate with managed identity: {e}") from e
        
        # No valid authentication method found
        raise ValueError(
            "No valid Azure Storage authentication found. "
            "Please provide either: "
            "1) AZURE_STORAGE_CONNECTION_STRING, or "
            "2) AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY, or "
            "3) AZURE_STORAGE_ACCOUNT_NAME (with managed identity configured)"
        )
    
    @property
    def service_client(self) -> BlobServiceClient:
        """Get the BlobServiceClient instance.
        
        Returns:
            BlobServiceClient: The initialized service client.
            
        Raises:
            RuntimeError: If the client is not initialized.
        """
        if self._service_client is None:
            raise RuntimeError("BlobServiceClient not initialized")
        return self._service_client
    
    def get_or_create_container(self, container_name: str) -> ContainerClient:
        """Get or create a blob container.
        
        Args:
            container_name: Name of the container to get or create.
            
        Returns:
            ContainerClient: Client for the container.
            
        Raises:
            AzureError: If container access or creation fails.
        """
        try:
            container_client = self.service_client.get_container_client(container_name)
            
            # Check if container exists
            if not container_client.exists():
                logger.info(f"Container '{container_name}' does not exist, creating...")
                container_client = self.service_client.create_container(container_name)
                logger.info(f"Container '{container_name}' created successfully")
            else:
                logger.debug(f"Container '{container_name}' already exists")
            
            return container_client
            
        except ResourceExistsError:
            # Container was created by another process between exists check and create
            logger.debug(f"Container '{container_name}' was created concurrently")
            return self.service_client.get_container_client(container_name)
        except AzureError as e:
            logger.error(f"Failed to get or create container '{container_name}': {e}")
            raise
    
    def list_containers(self) -> list[str]:
        """List all container names in the storage account.
        
        Returns:
            List of container names.
            
        Raises:
            AzureError: If listing containers fails.
        """
        try:
            containers = self.service_client.list_containers()
            container_names = [container.name for container in containers]
            logger.debug(f"Found {len(container_names)} containers")
            return container_names
        except AzureError as e:
            logger.error(f"Failed to list containers: {e}")
            raise
    
    def delete_container(self, container_name: str) -> bool:
        """Delete a blob container.
        
        Args:
            container_name: Name of the container to delete.
            
        Returns:
            True if container was deleted, False if it didn't exist.
            
        Raises:
            AzureError: If container deletion fails.
        """
        try:
            self.service_client.delete_container(container_name)
            logger.info(f"Container '{container_name}' deleted successfully")
            return True
        except ResourceNotFoundError:
            logger.warning(f"Container '{container_name}' not found for deletion")
            return False
        except AzureError as e:
            logger.error(f"Failed to delete container '{container_name}': {e}")
            raise
    
    def close(self) -> None:
        """Close the BlobServiceClient connection."""
        if self._service_client:
            self._service_client.close()
            logger.debug("Azure Blob Storage client connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
