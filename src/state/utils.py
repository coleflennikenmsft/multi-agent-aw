"""
Helper utilities for state checkpoint creation and environment configuration.

Usage:
    from state.utils import get_context_manager
    manager = get_context_manager('workflow-id')
    if manager:
        blob_name = manager.save_state({'foo': 'bar'})
        ...
"""
import os
from .blob_client import AzureBlobClient
from .context_manager import ContextManager

def get_blob_client() -> AzureBlobClient:
    """Return AzureBlobClient or None if not configured."""
    try:
        return AzureBlobClient()
    except Exception:
        return None

def get_context_manager(workflow_id: str):
    """Return ContextManager or None if Azure Blob is not configured."""
    blob_client = get_blob_client()
    if blob_client is None:
        return None
    return ContextManager(blob_client, workflow_id)
