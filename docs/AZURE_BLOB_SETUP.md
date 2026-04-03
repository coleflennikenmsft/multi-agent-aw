# Azure Blob Storage Setup for Workflow State Management

This guide explains how to configure Azure Blob Storage for persisting workflow state, enabling workflows to pause and resume across executions.

## Overview

The state management system uses Azure Blob Storage to:
- Save workflow state as JSON blobs
- Load workflow state for resumption
- Track workflow execution history
- Enable long-running workflows that can pause and resume

## Prerequisites

- An Azure Storage Account
- Appropriate permissions to create containers and manage blobs
- One of the following authentication methods configured

## Authentication Methods

The system supports three authentication methods, checked in this order:

### 1. Connection String (Recommended for Development)

**Environment Variable:** `AZURE_STORAGE_CONNECTION_STRING`

````bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=<account-name>;AccountKey=<account-key>;EndpointSuffix=core.windows.net"
````

**Obtaining the connection string:**
1. Navigate to your Storage Account in the Azure Portal
2. Go to "Access keys" under Security + networking
3. Copy the connection string from key1 or key2

### 2. Account Name + Key

**Environment Variables:**
- `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_STORAGE_ACCOUNT_KEY`

````bash
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
export AZURE_STORAGE_ACCOUNT_KEY="<your-account-key>"
````

**Obtaining the account key:**
1. Navigate to your Storage Account in the Azure Portal
2. Go to "Access keys" under Security + networking
3. Copy the key from key1 or key2

### 3. Managed Identity (Recommended for Production)

**Environment Variable:** `AZURE_STORAGE_ACCOUNT_NAME`

````bash
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
````

**Requirements:**
- Running on an Azure service (e.g., Azure VM, Azure Container Instances, App Service)
- Managed Identity enabled for the service
- Managed Identity assigned the "Storage Blob Data Contributor" role on the storage account

**Setting up Managed Identity:**
1. Enable system-assigned or user-assigned managed identity on your Azure service
2. Assign the "Storage Blob Data Contributor" role:
   ```bash
   az role assignment create \
     --role "Storage Blob Data Contributor" \
     --assignee <managed-identity-principal-id> \
     --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Storage/storageAccounts/<storage-account>
   ```

## GitHub Actions Configuration

To use state management in GitHub Actions workflows, add the Azure credentials as repository secrets:

### Option 1: Using Connection String

1. Go to your repository Settings > Secrets and variables > Actions
2. Add a new secret:
   - Name: `AZURE_STORAGE_CONNECTION_STRING`
   - Value: Your Azure Storage connection string

3. Update your workflow YAML to include the environment variable:

````yaml
jobs:
  workflow:
    runs-on: ubuntu-latest
    steps:
      - name: Run workflow with state management
        env:
          AZURE_STORAGE_CONNECTION_STRING: ${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}
        run: |
          python src/main.py
````

### Option 2: Using Account Name + Key

1. Go to your repository Settings > Secrets and variables > Actions
2. Add two secrets:
   - Name: `AZURE_STORAGE_ACCOUNT_NAME`, Value: Your storage account name
   - Name: `AZURE_STORAGE_ACCOUNT_KEY`, Value: Your storage account key

3. Update your workflow YAML:

````yaml
jobs:
  workflow:
    runs-on: ubuntu-latest
    steps:
      - name: Run workflow with state management
        env:
          AZURE_STORAGE_ACCOUNT_NAME: ${{ secrets.AZURE_STORAGE_ACCOUNT_NAME }}
          AZURE_STORAGE_ACCOUNT_KEY: ${{ secrets.AZURE_STORAGE_ACCOUNT_KEY }}
        run: |
          python src/main.py
````

## Creating an Azure Storage Account

If you don't have a storage account yet:

### Using Azure Portal

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" > "Storage account"
3. Fill in the required details:
   - Subscription: Select your subscription
   - Resource group: Create new or use existing
   - Storage account name: Unique name (lowercase, alphanumeric)
   - Region: Choose closest to your workflow execution
   - Performance: Standard (recommended for state storage)
   - Redundancy: LRS (Locally Redundant Storage) is sufficient for most cases
4. Click "Review + create" > "Create"

### Using Azure CLI

````bash
# Create resource group (if needed)
az group create --name myResourceGroup --location eastus

# Create storage account
az storage account create \
  --name mystorageaccount \
  --resource-group myResourceGroup \
  --location eastus \
  --sku Standard_LRS
````

## Container Configuration

By default, the system uses a container named `workflow-states`. This container is created automatically if it doesn't exist.

To use a custom container name:

````python
from src.storage import StateManager

manager = StateManager(container_name="my-custom-container")
````

## Usage Examples

### Basic Usage

````python
from src.storage import StateManager

# Initialize state manager (uses environment variables for authentication)
manager = StateManager()

# Save workflow state
state = {
    "workflow_id": "wf_12345",
    "status": "paused",
    "context": {
        "current_step": 3,
        "data": {"key": "value"}
    },
    "metadata": {
        "github_run_id": "123456789",
        "repository": "owner/repo"
    }
}
manager.save_state("wf_12345", state)

# Load workflow state
loaded_state = manager.load_state("wf_12345")

# Check if state exists
if manager.state_exists("wf_12345"):
    print("State exists")

# List all workflow states
all_states = manager.list_states()

# Get state metadata without downloading full blob
metadata = manager.get_state_metadata("wf_12345")

# Delete state when no longer needed
manager.delete_state("wf_12345")
````

### Using with Context Manager

````python
from src.storage import StateManager

with StateManager() as manager:
    manager.save_state("wf_123", {"status": "running"})
    state = manager.load_state("wf_123")
# Connection is automatically closed
````

### Custom Configuration

````python
from src.storage import AzureBlobClient, StateManager

# Create client with explicit credentials
blob_client = AzureBlobClient(
    account_name="mystorageaccount",
    account_key="myaccountkey"
)

# Create state manager with custom container
manager = StateManager(
    blob_client=blob_client,
    container_name="production-workflows"
)
````

## State Data Format

State is stored as JSON with the following recommended structure:

````json
{
  "workflow_id": "string",
  "timestamp": "ISO-8601 timestamp",
  "status": "paused|completed|failed|running",
  "context": {
    "task": "string",
    "plan": "string",
    "current_step": 0,
    "messages": []
  },
  "metadata": {
    "github_run_id": "string",
    "repository": "string",
    "issue_number": 0
  }
}
````

The `workflow_id` and `timestamp` fields are automatically added if not present.

## Security Considerations

1. **Never commit credentials** to version control
2. Use **Managed Identity** for production deployments when running on Azure
3. Use **connection strings or account keys** only for development/testing
4. Store credentials in **GitHub Secrets** for GitHub Actions workflows
5. Limit access using **Azure RBAC** (Role-Based Access Control)
6. Consider enabling **soft delete** on your storage account for data recovery

## Troubleshooting

### Authentication Errors

**Error:** `No valid Azure Storage authentication found`

**Solution:** Ensure at least one of the authentication methods is configured with valid credentials.

### Connection Errors

**Error:** `Failed to initialize with connection string`

**Solution:** 
- Verify the connection string is complete and properly formatted
- Check network connectivity to Azure
- Verify the storage account exists and is accessible

### Permission Errors

**Error:** `AuthorizationPermissionMismatch` or `403 Forbidden`

**Solution:**
- Ensure the account/identity has the "Storage Blob Data Contributor" role
- For managed identity, verify role assignment is correct
- For account keys, ensure the key is valid and not expired

### Container Not Found

If the container doesn't exist, it will be created automatically. If creation fails:
- Check that the account has permission to create containers
- Verify the container name follows Azure naming rules (lowercase, alphanumeric, hyphens)

## Cost Considerations

Azure Blob Storage costs are based on:
- **Storage capacity**: Amount of data stored (very low for JSON state files)
- **Operations**: Number of read/write operations
- **Data transfer**: Egress data transfer (minimal for state management)

For typical workflow state management usage, costs are minimal (usually < $1/month).

## Additional Resources

- [Azure Blob Storage Documentation](https://docs.microsoft.com/azure/storage/blobs/)
- [Azure Storage Python SDK](https://docs.microsoft.com/python/api/overview/azure/storage-blob-readme)
- [Azure Managed Identity Documentation](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [Azure RBAC Documentation](https://docs.microsoft.com/azure/role-based-access-control/)
