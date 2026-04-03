import logging
from typing import Optional
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.identity import DefaultAzureCredential
import os

class AzureBlobClient:
    """
    Azure Blob Storage client for workflow state management.
    Handles authentication, container management, and error handling.
    """
    def __init__(self, container_name: str = "workflow-states"):
        self.container_name = container_name
        self.logger = logging.getLogger("AzureBlobClient")
        self.service_client = self._init_blob_service_client()
        self.container_client = self._get_or_create_container()

    def _init_blob_service_client(self) -> BlobServiceClient:
        try:
            conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if conn_str:
                self.logger.debug("Using connection string for Azure Blob authentication.")
                return BlobServiceClient.from_connection_string(conn_str)
            account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
            if account_name and account_key:
                self.logger.debug("Using account name/key for Azure Blob authentication.")
                return BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
            self.logger.debug("Using DefaultAzureCredential for Azure Blob authentication.")
            return BlobServiceClient(account_url=f"https://{os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net", credential=DefaultAzureCredential())
        except Exception as e:
            self.logger.error(f"Failed to initialize BlobServiceClient: {e}")
            raise

    def _get_or_create_container(self) -> ContainerClient:
        try:
            container_client = self.service_client.get_container_client(self.container_name)
            if not container_client.exists():
                self.logger.info(f"Creating container: {self.container_name}")
                container_client.create_container()
            return container_client
        except Exception as e:
            self.logger.error(f"Failed to get or create container: {e}")
            raise

    def get_container_client(self) -> ContainerClient:
        return self.container_client
