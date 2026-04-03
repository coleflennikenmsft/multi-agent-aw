# Multi-Agent Workflow System

A GitHub Actions-based multi-agent workflow system with state persistence capabilities using Azure Blob Storage.

## Overview

This system provides a plan → implement → review workflow using GitHub Copilot agents. It supports long-running workflows with state persistence, allowing workflows to pause and resume across GitHub Actions runs.

## Features

- **Multi-Agent Workflow**: Coordinated planner, implementer, and reviewer agents
- **State Persistence**: Azure Blob Storage integration for workflow state management
- **GitHub Actions Integration**: Runs as a composite GitHub Action
- **Resumable Workflows**: Save and restore workflow state across executions

## Usage

### Basic Workflow

Use this action in your GitHub workflows:

```yaml
name: Multi-Agent Implementation

on:
  workflow_dispatch:
    inputs:
      task:
        description: 'Implementation task description'
        required: true

jobs:
  implement:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Multi-Agent Workflow
        uses: ./
        with:
          task: ${{ inputs.task }}
        env:
          COPILOT_GITHUB_TOKEN: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
```

### With State Persistence

To enable state persistence, configure Azure Blob Storage:

```yaml
- name: Run Multi-Agent Workflow with State Persistence
  uses: ./
  with:
    task: ${{ inputs.task }}
  env:
    COPILOT_GITHUB_TOKEN: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
    AZURE_STORAGE_CONNECTION_STRING: ${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}
```

## Prerequisites

### Required
- GitHub Copilot access
- Personal Access Token with appropriate permissions

### Optional (for state persistence)
- Azure Storage Account
- Configured authentication (see [Azure Blob Setup](docs/AZURE_BLOB_SETUP.md))

## State Management

The system includes Azure Blob Storage integration for workflow state persistence:

- **Save State**: Automatically save workflow progress at key points
- **Load State**: Resume workflows from previous checkpoints
- **State Storage**: JSON-based state storage with metadata
- **Multi-Workflow**: Support for multiple concurrent workflow states

### State Data Structure

Workflow state includes:
- Workflow ID and timestamps
- Current executor and status
- Task context and plan
- GitHub run metadata

For detailed setup instructions, see [Azure Blob Storage Setup](docs/AZURE_BLOB_SETUP.md).

## Architecture

### Workflow Executors

1. **PlannerExecutor**: Creates implementation plans from task descriptions
2. **ImplementerExecutor**: Executes tasks from the plan
3. **ReviewerExecutor**: Reviews implementation and provides feedback

### State Management Components

1. **AzureBlobClient**: Low-level Azure Blob Storage operations
2. **StateManager**: High-level workflow state management
3. **Integration Points**: Hooks for saving/loading state during workflow execution

### Directory Structure

```
src/
├── agents/          # Agent definitions (planner, implementer, reviewer)
├── storage/         # Azure Blob Storage integration
│   ├── azure_blob_client.py
│   └── state_manager.py
└── workflow/        # Workflow orchestration
    └── plan_implement_review.py

docs/
└── AZURE_BLOB_SETUP.md    # Azure configuration guide

tests/
├── test_azure_blob_client.py
└── test_state_manager.py
```

## Development

### Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- `agent-framework-github-copilot`: Core agent framework
- `azure-storage-blob`: Azure Blob Storage SDK
- `azure-identity`: Azure authentication

### Running Tests

```bash
python -m pytest tests/
```

### Local Development

For local development, set up environment variables:

```bash
export COPILOT_GITHUB_TOKEN="your_token"
export AZURE_STORAGE_CONNECTION_STRING="your_connection_string"  # Optional
```

Run the workflow locally:

```bash
python src/main.py "Your task description"
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `COPILOT_GITHUB_TOKEN` | Yes | GitHub Copilot access token |
| `AZURE_STORAGE_CONNECTION_STRING` | No | Azure Blob Storage connection string |
| `AZURE_STORAGE_ACCOUNT_NAME` | No | Azure Storage account name (alternative auth) |
| `AZURE_STORAGE_ACCOUNT_KEY` | No | Azure Storage account key (alternative auth) |

### Workflow Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `task` | Yes | Natural language description of the implementation task |

## Examples

### Simple Implementation Task

```yaml
with:
  task: "Add error handling to the user authentication module"
```

### Complex Feature Implementation  

```yaml
with:
  task: "Implement a REST API for user management with CRUD operations, input validation, and comprehensive error handling"
```

### Bug Fix with Context

```yaml
with:
  task: "Fix the memory leak in the data processing pipeline identified in issue #123"
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify `COPILOT_GITHUB_TOKEN` is valid and has required permissions
2. **Azure Storage Errors**: Check Azure configuration in [setup guide](docs/AZURE_BLOB_SETUP.md)
3. **Workflow Failures**: Review GitHub Actions logs for detailed error messages

### Debug Mode

Enable debug logging:

```yaml
env:
  AZURE_CORE_LOGGING_ENABLE: "True"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Ensure all tests pass
5. Submit a pull request

## License

[Add license information]