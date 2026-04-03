"""Configuration Management for Azure Blob Storage State Management

Handles environment variable loading, validation, and configuration for Azure Blob Storage.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StateConfig:
    """Configuration for Azure Blob Storage state management.
    
    Supports two authentication methods:
    1. Connection string (recommended)
    2. Account name + key
    """
    
    connection_string: Optional[str] = None
    account_name: Optional[str] = None
    account_key: Optional[str] = None
    container_name: str = "workflow-state"
    
    @classmethod
    def from_env(cls) -> 'StateConfig':
        """Create configuration from environment variables.
        
        Environment variables:
        - AZURE_STORAGE_CONNECTION_STRING: Full connection string (preferred)
        - AZURE_STORAGE_ACCOUNT_NAME: Storage account name
        - AZURE_STORAGE_ACCOUNT_KEY: Storage account key
        - AZURE_STORAGE_CONTAINER_NAME: Container name (default: workflow-state)
        
        Returns:
            StateConfig instance
            
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
        container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'workflow-state')
        
        config = cls(
            connection_string=connection_string,
            account_name=account_name,
            account_key=account_key,
            container_name=container_name
        )
        
        # Validate the configuration
        config.validate()
        
        return config
    
    def validate(self) -> None:
        """Validate the configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.connection_string and not (self.account_name and self.account_key):
            raise ValueError(
                "Azure Blob Storage configuration missing. Please set either:\n"
                "1. AZURE_STORAGE_CONNECTION_STRING, or\n"
                "2. Both AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY\n\n"
                "Example connection string format:\n"
                "DefaultEndpointsProtocol=https;AccountName=myaccount;"
                "AccountKey=mykey;EndpointSuffix=core.windows.net"
            )
        
        if not self.container_name:
            raise ValueError("Container name cannot be empty")
        
        # Validate container name format (basic validation)
        if not self._is_valid_container_name(self.container_name):
            raise ValueError(
                f"Invalid container name '{self.container_name}'. "
                "Container names must be 3-63 characters long, contain only "
                "lowercase letters, numbers, and hyphens, and cannot start or end with hyphens."
            )
        
        logger.info("Azure Blob Storage configuration validated successfully")
    
    def _is_valid_container_name(self, name: str) -> bool:
        """Validate Azure Blob container name format.
        
        Args:
            name: Container name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not (3 <= len(name) <= 63):
            return False
        
        if name.startswith('-') or name.endswith('-'):
            return False
        
        if '--' in name:
            return False
        
        # Must contain only lowercase letters, numbers, and hyphens
        return all(c.islower() or c.isdigit() or c == '-' for c in name)
    
    def has_connection_string(self) -> bool:
        """Check if connection string authentication is available.
        
        Returns:
            True if connection string is configured
        """
        return bool(self.connection_string)
    
    def has_account_credentials(self) -> bool:
        """Check if account name/key authentication is available.
        
        Returns:
            True if both account name and key are configured
        """
        return bool(self.account_name and self.account_key)
    
    def get_auth_method(self) -> str:
        """Get the authentication method being used.
        
        Returns:
            String describing the auth method
        """
        if self.has_connection_string():
            return "connection_string"
        elif self.has_account_credentials():
            return "account_key"
        else:
            return "none"
    
    def __repr__(self) -> str:
        """String representation (safe - no secrets)."""
        return (
            f"StateConfig("
            f"auth_method={self.get_auth_method()}, "
            f"container_name={self.container_name}, "
            f"account_name={self.account_name if self.account_name else 'not_set'}"
            f")"
        )