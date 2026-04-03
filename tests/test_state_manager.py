import unittest
from unittest.mock import patch, MagicMock
from src.storage.state_manager import StateManager

class TestStateManager(unittest.TestCase):
    @patch('src.storage.state_manager.AzureBlobClient')
    def test_save_and_load_state(self, mock_client):
        mock_container = MagicMock()
        mock_client.return_value.get_container_client.return_value = mock_container
        sm = StateManager()
        sm.save_state('testid', {'foo': 'bar'})
        self.assertTrue(mock_container.upload_blob.called)
        mock_blob = MagicMock()
        mock_blob.download_blob.return_value.readall.return_value = b'{"foo": "bar"}'
        mock_container.get_blob_client.return_value = mock_blob
        result = sm.load_state('testid')
        self.assertEqual(result, {'foo': 'bar'})

    @patch('src.storage.state_manager.AzureBlobClient')
    def test_delete_state(self, mock_client):
        mock_container = MagicMock()
        mock_client.return_value.get_container_client.return_value = mock_container
        sm = StateManager()
        sm.delete_state('testid')
        self.assertTrue(mock_container.delete_blob.called)

    @patch('src.storage.state_manager.AzureBlobClient')
    def test_list_states(self, mock_client):
        mock_container = MagicMock()
        mock_container.list_blobs.return_value = [MagicMock(name='a.json'), MagicMock(name='b.json')]
        mock_client.return_value.get_container_client.return_value = mock_container
        sm = StateManager()
        result = sm.list_states()
        self.assertEqual(result, ['a.json', 'b.json'])

if __name__ == '__main__':
    unittest.main()
