# Azure Blob Storage Integration for Context State Management

## Overview
This module provides a `BlobStorageClient` class for managing context state in Azure Blob Storage. It is designed as a foundation for future integration and does not affect existing workflows.

## Installation
Add the following to your `requirements.txt`:

````
azure-storage-blob
````

Install dependencies:

````bash
pip install -r requirements.txt
````

## Environment Variables
The following environment variables are supported:
- `AZURE_STORAGE_CONNECTION_STRING`: Full connection string for Azure Storage account.
- `AZURE_STORAGE_ACCOUNT_NAME`: Storage account name (optional, for managed identity scenarios).
- `AZURE_STORAGE_ACCOUNT_URL`: Storage account URL (optional, for managed identity scenarios).

## Usage Example
````python
from storage.blob_client import BlobStorageClient

# Initialize client
client = BlobStorageClient(container_name="context-states")

# Create container if needed
client.create_container()

# Upload state
client.upload_state("state1.json", b"my state data")

# Download state
state_data = client.download_state("state1.json")

# List all states
states = client.list_states()

# Delete state
client.delete_state("state1.json")
````

## API Reference
### `BlobStorageClient(container_name: str)`
- Initializes the client using either connection string or account URL.

### `create_container()`
- Creates the container if it does not exist.

### `container_exists() -> bool`
- Checks if the container exists.

### `upload_state(state_name: str, data: bytes)`
- Uploads a state blob.

### `download_state(state_name: str) -> Optional[bytes]`
- Downloads a state blob. Returns `None` if not found.

### `state_exists(state_name: str) -> bool`
- Checks if a state blob exists.

### `delete_state(state_name: str)`
- Deletes a state blob.

### `list_states() -> List[str]`
- Lists all state blob names in the container.

## Error Handling
All methods raise `RuntimeError` with descriptive messages on failure. Defensive checks are in place for connection and existence.

## Type Hints
All public methods use Python type hints for clarity and static analysis.

## Notes
- This module is a foundation for future integration. No breaking changes to existing code.
- For questions or issues, see the code comments and docstrings.
