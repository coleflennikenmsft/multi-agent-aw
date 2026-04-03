"""Azure Blob Storage client for context state management."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

from .config import StorageConfig

logger = logging.getLogger(__name__)


class BlobStorageError(Exception):
    """Base exception for blob storage operations."""
    pass


class BlobStorageConnectionError(BlobStorageError):
    """Exception raised when connection to blob storage fails."""
    pass


class BlobStorageClient:
    """Azure Blob Storage client for managing context state data.
    
    This client provides methods for uploading, downloading, and managing
    context state data in Azure Blob Storage. It supports both connection
    string and managed identity authentication methods.
    
    Example:
        # Using connection string
        config = StorageConfig(connection_string="DefaultEndpointsProtocol=https;...")
        client = BlobStorageClient(config)
        
        # Using managed identity
        config = StorageConfig(account_name="mystorageaccount")
        client = BlobStorageClient(config)
        
        # Upload state
        await client.upload_state("session-123", {"key": "value"})
        
        # Download state
        state = await client.download_state("session-123")
    """
    
    def __init__(self, config: StorageConfig):
        """Initialize the blob storage client.
        
        Args:
            config: Storage configuration containing authentication details
            
        Raises:
            BlobStorageConnectionError: If unable to create blob service client
        """
        self.config = config
        self._blob_service_client: Optional[BlobServiceClient] = None
        
    def _get_blob_service_client(self) -> BlobServiceClient:
        """Get or create the blob service client.
        
        Returns:
            BlobServiceClient: The blob service client instance
            
        Raises:
            BlobStorageConnectionError: If unable to create the client
        """
        if self._blob_service_client is not None:
            return self._blob_service_client
            
        try:
            if self.config.has_connection_string():
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    conn_str=self.config.connection_string
                )
                logger.info("Connected to Azure Blob Storage using connection string")
            elif self.config.has_managed_identity_config():
                credential = DefaultAzureCredential()
                account_url = self.config.get_account_url()
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                logger.info(f"Connected to Azure Blob Storage using managed identity: {account_url}")
            else:
                raise BlobStorageConnectionError(
                    "No valid authentication method configured"
                )
                
            return self._blob_service_client
            
        except Exception as e:
            logger.error(f"Failed to create blob service client: {str(e)}")
            raise BlobStorageConnectionError(f"Failed to connect to Azure Blob Storage: {str(e)}")
    
    async def create_container(self) -> bool:
        """Create the storage container if it doesn't exist.
        
        Returns:
            bool: True if container was created, False if it already exists
            
        Raises:
            BlobStorageError: If container creation fails
        """
        try:
            client = self._get_blob_service_client()
            container_client = client.get_container_client(self.config.container_name)
            container_client.create_container()
            logger.info(f"Created container: {self.config.container_name}")
            return True
        except ResourceExistsError:
            logger.debug(f"Container already exists: {self.config.container_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to create container {self.config.container_name}: {str(e)}")
            raise BlobStorageError(f"Failed to create container: {str(e)}")
    
    async def container_exists(self) -> bool:
        """Check if the storage container exists.
        
        Returns:
            bool: True if container exists, False otherwise
            
        Raises:
            BlobStorageError: If unable to check container existence
        """
        try:
            client = self._get_blob_service_client()
            containers = client.list_containers(name_starts_with=self.config.container_name)
            for container in containers:
                if container.name == self.config.container_name:
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to check container existence: {str(e)}")
            raise BlobStorageError(f"Failed to check container existence: {str(e)}")
    
    async def upload_state(self, state_id: str, state_data: Dict[str, Any]) -> bool:
        """Upload context state data to blob storage.
        
        Args:
            state_id: Unique identifier for the state
            state_data: Dictionary containing the state data to store
            
        Returns:
            bool: True if upload was successful
            
        Raises:
            BlobStorageError: If upload fails
        """
        try:
            # Ensure container exists
            await self.create_container()
            
            # Convert state data to JSON
            state_json = json.dumps(state_data, indent=2)
            
            # Upload to blob
            client = self._get_blob_service_client()
            blob_name = f"{state_id}.json"
            blob_client = client.get_blob_client(
                container=self.config.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(
                data=state_json,
                overwrite=True,
                content_type="application/json"
            )
            
            logger.info(f"Successfully uploaded state: {state_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload state {state_id}: {str(e)}")
            raise BlobStorageError(f"Failed to upload state: {str(e)}")
    
    async def download_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Download context state data from blob storage.
        
        Args:
            state_id: Unique identifier for the state
            
        Returns:
            Dict[str, Any]: The state data, or None if not found
            
        Raises:
            BlobStorageError: If download fails (other than not found)
        """
        try:
            client = self._get_blob_service_client()
            blob_name = f"{state_id}.json"
            blob_client = client.get_blob_client(
                container=self.config.container_name,
                blob=blob_name
            )
            
            blob_data = blob_client.download_blob().readall()
            state_data = json.loads(blob_data.decode('utf-8'))
            
            logger.info(f"Successfully downloaded state: {state_id}")
            return state_data
            
        except ResourceNotFoundError:
            logger.debug(f"State not found: {state_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to download state {state_id}: {str(e)}")
            raise BlobStorageError(f"Failed to download state: {str(e)}")
    
    async def state_exists(self, state_id: str) -> bool:
        """Check if a context state exists in blob storage.
        
        Args:
            state_id: Unique identifier for the state
            
        Returns:
            bool: True if state exists, False otherwise
            
        Raises:
            BlobStorageError: If check fails
        """
        try:
            client = self._get_blob_service_client()
            blob_name = f"{state_id}.json"
            blob_client = client.get_blob_client(
                container=self.config.container_name,
                blob=blob_name
            )
            
            return blob_client.exists()
            
        except Exception as e:
            logger.error(f"Failed to check state existence {state_id}: {str(e)}")
            raise BlobStorageError(f"Failed to check state existence: {str(e)}")
    
    async def delete_state(self, state_id: str) -> bool:
        """Delete a context state from blob storage.
        
        Args:
            state_id: Unique identifier for the state
            
        Returns:
            bool: True if state was deleted, False if it didn't exist
            
        Raises:
            BlobStorageError: If deletion fails (other than not found)
        """
        try:
            client = self._get_blob_service_client()
            blob_name = f"{state_id}.json"
            blob_client = client.get_blob_client(
                container=self.config.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"Successfully deleted state: {state_id}")
            return True
            
        except ResourceNotFoundError:
            logger.debug(f"State not found for deletion: {state_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete state {state_id}: {str(e)}")
            raise BlobStorageError(f"Failed to delete state: {str(e)}")
    
    async def list_states(self, prefix: Optional[str] = None) -> List[str]:
        """List all context states in blob storage.
        
        Args:
            prefix: Optional prefix to filter state IDs
            
        Returns:
            List[str]: List of state IDs (without .json extension)
            
        Raises:
            BlobStorageError: If listing fails
        """
        try:
            client = self._get_blob_service_client()
            container_client = client.get_container_client(self.config.container_name)
            
            # Build name filter
            name_starts_with = None
            if prefix:
                name_starts_with = f"{prefix}"
            
            # List blobs and extract state IDs
            state_ids = []
            blobs = container_client.list_blobs(name_starts_with=name_starts_with)
            
            for blob in blobs:
                if blob.name.endswith('.json'):
                    state_id = blob.name[:-5]  # Remove .json extension
                    state_ids.append(state_id)
            
            logger.info(f"Listed {len(state_ids)} states with prefix '{prefix or ''}'")
            return state_ids
            
        except ResourceNotFoundError:
            logger.debug(f"Container not found: {self.config.container_name}")
            return []
        except Exception as e:
            logger.error(f"Failed to list states: {str(e)}")
            raise BlobStorageError(f"Failed to list states: {str(e)}")