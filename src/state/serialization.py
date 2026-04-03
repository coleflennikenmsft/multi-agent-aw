"""Serialization utilities for state management

Provides serialization and deserialization capabilities with support for multiple formats
(JSON, pickle) and optional gzip compression.
"""

import json
import pickle
import gzip
import logging
from typing import Any, Dict, Optional, Union, Tuple
from enum import Enum
import io

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    PICKLE = "pickle"


class StateSerializer:
    """State serialization and deserialization with compression support."""
    
    def __init__(self, default_format: SerializationFormat = SerializationFormat.JSON,
                 use_compression: bool = False):
        """Initialize the serializer.
        
        Args:
            default_format: Default serialization format to use
            use_compression: Whether to use gzip compression by default
        """
        self.default_format = default_format
        self.use_compression = use_compression
    
    def serialize(self, data: Any, format: Optional[SerializationFormat] = None,
                  compress: Optional[bool] = None) -> bytes:
        """Serialize data to bytes.
        
        Args:
            data: Data to serialize
            format: Serialization format (uses default if None)
            compress: Whether to compress (uses default if None)
            
        Returns:
            Serialized data as bytes
            
        Raises:
            ValueError: If serialization fails
        """
        format = format or self.default_format
        compress = compress if compress is not None else self.use_compression
        
        try:
            # Serialize to bytes
            if format == SerializationFormat.JSON:
                serialized = json.dumps(data, default=self._json_default).encode('utf-8')
            elif format == SerializationFormat.PICKLE:
                serialized = pickle.dumps(data)
            else:
                raise ValueError(f"Unsupported serialization format: {format}")
            
            # Apply compression if requested
            if compress:
                with io.BytesIO() as buffer:
                    with gzip.GzipFile(fileobj=buffer, mode='wb') as gz_file:
                        gz_file.write(serialized)
                    serialized = buffer.getvalue()
            
            logger.debug(f"Serialized data using {format.value}, compressed={compress}, size={len(serialized)} bytes")
            return serialized
            
        except Exception as e:
            logger.error(f"Failed to serialize data with format {format.value}: {e}")
            raise ValueError(f"Serialization failed: {e}")
    
    def deserialize(self, data: bytes, format: Optional[SerializationFormat] = None,
                    compressed: Optional[bool] = None) -> Any:
        """Deserialize bytes back to original data.
        
        Args:
            data: Serialized data as bytes
            format: Serialization format (auto-detected if None)
            compressed: Whether data is compressed (auto-detected if None)
            
        Returns:
            Deserialized data
            
        Raises:
            ValueError: If deserialization fails
        """
        try:
            # Auto-detect compression if not specified
            if compressed is None:
                compressed = self._is_gzip_compressed(data)
            
            # Decompress if necessary
            if compressed:
                try:
                    data = gzip.decompress(data)
                except gzip.BadGzipFile as e:
                    logger.error(f"Failed to decompress data: {e}")
                    raise ValueError(f"Invalid gzip data: {e}")
            
            # Auto-detect format if not specified
            if format is None:
                format = self._detect_format(data)
            
            # Deserialize based on format
            if format == SerializationFormat.JSON:
                result = json.loads(data.decode('utf-8'))
            elif format == SerializationFormat.PICKLE:
                result = pickle.loads(data)
            else:
                raise ValueError(f"Unsupported deserialization format: {format}")
            
            logger.debug(f"Deserialized data using {format.value}, compressed={compressed}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to deserialize data: {e}")
            raise ValueError(f"Deserialization failed: {e}")
    
    def serialize_with_metadata(self, data: Any, metadata: Optional[Dict[str, Any]] = None,
                               format: Optional[SerializationFormat] = None,
                               compress: Optional[bool] = None) -> bytes:
        """Serialize data with metadata included.
        
        Args:
            data: Data to serialize
            metadata: Additional metadata to include
            format: Serialization format (uses default if None)
            compress: Whether to compress (uses default if None)
            
        Returns:
            Serialized data with metadata as bytes
        """
        format = format or self.default_format
        metadata = metadata or {}
        
        # Create wrapper with metadata
        wrapper = {
            'data': data,
            'metadata': {
                'format': format.value,
                'compressed': compress if compress is not None else self.use_compression,
                **metadata
            }
        }
        
        return self.serialize(wrapper, format, compress)
    
    def deserialize_with_metadata(self, data: bytes) -> Tuple[Any, Dict[str, Any]]:
        """Deserialize data and extract metadata.
        
        Args:
            data: Serialized data with metadata
            
        Returns:
            Tuple of (deserialized_data, metadata)
        """
        wrapper = self.deserialize(data)
        
        if isinstance(wrapper, dict) and 'data' in wrapper and 'metadata' in wrapper:
            return wrapper['data'], wrapper['metadata']
        else:
            # Data without metadata wrapper
            return wrapper, {}
    
    def _json_default(self, obj: Any) -> Any:
        """Default JSON serialization handler for non-standard types.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serializable representation
        """
        # Handle common non-JSON-serializable types
        if hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):  # Custom objects with __dict__
            return obj.__dict__
        else:
            logger.warning(f"Cannot serialize object of type {type(obj)}: {obj}")
            return str(obj)
    
    def _is_gzip_compressed(self, data: bytes) -> bool:
        """Check if data is gzip compressed.
        
        Args:
            data: Data to check
            
        Returns:
            True if data appears to be gzip compressed
        """
        # Gzip files start with magic number 0x1f 0x8b
        return len(data) >= 2 and data[0] == 0x1f and data[1] == 0x8b
    
    def _detect_format(self, data: bytes) -> SerializationFormat:
        """Auto-detect serialization format.
        
        Args:
            data: Serialized data
            
        Returns:
            Detected format
        """
        try:
            # Try to decode as UTF-8 and parse as JSON
            decoded = data.decode('utf-8')
            json.loads(decoded)
            return SerializationFormat.JSON
        except (UnicodeDecodeError, json.JSONDecodeError):
            # If JSON parsing fails, assume it's pickle
            return SerializationFormat.PICKLE
    
    @staticmethod
    def estimate_compression_benefit(data: bytes) -> float:
        """Estimate the compression ratio for given data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Estimated compression ratio (compressed_size / original_size)
        """
        try:
            compressed = gzip.compress(data)
            ratio = len(compressed) / len(data) if len(data) > 0 else 1.0
            return ratio
        except Exception:
            return 1.0  # No compression benefit if compression fails
    
    @staticmethod
    def should_compress(data: bytes, threshold: float = 0.9) -> bool:
        """Determine if data should be compressed based on estimated benefit.
        
        Args:
            data: Data to analyze
            threshold: Compression ratio threshold (below this, compression is beneficial)
            
        Returns:
            True if compression is recommended
        """
        if len(data) < 1024:  # Don't compress small data
            return False
        
        ratio = StateSerializer.estimate_compression_benefit(data)
        return ratio < threshold