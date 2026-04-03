"""Unit tests for Azure Blob Storage client."""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock

from src.storage.azure_blob_client import AzureBlobClient


class TestAzureBlobClient(unittest.TestCase):
    """Test cases for AzureBlobClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = AzureBlobClient(container_name="test-container")
    
    @patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test_connection_string'})
    @patch('src.storage.azure_blob_client.BlobServiceClient')
    def test_initialize_client_with_connection_string(self, mock_blob_service):
        """Test client initialization with connection string."""
        mock_service_instance = Mock()
        mock_blob_service.from_connection_string.return_value = mock_service_instance
        
        result = self.client._initialize_client()
        
        mock_blob_service.from_connection_string.assert_called_once_with('test_connection_string')
        self.assertEqual(result, mock_service_instance)
    
    @patch.dict(os.environ, {
        'AZURE_STORAGE_ACCOUNT_NAME': 'testaccount',
        'AZURE_STORAGE_ACCOUNT_KEY': 'testkey'
    })
    @patch('src.storage.azure_blob_client.BlobServiceClient')
    def test_initialize_client_with_account_key(self, mock_blob_service):
        """Test client initialization with account name and key."""
        mock_service_instance = Mock()
        mock_blob_service.return_value = mock_service_instance
        
        result = self.client._initialize_client()
        
        mock_blob_service.assert_called_once_with(
            account_url='https://testaccount.blob.core.windows.net',
            credential='testkey'
        )
        self.assertEqual(result, mock_service_instance)
    
    @patch.dict(os.environ, {'AZURE_STORAGE_ACCOUNT_NAME': 'testaccount'})
    @patch('src.storage.azure_blob_client.BlobServiceClient')
    @patch('src.storage.azure_blob_client.DefaultAzureCredential')
    def test_initialize_client_with_default_credential(self, mock_credential, mock_blob_service):
        """Test client initialization with DefaultAzureCredential."""
        mock_service_instance = Mock()
        mock_blob_service.return_value = mock_service_instance
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance
        
        result = self.client._initialize_client()
        
        mock_credential.assert_called_once()
        mock_blob_service.assert_called_once_with(
            account_url='https://testaccount.blob.core.windows.net',
            credential=mock_credential_instance
        )
        self.assertEqual(result, mock_service_instance)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_initialize_client_no_auth_raises_error(self):
        """Test client initialization raises error when no auth is configured."""
        with self.assertRaises(ValueError) as context:
            self.client._initialize_client()
        
        self.assertIn("No Azure Storage authentication configured", str(context.exception))
    
    @patch('src.storage.azure_blob_client.AzureBlobClient._get_container_client')
    def test_upload_blob_success(self, mock_get_container):
        """Test successful blob upload."""
        mock_container = Mock()
        mock_get_container.return_value = mock_container
        
        result = self.client.upload_blob("test.json", b"test data", {"key": "value"})
        
        mock_container.upload_blob.assert_called_once_with(
            name="test.json",
            data=b"test data",
            metadata={"key": "value"},
            overwrite=True
        )
        self.assertTrue(result)
    
    @patch('src.storage.azure_blob_client.AzureBlobClient._get_container_client')
    def test_download_blob_success(self, mock_get_container):
        """Test successful blob download."""
        mock_container = Mock()
        mock_blob_client = Mock()
        mock_download_stream = Mock()
        mock_download_stream.readall.return_value = b"test data"
        
        mock_container.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.return_value = mock_download_stream
        mock_get_container.return_value = mock_container
        
        result = self.client.download_blob("test.json")
        
        mock_container.get_blob_client.assert_called_once_with("test.json")
        mock_blob_client.download_blob.assert_called_once()
        self.assertEqual(result, b"test data")
    
    @patch('src.storage.azure_blob_client.AzureBlobClient._get_container_client')
    def test_delete_blob_success(self, mock_get_container):
        """Test successful blob deletion."""
        mock_container = Mock()
        mock_blob_client = Mock()
        
        mock_container.get_blob_client.return_value = mock_blob_client
        mock_get_container.return_value = mock_container
        
        result = self.client.delete_blob("test.json")
        
        mock_container.get_blob_client.assert_called_once_with("test.json")
        mock_blob_client.delete_blob.assert_called_once()
        self.assertTrue(result)
    
    @patch('src.storage.azure_blob_client.AzureBlobClient._get_container_client')
    def test_list_blobs_success(self, mock_get_container):
        """Test successful blob listing."""
        mock_container = Mock()
        mock_blob1 = Mock()
        mock_blob1.name = "blob1.json"
        mock_blob2 = Mock()
        mock_blob2.name = "blob2.json"
        
        mock_container.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_get_container.return_value = mock_container
        
        result = self.client.list_blobs()
        
        mock_container.list_blobs.assert_called_once_with(name_starts_with=None)
        self.assertEqual(result, ["blob1.json", "blob2.json"])


if __name__ == '__main__':
    unittest.main()