"""Azure Blob Storage State Management System

This module provides comprehensive state management capabilities for workflows using Azure Blob Storage.
It allows workflows to pause and resume with preserved state across long-running operations.

Key Components:
- BlobStorageClient: Low-level Azure Blob operations
- StateConfig: Configuration management
- StateSerializer: Serialization with compression support
- BlobStateManager: High-level state management
- CheckpointManager: Step-level checkpoint management

Basic Usage:
    from src.state import BlobStateManager
    
    manager = BlobStateManager()
    manager.save_state("workflow-001", {"step": "processing", "progress": 75})
    state = manager.load_state("workflow-001")
"""

import logging

# Configure logging for the state management module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler if no handlers exist
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Export main classes for easy imports
from .blob_client import BlobStorageClient
from .config import StateConfig
from .serialization import StateSerializer
from .manager import BlobStateManager
from .checkpoints import CheckpointManager

__all__ = [
    'BlobStorageClient',
    'StateConfig', 
    'StateSerializer',
    'BlobStateManager',
    'CheckpointManager'
]

__version__ = '1.0.0'