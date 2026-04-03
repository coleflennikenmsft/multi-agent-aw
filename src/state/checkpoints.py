"""Checkpoint management for step-level workflow recovery

Provides checkpoint creation and restoration capabilities for fine-grained
workflow state management at specific execution steps.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone
import uuid

from .blob_client import BlobStorageClient
from .config import StateConfig
from .serialization import StateSerializer, SerializationFormat

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoints for step-level workflow state recovery.
    
    Allows creating, restoring, and managing checkpoints at specific workflow steps
    for fine-grained recovery capabilities.
    """
    
    def __init__(self, config: Optional[StateConfig] = None,
                 serializer: Optional[StateSerializer] = None):
        """Initialize the checkpoint manager.
        
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
        
        logger.info("CheckpointManager initialized")
    
    def _ensure_initialized(self) -> None:
        """Ensure the manager is properly initialized."""
        if not self._initialized:
            try:
                # Test connection by checking if container exists or can be created
                self.blob_client._get_container_client()
                self._initialized = True
                logger.info("CheckpointManager connection verified")
            except Exception as e:
                logger.error(f"Failed to initialize CheckpointManager: {e}")
                raise
    
    def create_checkpoint(self, workflow_id: str, step: str, data: Dict[str, Any],
                         metadata: Optional[Dict[str, Any]] = None,
                         overwrite: bool = True) -> bool:
        """Create a checkpoint at a specific workflow step.
        
        Args:
            workflow_id: Unique identifier for the workflow
            step: Name/identifier of the workflow step
            data: Checkpoint data to save
            metadata: Additional metadata to include
            overwrite: Whether to overwrite existing checkpoint
            
        Returns:
            True if checkpoint created successfully, False otherwise
        """
        try:
            self._ensure_initialized()
            
            # Generate checkpoint blob name
            blob_name = self._get_checkpoint_blob_name(workflow_id, step)
            
            # Check if checkpoint already exists and overwrite is False
            if not overwrite and self.blob_client.blob_exists(blob_name):
                logger.warning(f"Checkpoint already exists for {workflow_id}:{step} "
                              f"and overwrite=False")
                return False
            
            # Prepare checkpoint metadata
            checkpoint_metadata = {
                'workflow_id': workflow_id,
                'step': step,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'checkpoint_id': str(uuid.uuid4()),
                'size_bytes': 0,  # Will be set after serialization
                **(metadata or {})
            }
            
            # Serialize checkpoint data with metadata
            try:
                serialized_data = self.serializer.serialize_with_metadata(
                    data, checkpoint_metadata
                )
                checkpoint_metadata['size_bytes'] = len(serialized_data)
            except Exception as e:
                logger.error(f"Failed to serialize checkpoint for {workflow_id}:{step}: {e}")
                return False
            
            # Upload to blob storage
            success = self.blob_client.upload_blob(blob_name, serialized_data, overwrite=overwrite)
            
            if success:
                logger.info(f"Successfully created checkpoint for {workflow_id}:{step} "
                           f"(size: {len(serialized_data)} bytes)")
                return True
            else:
                logger.error(f"Failed to upload checkpoint for {workflow_id}:{step}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating checkpoint for {workflow_id}:{step}: {e}")
            return False
    
    def restore_from_checkpoint(self, workflow_id: str, step: str) -> Optional[Dict[str, Any]]:
        """Restore data from a checkpoint.
        
        Args:
            workflow_id: Unique identifier for the workflow
            step: Name/identifier of the workflow step
            
        Returns:
            Checkpoint data if found, None otherwise
        """
        try:
            self._ensure_initialized()
            
            # Generate checkpoint blob name
            blob_name = self._get_checkpoint_blob_name(workflow_id, step)
            
            # Download from blob storage
            serialized_data = self.blob_client.download_blob(blob_name)
            
            if serialized_data is None:
                logger.warning(f"No checkpoint found for {workflow_id}:{step}")
                return None
            
            # Deserialize checkpoint data
            try:
                checkpoint_data, metadata = self.serializer.deserialize_with_metadata(serialized_data)
                logger.info(f"Successfully restored checkpoint for {workflow_id}:{step} "
                           f"(size: {len(serialized_data)} bytes, "
                           f"created: {metadata.get('timestamp', 'unknown')})")
                return checkpoint_data
            except Exception as e:
                logger.error(f"Failed to deserialize checkpoint for {workflow_id}:{step}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error restoring checkpoint for {workflow_id}:{step}: {e}")
            return None
    
    def list_checkpoints(self, workflow_id: str) -> List[Dict[str, Any]]:
        """List all checkpoints for a workflow.
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            List of checkpoint information dictionaries
        """
        try:
            self._ensure_initialized()
            
            prefix = f"checkpoints/{workflow_id}/"
            blobs = self.blob_client.list_blobs(prefix, include_metadata=True)
            
            checkpoints = []
            for blob_info in blobs:
                # Parse blob name to extract step info
                name_parts = blob_info['name'].split('/')
                if len(name_parts) >= 3:
                    step_file = name_parts[2]
                    step = step_file.replace('.checkpoint', '')
                    
                    checkpoint_info = {
                        'workflow_id': workflow_id,
                        'step': step,
                        'blob_name': blob_info['name'],
                        'size': blob_info['size'],
                        'last_modified': blob_info['last_modified'],
                        'metadata': blob_info.get('metadata', {})
                    }
                    checkpoints.append(checkpoint_info)
            
            # Sort by last_modified, newest first
            checkpoints.sort(key=lambda x: x['last_modified'], reverse=True)
            
            logger.info(f"Found {len(checkpoints)} checkpoints for workflow {workflow_id}")
            return checkpoints
            
        except Exception as e:
            logger.error(f"Error listing checkpoints for workflow {workflow_id}: {e}")
            return []
    
    def delete_checkpoint(self, workflow_id: str, step: str) -> bool:
        """Delete a specific checkpoint.
        
        Args:
            workflow_id: Unique identifier for the workflow
            step: Name/identifier of the workflow step
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            self._ensure_initialized()
            
            blob_name = self._get_checkpoint_blob_name(workflow_id, step)
            success = self.blob_client.delete_blob(blob_name)
            
            if success:
                logger.info(f"Successfully deleted checkpoint for {workflow_id}:{step}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting checkpoint for {workflow_id}:{step}: {e}")
            return False
    
    def delete_all_checkpoints(self, workflow_id: str) -> bool:
        """Delete all checkpoints for a workflow.
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            True if all deletions successful, False otherwise
        """
        try:
            self._ensure_initialized()
            
            # List all checkpoints for the workflow
            prefix = f"checkpoints/{workflow_id}/"
            blobs = self.blob_client.list_blobs(prefix)
            
            success_count = 0
            for blob_info in blobs:
                if self.blob_client.delete_blob(blob_info['name']):
                    success_count += 1
            
            logger.info(f"Deleted {success_count}/{len(blobs)} checkpoints "
                       f"for workflow {workflow_id}")
            return success_count == len(blobs)
            
        except Exception as e:
            logger.error(f"Error deleting all checkpoints for workflow {workflow_id}: {e}")
            return False
    
    def checkpoint_exists(self, workflow_id: str, step: str) -> bool:
        """Check if a checkpoint exists for a specific step.
        
        Args:
            workflow_id: Unique identifier for the workflow
            step: Name/identifier of the workflow step
            
        Returns:
            True if checkpoint exists, False otherwise
        """
        try:
            self._ensure_initialized()
            
            blob_name = self._get_checkpoint_blob_name(workflow_id, step)
            return self.blob_client.blob_exists(blob_name)
            
        except Exception as e:
            logger.error(f"Error checking if checkpoint exists for {workflow_id}:{step}: {e}")
            return False
    
    def get_checkpoint_metadata(self, workflow_id: str, step: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a checkpoint without loading the full data.
        
        Args:
            workflow_id: Unique identifier for the workflow
            step: Name/identifier of the workflow step
            
        Returns:
            Metadata dictionary if found, None otherwise
        """
        try:
            self._ensure_initialized()
            
            blob_name = self._get_checkpoint_blob_name(workflow_id, step)
            return self.blob_client.get_blob_metadata(blob_name)
            
        except Exception as e:
            logger.error(f"Error getting checkpoint metadata for {workflow_id}:{step}: {e}")
            return None
    
    def list_workflow_steps(self, workflow_id: str) -> Set[str]:
        """Get a set of all step names that have checkpoints.
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            Set of step names with checkpoints
        """
        try:
            checkpoints = self.list_checkpoints(workflow_id)
            return {cp['step'] for cp in checkpoints}
        except Exception as e:
            logger.error(f"Error listing workflow steps for {workflow_id}: {e}")
            return set()
    
    def cleanup_old_checkpoints(self, workflow_id: str, keep_latest: int = 10) -> int:
        """Clean up old checkpoints, keeping only the most recent ones.
        
        Args:
            workflow_id: Unique identifier for the workflow
            keep_latest: Number of latest checkpoints to keep per step
            
        Returns:
            Number of checkpoints deleted
        """
        try:
            self._ensure_initialized()
            
            checkpoints = self.list_checkpoints(workflow_id)
            
            # Group checkpoints by step
            step_checkpoints = {}
            for cp in checkpoints:
                step = cp['step']
                if step not in step_checkpoints:
                    step_checkpoints[step] = []
                step_checkpoints[step].append(cp)
            
            deleted_count = 0
            
            # For each step, keep only the latest N checkpoints
            for step, step_cps in step_checkpoints.items():
                # Sort by last_modified, newest first
                step_cps.sort(key=lambda x: x['last_modified'], reverse=True)
                
                # Delete old checkpoints beyond keep_latest
                for cp in step_cps[keep_latest:]:
                    if self.blob_client.delete_blob(cp['blob_name']):
                        deleted_count += 1
                        logger.debug(f"Deleted old checkpoint: {cp['blob_name']}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old checkpoints for workflow {workflow_id}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up checkpoints for workflow {workflow_id}: {e}")
            return 0
    
    def _get_checkpoint_blob_name(self, workflow_id: str, step: str) -> str:
        """Generate blob name for checkpoint storage.
        
        Args:
            workflow_id: Workflow identifier
            step: Step identifier
            
        Returns:
            Blob name string
        """
        # Sanitize step name for blob storage
        safe_step = step.replace('/', '_').replace('\\', '_').replace(' ', '_')
        return f"checkpoints/{workflow_id}/{safe_step}.checkpoint"