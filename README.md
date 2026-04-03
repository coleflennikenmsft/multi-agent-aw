# Multi-Agent Workflow Orchestration

## Overview
This project orchestrates multi-agent workflows for GitHub Actions, now with support for persistent state management using Azure Blob Storage.

## Features
- Multi-agent planning, implementation, and review
- State persistence via Azure Blob Storage (see [docs/AZURE_BLOB_SETUP.md](docs/AZURE_BLOB_SETUP.md))

## Prerequisites
- Python 3.11+
- Azure Blob Storage account (for state persistence)
- See [docs/AZURE_BLOB_SETUP.md](docs/AZURE_BLOB_SETUP.md) for setup

## State Management
Workflows can save and resume state using Azure Blob Storage. State is stored as JSON blobs, keyed by workflow ID.

## Environment Variables
Set one of the following for Azure authentication:
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY`
- (For managed identity) `AZURE_STORAGE_ACCOUNT_NAME`

## Usage Example
```python
from src.storage.state_manager import StateManager
sm = StateManager()
state = {"workflow_id": "abc123", "status": "paused", ...}
sm.save_state("abc123", state)
```

## License
MIT
