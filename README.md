# Multi-Agent Workflow

A multi-agent workflow system with Azure Blob Storage integration for context state management.

## Features

- Multi-agent workflow orchestration
- Azure Blob Storage integration for persistent state management
- Support for both connection string and managed identity authentication
- Type-safe API with comprehensive error handling

## Installation

Install the required dependencies:

````bash
pip install -r requirements.txt
````

## Azure Blob Storage Integration

The storage module provides a clean API for managing agent state in Azure Blob Storage.

### Configuration

The system supports multiple authentication methods via environment variables:

#### Option 1: Connection String (Recommended for Development)

````bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."
export AZURE_STORAGE_CONTAINER_NAME="agent-state"  # Optional, defaults to "agent-state"
````

#### Option 2: Managed Identity (Recommended for Production)

````bash
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
# OR
export AZURE_STORAGE_ACCOUNT_URL="https://mystorageaccount.blob.core.windows.net"

export AZURE_STORAGE_CONTAINER_NAME="agent-state"  # Optional
````

### Usage

#### Basic Usage

````python
from src.storage import BlobStorageClient, StorageConfig

# Load configuration from environment
config = StorageConfig.from_environment()

# Create client
client = BlobStorageClient(config)

# Ensure container exists
await client.create_container()

# Upload state
state_data = {
    "workflow_id": "abc123",
    "step": "planning",
    "context": {"key": "value"}
}
await client.upload_state("workflow-abc123", state_data)

# Check if state exists
exists = await client.state_exists("workflow-abc123")

# Download state
retrieved_state = await client.download_state("workflow-abc123")

# List all states
states = await client.list_states()

# List states with prefix
workflow_states = await client.list_states(prefix="workflow-")

# Delete state
deleted = await client.delete_state("workflow-abc123")

# Clean up
client.close()
````

#### Using Context Manager

````python
from src.storage import BlobStorageClient, StorageConfig

config = StorageConfig.from_environment()

with BlobStorageClient(config) as client:
    await client.upload_state("my-state", {"data": "value"})
    state = await client.download_state("my-state")
# Client automatically closed
````

#### Manual Configuration

````python
from src.storage import BlobStorageClient, StorageConfig

# Using connection string
config = StorageConfig(
    connection_string="DefaultEndpointsProtocol=https;...",
    container_name="my-container"
)

# Using managed identity
config = StorageConfig(
    account_name="mystorageaccount",
    container_name="my-container"
)

client = BlobStorageClient(config)
````

### API Reference

#### StorageConfig

Configuration class for Azure Blob Storage.

**Attributes:**
- `connection_string`: Azure Storage connection string (highest priority)
- `account_name`: Storage account name (used with managed identity)
- `account_url`: Storage account URL (used with managed identity)
- `container_name`: Default container name (default: "agent-state")

**Methods:**
- `from_environment()`: Load configuration from environment variables
- `validate()`: Validate configuration completeness
- `has_connection_string()`: Check if connection string is configured
- `has_managed_identity_config()`: Check if managed identity is configured

#### BlobStorageClient

Client for managing state in Azure Blob Storage.

**Methods:**

- `create_container() -> bool`: Create container if it doesn't exist
  - Returns: `True` if created, `False` if already existed

- `container_exists() -> bool`: Check if container exists
  - Returns: `True` if exists, `False` otherwise

- `upload_state(state_name: str, state_data: Dict[str, Any], overwrite: bool = True) -> None`: Upload state data
  - `state_name`: Name/identifier for the state
  - `state_data`: Dictionary with state data
  - `overwrite`: Whether to overwrite existing state
  - Raises: `ResourceExistsError` if exists and `overwrite=False`

- `download_state(state_name: str) -> Dict[str, Any]`: Download state data
  - `state_name`: Name/identifier of the state
  - Returns: Dictionary with state data
  - Raises: `ResourceNotFoundError` if state doesn't exist

- `state_exists(state_name: str) -> bool`: Check if state exists
  - `state_name`: Name/identifier to check
  - Returns: `True` if exists, `False` otherwise

- `delete_state(state_name: str) -> bool`: Delete a state
  - `state_name`: Name/identifier to delete
  - Returns: `True` if deleted, `False` if didn't exist

- `list_states(prefix: Optional[str] = None) -> List[str]`: List all states
  - `prefix`: Optional prefix filter
  - Returns: List of state names

- `close() -> None`: Close client and release resources

### Error Handling

The storage module uses defensive error handling:

````python
from azure.core.exceptions import ResourceNotFoundError

try:
    state = await client.download_state("nonexistent")
except ResourceNotFoundError:
    print("State not found")

try:
    await client.upload_state("existing", data, overwrite=False)
except ResourceExistsError:
    print("State already exists")

try:
    config = StorageConfig()
    config.validate()
except ValueError as e:
    print(f"Invalid configuration: {e}")
````

### Best Practices

1. **Use environment variables** for configuration in production
2. **Enable managed identity** for Azure-hosted applications
3. **Use connection strings** for local development only
4. **Use context managers** to ensure proper cleanup
5. **Handle exceptions** appropriately in your application
6. **Use meaningful state names** with clear naming conventions
7. **Consider state name prefixes** for organizing related states

## Development

### Running Tests

````bash
# Install test dependencies
pip install -r requirements.txt

# Run tests (when available)
pytest tests/
````

### Project Structure

````
.
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── agents/          # Agent implementations
│   ├── workflow/        # Workflow orchestration
│   └── storage/         # Azure Blob Storage integration
│       ├── __init__.py
│       ├── config.py    # Configuration management
│       └── blob_client.py  # Blob storage client
├── requirements.txt
└── action.yml
````

## License

See LICENSE file for details.
