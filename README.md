# Multi-Agent Workflow System

A GitHub Actions-based multi-agent workflow system that uses AI agents to plan, implement, and review tasks.

## Features

- **Plan-Implement-Review Workflow**: Automated workflow with three specialized agents
  - **Planner**: Creates detailed implementation plans from specifications
  - **Implementer**: Executes tasks from the plan
  - **Reviewer**: Reviews implementation and provides feedback
- **Azure Blob Storage State Management**: Persist workflow state to enable long-running workflows that can pause and resume
- **GitHub Copilot Integration**: Leverages GitHub Copilot agents for intelligent task execution

## Prerequisites

- Python 3.11+
- Azure Storage Account (optional, for state management)
- GitHub Actions environment (for workflow execution)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/coleflennikenmsft/multi-agent-aw.git
   cd multi-agent-aw
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Configure Azure Blob Storage for state management:
   - See [Azure Blob Storage Setup Guide](docs/AZURE_BLOB_SETUP.md) for detailed instructions
   - Set one of the following environment variable combinations:
     - `AZURE_STORAGE_CONNECTION_STRING`, or
     - `AZURE_STORAGE_ACCOUNT_NAME` + `AZURE_STORAGE_ACCOUNT_KEY`, or
     - `AZURE_STORAGE_ACCOUNT_NAME` (with managed identity)

## Usage

### Running Locally

```bash
python src/main.py "Your task description here"
```

### GitHub Actions

The workflow can be triggered via `workflow_dispatch` events. See `.github/workflows/` for available workflow configurations.

### State Management

The system includes Azure Blob Storage integration for workflow state persistence:

```python
from src.storage import StateManager

# Save workflow state
manager = StateManager()
state = {
    "workflow_id": "wf_123",
    "status": "paused",
    "context": {"step": 2, "data": "..."}
}
manager.save_state("wf_123", state)

# Load workflow state
loaded_state = manager.load_state("wf_123")
```

For complete documentation, see [Azure Blob Storage Setup Guide](docs/AZURE_BLOB_SETUP.md).

## Project Structure

```
.
├── src/
│   ├── agents/           # Agent implementations
│   │   ├── plan.py       # Planner agent
│   │   ├── implement.py  # Implementer agent
│   │   └── reviewer.py   # Reviewer agent
│   ├── storage/          # Azure Blob Storage integration
│   │   ├── azure_blob_client.py  # Azure Blob client
│   │   └── state_manager.py      # State management
│   ├── workflow/         # Workflow orchestration
│   │   └── plan_implement_review.py
│   └── main.py           # Entry point
├── tests/                # Unit tests
├── docs/                 # Documentation
└── requirements.txt      # Python dependencies
```

## Documentation

- [Azure Blob Storage Setup Guide](docs/AZURE_BLOB_SETUP.md) - Complete guide for configuring state management

## Development

### Running Tests

```bash
python -m unittest discover tests
```

### Code Structure

- **Agents**: Located in `src/agents/`, each agent is specialized for a specific task
- **Storage**: Located in `src/storage/`, handles Azure Blob Storage integration
- **Workflow**: Located in `src/workflow/`, orchestrates the multi-agent workflow

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## License

[Add your license information here]
