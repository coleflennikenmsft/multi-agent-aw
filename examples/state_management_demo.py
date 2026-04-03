import os
from src.state import BlobStorageClient, StateConfig, StateSerializer, BlobStateManager, CheckpointManager

def main():
    # Set up config (normally via env vars)
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "<your-connection-string>"
    os.environ["AZURE_STORAGE_CONTAINER_NAME"] = "state-management-demo"
    config = StateConfig()
    blob_client = BlobStorageClient(config.get_connection_string(), config.get_container_name())
    serializer = StateSerializer()
    state_manager = BlobStateManager(blob_client, serializer)
    checkpoint_manager = CheckpointManager(state_manager)

    # Save state
    state = {"step": 1, "data": "foo"}
    state_manager.save_state("demo_state.json", state)

    # Load state
    loaded = state_manager.load_state("demo_state.json")
    print("Loaded state:", loaded)

    # Create checkpoint
    checkpoint_manager.create_checkpoint("demo", state)

    # List checkpoints
    print("Checkpoints:", checkpoint_manager.list_checkpoints())

    # Restore from checkpoint
    restored = checkpoint_manager.restore_from_checkpoint("demo")
    print("Restored checkpoint:", restored)

    # Delete checkpoint
    checkpoint_manager.delete_checkpoint("demo")

    # Delete state
    state_manager.delete_state("demo_state.json")

if __name__ == "__main__":
    main()
