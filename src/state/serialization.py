import json
import pickle
import gzip
from typing import Any, Union

class StateSerializer:
    @staticmethod
    def serialize(obj: Any, fmt: str = "json", compress: bool = False) -> bytes:
        if fmt == "json":
            data = json.dumps(obj).encode("utf-8")
        elif fmt == "pickle":
            data = pickle.dumps(obj)
        else:
            raise ValueError(f"Unsupported serialization format: {fmt}")
        if compress:
            return gzip.compress(data)
        return data

    @staticmethod
    def deserialize(data: bytes, fmt: str = "json", compressed: bool = False) -> Any:
        if compressed:
            data = gzip.decompress(data)
        if fmt == "json":
            return json.loads(data.decode("utf-8"))
        elif fmt == "pickle":
            return pickle.loads(data)
        else:
            raise ValueError(f"Unsupported serialization format: {fmt}")

    @staticmethod
    def detect_format(data: bytes) -> str:
        try:
            json.loads(data.decode("utf-8"))
            return "json"
        except Exception:
            try:
                pickle.loads(data)
                return "pickle"
            except Exception:
                raise ValueError("Unknown serialization format.")
