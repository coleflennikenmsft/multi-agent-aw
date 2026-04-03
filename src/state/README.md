# Azure Blob Storage State Management System

A comprehensive state management system for workflows using Azure Blob Storage, enabling workflows to pause and resume with preserved state across long-running operations.

## Overview

This module provides high-level state management capabilities with the following key features:

- **Persistent State Storage**: Save and restore workflow state using Azure Blob Storage
- **Checkpoint Management**: Create step-level checkpoints for fine-grained recovery
- **Versioning Support**: Create and manage multiple versions of workflow states
- **Multiple Serialization Formats**: JSON and pickle with optional gzip compression
- **Automatic Error Handling**: Graceful degradation when Azure services are unavailable
- **Comprehensive Logging**: Full visibility into all state operations

## Quick Start

### Installation

Add to your `requirements.txt`:
````
azure-storage-blob>=12.19.0
````

### Environment Setup

Set up Azure Blob Storage credentials using one of these options:

**Option 1: Connection String (Recommended)**
````bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
````

**Option 2: Account Credentials**
````bash
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
export AZURE_STORAGE_ACCOUNT_KEY="your-account-key"
````

**Optional Configuration**
````bash
export AZURE_STORAGE_CONTAINER_NAME="workflow-state"  # default if not set
````

### Basic Usage

````python
from src.state import BlobStateManager

# Initialize manager (loads config from environment)
manager = BlobStateManager()

# Save workflow state
workflow_state = {
    "step": "processing",
    "progress": 75,
    "data": {"records_processed": 1500}
}
manager.save_state("workflow-001", workflow_state)

# Load workflow state
state = manager.load_state("workflow-001")
if state:
    print(f"Workflow progress: {state['progress']}%")

# Create a versioned snapshot
manager.save_state("workflow-001", updated_state, create_snapshot=True)
````

## Architecture

### Core Components

1. **BlobStorageClient**: Low-level Azure Blob operations with error handling
2. **StateConfig**: Configuration management and validation
3. **StateSerializer**: Serialization with multiple formats and compression
4. **BlobStateManager**: High-level state management with versioning
5. **CheckpointManager**: Step-level checkpoint management

### Module Structure
````
src/state/
├── __init__.py          # Module exports and configuration
├── blob_client.py       # Azure Blob Storage client wrapper
├── config.py           # Configuration management
├── serialization.py    # Data serialization utilities
├── manager.py          # Main state manager
├── checkpoints.py      # Checkpoint management
└── README.md           # This documentation
````

## API Reference

### BlobStateManager

The main interface for workflow state management.

#### Methods

**`save_state(workflow_id, state, create_snapshot=False, metadata=None)`**
- Save workflow state to Azure Blob Storage
- `workflow_id`: Unique identifier for the workflow
- `state`: State data dictionary to save
- `create_snapshot`: Create versioned snapshot if True
- `metadata`: Additional metadata to include
- Returns: `True` if successful, `False` otherwise

**`load_state(workflow_id, version=None)`**
- Load workflow state from Azure Blob Storage
- `workflow_id`: Unique identifier for the workflow
- `version`: Specific version to load (None for latest)
- Returns: State data dictionary or `None` if not found

**`delete_state(workflow_id, version=None, delete_all_versions=False)`**
- Delete workflow state
- `workflow_id`: Unique identifier for the workflow
- `version`: Specific version to delete (None for latest)
- `delete_all_versions`: Delete all versions if True
- Returns: `True` if successful, `False` otherwise

**`list_states(workflow_id_prefix="")`**
- List all saved workflow states
- `workflow_id_prefix`: Filter by workflow ID prefix
- Returns: List of state information dictionaries

**`list_versions(workflow_id)`**
- List all versions of a specific workflow state
- `workflow_id`: Unique identifier for the workflow
- Returns: List of version information dictionaries

### CheckpointManager

Manages step-level checkpoints for fine-grained recovery.

#### Methods

**`create_checkpoint(workflow_id, step, data, metadata=None, overwrite=True)`**
- Create checkpoint at a specific workflow step
- `workflow_id`: Unique identifier for the workflow
- `step`: Name/identifier of the workflow step
- `data`: Checkpoint data to save
- `metadata`: Additional metadata to include
- `overwrite`: Whether to overwrite existing checkpoint
- Returns: `True` if successful, `False` otherwise

**`restore_from_checkpoint(workflow_id, step)`**
- Restore data from a checkpoint
- `workflow_id`: Unique identifier for the workflow
- `step`: Name/identifier of the workflow step
- Returns: Checkpoint data dictionary or `None` if not found

**`list_checkpoints(workflow_id)`**
- List all checkpoints for a workflow
- `workflow_id`: Unique identifier for the workflow
- Returns: List of checkpoint information dictionaries

**`delete_checkpoint(workflow_id, step)`**
- Delete a specific checkpoint
- `workflow_id`: Unique identifier for the workflow
- `step`: Name/identifier of the workflow step
- Returns: `True` if successful, `False` otherwise

### StateConfig

Configuration management for Azure Blob Storage.

#### Class Methods

**`StateConfig.from_env()`**
- Create configuration from environment variables
- Validates required credentials
- Returns: `StateConfig` instance
- Raises: `ValueError` if configuration is invalid

### StateSerializer

Handles serialization with multiple formats and compression.

#### Methods

**`serialize(data, format=None, compress=None)`**
- Serialize data to bytes
- `data`: Data to serialize
- `format`: SerializationFormat (JSON or PICKLE)
- `compress`: Whether to use gzip compression
- Returns: Serialized data as bytes

**`deserialize(data, format=None, compressed=None)`**
- Deserialize bytes back to original data
- `data`: Serialized data as bytes
- `format`: Expected format (auto-detected if None)
- `compressed`: Whether data is compressed (auto-detected if None)
- Returns: Deserialized data

## Usage Examples

### Advanced State Management

````python
from src.state import BlobStateManager, CheckpointManager
from src.state.serialization import SerializationFormat, StateSerializer

# Custom serializer with pickle and compression
serializer = StateSerializer(
    default_format=SerializationFormat.PICKLE,
    use_compression=True
)

# Initialize with custom serializer
manager = BlobStateManager(serializer=serializer)

# Save complex state with metadata
complex_state = {
    "model": trained_model,  # Custom Python object
    "metrics": evaluation_metrics,
    "config": training_config
}

metadata = {
    "model_version": "1.2.3",
    "training_time_hours": 4.5,
    "dataset_size": 100000
}

manager.save_state("ml-training-001", complex_state, 
                  create_snapshot=True, metadata=metadata)

# List all versions with metadata
versions = manager.list_versions("ml-training-001")
for version in versions:
    print(f"Version: {version['version']}")
    print(f"Size: {version['size']} bytes")
    print(f"Metadata: {version['metadata']}")
````

### Checkpoint-Based Workflow Recovery

````python
from src.state import CheckpointManager

checkpoint_manager = CheckpointManager()
workflow_id = "data-pipeline-001"

def run_workflow():
    try:
        # Step 1: Data loading
        data = load_data()
        checkpoint_manager.create_checkpoint(workflow_id, "data_loaded", {
            "data_size": len(data),
            "load_time": time.time()
        })
        
        # Step 2: Data processing
        processed_data = process_data(data)
        checkpoint_manager.create_checkpoint(workflow_id, "data_processed", {
            "processed_size": len(processed_data),
            "processing_time": time.time()
        })
        
        # Step 3: Data validation
        validated_data = validate_data(processed_data)
        checkpoint_manager.create_checkpoint(workflow_id, "data_validated", {
            "validated_size": len(validated_data),
            "validation_time": time.time()
        })
        
    except Exception as e:
        print(f"Workflow failed at step: {e}")
        recover_from_checkpoint()

def recover_from_checkpoint():
    # Find the latest successful checkpoint
    checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
    
    if checkpoints:
        latest_checkpoint = checkpoints[0]  # Already sorted by time
        step = latest_checkpoint['step']
        
        print(f"Recovering from step: {step}")
        checkpoint_data = checkpoint_manager.restore_from_checkpoint(workflow_id, step)
        
        if step == "data_loaded":
            # Resume from processing step
            continue_from_processing(checkpoint_data)
        elif step == "data_processed":
            # Resume from validation step
            continue_from_validation(checkpoint_data)
````

### Error Handling and Graceful Degradation

````python
from src.state import BlobStateManager, StateConfig

def create_resilient_state_manager():
    try:
        # Attempt to create state manager
        config = StateConfig.from_env()
        manager = BlobStateManager(config)
        
        # Test connection
        test_success = manager.save_state("connection_test", {"test": True})
        if test_success:
            manager.delete_state("connection_test")
            print("✓ Azure Blob Storage connection verified")
            return manager
        else:
            print("⚠ Azure Blob Storage connection failed")
            return None
    
    except ValueError as e:
        print(f"⚠ Configuration error: {e}")
        return None
    
    except Exception as e:
        print(f"⚠ State manager initialization failed: {e}")
        return None

def workflow_with_fallback():
    state_manager = create_resilient_state_manager()
    
    # Workflow state
    state = {"step": "processing", "progress": 50}
    
    if state_manager:
        # Use persistent state management
        success = state_manager.save_state("workflow", state)
        if success:
            print("State saved to Azure Blob Storage")
        else:
            print("Falling back to local state storage")
            save_state_locally(state)
    else:
        # Fallback to local storage
        print("Using local state storage (Azure unavailable)")
        save_state_locally(state)

def save_state_locally(state):
    # Implement local backup storage
    import json
    with open("local_state_backup.json", "w") as f:
        json.dump(state, f)
````

## Troubleshooting

### Common Issues

**1. Authentication Errors**
````
ClientAuthenticationError: The request authorization header is not in the correct format.
````
- Verify your Azure Storage credentials
- Ensure connection string format is correct
- Check that account key is valid and not expired

**2. Container Access Errors**
````
ResourceNotFoundError: The specified container does not exist.
````
- Container will be created automatically on first use
- Ensure your account has permission to create containers
- Check container name format (3-63 chars, lowercase, no special chars)

**3. Serialization Errors**
````
ValueError: Serialization failed: Object of type ... is not JSON serializable
````
- Use pickle format for complex Python objects
- Implement custom JSON serialization for specific types
- Check data types before serialization

### Configuration Validation

The system automatically validates configuration on startup:

````python
from src.state import StateConfig

try:
    config = StateConfig.from_env()
    print("✓ Configuration valid")
except ValueError as e:
    print(f"✗ Configuration error: {e}")
````

### Logging and Debugging

Enable detailed logging to troubleshoot issues:

````python
import logging

# Enable debug logging for state management
logging.getLogger('src.state').setLevel(logging.DEBUG)

# Enable Azure SDK logging
logging.getLogger('azure.storage').setLevel(logging.DEBUG)
````

## Performance Considerations

### Compression

- Compression is beneficial for large states (>1KB)
- JSON with compression typically provides 60-80% size reduction
- Pickle format is more efficient for complex Python objects

### Blob Naming Strategy

The system uses a hierarchical naming structure:
- States: `states/{workflow_id}/latest.state`
- Snapshots: `states/{workflow_id}/{timestamp}_{uuid}.state`
- Checkpoints: `checkpoints/{workflow_id}/{step}.checkpoint`

### Recommended Practices

1. **Use snapshots sparingly**: Create snapshots only at major milestones
2. **Clean up old checkpoints**: Use `cleanup_old_checkpoints()` regularly
3. **Monitor blob storage costs**: Large states can incur significant storage costs
4. **Use appropriate serialization**: JSON for simple data, pickle for complex objects
5. **Enable compression**: For states larger than 1KB

## Security Considerations

- Store Azure credentials securely (Azure Key Vault, environment variables)
- Use managed identity in Azure environments when possible
- Implement access controls at the Azure Storage account level
- Consider encryption at rest (enabled by default in Azure Storage)
- Regularly rotate storage account keys

## Integration with Workflows

### GitHub Actions Example

````yaml
name: Stateful Workflow
on:
  workflow_dispatch:
    inputs:
      resume_from:
        description: 'Resume from checkpoint (optional)'
        required: false

jobs:
  stateful-job:
    runs-on: ubuntu-latest
    env:
      AZURE_STORAGE_CONNECTION_STRING: ${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run workflow
      run: python workflow_with_state.py
      env:
        RESUME_FROM: ${{ github.event.inputs.resume_from }}
````

## License

This module is part of the multi-agent workflow system. See the main project license for details.