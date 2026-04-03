"""Tests for Azure Blob Storage client."""

import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from azure.core.exceptions import AzureError, ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContainerClient

from src.storage.azure_blob_client import AzureBlobClient


class TestAzureBlobClient(unittest.TestCase):
    """Test cases for AzureBlobClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear environment variables
        self.original_env = os.environ.copy()
        for key in ["AZURE_STORAGE_CONNECTION_STRING", "AZURE_STORAGE_ACCOUNT_NAME", "AZURE_STORAGE_ACCOUNT_KEY"]:
            os.environ.pop(key, None)
    
    def tearDown(self):
        """Clean up after tests."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_init_with_connection_string(self, mock_blob_service):
        """Test initialization with connection string."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey"
        
        client = AzureBlobClient(connection_string=connection_string)
        
        mock_blob_service.from_connection_string.assert_called_once_with(connection_string)
        self.assertIsNotNone(client._service_client)
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_init_with_env_connection_string(self, mock_blob_service):
        """Test initialization with connection string from environment."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey"
        os.environ["AZURE_STORAGE_CONNECTION_STRING"] = connection_string
        
        client = AzureBlobClient()
        
        mock_blob_service.from_connection_string.assert_called_once_with(connection_string)
        self.assertIsNotNone(client._service_client)
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_init_with_account_key(self, mock_blob_service):
        """Test initialization with account name and key."""
        account_name = "testaccount"
        account_key = "testkey"
        
        client = AzureBlobClient(account_name=account_name, account_key=account_key)
        
        expected_url = f"https://{account_name}.blob.core.windows.net"
        mock_blob_service.assert_called_once()
        call_kwargs = mock_blob_service.call_args[1]
        self.assertEqual(call_kwargs["account_url"], expected_url)
        self.assertEqual(call_kwargs["credential"], account_key)
    
    @patch("src.storage.azure_blob_client.DefaultAzureCredential")
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_init_with_managed_identity(self, mock_blob_service, mock_credential):
        """Test initialization with managed identity."""
        account_name = "testaccount"
        
        client = AzureBlobClient(account_name=account_name)
        
        expected_url = f"https://{account_name}.blob.core.windows.net"
        mock_credential.assert_called_once()
        mock_blob_service.assert_called_once()
    
    def test_init_without_credentials_raises_error(self):
        """Test initialization without credentials raises ValueError."""
        with self.assertRaises(ValueError) as context:
            AzureBlobClient()
        
        self.assertIn("No valid Azure Storage authentication", str(context.exception))
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_get_or_create_container_exists(self, mock_blob_service):
        """Test getting an existing container."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey"
        
        # Set up mock
        mock_service_instance = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service_instance
        
        mock_container = MagicMock()
        mock_container.exists.return_value = True
        mock_service_instance.get_container_client.return_value = mock_container
        
        client = AzureBlobClient(connection_string=connection_string)
        container = client.get_or_create_container("test-container")
        
        mock_service_instance.get_container_client.assert_called_once_with("test-container")
        mock_container.exists.assert_called_once()
        mock_service_instance.create_container.assert_not_called()
        self.assertEqual(container, mock_container)
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_get_or_create_container_creates_new(self, mock_blob_service):
        """Test creating a new container."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey"
        
        # Set up mock
        mock_service_instance = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service_instance
        
        mock_container = MagicMock()
        mock_container.exists.return_value = False
        mock_service_instance.get_container_client.return_value = mock_container
        
        mock_new_container = MagicMock()
        mock_service_instance.create_container.return_value = mock_new_container
        
        client = AzureBlobClient(connection_string=connection_string)
        container = client.get_or_create_container("test-container")
        
        mock_service_instance.create_container.assert_called_once_with("test-container")
        self.assertEqual(container, mock_new_container)
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_list_containers(self, mock_blob_service):
        """Test listing containers."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey"
        
        # Set up mock
        mock_service_instance = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service_instance
        
        mock_containers = [
            MagicMock(name="container1"),
            MagicMock(name="container2"),
            MagicMock(name="container3"),
        ]
        mock_service_instance.list_containers.return_value = mock_containers
        
        client = AzureBlobClient(connection_string=connection_string)
        containers = client.list_containers()
        
        self.assertEqual(containers, ["container1", "container2", "container3"])
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_delete_container_success(self, mock_blob_service):
        """Test successful container deletion."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey"
        
        # Set up mock
        mock_service_instance = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service_instance
        
        client = AzureBlobClient(connection_string=connection_string)
        result = client.delete_container("test-container")
        
        mock_service_instance.delete_container.assert_called_once_with("test-container")
        self.assertTrue(result)
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_delete_container_not_found(self, mock_blob_service):
        """Test deleting a non-existent container."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey"
        
        # Set up mock
        mock_service_instance = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service_instance
        mock_service_instance.delete_container.side_effect = ResourceNotFoundError("Not found")
        
        client = AzureBlobClient(connection_string=connection_string)
        result = client.delete_container("test-container")
        
        self.assertFalse(result)
    
    @patch("src.storage.azure_blob_client.BlobServiceClient")
    def test_context_manager(self, mock_blob_service):
        """Test using client as context manager."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey"
        
        # Set up mock
        mock_service_instance = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service_instance
        
        with AzureBlobClient(connection_string=connection_string) as client:
            self.assertIsNotNone(client._service_client)
        
        mock_service_instance.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
