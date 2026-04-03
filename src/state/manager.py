"""High-level state management for Azure Blob Storage

Provides the main BlobStateManager class for saving, loading, and managing workflow states
with versioning, metadata, and error handling.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import uuid

from .blob_client import BlobStorageClient
from .config import StateConfig
from .serialization import StateSerializer, SerializationFormat

logger = logging.getLogger(__name__)


class BlobStateManager:
    """High-level state management using Azure Blob Storage.
    
    Provides save/load/delete operations for workflow states with automatic
    versioning, metadata injection, and error handling.
    """
    
    def __init__(self, config: Optional[StateConfig] = None,
                 serializer: Optional[StateSerializer] = None):
        """Initialize the state manager.
        
        Args:
            config: StateConfig instance. If None, loads from environment.
            serializer: StateSerializer instance. If None, creates default.
        """
        self.config = config or StateConfig.from_env()
        self.blob_client = BlobStorageClient(self.config)
        self.serializer = serializer or StateSerializer(
            default_format=SerializationFormat.JSON,
            use_compression=True
        )
        self._initialized = False
        
        logger.info("BlobStateManager initialized")
    
    def _ensure_initialized(self) -> None:
        """Ensure the manager is properly initialized."""
        if not self._initialized:
            try:
                # Test connection by checking if container exists or can be created
                self.blob_client._get_container_client()
                self._initialized = True
                logger.info("BlobStateManager connection verified")
            except Exception as e:
                logger.error(f"Failed to initialize BlobStateManager: {e}")
                raise
    
    def save_state(self, workflow_id: str, state: Dict[str, Any],
                   create_snapshot: bool = False, 
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save workflow state to Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow
            state: State data to save
            create_snapshot: Whether to create a versioned snapshot
            metadata: Additional metadata to include
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            self._ensure_initialized()
            
            # Generate blob name
            blob_name = self._get_state_blob_name(workflow_id, create_snapshot)
            
            # Prepare metadata
            save_metadata = {
                'workflow_id': workflow_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': str(uuid.uuid4()) if create_snapshot else 'latest',
                'size_bytes': 0,  # Will be set after serialization
                **(metadata or {})
            }
            
            # Serialize data with metadata
            try:
                serialized_data = self.serializer.serialize_with_metadata(
                    state, save_metadata
                )
                save_metadata['size_bytes'] = len(serialized_data)
            except Exception as e:
                logger.error(f"Failed to serialize state for workflow {workflow_id}: {e}")
                return False
            
            # Upload to blob storage
            success = self.blob_client.upload_blob(blob_name, serialized_data, overwrite=True)
            
            if success:
                logger.info(f"Successfully saved state for workflow {workflow_id} "
                           f"(blob: {blob_name}, size: {len(serialized_data)} bytes)")
                
                # Also save as latest if this was a snapshot
                if create_snapshot:
                    latest_blob_name = self._get_state_blob_name(workflow_id, False)
                    self.blob_client.upload_blob(latest_blob_name, serialized_data, overwrite=True)
                    logger.info(f"Also saved as latest: {latest_blob_name}")
                
                return True
            else:
                logger.error(f"Failed to upload state for workflow {workflow_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving state for workflow {workflow_id}: {e}")
            return False
    
    def load_state(self, workflow_id: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load workflow state from Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow
            version: Specific version to load (None for latest)
            
        Returns:
            State data if found, None otherwise
        """
        try:
            self._ensure_initialized()
            
            # Determine blob name
            if version:
                blob_name = f"states/{workflow_id}/{version}.state"
            else:
                blob_name = self._get_state_blob_name(workflow_id, False)
            
            # Download from blob storage
            serialized_data = self.blob_client.download_blob(blob_name)
            
            if serialized_data is None:
                logger.warning(f"No state found for workflow {workflow_id} "
                             f"(version: {version or 'latest'})")
                return None
            
            # Deserialize data
            try:
                state_data, metadata = self.serializer.deserialize_with_metadata(serialized_data)
                logger.info(f"Successfully loaded state for workflow {workflow_id} "
                           f"(version: {version or 'latest'}, "
                           f"size: {len(serialized_data)} bytes)")
                return state_data
            except Exception as e:
                logger.error(f"Failed to deserialize state for workflow {workflow_id}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading state for workflow {workflow_id}: {e}")
            return None
    
    def delete_state(self, workflow_id: str, version: Optional[str] = None,
                     delete_all_versions: bool = False) -> bool:
        """Delete workflow state from Azure Blob Storage.
        
        Args:
            workflow_id: Unique identifier for the workflow
            version: Specific version to delete (None for latest)
            delete_all_versions: Whether to delete all versions
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            self._ensure_initialized()
            
            if delete_all_versions:
                # Delete all blobs with the workflow prefix
                prefix = f"states/{workflow_id}/"
                blobs = self.blob_client.list_blobs(prefix)
                
                success_count = 0
                for blob_info in blobs:
                    if self.blob_client.delete_blob(blob_info['name']):
                        success_count += 1
                
                logger.info(f"Deleted {success_count}/{len(blobs)} state versions "
                           f"for workflow {workflow_id}")
                return success_count == len(blobs)
            
            else:
                # Delete specific version or latest
                if version:
                    blob_name = f"states/{workflow_id}/{version}.state"
                else:
                    blob_name = self._get_state_blob_name(workflow_id, False)
                
                success = self.blob_client.delete_blob(blob_name)
                
                if success:
                    logger.info(f"Successfully deleted state for workflow {workflow_id} "
                               f"(version: {version or 'latest'})")
                
                return success
                
        except Exception as e:
            logger.error(f"Error deleting state for workflow {workflow_id}: {e}")
            return False
    
    def list_states(self, workflow_id_prefix: str = "") -> List[Dict[str, Any]]:
        """List all saved workflow states.
        
        Args:
            workflow_id_prefix: Filter by workflow ID prefix
            
        Returns:
            List of state information dictionaries
        """
        try:
            self._ensure_initialized()
            
            prefix = f"states/{workflow_id_prefix}" if workflow_id_prefix else "states/"
            blobs = self.blob_client.list_blobs(prefix, include_metadata=True)
            
            states = []
            for blob_info in blobs:
                # Parse blob name to extract workflow info
                name_parts = blob_info['name'].split('/')
                if len(name_parts) >= 2:
                    workflow_id = name_parts[1]
                    is_snapshot = len(name_parts) > 2 and name_parts[2] != 'latest.state'
                    
                    state_info = {
                        'workflow_id': workflow_id,
                        'blob_name': blob_info['name'],
                        'size': blob_info['size'],
                        'last_modified': blob_info['last_modified'],
                        'is_snapshot': is_snapshot,
                        'metadata': blob_info.get('metadata', {})
                    }
                    states.append(state_info)
            
            logger.info(f"Listed {len(states)} workflow states")
            return states
            
        except Exception as e:
            logger.error(f"Error listing states: {e}")
            return []
    
    def list_versions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """List all versions of a specific workflow state.
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            List of version information dictionaries
        """
        try:
            self._ensure_initialized()
            
            prefix = f"states/{workflow_id}/"
            blobs = self.blob_client.list_blobs(prefix, include_metadata=True)
            
            versions = []
            for blob_info in blobs:
                name_parts = blob_info['name'].split('/')
                if len(name_parts) >= 3:
                    version_file = name_parts[2]
                    version = version_file.replace('.state', '')
                    
                    version_info = {
                        'version': version,
                        'is_latest': version == 'latest',
                        'blob_name': blob_info['name'],
                        'size': blob_info['size'],
                        'last_modified': blob_info['last_modified'],
                        'metadata': blob_info.get('metadata', {})
                    }
                    versions.append(version_info)
            
            # Sort by last_modified, latest first
            versions.sort(key=lambda x: x['last_modified'], reverse=True)
            
            logger.info(f"Found {len(versions)} versions for workflow {workflow_id}")
            return versions
            
        except Exception as e:
            logger.error(f"Error listing versions for workflow {workflow_id}: {e}")
            return []
    
    def get_state_metadata(self, workflow_id: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get metadata for a workflow state without loading the full state.
        
        Args:
            workflow_id: Unique identifier for the workflow
            version: Specific version (None for latest)
            
        Returns:
            Metadata dictionary if found, None otherwise
        """
        try:
            self._ensure_initialized()
            
            if version:
                blob_name = f"states/{workflow_id}/{version}.state"
            else:
                blob_name = self._get_state_blob_name(workflow_id, False)
            
            return self.blob_client.get_blob_metadata(blob_name)
            
        except Exception as e:
            logger.error(f"Error getting metadata for workflow {workflow_id}: {e}")
            return None
    
    def _get_state_blob_name(self, workflow_id: str, is_snapshot: bool) -> str:
        """Generate blob name for state storage.
        
        Args:
            workflow_id: Workflow identifier
            is_snapshot: Whether this is a versioned snapshot
            
        Returns:
            Blob name string
        """
        if is_snapshot:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            return f"states/{workflow_id}/{timestamp}_{uuid.uuid4().hex[:8]}.state"
        else:
            return f"states/{workflow_id}/latest.state"