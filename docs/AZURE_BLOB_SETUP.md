# Azure Blob Storage Setup for State Management

This guide explains how to configure Azure Blob Storage for workflow state persistence.

## Prerequisites
- Azure subscription
- Storage account with Blob service enabled
- Container (default: `workflow-states`)

## Authentication Methods
1. **Managed Identity** (recommended for Azure-hosted runners)
   - No secrets required. Uses Azure DefaultAzureCredential.
2. **Connection String**
   - Set `AZURE_STORAGE_CONNECTION_STRING` environment variable.
3. **Account Name & Key**
   - Set `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY` environment variables.
4. **SAS Token** (not recommended for full workflow state)

## Required Environment Variables
Set one of the following authentication methods:

### Managed Identity
- `AZURE_STORAGE_ACCOUNT_NAME`

### Connection String
- `AZURE_STORAGE_CONNECTION_STRING`

### Account Name & Key
- `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_STORAGE_ACCOUNT_KEY`

## Permissions
- The identity or key must have read/write/delete/list permissions on the container.

## Example Usage
```python
from src.storage.state_manager import StateManager
sm = StateManager()
state = {"workflow_id": "abc123", "status": "paused", ...}
sm.save_state("abc123", state)
loaded = sm.load_state("abc123")
```

## Troubleshooting
- Ensure environment variables are set in your workflow or local environment.
- Check Azure Portal for storage account and container existence.
- Review logs for authentication or network errors.
