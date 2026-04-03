# Azure Blob Storage State Management System

This module provides a robust state management system using Azure Blob Storage, supporting workflow pause/resume, checkpointing, and versioning.

## Features
- Upload, download, delete, and list blobs
- Automatic container creation
- State serialization (JSON, pickle, gzip)
- Versioning and checkpoint management
- Metadata support
- Configurable via environment variables

## Configuration
Set the following environment variables:
- `AZURE_STORAGE_CONNECTION_STRING` (or)
- `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_STORAGE_CONTAINER_NAME` (default: `state-management`)

## Usage Example
See `examples/state_management_demo.py` for a full example.

## API
- `BlobStorageClient`: Low-level blob operations
- `StateConfig`: Loads and validates configuration
- `StateSerializer`: Handles serialization and compression
- `BlobStateManager`: High-level state save/load/delete/version
- `CheckpointManager`: Checkpoint creation, restore, list, delete
