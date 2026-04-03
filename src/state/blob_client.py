"""Azure Blob Storage Client Wrapper

Provides a clean interface for Azure Blob Storage operations with error handling,
retry logic, and automatic container creation.
"""

import logging
from typing import List, Optional, Dict, Any
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import (
    AzureError, 
    ResourceNotFoundError, 
    ResourceExistsError,
    ClientAuthenticationError
)
import time

from .config import StateConfig

logger = logging.getLogger(__name__)


class BlobStorageClient:
    """Azure Blob Storage client wrapper with enhanced error handling and operations."""
    
    def __init__(self, config: Optional[StateConfig] = None):
        """Initialize the blob storage client.
        
        Args:
            config: StateConfig instance. If None, loads from environment.
        """
        self.config = config or StateConfig.from_env()
        self._service_client: Optional[BlobServiceClient] = None
        self._container_client: Optional[ContainerClient] = None
        
    def _get_service_client(self) -> BlobServiceClient:
        """Get or create the blob service client."""
        if self._service_client is None:
            try:
                if self.config.connection_string:
                    self._service_client = BlobServiceClient.from_connection_string(
                        self.config.connection_string
                    )
                else:
                    # Use account name/key authentication
                    account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                    self._service_client = BlobServiceClient(
                        account_url=account_url,
                        credential=self.config.account_key
                    )
                logger.info("Azure Blob Storage client initialized successfully")
            except ClientAuthenticationError as e:
                logger.error(f"Failed to authenticate with Azure Blob Storage: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize blob service client: {e}")
                raise
                
        return self._service_client
    
    def _get_container_client(self) -> ContainerClient:
        """Get or create the container client."""
        if self._container_client is None:
            service_client = self._get_service_client()
            self._container_client = service_client.get_container_client(
                self.config.container_name
            )
            
            # Ensure container exists
            self._ensure_container_exists()
                
        return self._container_client
    
    def _ensure_container_exists(self) -> None:
        """Ensure the storage container exists, create if necessary."""
        try:
            container_client = self._container_client
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.config.container_name}")
            else:
                logger.debug(f"Container exists: {self.config.container_name}")
        except ResourceExistsError:
            # Container already exists, which is fine
            logger.debug(f"Container already exists: {self.config.container_name}")
        except Exception as e:
            logger.error(f"Failed to ensure container exists: {e}")
            raise
    
    def upload_blob(self, blob_name: str, data: bytes, overwrite: bool = True) -> bool:
        """Upload data to a blob.
        
        Args:
            blob_name: Name of the blob
            data: Data to upload as bytes
            overwrite: Whether to overwrite if blob exists
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            blob_client.upload_blob(data, overwrite=overwrite)
            logger.info(f"Successfully uploaded blob: {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload blob {blob_name}: {e}")
            return False
    
    def download_blob(self, blob_name: str) -> Optional[bytes]:
        """Download data from a blob.
        
        Args:
            blob_name: Name of the blob to download
            
        Returns:
            Blob data as bytes, or None if download failed
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
        except Exception as e:
            logger.error(f"Failed to download blob {blob_name}: {e}")
            return None
    
    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob.
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            blob_client.delete_blob()
            logger.info(f"Successfully deleted blob: {blob_name}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {blob_name}")
            return True  # Consider missing blob as successfully deleted
        except Exception as e:
            logger.error(f"Failed to delete blob {blob_name}: {e}")
            return False
    
    def list_blobs(self, prefix: str = "", include_metadata: bool = False) -> List[Dict[str, Any]]:
        """List blobs in the container.
        
        Args:
            prefix: Filter blobs by prefix
            include_metadata: Whether to include blob metadata
            
        Returns:
            List of blob information dictionaries
        """
        try:
            container_client = self._get_container_client()
            
            blobs = []
            for blob_properties in container_client.list_blobs(
                name_starts_with=prefix,
                include=['metadata'] if include_metadata else None
            ):
                blob_info = {
                    'name': blob_properties.name,
                    'size': blob_properties.size,
                    'last_modified': blob_properties.last_modified,
                    'content_type': blob_properties.content_settings.content_type if blob_properties.content_settings else None,
                }
                
                if include_metadata and blob_properties.metadata:
                    blob_info['metadata'] = blob_properties.metadata
                    
                blobs.append(blob_info)
            
            logger.info(f"Listed {len(blobs)} blobs with prefix '{prefix}'")
            return blobs
            
        except Exception as e:
            logger.error(f"Failed to list blobs with prefix '{prefix}': {e}")
            return []
    
    def blob_exists(self, blob_name: str) -> bool:
        """Check if a blob exists.
        
        Args:
            blob_name: Name of the blob to check
            
        Returns:
            True if blob exists, False otherwise
        """
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            return blob_client.exists()
            
        except Exception as e:
            logger.error(f"Failed to check if blob exists {blob_name}: {e}")
            return False
    
    def get_blob_metadata(self, blob_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific blob.
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            Blob metadata dictionary, or None if failed
        """
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            properties = blob_client.get_blob_properties()
            return {
                'name': blob_name,
                'size': properties.size,
                'last_modified': properties.last_modified,
                'content_type': properties.content_settings.content_type if properties.content_settings else None,
                'metadata': properties.metadata or {}
            }
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get metadata for blob {blob_name}: {e}")
            return None