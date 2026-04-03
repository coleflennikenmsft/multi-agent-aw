# Azure Blob Storage Setup for Workflow State Management

This guide explains how to configure Azure Blob Storage for workflow state persistence in the multi-agent workflow system.

## Overview

The Azure Blob Storage integration allows workflows to:
- Save state data during execution
- Resume workflows from saved checkpoints
- Store workflow context across long-running operations
- Persist state across GitHub Actions runs

## Prerequisites

1. **Azure Storage Account**: You need an Azure Storage Account with Blob Storage enabled
2. **Authentication**: One of the following authentication methods configured
3. **Permissions**: The account/identity needs read/write access to blob containers

## Authentication Methods

The system supports multiple authentication methods in order of preference:

### 1. Connection String (Recommended for GitHub Actions)

Set the `AZURE_STORAGE_CONNECTION_STRING` environment variable:

```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=mystorageaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
```

**In GitHub Actions**, add this as a repository secret and reference it:

```yaml
env:
  AZURE_STORAGE_CONNECTION_STRING: ${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}
```

### 2. Account Name and Key

Set both environment variables:

```bash
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
export AZURE_STORAGE_ACCOUNT_KEY="myaccountkey"
```

### 3. Managed Identity (Azure-hosted runners)

For workflows running on Azure (like self-hosted runners), set only the account name:

```bash
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
```

The system will use `DefaultAzureCredential` which supports:
- Managed Identity
- Azure CLI credentials
- Visual Studio credentials
- Environment credentials

## Container Configuration

By default, the system uses a container named `workflow-states`. You can customize this by:

1. **Environment variable** (if added to code):
   ```bash
   export AZURE_BLOB_CONTAINER_NAME="my-custom-container"
   ```

2. **Code initialization**:
   ```python
   from src.storage import StateManager
   state_manager = StateManager(container_name="my-custom-container")
   ```

## Required Permissions

The storage account or identity needs these permissions:
- **Storage Blob Data Contributor** role, or
- Custom role with these permissions:
  - `Microsoft.Storage/storageAccounts/blobServices/containers/read`
  - `Microsoft.Storage/storageAccounts/blobServices/containers/write`
  - `Microsoft.Storage/storageAccounts/blobServices/generateUserDelegationKey/action`
  - `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read`
  - `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write`
  - `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete`

## GitHub Actions Configuration

### Repository Secrets

Add these secrets to your GitHub repository:

1. **AZURE_STORAGE_CONNECTION_STRING** (Recommended)
   - Navigate to your storage account in Azure Portal
   - Go to "Access keys" section
   - Copy the connection string
   - Add as repository secret

2. **Alternative: Separate secrets**
   - **AZURE_STORAGE_ACCOUNT_NAME**: Your storage account name
   - **AZURE_STORAGE_ACCOUNT_KEY**: Your storage account key

### Workflow YAML

Update your GitHub Actions workflow to include the secrets:

```yaml
name: Multi-Agent Workflow with State Persistence

on:
  workflow_dispatch:
    inputs:
      task:
        description: 'Task description'
        required: true

jobs:
  workflow:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Multi-Agent Workflow
        uses: ./
        with:
          task: ${{ inputs.task }}
        env:
          # Azure Blob Storage for state persistence
          AZURE_STORAGE_CONNECTION_STRING: ${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}
          
          # Alternative authentication:
          # AZURE_STORAGE_ACCOUNT_NAME: ${{ secrets.AZURE_STORAGE_ACCOUNT_NAME }}
          # AZURE_STORAGE_ACCOUNT_KEY: ${{ secrets.AZURE_STORAGE_ACCOUNT_KEY }}
```

## Creating Azure Storage Resources

### Using Azure Portal

1. **Create Storage Account**:
   - Navigate to Azure Portal
   - Click "Create a resource" > "Storage account"
   - Fill in details (name must be globally unique)
   - Choose Standard performance and LRS replication for basic usage
   - Create the resource

2. **Get Connection String**:
   - Open the storage account
   - Go to "Access keys"
   - Copy "Connection string" from key1 or key2

### Using Azure CLI

```bash
# Create resource group (if needed)
az group create --name myResourceGroup --location eastus

# Create storage account
az storage account create \
  --name mystorageaccount \
  --resource-group myResourceGroup \
  --location eastus \
  --sku Standard_LRS

# Get connection string
az storage account show-connection-string \
  --name mystorageaccount \
  --resource-group myResourceGroup \
  --output tsv
```

## Container Management

The system automatically creates the container if it doesn't exist. You can also pre-create it:

### Using Azure Portal
1. Open storage account
2. Go to "Containers"
3. Click "+" to add container
4. Name it `workflow-states` (or your custom name)
5. Set public access level to "Private"

### Using Azure CLI
```bash
az storage container create \
  --name workflow-states \
  --connection-string "your-connection-string"
```

## Security Best Practices

1. **Use Connection Strings in Production**: More secure than account keys
2. **Rotate Keys Regularly**: If using account keys, rotate them periodically
3. **Limit Permissions**: Use the minimum required permissions
4. **Network Restrictions**: Consider firewall rules for production accounts
5. **Private Endpoints**: Use private endpoints for enhanced security
6. **Managed Identity**: Preferred for Azure-hosted resources

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify environment variables are set correctly
   - Check that connection string is complete and valid
   - Ensure account name and key are correct

2. **Permission Errors**:
   - Verify the identity has blob storage permissions
   - Check that the storage account allows access from your IP/network

3. **Container Not Found**:
   - The system should auto-create containers
   - Check that the account has container creation permissions

4. **Network Connectivity**:
   - Verify firewall settings on storage account
   - Check if private endpoints are configured correctly

### Debugging

Enable verbose logging by setting:

```bash
export AZURE_CORE_LOGGING_ENABLE=True
```

Check application logs for detailed error messages from the Azure SDK.

## Example Usage

```python
from src.storage import StateManager

# Initialize state manager
state_manager = StateManager()

# Save workflow state
state_data = {
    "status": "paused",
    "current_step": 3,
    "context": {
        "task": "Implement Azure integration",
        "plan": "Multi-step implementation plan"
    }
}

success = state_manager.save_state("workflow-123", state_data)
if success:
    print("State saved successfully")

# Load workflow state
loaded_state = state_manager.load_state("workflow-123")
if loaded_state:
    print(f"Loaded state: {loaded_state}")

# List all saved states
workflow_ids = state_manager.list_states()
print(f"Saved workflows: {workflow_ids}")
```

## Cost Considerations

- **Storage Cost**: Blob storage is charged per GB stored
- **Transaction Cost**: Each read/write operation has a small cost
- **Data Transfer**: Egress charges may apply for large data transfers
- **Redundancy**: LRS is cheapest, GRS provides geo-redundancy

For workflow state storage, costs are typically minimal due to small file sizes.