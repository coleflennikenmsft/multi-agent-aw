from typing import Optional, List
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
from .config import Config

class BlobStorageClient:
    """
    Azure Blob Storage client for context state management.
    """
    def __init__(self, container_name: str):
        connection_string = Config.get_connection_string()
        account_url = Config.get_account_url()
        account_name = Config.get_account_name()
        self.container_name = container_name
        try:
            if connection_string:
                self.service_client = BlobServiceClient.from_connection_string(connection_string)
            elif account_url:
                self.service_client = BlobServiceClient(account_url=account_url)
            else:
                raise ValueError("Azure Storage connection string or account URL must be set.")
            self.container_client = self.service_client.get_container_client(container_name)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize BlobServiceClient: {e}")

    def create_container(self) -> None:
        try:
            self.service_client.create_container(self.container_name)
        except Exception as e:
            if "ContainerAlreadyExists" not in str(e):
                raise RuntimeError(f"Failed to create container: {e}")

    def container_exists(self) -> bool:
        try:
            return self.container_client.exists()
        except Exception as e:
            raise RuntimeError(f"Failed to check if container exists: {e}")

    def upload_state(self, state_name: str, data: bytes) -> None:
        try:
            blob_client = self.container_client.get_blob_client(state_name)
            blob_client.upload_blob(data, overwrite=True)
        except Exception as e:
            raise RuntimeError(f"Failed to upload state '{state_name}': {e}")

    def download_state(self, state_name: str) -> Optional[bytes]:
        try:
            blob_client = self.container_client.get_blob_client(state_name)
            if not blob_client.exists():
                return None
            return blob_client.download_blob().readall()
        except Exception as e:
            raise RuntimeError(f"Failed to download state '{state_name}': {e}")

    def state_exists(self, state_name: str) -> bool:
        try:
            blob_client = self.container_client.get_blob_client(state_name)
            return blob_client.exists()
        except Exception as e:
            raise RuntimeError(f"Failed to check if state exists '{state_name}': {e}")

    def delete_state(self, state_name: str) -> None:
        try:
            blob_client = self.container_client.get_blob_client(state_name)
            blob_client.delete_blob()
        except Exception as e:
            raise RuntimeError(f"Failed to delete state '{state_name}': {e}")

    def list_states(self) -> List[str]:
        try:
            return [blob.name for blob in self.container_client.list_blobs()]
        except Exception as e:
            raise RuntimeError(f"Failed to list states: {e}")
