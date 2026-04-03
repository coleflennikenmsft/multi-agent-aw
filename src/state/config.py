import os
from typing import Optional

class StateConfig:
    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "state-management")
        self._validate()

    def _validate(self):
        if not self.connection_string:
            if not (self.account_name and self.account_key):
                raise ValueError("Azure Storage configuration missing: set AZURE_STORAGE_CONNECTION_STRING or both AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY.")
        if not self.container_name:
            raise ValueError("AZURE_STORAGE_CONTAINER_NAME must be set.")

    def get_connection_string(self) -> str:
        if self.connection_string:
            return self.connection_string
        return f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"

    def get_container_name(self) -> str:
        return self.container_name
