import unittest
from unittest.mock import patch, MagicMock
from src.storage.azure_blob_client import AzureBlobClient

class TestAzureBlobClient(unittest.TestCase):
    @patch('src.storage.azure_blob_client.BlobServiceClient')
    def test_init_blob_service_client_connection_string(self, mock_bsc):
        with patch('os.getenv', side_effect=lambda k: 'connstr' if k == 'AZURE_STORAGE_CONNECTION_STRING' else None):
            client = AzureBlobClient()
            self.assertTrue(mock_bsc.from_connection_string.called)

    @patch('src.storage.azure_blob_client.BlobServiceClient')
    def test_init_blob_service_client_account_key(self, mock_bsc):
        with patch('os.getenv', side_effect=lambda k: 'test' if k in ['AZURE_STORAGE_ACCOUNT_NAME', 'AZURE_STORAGE_ACCOUNT_KEY'] else None):
            client = AzureBlobClient()
            self.assertTrue(mock_bsc.called)

    @patch('src.storage.azure_blob_client.BlobServiceClient')
    def test_get_or_create_container(self, mock_bsc):
        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_container.exists.return_value = False
        mock_service.get_container_client.return_value = mock_container
        mock_bsc.return_value = mock_service
        with patch('os.getenv', return_value='connstr'):
            client = AzureBlobClient()
            self.assertTrue(mock_container.create_container.called)

if __name__ == '__main__':
    unittest.main()
