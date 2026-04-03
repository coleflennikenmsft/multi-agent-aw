"""Configuration management for Azure Blob Storage."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class StorageConfig:
    """Configuration for Azure Blob Storage connection."""
    
    connection_string: Optional[str] = None
    account_name: Optional[str] = None
    account_url: Optional[str] = None
    container_name: str = "context-states"
    
    @classmethod
    def from_environment(cls) -> "StorageConfig":
        """Create configuration from environment variables.
        
        Supports the following environment variables:
        - AZURE_STORAGE_CONNECTION_STRING: Complete connection string
        - AZURE_STORAGE_ACCOUNT_NAME: Storage account name (requires managed identity)
        - AZURE_STORAGE_ACCOUNT_URL: Storage account URL (requires managed identity)
        - AZURE_STORAGE_CONTAINER_NAME: Container name (default: context-states)
        
        Returns:
            StorageConfig: Configuration object with values from environment
            
        Raises:
            ValueError: If no valid authentication method is configured
        """
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "context-states")
        
        config = cls(
            connection_string=connection_string,
            account_name=account_name,
            account_url=account_url,
            container_name=container_name
        )
        
        # Validate that at least one authentication method is provided
        if not any([connection_string, account_name, account_url]):
            raise ValueError(
                "No Azure Storage authentication configured. Please set one of: "
                "AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_ACCOUNT_NAME, "
                "or AZURE_STORAGE_ACCOUNT_URL"
            )
        
        return config
    
    def get_account_url(self) -> Optional[str]:
        """Get the storage account URL.
        
        Returns:
            str: The account URL, either directly configured or derived from account name
        """
        if self.account_url:
            return self.account_url
        elif self.account_name:
            return f"https://{self.account_name}.blob.core.windows.net"
        return None
    
    def has_connection_string(self) -> bool:
        """Check if connection string authentication is available."""
        return bool(self.connection_string)
    
    def has_managed_identity_config(self) -> bool:
        """Check if managed identity authentication is available."""
        return bool(self.account_name or self.account_url)