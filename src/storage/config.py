import os
from typing import Optional

class Config:
    """Configuration for Azure Blob Storage environment variables."""
    @staticmethod
    def get_connection_string() -> Optional[str]:
        return os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    @staticmethod
    def get_account_name() -> Optional[str]:
        return os.getenv("AZURE_STORAGE_ACCOUNT_NAME")

    @staticmethod
    def get_account_url() -> Optional[str]:
        return os.getenv("AZURE_STORAGE_ACCOUNT_URL")
