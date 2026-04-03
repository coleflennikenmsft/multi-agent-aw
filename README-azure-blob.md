# Azure Blob State Management Integration

This project supports workflow context state management using Azure Blob Storage.

## Configuration

Set the following environment variables (see `.env.example`):

````
AZURE_STORAGE_CONNECTION_STRING=<connection-string>
# OR for managed identity:
AZURE_STORAGE_ACCOUNT_NAME=<account-name>
AZURE_STORAGE_CONTAINER_NAME=<container-name>
````

## Usage Example

````python
from state.utils import get_context_manager

workflow_id = "my-workflow"
context_manager = get_context_manager(workflow_id)
if context_manager:
    # Save state
    blob_name = context_manager.save_state({"foo": "bar"})
    # List states
    blobs = context_manager.list_states()
    # Load state
    loaded = context_manager.load_state(blob_name)
    # Delete state
    context_manager.delete_state(blob_name)
else:
    print("Azure Blob Storage not configured.")
````

## Notes
- If Azure Blob is not configured, state management is skipped gracefully.
- State is versioned and stored as JSON.
- See inline docstrings for more details.
