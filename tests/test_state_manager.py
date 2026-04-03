"""Tests for State Manager."""

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from azure.core.exceptions import ResourceNotFoundError

from src.storage.state_manager import StateManager


class TestStateManager(unittest.TestCase):
    """Test cases for StateManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the AzureBlobClient
        self.mock_blob_client = MagicMock()
        self.mock_container = MagicMock()
        self.mock_blob_client.get_or_create_container.return_value = self.mock_container
        
        # Create StateManager with mocked client
        with patch("src.storage.state_manager.AzureBlobClient", return_value=self.mock_blob_client):
            self.state_manager = StateManager(blob_client=self.mock_blob_client)
    
    def test_init_default_container(self):
        """Test initialization with default container name."""
        self.assertEqual(self.state_manager._container_name, "workflow-states")
        self.mock_blob_client.get_or_create_container.assert_called_once_with("workflow-states")
    
    def test_init_custom_container(self):
        """Test initialization with custom container name."""
        mock_client = MagicMock()
        mock_client.get_or_create_container.return_value = MagicMock()
        
        with patch("src.storage.state_manager.AzureBlobClient", return_value=mock_client):
            manager = StateManager(blob_client=mock_client, container_name="custom-container")
        
        self.assertEqual(manager._container_name, "custom-container")
        mock_client.get_or_create_container.assert_called_with("custom-container")
    
    def test_get_blob_name(self):
        """Test blob name generation."""
        workflow_id = "workflow_123"
        blob_name = self.state_manager._get_blob_name(workflow_id)
        self.assertEqual(blob_name, "workflow_123.json")
    
    def test_get_blob_name_sanitizes_slashes(self):
        """Test blob name sanitization of slashes."""
        workflow_id = "workflow/123/test"
        blob_name = self.state_manager._get_blob_name(workflow_id)
        self.assertEqual(blob_name, "workflow_123_test.json")
    
    def test_save_state_success(self):
        """Test successful state save."""
        workflow_id = "wf_123"
        state_data = {
            "status": "paused",
            "context": {"step": 2, "data": "test"},
        }
        
        mock_blob_client = MagicMock()
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        result = self.state_manager.save_state(workflow_id, state_data)
        
        self.assertTrue(result)
        self.mock_container.get_blob_client.assert_called_once_with("wf_123.json")
        mock_blob_client.upload_blob.assert_called_once()
        
        # Check that workflow_id and timestamp were added
        self.assertEqual(state_data["workflow_id"], workflow_id)
        self.assertIn("timestamp", state_data)
    
    def test_save_state_adds_timestamp(self):
        """Test that save_state adds timestamp if not present."""
        workflow_id = "wf_123"
        state_data = {"status": "running"}
        
        mock_blob_client = MagicMock()
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        self.state_manager.save_state(workflow_id, state_data)
        
        self.assertIn("timestamp", state_data)
    
    def test_save_state_preserves_existing_timestamp(self):
        """Test that save_state preserves existing timestamp."""
        workflow_id = "wf_123"
        original_timestamp = "2024-01-01T00:00:00Z"
        state_data = {
            "status": "running",
            "timestamp": original_timestamp,
        }
        
        mock_blob_client = MagicMock()
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        self.state_manager.save_state(workflow_id, state_data)
        
        self.assertEqual(state_data["timestamp"], original_timestamp)
    
    def test_save_state_invalid_json(self):
        """Test save_state with non-serializable data."""
        workflow_id = "wf_123"
        state_data = {"invalid": set([1, 2, 3])}  # Sets are not JSON serializable
        
        with self.assertRaises(ValueError) as context:
            self.state_manager.save_state(workflow_id, state_data)
        
        self.assertIn("not JSON serializable", str(context.exception))
    
    def test_load_state_success(self):
        """Test successful state load."""
        workflow_id = "wf_123"
        state_data = {
            "workflow_id": workflow_id,
            "status": "paused",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        state_json = json.dumps(state_data)
        
        mock_blob_client = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = state_json.encode("utf-8")
        mock_blob_client.download_blob.return_value = mock_download
        
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        loaded_state = self.state_manager.load_state(workflow_id)
        
        self.assertEqual(loaded_state, state_data)
        self.mock_container.get_blob_client.assert_called_once_with("wf_123.json")
    
    def test_load_state_not_found(self):
        """Test loading non-existent state."""
        workflow_id = "wf_999"
        
        mock_blob_client = MagicMock()
        mock_blob_client.download_blob.side_effect = ResourceNotFoundError("Not found")
        
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        loaded_state = self.state_manager.load_state(workflow_id)
        
        self.assertIsNone(loaded_state)
    
    def test_load_state_invalid_json(self):
        """Test loading state with invalid JSON."""
        workflow_id = "wf_123"
        invalid_json = "{ invalid json }"
        
        mock_blob_client = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = invalid_json.encode("utf-8")
        mock_blob_client.download_blob.return_value = mock_download
        
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        with self.assertRaises(ValueError) as context:
            self.state_manager.load_state(workflow_id)
        
        self.assertIn("Invalid JSON", str(context.exception))
    
    def test_delete_state_success(self):
        """Test successful state deletion."""
        workflow_id = "wf_123"
        
        mock_blob_client = MagicMock()
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        result = self.state_manager.delete_state(workflow_id)
        
        self.assertTrue(result)
        mock_blob_client.delete_blob.assert_called_once()
    
    def test_delete_state_not_found(self):
        """Test deleting non-existent state."""
        workflow_id = "wf_999"
        
        mock_blob_client = MagicMock()
        mock_blob_client.delete_blob.side_effect = ResourceNotFoundError("Not found")
        
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        result = self.state_manager.delete_state(workflow_id)
        
        self.assertFalse(result)
    
    def test_list_states(self):
        """Test listing all states."""
        mock_blobs = [
            MagicMock(name="workflow1.json"),
            MagicMock(name="workflow2.json"),
            MagicMock(name="workflow3.json"),
        ]
        self.mock_container.list_blobs.return_value = mock_blobs
        
        states = self.state_manager.list_states()
        
        self.assertEqual(states, ["workflow1", "workflow2", "workflow3"])
    
    def test_list_states_filters_non_json(self):
        """Test that list_states filters out non-JSON files."""
        mock_blobs = [
            MagicMock(name="workflow1.json"),
            MagicMock(name="readme.txt"),
            MagicMock(name="workflow2.json"),
        ]
        self.mock_container.list_blobs.return_value = mock_blobs
        
        states = self.state_manager.list_states()
        
        self.assertEqual(states, ["workflow1", "workflow2"])
    
    def test_state_exists_true(self):
        """Test checking if state exists (true case)."""
        workflow_id = "wf_123"
        
        mock_blob_client = MagicMock()
        mock_blob_client.exists.return_value = True
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        exists = self.state_manager.state_exists(workflow_id)
        
        self.assertTrue(exists)
    
    def test_state_exists_false(self):
        """Test checking if state exists (false case)."""
        workflow_id = "wf_999"
        
        mock_blob_client = MagicMock()
        mock_blob_client.exists.return_value = False
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        exists = self.state_manager.state_exists(workflow_id)
        
        self.assertFalse(exists)
    
    def test_get_state_metadata_success(self):
        """Test getting state metadata."""
        workflow_id = "wf_123"
        
        mock_blob_client = MagicMock()
        mock_properties = MagicMock()
        mock_properties.last_modified = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        mock_properties.size = 1024
        mock_properties.content_type = "application/json"
        mock_properties.metadata = {"status": "paused"}
        
        mock_blob_client.get_blob_properties.return_value = mock_properties
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        metadata = self.state_manager.get_state_metadata(workflow_id)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["size"], 1024)
        self.assertEqual(metadata["content_type"], "application/json")
        self.assertEqual(metadata["status"], "paused")
    
    def test_get_state_metadata_not_found(self):
        """Test getting metadata for non-existent state."""
        workflow_id = "wf_999"
        
        mock_blob_client = MagicMock()
        mock_blob_client.get_blob_properties.side_effect = ResourceNotFoundError("Not found")
        self.mock_container.get_blob_client.return_value = mock_blob_client
        
        metadata = self.state_manager.get_state_metadata(workflow_id)
        
        self.assertIsNone(metadata)
    
    def test_context_manager(self):
        """Test using StateManager as context manager."""
        with patch("src.storage.state_manager.AzureBlobClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_or_create_container.return_value = MagicMock()
            
            with StateManager(blob_client=mock_client) as manager:
                self.assertIsNotNone(manager)
            
            mock_client.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
