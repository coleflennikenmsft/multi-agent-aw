# Multi-Agent Workflow with Azure Blob State Management

This repository provides a multi-agent workflow system with integrated Azure Blob Storage state management for long-running operations.

## Features

- **Plan-Implement-Review Workflow**: Automated workflow for planning, implementing, and reviewing code changes
- **Azure Blob State Management**: Persistent workflow context storage that survives long-running operations
- **Flexible Authentication**: Supports both connection strings and Azure managed identity
- **State Checkpoints**: Automatic and manual checkpointing for workflow recovery

## Azure Blob Storage State Management

The state management system allows workflows to persist their context to Azure Blob Storage, enabling:
- Recovery from interruptions
- Audit trails of workflow execution
- State sharing across distributed systems
- Long-running operation support

### Setup

#### Prerequisites

- Azure Storage Account
- Either:
  - Connection string for the storage account, OR
  - Managed identity with access to the storage account

#### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Configure Azure credentials using one of these methods:

   **Option 1: Connection String (Development)**
   ```bash
   export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=<account-name>;AccountKey=<account-key>;EndpointSuffix=core.windows.net"
   ```

   **Option 2: Managed Identity (Production)**
   ```bash
   export AZURE_STORAGE_ACCOUNT_NAME="<your-account-name>"
   ```

3. (Optional) Specify a custom container name:
   ```bash
   export AZURE_STORAGE_CONTAINER_NAME="workflow-context-state"
   ```

### Usage

#### Basic State Operations

```python
from state import save_state, load_state, list_states, delete_state

# Save workflow state
context = {
    "step": "planning",
    "data": {"plan": "..."},
    "metadata": {"user": "alice"}
}
blob_name = save_state("workflow-123", context)
print(f"Saved state to: {blob_name}")

# Load state
restored_context = load_state(blob_name)

# List all states for a workflow
states = list_states("workflow-123")
for state in states:
    print(f"{state['name']}: {state['size']} bytes, modified {state['last_modified']}")

# Delete old state
delete_state(blob_name)
```

#### Using the ContextManager Class

```python
from state import ContextManager

# Create a context manager
manager = ContextManager(use_json=True)

# Save state with custom timestamp
from datetime import datetime
blob_name = manager.save_state(
    workflow_id="workflow-456",
    context={"step": "implementation", "progress": 0.5},
    timestamp=datetime.utcnow()
)

# Get the latest state for a workflow
latest = manager.get_latest_state("workflow-456")
if latest:
    print(f"Current step: {latest['step']}")

# List states
states = manager.list_states("workflow-456")
print(f"Found {len(states)} saved states")
```

#### Utility Functions

```python
from state.utils import (
    is_state_management_available,
    create_state_checkpoint,
    restore_latest_checkpoint,
    cleanup_old_checkpoints
)

# Check if Azure is configured
if is_state_management_available():
    print("State management is ready!")

# Create a checkpoint (gracefully handles missing config)
checkpoint = create_state_checkpoint(
    workflow_id="workflow-789",
    step_name="planner",
    data={"plan": "Implementation plan..."},
    metadata={"agent": "planner", "version": "1.0"}
)

# Restore latest checkpoint
context = restore_latest_checkpoint("workflow-789")
if context:
    print(f"Restored step: {context['step_name']}")

# Cleanup old checkpoints, keep only 5 most recent
deleted = cleanup_old_checkpoints("workflow-789", keep_latest=5)
print(f"Deleted {deleted} old checkpoints")
```

#### Integration with Workflows

The workflow runner automatically creates checkpoints when state management is configured:

```python
from workflow.plan_implement_review import run_workflow

# Run workflow with state management
result = await run_workflow(
    task="Implement feature X",
    workflow_id="feature-x-2026-04-03"
)
```

### Storage Structure

States are stored in Azure Blob Storage with the following structure:

```
workflow-state/
  ├── workflow-123/
  │   ├── 20260403-143000-123456.json
  │   ├── 20260403-144500-789012.json
  │   └── ...
  └── workflow-456/
      ├── 20260403-150000-345678.json
      └── ...
```

Each blob contains:
- **version**: Format version (for future compatibility)
- **timestamp**: ISO 8601 timestamp of when the state was saved
- **format**: Serialization format (json or pickle)
- **context**: The actual workflow context data

### State Format

States can be serialized in two formats:

1. **JSON** (default, recommended):
   - Human-readable
   - Language-agnostic
   - Suitable for most use cases
   - Supports basic Python types

2. **Pickle**:
   - Python-specific
   - Supports complex Python objects
   - Use when JSON serialization is insufficient

### Error Handling

The state management system handles errors gracefully:

- **Missing Configuration**: Operations that require Azure will raise `RuntimeError` with a helpful message
- **Network Failures**: Azure SDK exceptions are caught and logged
- **Serialization Errors**: `ValueError` is raised with context about what failed
- **Missing Blobs**: `ResourceNotFoundError` is raised when accessing non-existent states

### Best Practices

1. **Use meaningful workflow IDs**: Include dates, feature names, or user identifiers
2. **Regular cleanup**: Use `cleanup_old_checkpoints()` to avoid storage bloat
3. **Choose the right format**: Use JSON unless you need pickle's capabilities
4. **Monitor storage costs**: Each checkpoint creates a new blob; implement retention policies
5. **Secure your credentials**: Use managed identity in production environments

### Troubleshooting

#### "Azure Blob Storage not configured" Error

This means the required environment variables are not set. Check:
- `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT_NAME` is set
- The credentials are valid and not expired
- The storage account exists and is accessible

#### Authentication Failures

- Verify the connection string is correct
- For managed identity: ensure the identity has "Storage Blob Data Contributor" role
- Check network connectivity to Azure

#### Container Creation Failures

- Ensure your credentials have permission to create containers
- The container name must be lowercase and follow Azure naming rules
- Check if the container already exists but is inaccessible

## Development

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### Running Tests

(To be added based on your testing framework)

## License

(Add your license information here)

## Contributing

(Add contribution guidelines here)
