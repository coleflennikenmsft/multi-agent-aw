"""Unit tests for state manager."""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock

from src.storage.state_manager import StateManager


class TestStateManager(unittest.TestCase):
    """Test cases for StateManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.state_manager = StateManager(container_name="test-states")
    
    def test_generate_blob_name(self):
        """Test blob name generation."""
        workflow_id = "test-workflow-123"
        expected = "test-workflow-123.json"
        result = self.state_manager._generate_blob_name(workflow_id)
        self.assertEqual(result, expected)
    
    def test_generate_blob_name_sanitization(self):
        """Test blob name sanitization for invalid characters."""
        workflow_id = "test/workflow:123*"
        expected = "testworkflow123.json"
        result = self.state_manager._generate_blob_name(workflow_id)
        self.assertEqual(result, expected)
    
    @patch('src.storage.state_manager.datetime')
    def test_save_state_success(self, mock_datetime):
        """Test successful state saving."""
        # Mock datetime
        mock_now = Mock()
        mock_now.isoformat.return_value = "2023-01-01T12:00:00Z"
        mock_datetime.now.return_value = mock_now
        
        # Mock blob client
        self.state_manager.blob_client.upload_blob = Mock(return_value=True)
        
        state_data = {"status": "running", "step": 1}
        result = self.state_manager.save_state("test-workflow", state_data)
        
        # Verify blob_client.upload_blob was called
        self.state_manager.blob_client.upload_blob.assert_called_once()
        call_args = self.state_manager.blob_client.upload_blob.call_args
        
        # Check blob name
        self.assertEqual(call_args[1]['blob_name'], "test-workflow.json")
        
        # Check that data contains enriched state
        blob_data = call_args[1]['data']
        parsed_data = json.loads(blob_data.decode('utf-8'))
        self.assertEqual(parsed_data['workflow_id'], "test-workflow")
        self.assertEqual(parsed_data['status'], "running")
        self.assertEqual(parsed_data['step'], 1)
        self.assertIn('timestamp', parsed_data)
        
        self.assertTrue(result)
    
    def test_load_state_success(self):
        """Test successful state loading."""
        test_state = {
            "workflow_id": "test-workflow",
            "timestamp": "2023-01-01T12:00:00Z",
            "status": "running",
            "step": 1
        }
        json_data = json.dumps(test_state).encode('utf-8')
        
        self.state_manager.blob_client.download_blob = Mock(return_value=json_data)
        
        result = self.state_manager.load_state("test-workflow")
        
        self.state_manager.blob_client.download_blob.assert_called_once_with("test-workflow.json")
        self.assertEqual(result, test_state)
    
    def test_load_state_not_found(self):
        """Test loading state when blob not found."""
        self.state_manager.blob_client.download_blob = Mock(return_value=None)
        
        result = self.state_manager.load_state("test-workflow")
        
        self.state_manager.blob_client.download_blob.assert_called_once_with("test-workflow.json")
        self.assertIsNone(result)
    
    def test_delete_state_success(self):
        """Test successful state deletion."""
        self.state_manager.blob_client.delete_blob = Mock(return_value=True)
        
        result = self.state_manager.delete_state("test-workflow")
        
        self.state_manager.blob_client.delete_blob.assert_called_once_with("test-workflow.json")
        self.assertTrue(result)
    
    def test_list_states_success(self):
        """Test successful state listing."""
        blob_names = ["workflow1.json", "workflow2.json", "other-file.txt"]
        self.state_manager.blob_client.list_blobs = Mock(return_value=blob_names)
        
        result = self.state_manager.list_states()
        
        self.state_manager.blob_client.list_blobs.assert_called_once_with(name_starts_with="")
        # Should only return workflow IDs from .json files
        self.assertEqual(result, ["workflow1", "workflow2"])
    
    @patch.dict('os.environ', {
        'GITHUB_RUN_ID': '123456',
        'GITHUB_REPOSITORY': 'owner/repo',
        'GITHUB_ACTOR': 'test-user'
    })
    def test_save_checkpoint_success(self):
        """Test successful checkpoint saving."""
        self.state_manager.save_state = Mock(return_value=True)
        
        context = {"task": "test task", "step": 1}
        result = self.state_manager.save_checkpoint(
            "test-workflow", 
            "planner", 
            context, 
            "paused"
        )
        
        # Verify save_state was called with checkpoint data
        self.state_manager.save_state.assert_called_once()
        call_args = self.state_manager.save_state.call_args[0]
        
        self.assertEqual(call_args[0], "test-workflow")  # workflow_id
        checkpoint_data = call_args[1]
        self.assertEqual(checkpoint_data['executor_id'], "planner")
        self.assertEqual(checkpoint_data['status'], "paused")
        self.assertEqual(checkpoint_data['context'], context)
        self.assertIn('metadata', checkpoint_data)
        self.assertIn('github', checkpoint_data['metadata'])
        
        self.assertTrue(result)
    
    def test_load_checkpoint_delegates_to_load_state(self):
        """Test that load_checkpoint delegates to load_state."""
        expected_state = {"test": "data"}
        self.state_manager.load_state = Mock(return_value=expected_state)
        
        result = self.state_manager.load_checkpoint("test-workflow")
        
        self.state_manager.load_state.assert_called_once_with("test-workflow")
        self.assertEqual(result, expected_state)


if __name__ == '__main__':
    unittest.main()