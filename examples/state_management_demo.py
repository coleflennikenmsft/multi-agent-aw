"""
Azure Blob Storage State Management System - Demo Script

This script demonstrates the key features of the state management system including:
- Basic state save/load operations
- Checkpoint management for step-level recovery
- Versioning and snapshots
- Error handling and graceful degradation
- Compression and serialization formats

Prerequisites:
    pip install azure-storage-blob>=12.19.0

Environment Variables (set one of these options):
    Option 1 - Connection String (recommended):
        AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
    
    Option 2 - Account Credentials:
        AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
        AZURE_STORAGE_ACCOUNT_KEY="your-account-key"
    
    Optional:
        AZURE_STORAGE_CONTAINER_NAME="workflow-state"  # default if not set

Note: This demo will work even without Azure credentials by catching and demonstrating error handling.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from state import BlobStateManager, CheckpointManager, StateConfig
    from state.serialization import SerializationFormat
except ImportError as e:
    print(f"Error importing state management modules: {e}")
    print("Make sure you're running from the project root and have installed dependencies")
    sys.exit(1)

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_basic_state_operations():
    """Demonstrate basic state save/load/delete operations."""
    print("\\n" + "="*60)
    print("DEMO 1: Basic State Operations")
    print("="*60)
    
    try:
        # Initialize state manager
        manager = BlobStateManager()
        
        # Sample workflow state
        workflow_id = "demo-workflow-001"
        sample_state = {
            "step": "data_processing",
            "progress": 75,
            "processed_records": 1500,
            "config": {
                "batch_size": 100,
                "timeout": 30
            },
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "user": "demo_user",
                "session": "abc123"
            }
        }
        
        print(f"\\nSaving state for workflow: {workflow_id}")
        print(f"State data: {json.dumps(sample_state, indent=2)}")
        
        # Save state
        success = manager.save_state(workflow_id, sample_state)
        print(f"Save result: {'SUCCESS' if success else 'FAILED'}")
        
        if success:
            # Load state back
            print(f"\\nLoading state for workflow: {workflow_id}")
            loaded_state = manager.load_state(workflow_id)
            
            if loaded_state:
                print("Loaded state successfully:")
                print(json.dumps(loaded_state, indent=2))
                
                # Verify data integrity
                if loaded_state["progress"] == sample_state["progress"]:
                    print("✓ Data integrity verified")
                else:
                    print("✗ Data integrity check failed")
            else:
                print("Failed to load state")
        
        # List all states
        print("\\nListing all workflow states:")
        states = manager.list_states()
        for state in states:
            print(f"  - {state['workflow_id']}: {state['size']} bytes, "
                  f"modified: {state['last_modified']}")
    
    except Exception as e:
        print(f"Demo 1 Error: {e}")
        logger.error(f"Basic state operations demo failed: {e}")


def demo_versioning_and_snapshots():
    """Demonstrate state versioning and snapshot capabilities."""
    print("\\n" + "="*60)
    print("DEMO 2: Versioning and Snapshots")
    print("="*60)
    
    try:
        manager = BlobStateManager()
        workflow_id = "demo-workflow-002"
        
        # Save multiple versions
        for i in range(3):
            state = {
                "version": i + 1,
                "step": f"step_{i+1}",
                "data": f"Version {i+1} data",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"\\nSaving version {i+1} as snapshot...")
            success = manager.save_state(workflow_id, state, create_snapshot=True)
            print(f"Snapshot {i+1}: {'SUCCESS' if success else 'FAILED'}")
        
        # List all versions
        print(f"\\nListing all versions for {workflow_id}:")
        versions = manager.list_versions(workflow_id)
        for version in versions:
            print(f"  - Version: {version['version']}, "
                  f"Size: {version['size']} bytes, "
                  f"Latest: {version['is_latest']}")
        
        # Load latest version
        print("\\nLoading latest version:")
        latest = manager.load_state(workflow_id)
        if latest:
            print(f"Latest version data: {json.dumps(latest, indent=2)}")
    
    except Exception as e:
        print(f"Demo 2 Error: {e}")
        logger.error(f"Versioning demo failed: {e}")


def demo_checkpoint_management():
    """Demonstrate checkpoint management for step-level recovery."""
    print("\\n" + "="*60)
    print("DEMO 3: Checkpoint Management")
    print("="*60)
    
    try:
        checkpoint_manager = CheckpointManager()
        workflow_id = "demo-workflow-003"
        
        # Simulate a multi-step workflow
        workflow_steps = [
            ("initialization", {"status": "initialized", "config": {"threads": 4}}),
            ("data_loading", {"status": "loaded", "records": 1000, "errors": 0}),
            ("processing", {"status": "processing", "completed": 750, "remaining": 250}),
            ("validation", {"status": "validating", "passed": 700, "failed": 50}),
        ]
        
        # Create checkpoints for each step
        print("\\nCreating checkpoints for workflow steps:")
        for step_name, step_data in workflow_steps:
            print(f"Creating checkpoint for step: {step_name}")
            success = checkpoint_manager.create_checkpoint(workflow_id, step_name, step_data)
            print(f"  Result: {'SUCCESS' if success else 'FAILED'}")
        
        # List all checkpoints
        print(f"\\nListing checkpoints for {workflow_id}:")
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        for cp in checkpoints:
            print(f"  - Step: {cp['step']}, Size: {cp['size']} bytes, "
                  f"Modified: {cp['last_modified']}")
        
        # Restore from a specific checkpoint
        restore_step = "processing"
        print(f"\\nRestoring from checkpoint: {restore_step}")
        restored_data = checkpoint_manager.restore_from_checkpoint(workflow_id, restore_step)
        
        if restored_data:
            print(f"Restored data: {json.dumps(restored_data, indent=2)}")
            print("✓ Checkpoint restoration successful")
        else:
            print("✗ Checkpoint restoration failed")
    
    except Exception as e:
        print(f"Demo 3 Error: {e}")
        logger.error(f"Checkpoint management demo failed: {e}")


def demo_serialization_formats():
    """Demonstrate different serialization formats and compression."""
    print("\\n" + "="*60)
    print("DEMO 4: Serialization Formats and Compression")
    print("="*60)
    
    try:
        from state.serialization import StateSerializer
        
        # Test data
        test_data = {
            "large_text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 100,
            "numbers": list(range(1000)),
            "nested": {
                "level1": {
                    "level2": {
                        "data": "deep nested data" * 50
                    }
                }
            }
        }
        
        print("Testing different serialization formats:")
        
        # JSON without compression
        json_serializer = StateSerializer(SerializationFormat.JSON, use_compression=False)
        json_data = json_serializer.serialize(test_data)
        print(f"\\nJSON (no compression): {len(json_data)} bytes")
        
        # JSON with compression
        json_compressed = StateSerializer(SerializationFormat.JSON, use_compression=True)
        json_compressed_data = json_compressed.serialize(test_data)
        print(f"JSON (compressed): {len(json_compressed_data)} bytes")
        compression_ratio = len(json_compressed_data) / len(json_data)
        print(f"Compression ratio: {compression_ratio:.2f} ({100*(1-compression_ratio):.1f}% smaller)")
        
        # Test deserialization
        restored_data = json_compressed.deserialize(json_compressed_data)
        print(f"Deserialization: {'SUCCESS' if restored_data == test_data else 'FAILED'}")
        
        # Pickle format
        pickle_serializer = StateSerializer(SerializationFormat.PICKLE, use_compression=True)
        pickle_data = pickle_serializer.serialize(test_data)
        print(f"Pickle (compressed): {len(pickle_data)} bytes")
        
    except Exception as e:
        print(f"Demo 4 Error: {e}")
        logger.error(f"Serialization demo failed: {e}")


def demo_error_handling():
    """Demonstrate error handling and graceful degradation."""
    print("\\n" + "="*60)
    print("DEMO 5: Error Handling and Graceful Degradation")
    print("="*60)
    
    try:
        from state.config import StateConfig
        
        # Test with invalid configuration
        print("Testing configuration validation:")
        
        # Save current environment
        original_env = {}
        for key in ['AZURE_STORAGE_CONNECTION_STRING', 'AZURE_STORAGE_ACCOUNT_NAME', 'AZURE_STORAGE_ACCOUNT_KEY']:
            original_env[key] = os.environ.get(key)
        
        try:
            # Clear all Azure config
            for key in original_env:
                if key in os.environ:
                    del os.environ[key]
            
            print("\\nAttempting to create config with no credentials:")
            config = StateConfig.from_env()
            print("✗ Should have failed validation")
        
        except ValueError as e:
            print(f"✓ Correctly caught configuration error: {e}")
        
        finally:
            # Restore environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
        
        # Test operations without Azure connection
        print("\\nTesting operations without Azure connection (simulated):")
        
        try:
            # This might fail if no credentials are available, which is expected
            manager = BlobStateManager()
            success = manager.save_state("test", {"data": "test"})
            print(f"Save without credentials: {'SUCCESS' if success else 'FAILED (expected)'}")
        
        except Exception as e:
            print(f"✓ Gracefully handled connection error: {type(e).__name__}")
    
    except Exception as e:
        print(f"Demo 5 Error: {e}")
        logger.error(f"Error handling demo failed: {e}")


def main():
    """Run all demos."""
    print("Azure Blob Storage State Management System - Demo")
    print("=" * 60)
    
    # Check if Azure credentials are configured
    has_connection_string = bool(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
    has_account_creds = bool(os.getenv('AZURE_STORAGE_ACCOUNT_NAME') and 
                            os.getenv('AZURE_STORAGE_ACCOUNT_KEY'))
    
    if has_connection_string:
        print("✓ Azure connection string found")
    elif has_account_creds:
        print("✓ Azure account credentials found")
    else:
        print("⚠ No Azure credentials found - some demos will show error handling")
        print("  Set AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY")
    
    print(f"Container name: {os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'workflow-state (default)')}")
    
    # Run all demos
    try:
        demo_basic_state_operations()
        demo_versioning_and_snapshots()
        demo_checkpoint_management()
        demo_serialization_formats()
        demo_error_handling()
        
        print("\\n" + "="*60)
        print("DEMO COMPLETE")
        print("="*60)
        print("All demos have been executed. Check the output above for results.")
        print("Note: Some operations may fail if Azure credentials are not configured,")
        print("which demonstrates the error handling capabilities of the system.")
    
    except KeyboardInterrupt:
        print("\\nDemo interrupted by user")
    except Exception as e:
        print(f"\\nDemo failed with error: {e}")
        logger.error(f"Demo execution failed: {e}")


if __name__ == "__main__":
    main()