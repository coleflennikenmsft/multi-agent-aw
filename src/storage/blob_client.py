"""Azure Blob Storage client for state management."""

import json
from typing import Optional, List, Dict, Any
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from azure.identity import DefaultAzureCredential

from .config import StorageConfig


class BlobStorageClient:
    """Client for managing state storage in Azure Blob Storage.
    
    Provides operations for uploading, downloading, and managing state data
    stored as JSON blobs in Azure Blob Storage.
    
    Supports two authentication methods:
    1. Connection string (AZURE_STORAGE_CONNECTION_STRING)
    2. Managed identity (AZURE_STORAGE_ACCOUNT_NAME or AZURE_STORAGE_ACCOUNT_URL)
    
    Example:
        # Using connection string
        config = StorageConfig.from_environment()
        client = BlobStorageClient(config)
        await client.upload_state("my-state", {"key": "value"})
        
        # Using managed identity
        config = StorageConfig(account_name="mystorageaccount")
        client = BlobStorageClient(config)
        state = await client.download_state("my-state")
    """
    
    def __init__(self, config: StorageConfig):
        """Initialize the BlobStorageClient.
        
        Args:
            config: Storage configuration
            
        Raises:
            ValueError: If configuration is invalid
        """
        config.validate()
        self.config = config
        self._service_client: Optional[BlobServiceClient] = None
        self._container_client: Optional[ContainerClient] = None
    
    def _get_service_client(self) -> BlobServiceClient:
        """Get or create the BlobServiceClient.
        
        Returns:
            BlobServiceClient instance
            
        Raises:
            ValueError: If authentication configuration is invalid
        """
        if self._service_client is None:
            if self.config.has_connection_string():
                self._service_client = BlobServiceClient.from_connection_string(
                    self.config.connection_string
                )
            elif self.config.has_managed_identity_config():
                credential = DefaultAzureCredential()
                if self.config.account_url:
                    account_url = self.config.account_url
                elif self.config.account_name:
                    account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                else:
                    raise ValueError("Either account_url or account_name must be set")
                
                self._service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
            else:
                raise ValueError("No valid authentication configuration found")
        
        return self._service_client
    
    def _get_container_client(self) -> ContainerClient:
        """Get or create the ContainerClient for the configured container.
        
        Returns:
            ContainerClient instance
        """
        if self._container_client is None:
            service_client = self._get_service_client()
            self._container_client = service_client.get_container_client(
                self.config.container_name
            )
        return self._container_client
    
    def _get_blob_client(self, blob_name: str) -> BlobClient:
        """Get a BlobClient for a specific blob.
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            BlobClient instance
        """
        container_client = self._get_container_client()
        return container_client.get_blob_client(blob_name)
    
    async def create_container(self) -> bool:
        """Create the storage container if it doesn't exist.
        
        Returns:
            True if container was created, False if it already existed
            
        Raises:
            Exception: If container creation fails for reasons other than already existing
        """
        try:
            container_client = self._get_container_client()
            container_client.create_container()
            return True
        except ResourceExistsError:
            return False
    
    async def container_exists(self) -> bool:
        """Check if the storage container exists.
        
        Returns:
            True if container exists, False otherwise
        """
        try:
            container_client = self._get_container_client()
            container_client.get_container_properties()
            return True
        except ResourceNotFoundError:
            return False
    
    async def upload_state(
        self,
        state_name: str,
        state_data: Dict[str, Any],
        overwrite: bool = True
    ) -> None:
        """Upload state data to blob storage.
        
        Args:
            state_name: Name/identifier for the state (will be used as blob name)
            state_data: Dictionary containing the state data to store
            overwrite: Whether to overwrite existing state (default: True)
            
        Raises:
            ResourceExistsError: If state exists and overwrite=False
            ValueError: If state_data cannot be serialized to JSON
            Exception: If upload fails
        """
        if not state_name:
            raise ValueError("state_name cannot be empty")
        
        # Ensure state_name has .json extension
        blob_name = state_name if state_name.endswith('.json') else f"{state_name}.json"
        
        try:
            # Serialize state data to JSON
            json_data = json.dumps(state_data, indent=2)
            
            # Upload to blob storage
            blob_client = self._get_blob_client(blob_name)
            blob_client.upload_blob(json_data, overwrite=overwrite)
            
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize state data to JSON: {e}")
    
    async def download_state(self, state_name: str) -> Dict[str, Any]:
        """Download state data from blob storage.
        
        Args:
            state_name: Name/identifier of the state to retrieve
            
        Returns:
            Dictionary containing the state data
            
        Raises:
            ResourceNotFoundError: If state does not exist
            ValueError: If state data is not valid JSON
            Exception: If download fails
        """
        if not state_name:
            raise ValueError("state_name cannot be empty")
        
        # Ensure state_name has .json extension
        blob_name = state_name if state_name.endswith('.json') else f"{state_name}.json"
        
        try:
            blob_client = self._get_blob_client(blob_name)
            blob_data = blob_client.download_blob()
            content = blob_data.readall()
            
            # Parse JSON data
            return json.loads(content)
            
        except ResourceNotFoundError:
            raise ResourceNotFoundError(f"State '{state_name}' not found")
        except json.JSONDecodeError as e:
            raise ValueError(f"State data is not valid JSON: {e}")
    
    async def state_exists(self, state_name: str) -> bool:
        """Check if a state exists in blob storage.
        
        Args:
            state_name: Name/identifier of the state to check
            
        Returns:
            True if state exists, False otherwise
        """
        if not state_name:
            return False
        
        # Ensure state_name has .json extension
        blob_name = state_name if state_name.endswith('.json') else f"{state_name}.json"
        
        try:
            blob_client = self._get_blob_client(blob_name)
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
    
    async def delete_state(self, state_name: str) -> bool:
        """Delete a state from blob storage.
        
        Args:
            state_name: Name/identifier of the state to delete
            
        Returns:
            True if state was deleted, False if it didn't exist
            
        Raises:
            Exception: If deletion fails for reasons other than not existing
        """
        if not state_name:
            raise ValueError("state_name cannot be empty")
        
        # Ensure state_name has .json extension
        blob_name = state_name if state_name.endswith('.json') else f"{state_name}.json"
        
        try:
            blob_client = self._get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False
    
    async def list_states(self, prefix: Optional[str] = None) -> List[str]:
        """List all states in the container.
        
        Args:
            prefix: Optional prefix to filter state names
            
        Returns:
            List of state names (without .json extension)
            
        Raises:
            Exception: If listing fails
        """
        container_client = self._get_container_client()
        
        try:
            blob_list = container_client.list_blobs(name_starts_with=prefix)
            
            # Remove .json extension from blob names
            state_names = []
            for blob in blob_list:
                name = blob.name
                if name.endswith('.json'):
                    name = name[:-5]  # Remove .json extension
                state_names.append(name)
            
            return state_names
            
        except Exception as e:
            raise Exception(f"Failed to list states: {e}")
    
    def close(self) -> None:
        """Close the client and release resources."""
        if self._service_client:
            self._service_client.close()
            self._service_client = None
            self._container_client = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
