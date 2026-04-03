"""Configuration management for Azure Blob Storage."""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class StorageConfig:
    """Configuration for Azure Blob Storage.
    
    Supports authentication via connection string or managed identity.
    
    Attributes:
        connection_string: Azure Storage connection string (highest priority)
        account_name: Storage account name (used with managed identity)
        account_url: Storage account URL (used with managed identity)
        container_name: Default container name for state storage
    """
    
    connection_string: Optional[str] = None
    account_name: Optional[str] = None
    account_url: Optional[str] = None
    container_name: str = "agent-state"
    
    @classmethod
    def from_environment(cls) -> "StorageConfig":
        """Load configuration from environment variables.
        
        Environment variables:
            AZURE_STORAGE_CONNECTION_STRING: Complete connection string
            AZURE_STORAGE_ACCOUNT_NAME: Storage account name
            AZURE_STORAGE_ACCOUNT_URL: Storage account URL
            AZURE_STORAGE_CONTAINER_NAME: Container name (default: agent-state)
        
        Returns:
            StorageConfig instance populated from environment
        """
        return cls(
            connection_string=os.environ.get("AZURE_STORAGE_CONNECTION_STRING"),
            account_name=os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"),
            account_url=os.environ.get("AZURE_STORAGE_ACCOUNT_URL"),
            container_name=os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "agent-state"),
        )
    
    def validate(self) -> None:
        """Validate that required configuration is present.
        
        Raises:
            ValueError: If configuration is invalid or incomplete
        """
        if not self.connection_string and not (self.account_name or self.account_url):
            raise ValueError(
                "Either AZURE_STORAGE_CONNECTION_STRING or "
                "(AZURE_STORAGE_ACCOUNT_NAME/AZURE_STORAGE_ACCOUNT_URL) must be set"
            )
        
        if not self.container_name:
            raise ValueError("Container name must be specified")
    
    def has_connection_string(self) -> bool:
        """Check if connection string is configured."""
        return bool(self.connection_string)
    
    def has_managed_identity_config(self) -> bool:
        """Check if managed identity configuration is present."""
        return bool(self.account_name or self.account_url)
