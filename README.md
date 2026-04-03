# Multi-Agent Workflow

A GitHub Action that runs a plan → implement → review agent workflow using GitHub Copilot.

## Features

- **Plan**: Creates detailed implementation plans for tasks
- **Implement**: Executes the plan by making code changes
- **Review**: Reviews implementation against the original plan
- **State Management**: Optional Azure Blob Storage integration for workflow context persistence

## Usage

Add this action to your GitHub workflow:

```yaml
- name: Run Multi-Agent Workflow
  uses: coleflennikenmsft/multi-agent-aw@main
  env:
    PERSONAL_ACCESS_TOKEN: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
  with:
    task: "Implement a new feature for user authentication"
```

## Azure Blob Storage State Management

The workflow supports optional state management using Azure Blob Storage to persist context across long-running operations. This enables workflow pause/resume capabilities and checkpoint recovery.

### Configuration

Set up Azure Blob Storage by configuring one of the following authentication methods:

#### Option 1: Connection String (Development/Testing)

```yaml
env:
  AZURE_STORAGE_CONNECTION_STRING: ${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}
```

#### Option 2: Managed Identity (Production)

```yaml
env:
  AZURE_STORAGE_ACCOUNT_NAME: ${{ vars.AZURE_STORAGE_ACCOUNT_NAME }}
  AZURE_STORAGE_CONTAINER_NAME: ${{ vars.AZURE_STORAGE_CONTAINER_NAME }}  # Optional
```

### Azure Setup

1. **Create Storage Account**:
   ```bash
   az storage account create \
     --name mystorageaccount \
     --resource-group myresourcegroup \
     --location eastus \
     --sku Standard_LRS
   ```

2. **Create Container**:
   ```bash
   az storage container create \
     --name workflow-state \
     --account-name mystorageaccount
   ```

3. **Get Connection String** (for development):
   ```bash
   az storage account show-connection-string \
     --name mystorageaccount \
     --resource-group myresourcegroup
   ```

### Environment Variables

- `AZURE_STORAGE_CONNECTION_STRING`: Full connection string (Option 1)
- `AZURE_STORAGE_ACCOUNT_NAME`: Storage account name for managed identity (Option 2)
- `AZURE_STORAGE_CONTAINER_NAME`: Container name (defaults to 'workflow-state')

### State Management Features

- **Automatic Checkpoints**: Creates checkpoints at workflow start and completion
- **Phase Tracking**: Tracks workflow progress through planning, implementation, and review phases
- **State Recovery**: Ability to restore workflow state from checkpoints
- **Cleanup**: Automatic cleanup of old states to manage storage costs
- **Graceful Fallback**: Works without Azure configuration (state management disabled)

### Usage Examples

```python
from state.context_manager import save_workflow_state, load_workflow_state
from state.utils import create_checkpoint, is_state_management_available

# Check if state management is available
if is_state_management_available():
    # Create a checkpoint
    await create_checkpoint(workflow_id, "planning", {"plan": plan_content})
    
    # Save custom state
    state_key = await save_workflow_state(workflow_id, context_data)
    
    # Load state
    restored_context = await load_workflow_state(state_key)
```

## Requirements

- Python 3.11+
- GitHub Copilot CLI
- Azure Storage Blob SDK (optional, for state management)

## Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure Azure settings (optional)
4. Run locally: `python src/main.py "your task description"`