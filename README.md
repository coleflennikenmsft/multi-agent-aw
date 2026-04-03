# Multi-Agent Workflow System

A multi-agent workflow system for collaborative task planning, implementation, and review using GitHub Copilot agents.

## Features

- **Multi-Agent Workflow**: Coordinated planning, implementation, and review agents
- **Azure Blob Storage Integration**: Persistent context state management using Azure Blob Storage
- **GitHub Actions Integration**: Seamless workflow execution in GitHub Actions environment
- **Type Safety**: Full type hints and error handling throughout

## Azure Blob Storage Integration

The system includes Azure Blob Storage integration for managing context state across workflow executions. This allows agents to persist and share state data efficiently.

### Configuration

The storage system supports multiple authentication methods:

#### Connection String Authentication

```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
export AZURE_STORAGE_CONTAINER_NAME="context-states"  # Optional, defaults to "context-states"
```

#### Managed Identity Authentication

```bash
# Using storage account name (will construct URL automatically)
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"

# Or using full account URL
export AZURE_STORAGE_ACCOUNT_URL="https://mystorageaccount.blob.core.windows.net"

export AZURE_STORAGE_CONTAINER_NAME="context-states"  # Optional
```

### Usage Examples

#### Basic Usage

```python
from src.storage import BlobStorageClient, StorageConfig

# Initialize from environment variables
config = StorageConfig.from_environment()
client = BlobStorageClient(config)

# Upload state data
state_data = {
    "session_id": "abc123",
    "agent_context": {"current_task": "implementation"},
    "metadata": {"timestamp": "2024-01-01T00:00:00Z"}
}

await client.upload_state("session-123", state_data)

# Download state data
retrieved_state = await client.download_state("session-123")
print(retrieved_state)  # {'session_id': 'abc123', ...}

# Check if state exists
exists = await client.state_exists("session-123")
print(exists)  # True

# List all states
all_states = await client.list_states()
print(all_states)  # ['session-123', 'session-456', ...]

# List states with prefix
filtered_states = await client.list_states(prefix="session-")
print(filtered_states)  # ['session-123', 'session-456']

# Delete state
deleted = await client.delete_state("session-123")
print(deleted)  # True
```

#### Advanced Configuration

```python
from src.storage import BlobStorageClient, StorageConfig

# Manual configuration
config = StorageConfig(
    connection_string="DefaultEndpointsProtocol=https;...",
    container_name="my-custom-container"
)

client = BlobStorageClient(config)

# Ensure container exists before operations
await client.create_container()

# Check container existence
exists = await client.container_exists()
print(exists)  # True
```

#### Error Handling

```python
from src.storage import BlobStorageClient, StorageConfig, BlobStorageError, BlobStorageConnectionError

try:
    config = StorageConfig.from_environment()
    client = BlobStorageClient(config)
    
    await client.upload_state("test-session", {"data": "value"})
    
except BlobStorageConnectionError as e:
    print(f"Connection failed: {e}")
except BlobStorageError as e:
    print(f"Storage operation failed: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
```

### Storage Schema

State data is stored as JSON blobs with the following structure:

- **Blob Name**: `{state_id}.json`
- **Content-Type**: `application/json`
- **Format**: UTF-8 encoded JSON

Example blob content:
```json
{
  "session_id": "abc123",
  "agent_context": {
    "current_task": "implementation",
    "completed_steps": ["planning", "analysis"]
  },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "agent_version": "1.0.0"
  }
}
```

### API Reference

#### StorageConfig

Configuration class for Azure Blob Storage connection.

**Methods:**
- `from_environment()` - Create configuration from environment variables
- `get_account_url()` - Get the storage account URL
- `has_connection_string()` - Check if connection string auth is available
- `has_managed_identity_config()` - Check if managed identity auth is available

**Environment Variables:**
- `AZURE_STORAGE_CONNECTION_STRING` - Complete connection string
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account name (requires managed identity)
- `AZURE_STORAGE_ACCOUNT_URL` - Storage account URL (requires managed identity)  
- `AZURE_STORAGE_CONTAINER_NAME` - Container name (default: "context-states")

#### BlobStorageClient

Main client for blob storage operations.

**Methods:**
- `upload_state(state_id: str, state_data: Dict[str, Any]) -> bool` - Upload state data
- `download_state(state_id: str) -> Optional[Dict[str, Any]]` - Download state data
- `state_exists(state_id: str) -> bool` - Check if state exists
- `delete_state(state_id: str) -> bool` - Delete state data
- `list_states(prefix: Optional[str] = None) -> List[str]` - List all states
- `create_container() -> bool` - Create storage container
- `container_exists() -> bool` - Check if container exists

**Exceptions:**
- `BlobStorageError` - Base exception for storage operations
- `BlobStorageConnectionError` - Connection-specific errors

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Azure Storage (choose one method):

   **Connection String:**
   ```bash
   export AZURE_STORAGE_CONNECTION_STRING="your-connection-string"
   ```

   **Managed Identity:**
   ```bash
   export AZURE_STORAGE_ACCOUNT_NAME="your-storage-account"
   # or
   export AZURE_STORAGE_ACCOUNT_URL="https://your-account.blob.core.windows.net"
   ```

3. Run the workflow:
```bash
python -m src.main "Your task description"
```

## Architecture

The system consists of three main components:

- **Planning Agent**: Analyzes tasks and creates implementation plans
- **Implementation Agent**: Executes the planned tasks and makes code changes  
- **Review Agent**: Reviews implementation and provides feedback

Each agent can persist context state using the Azure Blob Storage integration, enabling:
- Cross-agent communication
- Workflow state persistence  
- Recovery from failures
- Audit trails and debugging

## Development

### Project Structure

```
src/
├── __init__.py           # Main package
├── main.py              # CLI entry point
├── agents/              # Agent implementations
│   ├── implement.py     # Implementation agent
│   ├── plan.py         # Planning agent
│   └── reviewer.py     # Review agent
├── storage/            # Azure Blob Storage integration
│   ├── __init__.py     # Storage package
│   ├── blob_client.py  # Main storage client
│   └── config.py       # Configuration management
└── workflow/           # Workflow orchestration
    └── plan_implement_review.py
```

### Type Safety

The codebase uses comprehensive type hints throughout:

```python
from typing import Dict, List, Optional, Any

async def upload_state(self, state_id: str, state_data: Dict[str, Any]) -> bool:
    """Upload context state data to blob storage."""
    # Implementation with full type safety
```

### Error Handling

Defensive error handling with custom exception hierarchy:

```python
class BlobStorageError(Exception):
    """Base exception for blob storage operations."""
    pass

class BlobStorageConnectionError(BlobStorageError):
    """Exception raised when connection to blob storage fails."""
    pass
```

### Logging

Structured logging throughout the storage system:

```python
import logging

logger = logging.getLogger(__name__)

# Usage
logger.info(f"Successfully uploaded state: {state_id}")
logger.error(f"Failed to connect to Azure Blob Storage: {str(e)}")
```

## Contributing

1. Ensure all new code includes comprehensive type hints
2. Add appropriate error handling and logging
3. Update documentation for new features
4. Follow the existing code patterns and conventions

## License

This project is part of the GitHub Copilot ecosystem.